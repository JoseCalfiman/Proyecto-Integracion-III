import json
import logging
import os
from datetime import datetime, timezone

from confluent_kafka import Producer

TOPIC_ALERTS = "haccp.alerts"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

logger = logging.getLogger(__name__)


def _delivery_report(err, message):
    if err is not None:
        logger.error("Fallo al publicar en %s: %s", TOPIC_ALERTS, err)
        return
    logger.info("Evento publicado en %s [%s]", message.topic(), message.partition())


def publish_haccp_alert(alert_payload: dict) -> None:
    """Publica la alerta final HACCP en Kafka."""
    producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})

    payload = {
        "id_chamber": alert_payload.get("id_chamber"),
        "id_prediction": alert_payload.get("id_prediction"),
        "alert_type": "haccp_violation",
        "severity": alert_payload.get("severity", "warning"),
        "status": "active",
        "message": alert_payload.get("message", "Alerta HACCP generada"),
        "generation_date": alert_payload.get(
            "generation_date",
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ),
    }

    producer.produce(
        TOPIC_ALERTS,
        json.dumps(payload, default=str).encode("utf-8"),
        callback=_delivery_report,
    )
    producer.flush()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    publish_haccp_alert({
        "id_chamber": "demo-chamber",
        "id_prediction": 1,
        "severity": "warning",
        "message": "Prueba de publicación HACCP",
    })
