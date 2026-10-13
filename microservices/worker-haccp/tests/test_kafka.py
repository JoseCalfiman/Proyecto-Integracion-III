from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from kafka_consumer import _persist_generated_alert
from models import AlertAudit, GeneratedAlert


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
		saved_alert = session.scalar(
			select(GeneratedAlert).where(GeneratedAlert.id_alert == alert.id_alert)
		)

	assert saved_alert is not None
	assert saved_alert.id_chamber == 3
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
