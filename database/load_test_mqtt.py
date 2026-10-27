#!/usr/bin/env python3
import argparse
import json
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

MQTT_TOPIC = "sensor/raw"
ID_PREFIJO = "aaaaaaaa-aaaa-4aaa-8aaa-"  # debe coincidir con load_test_camaras.sql

# (temperatura base °C, consumo base kW) según el tipo de cámara (n % 3),
# igual que el reparto del archivo SQL y del simulador.
BASES = {
    1: (-18.0, 1.8),   # congelados
    2: (2.5, 1.2),     # refrigerados
    0: (-5.0, 2.5),    # túnel de enfriamiento
}


def cargar_env():
    """Lee el .env del proyecto. Las variables ya definidas en el entorno no se sobreescriben."""
    candidatos = [
        Path(__file__).resolve().parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for ruta in candidatos:
        if ruta.is_file():
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
            return ruta
    return None


class Camara:
    """Estado de una cámara simulada (caminata aleatoria que vuelve a su valor base)."""

    def __init__(self, n):
        self.id = f"{ID_PREFIJO}{n:012d}"
        self.base_temp, self.base_kw = BASES[n % 3]
        self.temp = self.base_temp
        self.kw = self.base_kw

    def siguiente(self):
        # ±0.3 °C y ±0.15 kW por lectura, con un tirón suave hacia el valor base
        # para que una prueba larga no dispare alertas HACCP falsas.
        self.temp += random.uniform(-0.3, 0.3) + 0.1 * (self.base_temp - self.temp)
        self.kw += random.uniform(-0.15, 0.15) + 0.1 * (self.base_kw - self.kw)
        self.temp = round(min(49.9, max(-49.9, self.temp)), 2)
        self.kw = round(min(999.0, max(0.5, self.kw)), 2)
        return {
            "id_chamber": self.id,
            "temperature": self.temp,
            "consumption_kw": self.kw,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class Estadisticas:
    def __init__(self):
        self.enviados = 0
        self.errores = 0
        self._lock = threading.Lock()

    def registrar(self, ok):
        with self._lock:
            if ok:
                self.enviados += 1
            else:
                self.errores += 1

    def snapshot(self):
        with self._lock:
            return self.enviados, self.errores


def trabajar(camara, publicar, intervalo, detener):
    """Bucle de una cámara: espera un desfase aleatorio y publica cada `intervalo` segundos."""
    # El desfase evita que las 50 cámaras publiquen todas en el mismo instante.
    if detener.wait(random.uniform(0, intervalo)):
        return
    while not detener.is_set():
        publicar(camara.siguiente())
        if detener.wait(intervalo):
            break


def parsear_args():
    p = argparse.ArgumentParser(description="Prueba de carga MQTT (cámaras concurrentes)")
    p.add_argument("--camaras", type=int, default=50, help="cantidad de cámaras (1-50, default 50)")
    p.add_argument("--intervalo", type=float, default=10.0, help="segundos entre mensajes de cada cámara (default 10)")
    p.add_argument("--duracion", type=int, default=120, help="duración en segundos; 0 = hasta Ctrl+C (default 120)")
    p.add_argument("--qos", type=int, choices=(0, 1), default=0, help="QoS MQTT (default 0)")
    p.add_argument("--host", help="host del broker (default: MQTT_HOST_LOCAL o localhost)")
    p.add_argument("--port", type=int, help="puerto del broker (default: MQTT_BROKER_PORT o 1883)")
    p.add_argument("--usuario", help="usuario MQTT (default: MQTT_ESP32_USER o esp32)")
    p.add_argument("--dry-run", action="store_true", help="no conecta al broker; solo genera y muestra mensajes")
    args = p.parse_args()
    if not 1 <= args.camaras <= 50:
        p.error("--camaras debe estar entre 1 y 50 (son las que crea load_test_camaras.sql)")
    if args.intervalo <= 0:
        p.error("--intervalo debe ser mayor que 0")
    return args


def main():
    args = parsear_args()
    env = cargar_env()

    host = args.host or os.getenv("MQTT_HOST_LOCAL", "localhost")
    port = args.port or int(os.getenv("MQTT_BROKER_PORT", "1883"))
    usuario = args.usuario or os.getenv("MQTT_ESP32_USER", "esp32")
    password = os.getenv("MQTT_ESP32_PASSWORD", "1234")

    mensajes_por_seg = args.camaras / args.intervalo
    print("=" * 60)
    print("   PRUEBA DE CARGA MQTT - SMART FRIDGE MONITORING")
    print("=" * 60)
    print(f"Broker:     {'(dry-run, sin conexión)' if args.dry_run else f'{host}:{port} como {usuario!r}'}")
    print(f"Tópico:     {MQTT_TOPIC}   QoS: {args.qos}")
    print(f"Cámaras:    {args.camaras}   Intervalo: {args.intervalo}s")
    print(f"Duración:   {'hasta Ctrl+C' if args.duracion == 0 else f'{args.duracion}s'}")
    print(f"Carga:      ~{mensajes_por_seg:.1f} mensajes/s")
    print(f".env:       {env or 'no encontrado (usando valores por defecto)'}")
    print("=" * 60)

    stats = Estadisticas()
    detener = threading.Event()
    client = None

    if args.dry_run:
        muestras = {"n": 0}

        def publicar(datos):
            stats.registrar(True)
            if muestras["n"] < 3:
                muestras["n"] += 1
                print("  ejemplo:", json.dumps(datos))
    else:
        conectado = threading.Event()
        fallo = {"msg": None}

        def on_connect(c, userdata, flags, rc, properties=None):
            es_fallo = getattr(rc, "is_failure", None)
            es_fallo = es_fallo if es_fallo is not None else (rc != 0)
            if es_fallo:
                fallo["msg"] = f"El broker rechazó la conexión ({rc}). Revisa usuario/contraseña."
            conectado.set()

        if hasattr(mqtt, "CallbackAPIVersion"):
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"load-test-{random.randint(1000, 9999)}")
        else:
            client = mqtt.Client(client_id=f"load-test-{random.randint(1000, 9999)}")
        client.username_pw_set(usuario, password)
        client.on_connect = on_connect

        try:
            client.connect(host, port, 60)
        except Exception as e:
            print(f"No se pudo conectar a {host}:{port}: {e}")
            sys.exit(1)
        client.loop_start()
        if not conectado.wait(timeout=10) or fallo["msg"]:
            print(f"ERROR: {fallo['msg'] or 'el broker no respondió en 10 s.'}")
            client.loop_stop()
            sys.exit(1)
        print(f"Conectado a {host}:{port}\n")

        def publicar(datos):
            info = client.publish(MQTT_TOPIC, json.dumps(datos), qos=args.qos)
            stats.registrar(info.rc == mqtt.MQTT_ERR_SUCCESS)

    def apagar(signum, frame):
        detener.set()

    signal.signal(signal.SIGINT, apagar)
    signal.signal(signal.SIGTERM, apagar)

    # Un hilo por cámara: publican de forma concurrente, cada una a su ritmo.
    hilos = [
        threading.Thread(target=trabajar, args=(Camara(n), publicar, args.intervalo, detener), daemon=True)
        for n in range(1, args.camaras + 1)
    ]
    inicio = time.monotonic()
    for h in hilos:
        h.start()

    # Progreso cada 10 s hasta cumplir la duración o recibir Ctrl+C.
    ultimo = 0
    while not detener.is_set():
        transcurrido = time.monotonic() - inicio
        if args.duracion and transcurrido >= args.duracion:
            break
        detener.wait(min(10, max(0.1, (args.duracion - transcurrido) if args.duracion else 10)))
        env_, err_ = stats.snapshot()
        print(f"[{time.monotonic() - inicio:6.1f}s] enviados={env_} errores={err_} "
              f"(+{env_ - ultimo} desde el reporte anterior)")
        ultimo = env_

    detener.set()
    for h in hilos:
        h.join(timeout=2)
    duracion_real = time.monotonic() - inicio

    if client is not None:
        client.loop_stop()
        client.disconnect()

    enviados, errores = stats.snapshot()
    total = enviados + errores
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Cámaras:           {args.camaras}")
    print(f"Duración real:     {duracion_real:.1f} s")
    print(f"Mensajes enviados: {enviados}")
    print(f"Errores:           {errores} ({(errores / total * 100) if total else 0:.1f}%)")
    print(f"Throughput:        {enviados / duracion_real:.2f} mensajes/s")
    print("=" * 60)


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------
# Para comparar con lo que llegó a la base de datos (psql), ajustar
# el intervalo a la duración de la prueba:
#
#   SELECT count(*) AS lecturas_guardadas
#   FROM sensor_data s JOIN chambers c USING (id_chamber)
#   WHERE c.location = 'Prueba de carga'
#     AND s.insertion_date > now() - interval '5 minutes';
#
#   -- Sin JOIN a propósito: el mqtt_client.py actual deja id_chamber en NULL
#   -- en ingestion_log cuando el mensaje trae "id_chamber" (la segunda
#   -- definición de _extraer_chamber_id pisa a la primera).
#   SELECT processing_status, count(*)
#   FROM ingestion_log
#   WHERE reception_date > now() - interval '5 minutes'
#   GROUP BY 1;
# ----------------------------------------------------------------