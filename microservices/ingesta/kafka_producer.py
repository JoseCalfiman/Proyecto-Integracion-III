import json
import os

from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = "sensor.raw"

producer = Producer({"bootstrap.servers": KAFKA_BROKER})


def delivery_report(err, msg):
    if err is not None:
        print(f"Error publicando en Kafka: {err}")
    else:
        print(f"Publicado en {msg.topic()} [partition {msg.partition()}] key={msg.key()}")


def publish_sensor_data(data: dict) -> None:
    """Publica una lectura de sensor en el tópico sensor.raw, usando chamber_id como key."""
    key = str(data["chamber_id"])
    value = json.dumps(data)

    producer.produce(KAFKA_TOPIC, key=key, value=value, callback=delivery_report)
    producer.poll(0)  # dispara el callback de mensajes ya entregados


def flush():
    """Espera a que se envíen los mensajes pendientes. Llamar al cerrar el servicio."""
    producer.flush()


if __name__ == "__main__":
    # Prueba rápida
    ejemplo = {
        "chamber_id": "22222222-2222-2222-2222-222222222222",
        "temperature": -18.5,
        "consumption_kw": 2.34,
        "recorded_at": "2026-09-28T21:00:00+00:00",
    }
    publish_sensor_data(ejemplo)
    flush()