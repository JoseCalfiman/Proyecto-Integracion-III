from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
	pass


class Chamber(Base):
	"""Reference to an existing chamber in the shared database."""

	__tablename__ = "chambers"

	chamber_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class User(Base):
	"""Reference to an existing user in the shared database."""

	__tablename__ = "users"

	user_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class HaccpRule(Base):
	__tablename__ = "haccp_rules"
	__table_args__ = (UniqueConstraint("chamber_id", name="uq_haccp_rules_chamber_id"),)

	rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
	chamber_id: Mapped[int] = mapped_column(ForeignKey("chambers.chamber_id"), nullable=False)
	absolute_max_temp: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
	absolute_min_temp: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
	tolerance_time_min: Mapped[int] = mapped_column(Integer, nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, nullable=False, server_default=func.now()
	)
	modified_by_user_id: Mapped[int | None] = mapped_column(
		ForeignKey("users.user_id"), nullable=True
	)
