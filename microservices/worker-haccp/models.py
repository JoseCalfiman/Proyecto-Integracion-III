from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Chamber(Base):
    __tablename__ = "chambers"

    id_chamber: Mapped[int] = mapped_column(Integer, primary_key=True)


class User(Base):
    __tablename__ = "users"

    id_user: Mapped[int] = mapped_column(Integer, primary_key=True)


class HaccpRule(Base):
    __tablename__ = "haccp_rules"
    __table_args__ = (UniqueConstraint("id_chamber", name="uq_haccp_rules_id_chamber"),)

    id_rule: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_chamber: Mapped[int] = mapped_column(ForeignKey("chambers.id_chamber"), nullable=False)
    tolerance_time_min: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_absolute_temp: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    min_absolute_temp: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    id_user_modified: Mapped[int | None] = mapped_column(ForeignKey("users.id_user"), nullable=True)


class GeneratedAlert(Base):
    __tablename__ = "generated_alerts"

    id_alert: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_chamber: Mapped[int] = mapped_column(ForeignKey("chambers.id_chamber"), nullable=False)
    id_prediction: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("predictions.id_prediction"), nullable=True)
    id_haccp_rule: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("haccp_rules.id_rule"), nullable=True)
    alert_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    id_user_acknowledged: Mapped[int | None] = mapped_column(ForeignKey("users.id_user"), nullable=True)
    acknowledgment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    id_user_resolved: Mapped[int | None] = mapped_column(ForeignKey("users.id_user"), nullable=True)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlertAudit(Base):
    __tablename__ = "alert_audit"

    id_audit: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    id_alert: Mapped[int] = mapped_column(BigInteger, ForeignKey("generated_alerts.id_alert"), nullable=False)
    id_user: Mapped[int | None] = mapped_column(ForeignKey("users.id_user"), nullable=True)
    action: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
