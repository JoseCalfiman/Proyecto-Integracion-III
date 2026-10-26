import json
import logging
import os

from confluent_kafka import Producer

TOPIC_ALERTS = "haccp.alerts"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DELIVERY_TIMEOUT_SECONDS = 10.0

logger = logging.getLogger(__name__)


class HaccpAlertPublicationError(RuntimeError):
    """Kafka did not confirm delivery of the persisted alert."""


def publish_haccp_alert(alert_payload: dict) -> None:
    """Return only after Kafka confirms delivery; propagate every delivery failure."""
    payload = {
        field: alert_payload[field]
        for field in (
            "id_alert", "id_chamber", "id_prediction", "severity", "status",
            "message", "generation_date",
        )
    }
    payload["alert_type"] = alert_payload.get("alert_type", "haccp_violation")
    delivery_confirmed = False
    delivery_error = None

    def delivery_report(err, message):
        nonlocal delivery_confirmed, delivery_error
        delivery_confirmed = True
        delivery_error = err

    try:
        producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})
        producer.produce(
            TOPIC_ALERTS,
            json.dumps(payload).encode("utf-8"),
            key=payload["id_chamber"].encode("utf-8"),
            callback=delivery_report,
        )
        pending = producer.flush(DELIVERY_TIMEOUT_SECONDS)
    except Exception as exc:
        raise HaccpAlertPublicationError(
            f"Fallo al publicar alerta {payload['id_alert']} en {TOPIC_ALERTS}"
        ) from exc

    if delivery_error is not None:
        raise HaccpAlertPublicationError(f"Error de entrega Kafka: {delivery_error}")
    if pending != 0:
        raise HaccpAlertPublicationError(
            f"Timeout de entrega Kafka: {pending} mensajes pendientes"
        )
    if not delivery_confirmed:
        raise HaccpAlertPublicationError("Kafka no confirmó la entrega de la alerta")
    logger.info("Alerta %s publicada en %s", payload["id_alert"], TOPIC_ALERTS)
