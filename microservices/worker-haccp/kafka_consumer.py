import json
import logging
import os
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crud import get_active_rule
from haccp_validator import validar_haccp
from kafka_producer import publish_haccp_alert
from models import AlertAudit, GeneratedAlert

TOPIC_ANOMALY = "sensor.anomaly"
TOPIC_ALERTS = "haccp.alerts"
GROUP_ID = "haccp-worker-group"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///haccp_worker.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, future=True)


def _alert_payload_from_message(payload: dict) -> dict:
    chamber_id = payload.get("id_chamber") or payload.get("chamber_id")
    if chamber_id is None:
        raise ValueError("La alerta predictiva no tiene id_chamber")
    return {
        "id_chamber": chamber_id,
        "id_prediction": payload.get("id_prediction"),
        "severity": payload.get("severity", "warning"),
        "message": payload.get("message", "Alerta HACCP detectada"),
        "generation_date": payload.get("generation_date") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _persist_generated_alert(session: Session, payload: dict, rule_id: int | None) -> GeneratedAlert:
    alert = GeneratedAlert(
        id_chamber=payload["id_chamber"],
        id_prediction=payload.get("id_prediction"),
        id_haccp_rule=rule_id,
        alert_type="haccp_violation",
        severity=payload.get("severity", "warning"),
        status="active",
        message=payload.get("message", "Alerta HACCP detectada"),
        generation_date=datetime.now(timezone.utc),
    )
    session.add(alert)
    session.flush()
    return alert


def _persist_audit(session: Session, alert_id: int, action: str, detail: str) -> None:
    audit = AlertAudit(
        id_alert=alert_id,
        id_user=None,
        action=action,
        detail=detail,
        action_date=datetime.now(timezone.utc),
    )
    session.add(audit)


def process_alert(payload: dict) -> None:
    with Session(engine) as session:
        chamber_id = payload.get("id_chamber") or payload.get("chamber_id")
        if chamber_id is None:
            logger.warning("Se ignoró un evento sin id_chamber: %s", payload)
            return

        rule = get_active_rule(session, chamber_id)
        if rule is None:
            logger.warning("No existe regla HACCP activa para la cámara %s", chamber_id)
            return

        if not validar_haccp(payload, rule):
            logger.info("Falso positivo para cámara %s: %s", chamber_id, payload)
            return

        alert_payload = _alert_payload_from_message(payload)
        alert = _persist_generated_alert(session, alert_payload, getattr(rule, "id_rule", None))
        _persist_audit(
            session,
            alert.id_alert,
            "created",
            f"Alerta HACCP validada para cámara {chamber_id}.",
        )
        session.commit()

        publish_haccp_alert({
            "id_chamber": chamber_id,
            "id_prediction": payload.get("id_prediction"),
            "severity": alert_payload["severity"],
            "message": alert_payload["message"],
            "generation_date": alert_payload["generation_date"],
        })
        logger.info("Alerta HACCP guardada para cámara %s", chamber_id)


def consume_anomalies() -> None:
    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "group.id": GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([TOPIC_ANOMALY])
    logger.info("Suscrito a %s", TOPIC_ANOMALY)

    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Error Kafka: %s", message.error())
                continue

            payload = json.loads(message.value().decode("utf-8"))
            process_alert(payload)
            consumer.commit(asynchronous=False)
    finally:
        consumer.close()


if __name__ == "__main__":
    consume_anomalies()
