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
from haccp_validator import HaccpRuleConfigurationError
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
            temperature=5,
            remaining_time_min=15,
        )
    )

    with Session(engine) as session:
        saved_alert = session.scalar(select(GeneratedAlert))
        saved_audit = session.scalar(select(AlertAudit))

    assert saved_alert is not None
    assert saved_alert.id_haccp_rule == rule_id
    assert saved_alert.severity == "high"
    assert saved_audit is not None
    assert saved_audit.id_alert == saved_alert.id_alert
    assert published[0]["severity"] == "high"
    assert published[0]["id_prediction"] == 17


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
    with pytest.raises(HaccpRuleConfigurationError, match="Severidad"):
        kafka_consumer._handle_kafka_message(
            consumer,
            FakeKafkaMessage(
                json.dumps(
                    valid_anomaly_payload(id_chamber=str(chamber_id))
                ).encode("utf-8"),
                20,
            ),
        )

    assert consumer.committed_offsets == []
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


def test_valid_contract_uses_predictive_decision_and_commits_after_publish(
    monkeypatch,
):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID(CHAMBER_ID)
    with Session(engine) as session:
        session.add(Chamber(id_chamber=chamber_id))
        session.add(
            HaccpRule(
                id_chamber=chamber_id,
                active=True,
                severity="high",
                max_absolute_temp=4,
                min_absolute_temp=-30,
                tolerance_time_min=15,
            )
        )
        session.commit()
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    published = []
    monkeypatch.setattr(kafka_consumer, "publish_haccp_alert", published.append)
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(
            json.dumps(
                valid_anomaly_payload(temperature=5, remaining_time_min=20)
            ).encode("utf-8"),
            28,
        ),
    )

    assert consumer.committed_offsets == [28]
    assert published[0]["severity"] == "high"
    assert published[0]["id_prediction"] == 17
    with Session(engine) as session:
        alert = session.scalar(select(GeneratedAlert))
        audit = session.scalar(select(AlertAudit))
    assert alert is not None
    assert audit is not None
    assert audit.id_alert == alert.id_alert


def test_predictive_event_without_infringement_is_not_persisted_and_commits(
    monkeypatch, caplog
):
    caplog.set_level("INFO")
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    chamber_id = UUID(CHAMBER_ID)
    with Session(engine) as session:
        session.add(Chamber(id_chamber=chamber_id))
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
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(
            json.dumps(
                valid_anomaly_payload(temperature=4, remaining_time_min=16)
            ).encode("utf-8"),
            30,
        ),
    )

    assert consumer.committed_offsets == [30]
    assert "sin infracciones HACCP" in caplog.text
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None


@pytest.mark.parametrize(
    "rule_overrides",
    [
        {"min_absolute_temp": None},
        {"max_absolute_temp": None},
        {"tolerance_time_min": None},
        {"min_absolute_temp": float("-inf")},
        {"max_absolute_temp": float("nan")},
        {"max_absolute_temp": float("inf")},
        {"tolerance_time_min": float("nan")},
        {"tolerance_time_min": -1},
        {"min_absolute_temp": 6, "max_absolute_temp": 5},
        {"max_absolute_temp": "5"},
    ],
)
def test_invalid_active_rule_leaves_offset_uncommitted_and_stops_processing(
    monkeypatch, caplog, rule_overrides
):
    caplog.set_level("ERROR")
    monkeypatch.setattr(
        kafka_consumer, "get_engine", lambda: create_engine("sqlite://")
    )
    rule_values = {
        "severity": "high",
        "min_absolute_temp": -20,
        "max_absolute_temp": 5,
        "tolerance_time_min": 15,
    }
    rule_values.update(rule_overrides)
    rule = SimpleNamespace(**rule_values)
    monkeypatch.setattr(
        kafka_consumer, "get_active_rule", lambda session, chamber_id: rule
    )
    consumer = FakeKafkaConsumer()

    with pytest.raises(HaccpRuleConfigurationError):
        _handle_kafka_message(
            consumer,
            FakeKafkaMessage(
                json.dumps(valid_anomaly_payload()).encode("utf-8"), 31
            ),
        )

    assert consumer.committed_offsets == []
    assert "offset queda sin confirmar" in caplog.text


def test_missing_active_rule_does_not_create_alert_and_commits(monkeypatch, caplog):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    monkeypatch.setattr(
        kafka_consumer, "get_active_rule", lambda session, chamber_id: None
    )
    consumer = FakeKafkaConsumer()

    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(
            json.dumps(valid_anomaly_payload()).encode("utf-8"), 32
        ),
    )

    assert consumer.committed_offsets == [32]
    assert "No existe regla HACCP activa" in caplog.text
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None


@pytest.mark.parametrize("delivery_failure", [False, True])
def test_persist_delivery_and_offset_order(monkeypatch, delivery_failure):
    from datetime import datetime, timezone
    from sqlalchemy import event
    import kafka_producer

    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(Chamber(id_chamber=UUID(CHAMBER_ID)))
        session.add(HaccpRule(
            id_chamber=UUID(CHAMBER_ID), active=True, severity="high",
            min_absolute_temp=-30, max_absolute_temp=4, tolerance_time_min=15,
        ))
        session.commit()
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    steps = []
    published = []

    def after_commit(session):
        steps.append("database_commit")

    event.listen(Session, "after_commit", after_commit)

    class Producer:
        def __init__(self, config):
            pass

        def produce(self, topic, value, *, key, callback):
            assert steps == ["database_commit"]
            published.append(json.loads(value.decode("utf-8")))
            assert key == CHAMBER_ID.encode("utf-8")
            self.callback = callback

        def flush(self, timeout):
            steps.append("delivery_failure" if delivery_failure else "delivery_success")
            self.callback("delivery failed" if delivery_failure else None, object())
            return 0

    class Consumer(FakeKafkaConsumer):
        def commit(self, message, asynchronous):
            steps.append("offset_commit")
            super().commit(message, asynchronous)

    monkeypatch.setattr(kafka_producer, "Producer", Producer)
    consumer = Consumer()
    message = FakeKafkaMessage(json.dumps(valid_anomaly_payload(
        generation_date="2000-01-01T00:00:00Z",
    )).encode("utf-8"), 33)
    try:
        if delivery_failure:
            with pytest.raises(kafka_producer.HaccpAlertPublicationError):
                _handle_kafka_message(consumer, message)
        else:
            _handle_kafka_message(consumer, message)
    finally:
        event.remove(Session, "after_commit", after_commit)

    if delivery_failure:
        assert steps == ["database_commit", "delivery_failure"]
        assert consumer.committed_offsets == []
    else:
        assert steps == ["database_commit", "delivery_success", "offset_commit"]
        assert consumer.committed_offsets == [33]
    with Session(engine) as session:
        alert = session.scalar(select(GeneratedAlert))
        audit = session.scalar(select(AlertAudit))
        assert audit.id_alert == alert.id_alert
        assert published == [{
            "id_alert": alert.id_alert,
            "id_chamber": str(alert.id_chamber),
            "id_prediction": alert.id_prediction,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "status": alert.status,
            "message": alert.message,
            "generation_date": alert.generation_date.replace(tzinfo=timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        }]
        assert datetime.fromisoformat(published[0]["generation_date"].replace("Z", "+00:00")).year != 2000


@pytest.mark.parametrize("discard", ["invalid", "no_rule", "no_infringement"])
def test_discarded_events_never_publish(monkeypatch, discard):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    if discard == "no_infringement":
        with Session(engine) as session:
            session.add(Chamber(id_chamber=UUID(CHAMBER_ID)))
            session.add(HaccpRule(
                id_chamber=UUID(CHAMBER_ID), active=True, severity="high",
                min_absolute_temp=-30, max_absolute_temp=4, tolerance_time_min=15,
            ))
            session.commit()
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)

    def unexpected_publication(payload):
        pytest.fail("A discarded event must never be published")

    monkeypatch.setattr(kafka_consumer, "publish_haccp_alert", unexpected_publication)
    payload = valid_anomaly_payload(temperature=4, remaining_time_min=16)
    if discard == "invalid":
        del payload["id_prediction"]
    consumer = FakeKafkaConsumer()
    _handle_kafka_message(consumer, FakeKafkaMessage(json.dumps(payload).encode("utf-8"), 34))
    assert consumer.committed_offsets == [34]
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None
        assert session.scalar(select(AlertAudit)) is None


@pytest.fixture
def persistence_failure_engine(monkeypatch):
    # SQLite verifies transaction control here, not PostgreSQL foreign keys.
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(Chamber(id_chamber=UUID(CHAMBER_ID)))
        session.add(HaccpRule(
            id_chamber=UUID(CHAMBER_ID), active=True, severity="medium",
            min_absolute_temp=-30, max_absolute_temp=4, tolerance_time_min=15,
        ))
        session.commit()
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("stage", ["alert_flush", "audit_insert", "commit"])
@pytest.mark.parametrize("error_type", [
    kafka_consumer.IntegrityError,
    kafka_consumer.DataError,
    kafka_consumer.SQLAlchemyError,
])
def test_persistence_failure_rolls_back_without_publication(
    monkeypatch, caplog, persistence_failure_engine, stage, error_type,
):
    from sqlalchemy import event

    engine = persistence_failure_engine
    error = (
        error_type("simulated persistence rejection", {}, Exception("test failure"))
        if error_type in (kafka_consumer.IntegrityError, kafka_consumer.DataError)
        else error_type("simulated persistence failure")
    )
    failures = []
    published = []
    consumer = FakeKafkaConsumer()

    def fail():
        failures.append(stage)
        assert published == []
        assert consumer.committed_offsets == []
        raise error

    class FailingSession(Session):
        def flush(self, *args, **kwargs):
            if stage == "alert_flush" and any(
                isinstance(item, GeneratedAlert) for item in self.new
            ):
                fail()
            return super().flush(*args, **kwargs)

        def commit(self):
            if stage == "commit":
                # The alert has reached SQL and the audit is pending together.
                assert self.scalar(select(GeneratedAlert)) is not None
                assert self.scalar(select(AlertAudit)) is not None
                fail()
            return super().commit()

    def fail_audit_insert(mapper, connection, target):
        # The real alert INSERT has already happened in this transaction.
        assert connection.execute(select(GeneratedAlert.id_alert)).scalar() is not None
        fail()

    monkeypatch.setattr(kafka_consumer, "Session", FailingSession)
    monkeypatch.setattr(kafka_consumer, "publish_haccp_alert", published.append)
    if stage == "audit_insert":
        event.listen(AlertAudit, "before_insert", fail_audit_insert)
    message = FakeKafkaMessage(json.dumps(valid_anomaly_payload()).encode("utf-8"), 35)
    permanent_rejection = error_type in (
        kafka_consumer.IntegrityError, kafka_consumer.DataError,
    )
    try:
        if permanent_rejection:
            _handle_kafka_message(consumer, message)
        else:
            with pytest.raises(kafka_consumer.SQLAlchemyError) as caught:
                _handle_kafka_message(consumer, message)
            assert caught.value is error
    finally:
        if stage == "audit_insert":
            event.remove(AlertAudit, "before_insert", fail_audit_insert)

    assert failures == [stage]
    assert published == []
    if permanent_rejection:
        assert consumer.committed_offsets == [35]
        assert "Datos rechazados por PostgreSQL" in caplog.text
        assert "se descartan y confirma el offset" in caplog.text
    else:
        assert consumer.committed_offsets == []
        assert "offset queda sin confirmar" in caplog.text
    with Session(engine) as session:
        assert session.scalar(select(GeneratedAlert)) is None
        assert session.scalar(select(AlertAudit)) is None


@pytest.mark.parametrize("error_type", [
    kafka_consumer.DisconnectionError,
    kafka_consumer.InterfaceError,
    kafka_consumer.OperationalError,
    kafka_consumer.SQLAlchemyTimeoutError,
])
def test_transient_persistence_failure_recovers_before_offset_commit(
    monkeypatch, caplog, persistence_failure_engine, error_type,
):
    engine = persistence_failure_engine
    error = (
        error_type("simulated disconnect", {}, Exception("test failure"))
        if error_type in (kafka_consumer.InterfaceError, kafka_consumer.OperationalError)
        else error_type("simulated transient failure")
    )
    attempts = []
    published = []
    delays = []
    consumer = FakeKafkaConsumer()

    class RecoveringSession(Session):
        def commit(self):
            attempts.append("commit")
            if len(attempts) == 1:
                # Fail after both INSERTs, before the transaction is committed.
                self.flush()
                assert self.scalar(select(GeneratedAlert)) is not None
                assert self.scalar(select(AlertAudit)) is not None
                assert consumer.committed_offsets == []
                assert published == []
                raise error
            return super().commit()

    def publish(payload):
        assert attempts == ["commit", "commit"]
        assert consumer.committed_offsets == []
        published.append(payload)

    monkeypatch.setattr(kafka_consumer, "Session", RecoveringSession)
    monkeypatch.setattr(kafka_consumer, "publish_haccp_alert", publish)
    monkeypatch.setattr(kafka_consumer.time, "sleep", delays.append)
    _handle_kafka_message(
        consumer,
        FakeKafkaMessage(json.dumps(valid_anomaly_payload()).encode("utf-8"), 36),
    )

    assert attempts == ["commit", "commit"]
    assert delays == [kafka_consumer.DATABASE_RETRY_DELAY_SECONDS]
    assert consumer.committed_offsets == [36]
    assert len(published) == 1
    assert "Fallo transitorio de base de datos" in caplog.text
    with Session(engine) as session:
        alerts = session.scalars(select(GeneratedAlert)).all()
        audits = session.scalars(select(AlertAudit)).all()
        assert len(alerts) == len(audits) == 1
        assert audits[0].id_alert == alerts[0].id_alert == published[0]["id_alert"]
