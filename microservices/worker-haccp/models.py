from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chamber(Base):
    __tablename__ = "chambers"

    id_chamber: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id_user: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)


class HaccpRule(Base):
    __tablename__ = "haccp_rules"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="haccp_rules_severity_check",
        ),
    )

    id_rule: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    id_chamber: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chambers.id_chamber", ondelete="CASCADE")
    )
    tolerance_time_min: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool | None] = mapped_column(
        Boolean, default=True, server_default=text("true")
    )
    review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    max_absolute_temp: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    min_absolute_temp: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    severity: Mapped[str | None] = mapped_column(String(20), server_default=text("'medium'"))
    id_user_modified: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id_user")
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id_prediction: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class GeneratedAlert(Base):
    __tablename__ = "generated_alerts"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="generated_alerts_severity_check",
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved')",
            name="generated_alerts_status_check",
        ),
    )

    id_alert: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    id_chamber: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("chambers.id_chamber", ondelete="CASCADE")
    )
    id_prediction: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("predictions.id_prediction", ondelete="SET NULL")
    )
    id_haccp_rule: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("haccp_rules.id_rule", ondelete="SET NULL")
    )
    alert_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default=text("'active'")
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    id_user_acknowledged: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id_user")
    )
    acknowledgment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    id_user_resolved: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id_user")
    )
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertAudit(Base):
    __tablename__ = "alert_audit"

    id_audit: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    id_alert: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("generated_alerts.id_alert", ondelete="CASCADE")
    )
    id_user: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id_user")
    )
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
