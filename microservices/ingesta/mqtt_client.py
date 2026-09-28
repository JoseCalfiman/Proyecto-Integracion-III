import json
import os

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from database import SessionLocal
from models import SensorData
from schemas import SensorDataCreate

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = "sensor/raw"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

if MQTT_USER and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


def save_sensor_data(data: dict) -> None:
    """Valida el payload y lo inserta en la hipertabla sensor_data."""
    reading = SensorDataCreate(**data)  # lanza ValidationError si el payload es invalido

    db = SessionLocal()
    try:
        db.add(
            SensorData(
            id_chamber=reading.id_chamber,
            timestamp=reading.timestamp,
            temperature=reading.temperature,
            consumption_kw=reading.consumption_kw,
        )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def procesar_payload(data: dict):
    try:
        save_sensor_data(data)
        print("Lectura guardada en la base de datos")
    except Exception as e:
        print(f"Error guardando lectura: {e}")


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Conectado al broker MQTT (rc={reason_code})")
    client.subscribe(MQTT_TOPIC)
    print(f"Suscrito al topico '{MQTT_TOPIC}'")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"Mensaje recibido en '{msg.topic}': {payload}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("Payload no es JSON valido, se descarta")
        return

    procesar_payload(data)


client.on_connect = on_connect
client.on_message = on_message


def start():
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    start()