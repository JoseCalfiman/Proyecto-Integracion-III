import json
import os

from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv()

KAFKA_BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS") or os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = "sensor.raw"
DELIVERY_TIMEOUT_MS = 10000
FLUSH_TIMEOUT_SECONDS = 11

producer = Producer({
    "bootstrap.servers": KAFKA_BROKER,
    "acks": "all",
    "enable.idempotence": True,
    "delivery.timeout.ms": DELIVERY_TIMEOUT_MS,
})


class KafkaPublishError(RuntimeError):
    """La publicación falló o no se pudo confirmar dentro del plazo."""


def delivery_report(err, msg):
    key = msg.key()
    if isinstance(key, bytes):
        key = key.decode("utf-8", errors="replace")
    context = f"topic={msg.topic()} partition={msg.partition()} key={key}"
    if err is not None:
        print(f"Error de entrega Kafka: {context} error={err}", flush=True)
    else:
        print(f"Entrega Kafka confirmada: {context} offset={msg.offset()}", flush=True)


def publish_sensor_data(data: dict) -> None:
    """Retorna solo tras la confirmación del broker; lanza error si no llega."""
    chamber_id = data.get("id_chamber") or data.get("chamber_id")
    if not chamber_id:
        raise KafkaPublishError(f"topic={KAFKA_TOPIC} partition=unknown key=None: falta id_chamber")
    key = str(chamber_id)
    context = f"topic={KAFKA_TOPIC} partition=unknown key={key}"
    delivered = False
    delivery_error = None

    def on_delivery(err, msg):
        nonlocal delivered, delivery_error, context
        context = f"topic={msg.topic()} partition={msg.partition()} key={key}"
        delivered = True
        delivery_error = err
        delivery_report(err, msg)

    try:
        value = json.dumps(data, allow_nan=False)
        producer.produce(KAFKA_TOPIC, key=key, value=value, callback=on_delivery)
        pending = producer.flush(FLUSH_TIMEOUT_SECONDS)
    except Exception as exc:
        message = f"Publicación Kafka fallida: {context} error={exc}"
        print(message, flush=True)
        raise KafkaPublishError(message) from exc

    if delivery_error is not None:
        raise KafkaPublishError(f"Entrega Kafka fallida: {context} error={delivery_error}")
    if not delivered or pending:
        message = f"Entrega Kafka sin confirmar: {context} pendientes={pending}"
        print(message, flush=True)
        raise KafkaPublishError(message)


def flush():
    """Drena al cerrar con un plazo acotado; informa si quedan mensajes."""
    pending = producer.flush(FLUSH_TIMEOUT_SECONDS)
    if pending:
        message = f"Cierre Kafka incompleto: topic={KAFKA_TOPIC} partition=unknown key=unknown pendientes={pending}"
        print(message, flush=True)
        raise KafkaPublishError(message)


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
