"""
Simulador de ESP32 para Smart Fridge Monitoring.
Publica datos de 3 cámaras en MQTT cada 10 segundos.
"""
import json
import os
import time
import random
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt


def cargar_env():
    """Lee el .env de la raíz del proyecto. Las variables ya definidas en el entorno no se sobreescriben."""
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


ENV_CARGADO = cargar_env()

# CONFIGURACIÓN

MQTT_BROKER = os.getenv("MQTT_HOST_LOCAL", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_ESP32_USER", "esp32")
MQTT_PASSWORD = os.getenv("MQTT_ESP32_PASSWORD", "1234")
MQTT_CLIENT_ID = f"python-sim-{random.randint(1000, 9999)}"
MQTT_TOPIC = "sensor/raw"  

# IDs de las 3 cámaras (coinciden con database/seeds.sql)
CAMARAS = [
    "44444444-4444-4444-4444-444444444444",  # Cámara Principal 01
    "55555555-5555-5555-5555-555555555555",  # Cámara Principal 02
    "66666666-6666-6666-6666-666666666666",  # Túnel de Enfriamiento A
]

# Frecuencia de envío (segundos)
INTERVALO = 10

# ESTADO INICIAL (simula temperatura y consumo base)

temperaturas = {
    CAMARAS[0]: -18.0,  # Cámara congelados
    CAMARAS[1]: 2.5,    # Cámara refrigerados
    CAMARAS[2]: -5.0,   # Túnel de enfriamiento
}

consumos = {
    CAMARAS[0]: 1.8,
    CAMARAS[1]: 1.2,
    CAMARAS[2]: 2.5,
}

conectado = threading.Event()
error_conexion = {"mensaje": None}


def on_connect(client, userdata, flags, rc, properties=None):
    fallo = getattr(rc, "is_failure", None)
    fallo = fallo if fallo is not None else (rc != 0)
    if not fallo:
        print(f"Conectado a MQTT: {MQTT_BROKER}:{MQTT_PORT} como '{MQTT_USER}'")
    else:
        error_conexion["mensaje"] = (
            f"El broker rechazó la conexión ({rc}). "
            "Revisa MQTT_ESP32_USER / MQTT_ESP32_PASSWORD y mosquitto/pwfile."
        )
    conectado.set()


def on_publish(client, userdata, *args):
    pass  


# SIMULACIÓN DE DATOS

def generar_datos(camara_id):
    """Genera datos realistas para una cámara."""
    temperaturas[camara_id] += random.uniform(-0.3, 0.3)
    temperaturas[camara_id] = round(temperaturas[camara_id], 2)

    # Variación aleatoria de consumo (±0.15 kW)
    consumos[camara_id] += random.uniform(-0.15, 0.15)
    consumos[camara_id] = round(max(0.5, consumos[camara_id]), 2)

    return {
        "id_chamber": camara_id,
        "temperature": temperaturas[camara_id],
        "consumption_kw": consumos[camara_id],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("   SIMULADOR ESP32 - SMART FRIDGE MONITORING")
    print("=" * 60)
    print(f"Broker:    {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Usuario:   {MQTT_USER}")
    print(f"Tópico:    {MQTT_TOPIC}")
    print(f"Cámaras:   {len(CAMARAS)}")
    print(f"Intervalo: {INTERVALO}s")
    print(f".env:      {ENV_CARGADO or 'no encontrado (usando valores por defecto)'}")
    print("=" * 60)
    print()

    # Configurar cliente MQTT 
    if hasattr(mqtt, "CallbackAPIVersion"):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=MQTT_CLIENT_ID)
    else:
        client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"No se pudo conectar a {MQTT_BROKER}:{MQTT_PORT}: {e}")
        print("¿Está corriendo el contenedor 'mosquitto'? (docker compose ps)")
        sys.exit(1)

    client.loop_start()

    # Esperar la respuesta del broker antes de publicar
    if not conectado.wait(timeout=10):
        print("ERROR: el broker no respondió en 10 s.")
        client.loop_stop()
        sys.exit(1)
    if error_conexion["mensaje"]:
        print(f"ERROR: {error_conexion['mensaje']}")
        client.loop_stop()
        sys.exit(1)

    # Manejar Ctrl+C
    def handle_shutdown(signum, frame):
        print("\n\nDeteniendo simulador...")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Bucle principal
    ciclo = 0
    try:
        while True:
            ciclo += 1
            print(f"\n--- Ciclo #{ciclo} ---")

            for camara_id in CAMARAS:
                datos = generar_datos(camara_id)
                payload = json.dumps(datos)
                info = client.publish(MQTT_TOPIC, payload, qos=0)
                estado = "OK" if info.rc == mqtt.MQTT_ERR_SUCCESS else f"ERROR rc={info.rc}"
                print(f"  Cámara {camara_id[:8]}: "
                      f"temp={datos['temperature']}°C, "
                      f"consumo={datos['consumption_kw']}kW [{estado}]")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        handle_shutdown(None, None)


if __name__ == "__main__":
    main()