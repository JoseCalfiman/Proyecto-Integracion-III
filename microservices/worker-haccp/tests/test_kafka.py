import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Uuid,
    UniqueConstraint,
    create_engine,
    inspect,
    select,
    update,
)
from sqlalchemy.orm import Session

import kafka_consumer
from kafka_consumer import (
    InvalidKafkaMessage,
    TransientDatabaseError,
    _handle_kafka_message,
    _persist_generated_alert,
)
from models import AlertAudit, Base, Chamber, GeneratedAlert, HaccpRule, Prediction, User


CHAMBER_ID = "44444444-4444-4444-4444-444444444444"


def valid_anomaly_payload(**overrides):
    payload = {
        "id_chamber": CHAMBER_ID,
        "id_prediction": 17,
        "temperature": 5.0,
        "remaining_time_min": 10.0,
        "severity": "critical",
        "risk_level": "MEDIO",
        "recorded_at": "2025-01-02T03:04:05+00:00",
    }
    payload.update(overrides)
    return payload


def test_shared_table_identifiers_match_postgresql_types():
    uuid_columns = (
        Chamber.id_chamber,
        User.id_user,
        HaccpRule.id_chamber,
        HaccpRule.id_user_modified,
        GeneratedAlert.id_chamber,
        GeneratedAlert.id_user_acknowledged,
        GeneratedAlert.id_user_resolved,
        AlertAudit.id_user,
    )
    bigint_columns = (
        HaccpRule.id_rule,
        Prediction.id_prediction,
        GeneratedAlert.id_alert,
        GeneratedAlert.id_prediction,
        GeneratedAlert.id_haccp_rule,
        AlertAudit.id_audit,
        AlertAudit.id_alert,
    )

    assert all(isinstance(column.property.columns[0].type, Uuid) for column in uuid_columns)
    assert all(
        isinstance(column.property.columns[0].type, BigInteger)
        for column in bigint_columns
    )
    assert not any(
        isinstance(constraint, UniqueConstraint)
        for constraint in HaccpRule.__table__.constraints
    )


def test_shared_table_check_constraints_match_postgresql_schema():
    constraints = {
        table.name: {
            constraint.sqltext.text
            for constraint in table.constraints
            if isinstance(constraint, CheckConstraint)
        }
        for table in (HaccpRule.__table__, GeneratedAlert.__table__)
    }

    assert constraints["haccp_rules"] == {
        "severity IN ('low', 'medium', 'high', 'critical')"
    }
    assert constraints["generated_alerts"] == {
        "severity IN ('low', 'medium', 'high', 'critical')",
        "status IN ('active', 'acknowledged', 'resolved')",
    }
    assert HaccpRule.__table__.c.severity.nullable
    assert not GeneratedAlert.__table__.c.severity.nullable
    assert not GeneratedAlert.__table__.c.status.nullable


def test_alert_audit_table_has_requested_columns():
    engine = create_engine("sqlite://")

    AlertAudit.__table__.create(bind=engine, checkfirst=True)

    assert inspect(engine).get_table_names() == ["alert_audit"]
    assert {column["name"] for column in inspect(engine).get_columns("alert_audit")} == {
        "id_audit",
        "id_alert",
        "id_user",
        "action",
        "detail",
        "action_date",
    }


def test_generated_alert_is_persisted_with_requested_columns():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID("44444444-4444-4444-4444-444444444444")
    payload = {
        "id_chamber": chamber_id,
        "id_prediction": 17,
        "severity": "critical",
        "message": "Temperatura fuera de rango",
    }

    with Session(engine) as session:
        alert = _persist_generated_alert(session, payload, rule_id=5)
        session.commit()
        saved_alert = session.scalar(
            select(GeneratedAlert).where(GeneratedAlert.id_alert == alert.id_alert)
        )

    assert saved_alert is not None
    assert saved_alert.id_chamber == chamber_id
    assert saved_alert.id_prediction == 17
    assert saved_alert.id_haccp_rule == 5
    assert saved_alert.alert_type == "haccp_violation"
    assert saved_alert.severity == "critical"
    assert saved_alert.status == "active"
    assert saved_alert.message == "Temperatura fuera de rango"
    assert saved_alert.generation_date is not None
    assert {column["name"] for column in inspect(engine).get_columns("generated_alerts")} == {
        "id_alert",
        "id_chamber",
        "id_prediction",
        "id_haccp_rule",
        "alert_type",
        "severity",
        "status",
        "message",
        "generation_date",
        "id_user_acknowledged",
        "acknowledgment_date",
        "id_user_resolved",
        "resolution_date",
    }


def test_generated_alert_rejects_severity_outside_postgres_check():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    payload = {
        "id_chamber": UUID("44444444-4444-4444-4444-444444444444"),
        "severity": "warning",
    }

    with Session(engine) as session:
        with pytest.raises(ValueError, match="Severidad inválida"):
            _persist_generated_alert(session, payload, rule_id=None)


def test_process_alert_persists_rule_configured_severity(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID("44444444-4444-4444-4444-444444444444")
    with Session(engine) as session:
        rule = HaccpRule(
            id_chamber=chamber_id,
            active=True,
            severity="high",
            max_absolute_temp=4,
            min_absolute_temp=-30,
            tolerance_time_min=15,
        )
        session.add(rule)
        session.commit()
        rule_id = rule.id_rule

    published = []
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    monkeypatch.setattr(
        kafka_consumer,
        "publish_haccp_alert",
        lambda payload: published.append(payload),
    )

    kafka_consumer.process_alert(
        valid_anomaly_payload(
            id_chamber=str(chamber_id),
            temperature_c=5,
            duration_seconds=900,
        )
    )

    with Session(engine) as session:
        saved_alert = session.scalar(select(GeneratedAlert))

    assert saved_alert is not None
    assert saved_alert.id_haccp_rule == rule_id
    assert saved_alert.severity == "high"
    assert published[0]["severity"] == "high"


def test_process_alert_rejects_null_rule_severity_as_invalid(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID("44444444-4444-4444-4444-444444444444")
    with Session(engine) as session:
        session.add(
            HaccpRule(
                id_chamber=chamber_id,
                active=True,
                severity="medium",
                max_absolute_temp=4,
                min_absolute_temp=-30,
                tolerance_time_min=15,
            )
        )
        session.commit()
        session.execute(
            update(HaccpRule)
            .where(HaccpRule.id_chamber == chamber_id)
            .values(severity=None)
        )
        session.commit()

    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)

    consumer = FakeKafkaConsumer()
    kafka_consumer._handle_kafka_message(
        consumer,
        FakeKafkaMessage(
            json.dumps(
                valid_anomaly_payload(
                    id_chamber=str(chamber_id),
                    temperature_c=5,
                    duration_seconds=900,
                )
            ).encode("utf-8"),
            20,
        ),
    )

    assert consumer.committed_offsets == [20]
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None


class FakeKafkaMessage:
    def __init__(self, value, offset):
        self._value = value
        self._offset = offset

    def error(self):
        return None

    def value(self):
        return self._value

    def offset(self):
        return self._offset


class FakeKafkaConsumer:
    def __init__(self):
        self.committed_offsets = []

    def commit(self, message, asynchronous):
        self.committed_offsets.append(message.offset())


def test_invalid_message_is_logged_discarded_and_offset_confirmed(monkeypatch, caplog):
    consumer = FakeKafkaConsumer()

    def process(payload):
        if payload["id_chamber"] == "invalid":
            raise InvalidKafkaMessage("id_chamber inválido")

    monkeypatch.setattr(kafka_consumer, "process_alert", process)

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(b'{"id_chamber": "invalid"}', 21),
    )
    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(b'{"id_chamber": "valid"}', 22),
    )

    assert consumer.committed_offsets == [21, 22]
    assert "se descarta y confirma" in caplog.text


def test_malformed_json_is_logged_and_offset_confirmed(caplog):
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(consumer, FakeKafkaMessage(b"{invalid json", 23))

    assert consumer.committed_offsets == [23]
    assert "se descarta y confirma" in caplog.text


def test_transient_database_failure_does_not_confirm_offset(monkeypatch):
    consumer = FakeKafkaConsumer()
    monkeypatch.setattr(kafka_consumer, "MAX_DATABASE_ATTEMPTS", 2)
    monkeypatch.setattr(kafka_consumer, "DATABASE_RETRY_DELAY_SECONDS", 0)
    attempts = []

    def fail_database(payload):
        attempts.append(payload)
        raise kafka_consumer.OperationalError(
            "database unavailable", {}, Exception("connection refused")
        )

    monkeypatch.setattr(kafka_consumer, "process_alert", fail_database)

    with pytest.raises(TransientDatabaseError, match="sin confirmar el mensaje"):
        _handle_kafka_message(
            consumer,
            FakeKafkaMessage(b'{"id_chamber": "valid"}', 24),
        )

    assert len(attempts) == 2
    assert consumer.committed_offsets == []


def test_valid_anomaly_contract_is_accepted_and_committed(monkeypatch):
    consumer = FakeKafkaConsumer()
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: create_engine("sqlite://"))
    monkeypatch.setattr(kafka_consumer, "get_active_rule", lambda session, chamber_id: None)

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(valid_anomaly_payload()).encode("utf-8"), 25),
    )

    assert consumer.committed_offsets == [25]


@pytest.mark.parametrize(
    "payload",
    [
        valid_anomaly_payload(),
        valid_anomaly_payload(
            id_chamber=None,
            chamber_id=CHAMBER_ID,
        ),
    ],
)
def test_contract_normalizes_canonical_or_alias_chamber_id(payload):
    if payload["id_chamber"] is None:
        payload.pop("id_chamber")

    normalized = kafka_consumer._validate_anomaly_contract(payload)

    assert normalized["id_chamber"] == UUID(CHAMBER_ID)


def test_contract_accepts_matching_chamber_aliases():
    payload = valid_anomaly_payload(chamber_id=CHAMBER_ID)

    normalized = kafka_consumer._validate_anomaly_contract(payload)

    assert normalized["id_chamber"] == UUID(CHAMBER_ID)


@pytest.mark.parametrize(
    ("canonical_id", "alias_id", "expected_reason"),
    [
        ("not-a-uuid", CHAMBER_ID, "id_chamber"),
        (CHAMBER_ID, "not-a-uuid", "chamber_id"),
        (
            CHAMBER_ID,
            "55555555-5555-5555-5555-555555555555",
            "cámaras distintas",
        ),
    ],
)
def test_conflicting_or_invalid_chamber_alias_is_rejected_and_logged(
    canonical_id, alias_id, expected_reason, caplog
):
    payload = valid_anomaly_payload(
        id_chamber=canonical_id,
        chamber_id=alias_id,
    )
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(payload).encode("utf-8"), 29),
    )

    assert consumer.committed_offsets == [29]
    assert expected_reason in caplog.text
    assert "se descarta y confirma" in caplog.text


def test_contract_rejects_when_both_chamber_identifiers_are_missing():
    payload = valid_anomaly_payload()

    payload.pop("id_chamber")
    payload.pop("chamber_id", None)

    with pytest.raises(InvalidKafkaMessage, match="id_chamber"):
        kafka_consumer._validate_anomaly_contract(payload)


@pytest.mark.parametrize(
    "field",
    [
        "id_chamber",
        "id_prediction",
        "temperature",
        "remaining_time_min",
        "severity",
        "risk_level",
        "recorded_at",
    ],
)
def test_missing_required_contract_field_is_logged_and_committed(field, caplog):
    payload = valid_anomaly_payload()
    payload.pop(field)
    if field == "id_chamber":
        payload.pop("chamber_id", None)

    consumer = FakeKafkaConsumer()
    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(payload).encode("utf-8"), 26),
    )

    assert consumer.committed_offsets == [26]
    assert field in caplog.text
    assert "se descarta y confirma" in caplog.text


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id_chamber", None),
        ("id_prediction", None),
        ("temperature", None),
        ("remaining_time_min", None),
        ("severity", None),
        ("risk_level", None),
        ("recorded_at", None),
        ("id_chamber", "not-a-uuid"),
        ("id_prediction", "17"),
        ("id_prediction", 0),
        ("id_prediction", 2**63),
        ("temperature", "5.0"),
        ("temperature", True),
        ("temperature", float("nan")),
        ("temperature", float("inf")),
        ("remaining_time_min", -0.1),
        ("remaining_time_min", float("nan")),
        ("severity", ""),
        ("severity", "urgent"),
        ("risk_level", "LOW"),
        ("recorded_at", "not-a-date"),
        ("recorded_at", "2025-01-02"),
    ],
)
def test_invalid_contract_value_is_logged_and_committed(field, value, caplog):
    payload = valid_anomaly_payload()
    payload[field] = value
    consumer = FakeKafkaConsumer()
    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(payload).encode("utf-8"), 27),
    )

    assert consumer.committed_offsets == [27]
    assert field in caplog.text
    assert "se descarta y confirma" in caplog.text


def test_valid_contract_without_duration_is_not_misclassified_as_invalid(
    monkeypatch, caplog
):
    caplog.set_level("INFO")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    monkeypatch.setattr(
        kafka_consumer,
        "get_active_rule",
        lambda session, chamber_id: SimpleNamespace(
            max_absolute_temp=4,
            min_absolute_temp=-30,
            tolerance_time_min=15,
        ),
    )
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(valid_anomaly_payload()).encode("utf-8"), 28),
    )

    assert consumer.committed_offsets == [28]
    assert "Evento sensor.anomaly válido, pero sin decisión HACCP" in caplog.text
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None
