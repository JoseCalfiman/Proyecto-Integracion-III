import json
import os

import paho.mqtt.client as mqtt

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = "sensor/raw"

client = mqtt.Client()

if MQTT_USER and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


def on_connect(client, userdata, flags, rc):
    print(f"Conectado al broker MQTT (rc={rc})")
    client.subscribe(MQTT_TOPIC)
    print(f"Suscrito al tópico '{MQTT_TOPIC}'")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"Mensaje recibido en '{msg.topic}': {payload}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("Payload no es JSON válido, se descarta")
        return

    # Acá va la lógica de procesamiento del payload
    procesar_payload(data)


def procesar_payload(data: dict):
    """Ajustá esta función según la estructura real de los datos del sensor."""
    print(f"Payload procesado: {data}")


client.on_connect = on_connect
client.on_message = on_message


def start():
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    start()