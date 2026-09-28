#!/usr/bin/env python3
"""
Simulador de ESP32 para Smart Fridge Monitoring.
Publica datos de 3 cámaras en MQTT cada 10 segundos.
Compatible con el broker público test.mosquitto.org.
"""

import json
import time
import random
import signal
import sys
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

# ============================================================
# CONFIGURACIÓN
# ============================================================

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_CLIENT_ID = f"python-sim-{random.randint(1000, 9999)}"
MQTT_TOPIC = "sensor/raw"

# IDs de las 3 cámaras (según el MER oficial)
CAMARAS = [
    "44444444-4444-4444-4444-444444444444",  # Cámara Principal 01
    "55555555-5555-5555-5555-555555555555",  # Cámara Principal 02
    "66666666-6666-6666-6666-666666666666",  # Túnel de Enfriamiento A
]

# Frecuencia de envío (segundos)
INTERVALO = 10

# ============================================================
# ESTADO INICIAL (simula temperatura y consumo base)
# ============================================================

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

# ============================================================
# CALLBACKS MQTT
# ============================================================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Conectado a MQTT: {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"Error de conexión MQTT. Código: {rc}")


def on_publish(client, userdata, mid):
    pass  # Silencioso para no saturar la consola


# SIMULACIÓN DE DATOS

def generar_datos(camara_id):
    """Genera datos realistas para una cámara."""
    # Variación aleatoria de temperatura (±0.3°C)
    temperaturas[camara_id] += random.uniform(-0.3, 0.3)
    # Mantener en rango realista
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
    print(f"Tópico:    {MQTT_TOPIC}")
    print(f"Cámaras:   {len(CAMARAS)}")
    print(f"Intervalo: {INTERVALO}s")
    print("=" * 60)
    print()

    # Configurar cliente MQTT
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"No se pudo conectar a {MQTT_BROKER}: {e}")
        sys.exit(1)

    client.loop_start()

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
                client.publish(MQTT_TOPIC, payload, qos=0)
                print(f"  Cámara {camara_id[:8]}: "
                      f"temp={datos['temperature']}°C, "
                      f"consumo={datos['consumption_kw']}kW")

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        handle_shutdown(None, None)


if __name__ == "__main__":
    main()