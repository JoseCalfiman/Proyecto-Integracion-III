from sqlalchemy import BigInteger, Column, Table, create_engine, inspect, select
from sqlalchemy.orm import Session

from kafka_consumer import _persist_generated_alert
from models import AlertAuditLog, GeneratedAlert

Table(
	"predictions",
	GeneratedAlert.metadata,
	Column("id_prediction", BigInteger, primary_key=True),
)


def test_alert_audit_log_table_has_requested_columns():
	engine = create_engine("sqlite://")

	AlertAuditLog.__table__.create(bind=engine, checkfirst=True)

	assert inspect(engine).get_table_names() == ["alert_audit_log"]
	assert {column["name"] for column in inspect(engine).get_columns("alert_audit_log")} == {
		"audit_id",
		"alert_id",
		"user_id",
		"action",
		"detail",
		"action_at",
	}


def test_generated_alert_is_persisted_with_requested_columns():
	engine = create_engine("sqlite://")
	GeneratedAlert.__table__.create(bind=engine, checkfirst=True)
	payload = {
		"id_chamber": 3,
		"id_prediction": 17,
		"severity": "critical",
		"message": "Temperatura fuera de rango",
	}

	with Session(engine) as session:
		alert = _persist_generated_alert(session, payload, rule_id=5)
		session.commit()
		saved_alert = session.scalar(select(GeneratedAlert).where(GeneratedAlert.alert_id == alert.alert_id))

	assert saved_alert is not None
	assert saved_alert.chamber_id == 3
	assert saved_alert.prediction_id == 17
	assert saved_alert.haccp_rule_id == 5
	assert saved_alert.alert_type == "haccp_violation"
	assert saved_alert.severity == "critical"
	assert saved_alert.status == "active"
	assert saved_alert.message == "Temperatura fuera de rango"
	assert saved_alert.generated_at is not None
	assert {column["name"] for column in inspect(engine).get_columns("generated_alerts")} == {
		"alert_id",
		"chamber_id",
		"prediction_id",
		"haccp_rule_id",
		"alert_type",
		"severity",
		"status",
		"message",
		"generated_at",
	}
