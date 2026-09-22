"""
Publica datos falsos de temperatura y consumo
eléctrico por MQTT cada 10 segundos
"""
import os
import json
import random
import time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()
BROKER_HOST = os.getenv("MQTT_HOST_LOCAL", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_ESP32_USER", "esp32")
MQTT_PASSWORD = os.getenv("MQTT_ESP32_PASSWORD", "1234")

TOPIC = "sensor/raw"          
INTERVALO = 10
CAMARAS = 3

camaras_estado = {
    camara_id: {
        "temperatura": round(random.uniform(2.0, 5.0), 2),
        "consumo_kw": round(random.uniform(0.8, 2.5), 2),
    }
    for camara_id in range(1, CAMARAS + 1)
}

def simular_siguiente_lectura(camara_id: int) -> dict:
    estado = camaras_estado[camara_id]
    estado["temperatura"] = round(estado["temperatura"] + random.uniform(-0.3, 0.3), 2)
    estado["consumo_kw"] = round(max(0.1, estado["consumo_kw"] + random.uniform(-0.1, 0.1)), 2)

    return {
        "camara_id": camara_id,
        "temperatura": estado["temperatura"],
        "consumo_kw": estado["consumo_kw"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"Conectado al broker MQTT en {BROKER_HOST}:{BROKER_PORT} como {MQTT_USER}")
    else:
        print(f"No se pudo conectar {reason_code}")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="simuladorESP32")
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()
    print(f"Publicando datos falsos en '{TOPIC}' cada {INTERVALO} segundos\n")

    try:
        while True:
            for camara_id in camaras_estado:
                payload = simular_siguiente_lectura(camara_id)
                client.publish(TOPIC, json.dumps(payload), qos=0)
                print(f"Publicado: {payload}")
            time.sleep(INTERVALO)
    except KeyboardInterrupt:
        print("\nDetenido")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()