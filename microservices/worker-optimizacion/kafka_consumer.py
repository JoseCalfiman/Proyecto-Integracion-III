import json
import os
import signal
import threading
import time

from confluent_kafka import Consumer, KafkaError, KafkaException

from buffer import ReadingsBuffer, get_buffer, normalize_reading

TOPIC = os.getenv("KAFKA_TOPIC", "sensor.raw")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "worker-optimizacion")

def build_consumer():
    return Consumer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )

def process_message(raw, buffer: ReadingsBuffer | None = None) -> dict | None:
    """Parsea el payload, lo normaliza y lo agrega al buffer compartido."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, AttributeError) as exc:
        print(f"[kafka_consumer] payload invalido en sensor.raw: {exc}")
        return None

    reading = normalize_reading(data)
    if reading is None:
        print(f"[kafka_consumer] dato incompleto (sin timestamp o sin consumo/temperatura): {data}")
        return None

    target = buffer if buffer is not None else get_buffer()
    target.add(reading)
    print(f"[kafka_consumer] dato recibido desde {TOPIC}: {reading}")
    return reading


def consume(consumer, stop_event, buffer: ReadingsBuffer | None = None):
    consumer.subscribe([TOPIC])
    while not stop_event.is_set():
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        error = msg.error()
        if error:
            if error.code() == KafkaError._PARTITION_EOF:
                continue
            if error.fatal():
                raise KafkaException(error)
            print(f"[kafka_consumer] error transitorio en {TOPIC}: {error}; se reintentará")
            time.sleep(1)
            continue
        process_message(msg.value(), buffer)

def main():
    consumer = build_consumer()
    stop_event = threading.Event()

    def handle_shutdown(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        consume(consumer, stop_event)
    finally:
        print("[kafka_consumer] cerrando consumidor...")
        consumer.close()

if __name__ == "__main__":
    main()
