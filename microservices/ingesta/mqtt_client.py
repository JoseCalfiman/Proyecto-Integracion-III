import json
import os
import uuid

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from database import SessionLocal
from kafka_producer import flush as kafka_flush
from kafka_producer import publish_sensor_data
from models import Chamber, IngestionLog, SensorData
from schemas import SensorDataCreate

load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
# Usar la cuenta de lectura de Ingesta; conservar el par anterior como fallback.
MQTT_USER = os.getenv("MQTT_INGESTA_USER") or os.getenv("MQTT_USER", "")
MQTT_PASSWORD = (
    os.getenv("MQTT_INGESTA_PASSWORD", "")
    if os.getenv("MQTT_INGESTA_USER")
    else os.getenv("MQTT_PASSWORD", "")
)
MQTT_TOPIC = "sensor/raw"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

if MQTT_USER and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)


def save_sensor_data(data: dict) -> SensorDataCreate:
    reading = SensorDataCreate.model_validate(data)

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

    return reading


def _extraer_chamber_id(data: dict):
    """Obtiene el UUID usando cualquiera de los nombres aceptados del sensor."""
    if not isinstance(data, dict):
        return None
    try:
        return uuid.UUID(
            str(data.get("id_chamber") or data.get("chamber_id"))
        )
    except (TypeError, ValueError):
        return None


def log_ingestion(raw_payload: str, status: str, id_chamber=None, error_message: str = None) -> None:
    """Registra el resultado del procesamiento de un mensaje en ingestion_log."""
    db = SessionLocal()
    try:
        # El payload original conserva el ID incluso si no existe la cámara.
        # La FK del log no debe impedir registrar el motivo del rechazo.
        if id_chamber is not None and db.get(Chamber, id_chamber) is None:
            id_chamber = None
        db.add(
            IngestionLog(
                id_chamber=id_chamber,
                received_payload=raw_payload,
                processing_status=status,  
                error_message=error_message,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def procesar_payload(data: dict, raw_payload: str):
    chamber_id = _extraer_chamber_id(data)

    try:
        reading = save_sensor_data(data)
        print("Lectura guardada en la base de datos")
    except Exception as e:
        print(f"Error guardando lectura: {e}")
        log_ingestion(raw_payload, "error", id_chamber=chamber_id, error_message=str(e))
        return  

    try:
        # Publicar los mismos nombres y valores validados que se guardaron.
        publish_sensor_data(reading.model_dump(mode="json"))
    except Exception as e:
        print(f"Error publicando en Kafka: {e}")
        log_ingestion(raw_payload, "error", id_chamber=chamber_id, error_message=str(e))
        return

    log_ingestion(raw_payload, "success", id_chamber=chamber_id)


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Conectado al broker MQTT (rc={reason_code})")
    client.subscribe(MQTT_TOPIC)
    print(f"Suscrito al topico '{MQTT_TOPIC}'")


def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode("utf-8", errors="replace")
    print(f"Mensaje recibido en '{msg.topic}': {raw_payload}")

    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        print("Payload no es JSON valido, se descarta")
        log_ingestion(raw_payload, "error", error_message=f"JSON invalido: {e}")
        return

    procesar_payload(data, raw_payload)


client.on_connect = on_connect
client.on_message = on_message


def start():
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    try:
        client.loop_forever()
    finally:
        kafka_flush()  


if __name__ == "__main__":
    start()
