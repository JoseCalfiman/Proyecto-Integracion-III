from sqlalchemy import create_engine, inspect

from models import AlertAuditLog


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
