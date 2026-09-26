from __future__ import annotations

import logging
import signal
import threading

from buffer import get_buffer
from kafka_consumer import build_consumer, consume
from scheduler import build_scheduler

logger = logging.getLogger(__name__)


def main() -> None:
    """Proceso unico: consumer de Kafka alimenta el buffer y el scheduler optimiza."""
    logging.basicConfig(level=logging.INFO)
    buffer = get_buffer()
    stop_event = threading.Event()

    consumer = build_consumer()
    consumer_thread = threading.Thread(
        target=consume,
        args=(consumer, stop_event, buffer),
        name="kafka-consumer",
        daemon=True,
    )
    consumer_thread.start()
    logger.info("[main] consumer de Kafka iniciado")

    scheduler = build_scheduler(buffer)
    scheduler.start()
    logger.info("[main] scheduler iniciado")

    def handle_shutdown(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        while not stop_event.is_set():
            stop_event.wait(1.0)
    except (KeyboardInterrupt, SystemExit):
        stop_event.set()
    finally:
        scheduler.shutdown(wait=False)
        consumer.close()
        logger.info("[main] worker-optimizacion detenido")


if __name__ == "__main__":
    main()
