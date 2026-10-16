import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID

from confluent_kafka import Consumer, KafkaError
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import (
    DataError,
    DisconnectionError,
    IntegrityError,
    InterfaceError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.orm import Session

from config import get_database_url
from crud import get_active_rule
from haccp_validator import validar_haccp
from kafka_producer import publish_haccp_alert
from models import AlertAudit, GeneratedAlert

TOPIC_ANOMALY = "sensor.anomaly"
TOPIC_ALERTS = "haccp.alerts"
GROUP_ID = "haccp-worker-group"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
ALLOWED_ALERT_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
MAX_DATABASE_ATTEMPTS = 3
DATABASE_RETRY_DELAY_SECONDS = 1

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class InvalidKafkaMessage(ValueError):
    """A permanently invalid message that should be logged and discarded."""


class TransientDatabaseError(RuntimeError):
    """A database failure exhausted its bounded retries without committing."""


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the PostgreSQL engine from the configured database settings."""
    return create_engine(get_database_url(), future=True, pool_pre_ping=True)


def _alert_payload_from_message(payload: dict) -> dict:
    chamber_id = payload.get("id_chamber") or payload.get("chamber_id")
    if chamber_id is None:
        raise InvalidKafkaMessage("El mensaje no tiene id_chamber")
    try:
        chamber_uuid = UUID(str(chamber_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidKafkaMessage(f"id_chamber inválido: {chamber_id!r}") from exc
    return {
        "id_chamber": chamber_uuid,
        "id_prediction": payload.get("id_prediction"),
        "message": payload.get("message", "Alerta HACCP detectada"),
        "generation_date": payload.get("generation_date") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _persist_generated_alert(session: Session, payload: dict, rule_id: int | None) -> GeneratedAlert:
    severity = payload["severity"]
    if severity not in ALLOWED_ALERT_SEVERITIES:
        raise ValueError(
            f"Severidad inválida para generated_alerts: {severity!r}. "
            f"Valores permitidos: {', '.join(sorted(ALLOWED_ALERT_SEVERITIES))}."
        )

    alert = GeneratedAlert(
        id_chamber=payload["id_chamber"],
        id_prediction=payload.get("id_prediction"),
        id_haccp_rule=rule_id,
        alert_type="haccp_violation",
        severity=severity,
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
    )
    session.add(audit)


def process_alert(payload: dict) -> None:
    with Session(get_engine()) as session:
        chamber_id = payload.get("id_chamber") or payload.get("chamber_id")
        if chamber_id is None:
            logger.warning("Se ignoró un evento sin id_chamber: %s", payload)
            raise InvalidKafkaMessage("El mensaje no tiene id_chamber")

        try:
            chamber_id = UUID(str(chamber_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise InvalidKafkaMessage(f"id_chamber inválido: {chamber_id!r}") from exc
        rule = get_active_rule(session, chamber_id)
        if rule is None:
            logger.warning("No existe regla HACCP activa para la cámara %s", chamber_id)
            return

        validation = validar_haccp(payload, rule)
        if not validation["is_alert"]:
            logger.info("Evento no validado para cámara %s: %s", chamber_id, validation["message"])
            return

        if rule.severity not in ALLOWED_ALERT_SEVERITIES:
            raise InvalidKafkaMessage(
                f"Severidad de regla inválida para cámara {chamber_id}: "
                f"{rule.severity!r}"
            )

        alert_payload = _alert_payload_from_message(payload)
        alert_payload["severity"] = rule.severity
        alert_payload["message"] = validation["message"]
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


def _handle_kafka_message(consumer: Consumer, message) -> None:
    try:
        payload = json.loads(message.value().decode("utf-8"))
        if not isinstance(payload, dict):
            raise InvalidKafkaMessage("El contenido del mensaje debe ser un objeto JSON")
    except (
        AttributeError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        InvalidKafkaMessage,
    ) as exc:
        logger.error("Mensaje Kafka inválido; se descarta y confirma el offset: %s", exc)
        consumer.commit(message=message, asynchronous=False)
        return

    for attempt in range(1, MAX_DATABASE_ATTEMPTS + 1):
        try:
            process_alert(payload)
        except InvalidKafkaMessage as exc:
            logger.error(
                "Mensaje inválido para la cámara %s; se descarta y confirma "
                "el offset: %s",
                payload.get("id_chamber") or payload.get("chamber_id"),
                exc,
            )
            consumer.commit(message=message, asynchronous=False)
            return
        except (IntegrityError, DataError) as exc:
            logger.error(
                "Datos rechazados por PostgreSQL para la cámara %s; "
                "se descartan y confirma el offset: %s",
                payload.get("id_chamber") or payload.get("chamber_id"),
                exc,
            )
            consumer.commit(message=message, asynchronous=False)
            return
        except (
            DisconnectionError,
            InterfaceError,
            OperationalError,
            SQLAlchemyTimeoutError,
        ) as exc:
            if attempt == MAX_DATABASE_ATTEMPTS:
                logger.exception(
                    "Falló la base de datos al procesar el mensaje tras %s "
                    "intentos; el offset queda sin confirmar",
                    MAX_DATABASE_ATTEMPTS,
                )
                raise TransientDatabaseError(
                    "Se agotaron los reintentos acotados de base de datos; "
                    "se detiene el consumidor sin confirmar el mensaje."
                ) from exc
            logger.warning(
                "Fallo transitorio de base de datos (intento %s/%s); "
                "se reintentará sin confirmar el offset: %s",
                attempt,
                MAX_DATABASE_ATTEMPTS,
                exc,
            )
            time.sleep(DATABASE_RETRY_DELAY_SECONDS * attempt)
        except SQLAlchemyError:
            logger.exception(
                "Error no transitorio de SQLAlchemy; el offset queda sin confirmar"
            )
            raise
        else:
            consumer.commit(message=message, asynchronous=False)
            return


def consume_anomalies() -> None:
    get_engine()
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

            _handle_kafka_message(consumer, message)
    finally:
        consumer.close()


if __name__ == "__main__":
    consume_anomalies()
