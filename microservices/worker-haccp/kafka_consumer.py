import json
import logging
import math
import os
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from functools import lru_cache
from threading import Event, Thread
from uuid import UUID

from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient
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
from crud import DEFAULT_RULE_VALUES, get_active_rule
from haccp_validator import (
    HaccpRuleConfigurationError,
    evaluate_predictive_event,
)
from health import HealthHTTPServer, WorkerHealth, create_health_handler
from kafka_producer import publish_haccp_alert
from models import AlertAudit, GeneratedAlert

TOPIC_ANOMALY = "sensor.anomaly"
TOPIC_ALERTS = "haccp.alerts"
GROUP_ID = "haccp-worker-group"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
ALLOWED_ALERT_SEVERITIES = frozenset({"low", "medium", "high", "critical"})
ALLOWED_RISK_LEVELS = frozenset({"SIN_RIESGO", "CRITICO", "ALTO", "MEDIO", "BAJO"})
MAX_BIGINT = 2**63 - 1
MAX_DATABASE_ATTEMPTS = 3
DATABASE_RETRY_DELAY_SECONDS = 1
HEALTH_PORT_ENV = "HEALTH_PORT"
DEFAULT_HEALTH_PORT = 8080
KAFKA_HEALTH_CHECK_INTERVAL_SECONDS = 5
KAFKA_HEALTH_CHECK_TIMEOUT_SECONDS = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class InvalidKafkaMessage(ValueError):
    """A permanently invalid message that should be logged and discarded."""


class TransientDatabaseError(RuntimeError):
    """A database failure exhausted its bounded retries without committing."""


class KafkaOffsetCommitError(RuntimeError):
    """A synchronous Kafka offset commit did not confirm the message offset."""


def _commit_message_offset(consumer: Consumer, message) -> None:
    try:
        committed_offsets = consumer.commit(message=message, asynchronous=False)
    except KafkaException:
        logger.exception("Falló la confirmación síncrona del offset Kafka")
        raise

    if not committed_offsets:
        raise KafkaOffsetCommitError(
            "Kafka no devolvió confirmación para el offset del mensaje"
        )

    expected_topic = message.topic()
    expected_partition = message.partition()
    expected_offset = message.offset() + 1
    matching_offset = False
    for committed in committed_offsets:
        if committed.error is not None:
            raise KafkaOffsetCommitError(
                f"Kafka rechazó la confirmación del offset: {committed.error}"
            )
        if (
            committed.topic == expected_topic
            and committed.partition == expected_partition
            and committed.offset == expected_offset
        ):
            matching_offset = True

    if not matching_offset:
        raise KafkaOffsetCommitError(
            "Kafka no confirmó el offset esperado del mensaje"
        )


def _validate_anomaly_contract(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise InvalidKafkaMessage("El contenido del mensaje debe ser un objeto JSON")

    if "id_chamber" in payload:
        chamber_id = payload["id_chamber"]
    elif "chamber_id" in payload:
        chamber_id = payload["chamber_id"]
    else:
        raise InvalidKafkaMessage("Falta el campo obligatorio id_chamber")
    try:
        chamber_uuid = UUID(str(chamber_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidKafkaMessage("El campo id_chamber debe ser un UUID válido") from exc

    if "chamber_id" in payload:
        try:
            alias_uuid = UUID(str(payload["chamber_id"]))
        except (TypeError, ValueError, AttributeError) as exc:
            raise InvalidKafkaMessage(
                "El campo chamber_id debe ser un UUID válido"
            ) from exc
        if alias_uuid != chamber_uuid:
            raise InvalidKafkaMessage(
                "Los campos id_chamber y chamber_id identifican cámaras distintas"
            )

    prediction_id = payload.get("id_prediction")
    if (
        type(prediction_id) is not int
        or prediction_id <= 0
        or prediction_id > MAX_BIGINT
    ):
        raise InvalidKafkaMessage(
            "El campo id_prediction debe ser un BIGINT positivo"
        )

    normalized = payload.copy()
    normalized["id_chamber"] = chamber_uuid

    for field in ("temperature", "remaining_time_min"):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidKafkaMessage(f"El campo {field} debe ser un número finito")
        try:
            number = float(value)
        except (OverflowError, TypeError, ValueError) as exc:
            raise InvalidKafkaMessage(
                f"El campo {field} debe ser un número finito"
            ) from exc
        if not math.isfinite(number):
            raise InvalidKafkaMessage(f"El campo {field} debe ser un número finito")
        if field == "remaining_time_min" and number < 0:
            raise InvalidKafkaMessage(
                "El campo remaining_time_min no puede ser negativo"
            )
        normalized[field] = number

    severity = payload.get("severity")
    if not isinstance(severity, str):
        raise InvalidKafkaMessage(
            "El campo severity debe ser uno de: "
            + ", ".join(sorted(ALLOWED_ALERT_SEVERITIES))
        )
    severity = severity.strip().lower()
    if severity not in ALLOWED_ALERT_SEVERITIES:
        raise InvalidKafkaMessage(
            "El campo severity debe ser uno de: "
            + ", ".join(sorted(ALLOWED_ALERT_SEVERITIES))
        )
    normalized["severity"] = severity

    risk_level = payload.get("risk_level")
    if not isinstance(risk_level, str):
        raise InvalidKafkaMessage(
            "El campo risk_level no coincide con las categorías del predictor"
        )
    risk_level = risk_level.strip().upper()
    if risk_level not in ALLOWED_RISK_LEVELS:
        raise InvalidKafkaMessage(
            "El campo risk_level no coincide con las categorías del predictor"
        )
    normalized["risk_level"] = risk_level

    recorded_at = payload.get("recorded_at")
    if not isinstance(recorded_at, str):
        raise InvalidKafkaMessage(
            "El campo recorded_at debe ser una fecha y hora ISO 8601"
        )
    recorded_at = recorded_at.strip()
    if "T" not in recorded_at.upper():
        raise InvalidKafkaMessage(
            "El campo recorded_at debe ser una fecha y hora ISO 8601"
        )
    try:
        parsed_recorded_at = datetime.fromisoformat(
            recorded_at[:-1] + "+00:00"
            if recorded_at.endswith("Z")
            else recorded_at
        )
    except (OverflowError, ValueError) as exc:
        raise InvalidKafkaMessage(
            "El campo recorded_at debe ser una fecha y hora ISO 8601 válida"
        ) from exc
    normalized["recorded_at"] = parsed_recorded_at.isoformat()
    return normalized


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
    payload = _validate_anomaly_contract(payload)
    chamber_id = payload["id_chamber"]
    with Session(get_engine()) as session:
        rule = get_active_rule(session, chamber_id)
        if rule is None:
            logger.warning(
                "No existe regla HACCP activa para la cámara %s; "
                "se utiliza la regla predeterminada",
                chamber_id,
            )
            rule = DEFAULT_RULE_VALUES.copy()

        rule_severity = (
            rule.get("severity")
            if isinstance(rule, Mapping)
            else getattr(rule, "severity", None)
        )
        if (
            not isinstance(rule_severity, str)
            or rule_severity not in ALLOWED_ALERT_SEVERITIES
        ):
            raise HaccpRuleConfigurationError(
                f"Severidad de regla HACCP inválida para cámara {chamber_id}: "
                f"{rule_severity!r}"
            )

        validation = evaluate_predictive_event(payload, rule)
        if not validation["is_alert"]:
            logger.info(
                "Evento sensor.anomaly válido sin infracciones HACCP para "
                "la cámara %s: %s",
                chamber_id,
                validation["message"],
            )
            return

        alert_payload = _alert_payload_from_message(payload)
        alert_payload["severity"] = rule_severity
        alert_payload["message"] = validation["message"]
        alert = _persist_generated_alert(session, alert_payload, getattr(rule, "id_rule", None))
        _persist_audit(
            session,
            alert.id_alert,
            "created",
            f"Alerta HACCP validada para cámara {chamber_id}.",
        )
        # Snapshot flushed values before commit expires the ORM instance.
        publication_payload = {
            "id_alert": alert.id_alert,
            "id_chamber": str(alert.id_chamber),
            "id_prediction": alert.id_prediction,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "status": alert.status,
            "message": alert.message,
            "generation_date": alert.generation_date.astimezone(timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        }
        session.commit()

        # Publication errors propagate: the source offset must remain uncommitted.
        publish_haccp_alert(publication_payload)
        logger.info("Alerta HACCP guardada para cámara %s", chamber_id)


def _handle_kafka_message(consumer: Consumer, message) -> bool:
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
        logger.warning("Mensaje Kafka inválido; se descarta y confirma el offset: %s", exc)
        _commit_message_offset(consumer, message)
        return False

    for attempt in range(1, MAX_DATABASE_ATTEMPTS + 1):
        try:
            process_alert(payload)
        except InvalidKafkaMessage as exc:
            logger.warning(
                "Mensaje inválido para la cámara %s; se descarta y confirma "
                "el offset: %s",
                payload.get("id_chamber") or payload.get("chamber_id"),
                exc,
            )
            _commit_message_offset(consumer, message)
            return False
        except HaccpRuleConfigurationError as exc:
            logger.error(
                "Configuración inválida de regla HACCP para la cámara %s; "
                "el offset queda sin confirmar y el procesamiento se detiene: %s",
                payload.get("id_chamber") or payload.get("chamber_id"),
                exc,
            )
            raise
        except (IntegrityError, DataError) as exc:
            logger.error(
                "Datos rechazados por PostgreSQL para la cámara %s; "
                "se descartan y confirma el offset: %s",
                payload.get("id_chamber") or payload.get("chamber_id"),
                exc,
            )
            _commit_message_offset(consumer, message)
            return False
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
            _commit_message_offset(consumer, message)
            return True


def consume_anomalies(
    health: WorkerHealth | None = None,
    stop_event: Event | None = None,
) -> None:
    health = health or WorkerHealth()
    stop_event = stop_event or Event()
    consumer = None
    try:
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
        health.set_consumer_operational(True)
        logger.info("Suscrito a %s", TOPIC_ANOMALY)

        while not stop_event.is_set():
            message = consumer.poll(1.0)
            if message is None:
                health.set_consumer_poll_error(False)
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    health.set_consumer_poll_error(False)
                    continue
                logger.error("Error Kafka: %s", message.error())
                health.set_consumer_poll_error(True)
                health.set_kafka_connected(False)
                continue

            health.set_consumer_poll_error(False)
            if _handle_kafka_message(consumer, message):
                health.mark_processed()
    finally:
        health.mark_stopped()
        if consumer is not None:
            consumer.close()


def _monitor_kafka_health(health: WorkerHealth, stop_event: Event) -> None:
    admin_client = None
    while not stop_event.is_set():
        try:
            if admin_client is None:
                admin_client = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
            admin_client.list_topics(timeout=KAFKA_HEALTH_CHECK_TIMEOUT_SECONDS)
        except Exception:
            health.set_kafka_connected(False)
            logger.warning("No se pudo comprobar la conectividad con Kafka", exc_info=True)
            admin_client = None
        else:
            health.set_kafka_connected(True)
        stop_event.wait(KAFKA_HEALTH_CHECK_INTERVAL_SECONDS)


def run_worker() -> None:
    health = WorkerHealth()
    stop_event = Event()
    try:
        port = int(os.getenv(HEALTH_PORT_ENV, str(DEFAULT_HEALTH_PORT)))
    except ValueError as exc:
        raise RuntimeError(f"{HEALTH_PORT_ENV} debe ser un puerto entero") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(f"{HEALTH_PORT_ENV} debe estar entre 1 y 65535")

    server = HealthHTTPServer(
        ("0.0.0.0", port),
        create_health_handler(health),
    )
    http_thread = Thread(target=server.serve_forever, name="health-http", daemon=True)
    kafka_health_thread = Thread(
        target=_monitor_kafka_health,
        args=(health, stop_event),
        name="kafka-health",
        daemon=True,
    )
    try:
        http_thread.start()
        kafka_health_thread.start()
        consume_anomalies(health, stop_event)
    finally:
        stop_event.set()
        health.mark_stopped()
        server.shutdown()
        server.server_close()
        http_thread.join(timeout=2)
        kafka_health_thread.join(timeout=KAFKA_HEALTH_CHECK_TIMEOUT_SECONDS + 1)


if __name__ == "__main__":
    run_worker()
