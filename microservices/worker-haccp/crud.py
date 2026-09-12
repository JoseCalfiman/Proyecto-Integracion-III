from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Chamber, HaccpRule


DEFAULT_RULE_VALUES = {
	"absolute_max_temp": Decimal("4.00"),
	"absolute_min_temp": Decimal("-30.00"),
	"tolerance_time_min": 15,
	"is_active": True,
}


def create_default_rules_for_all_chambers(
	session: Session,
	modified_by_user_id: int | None = None,
) -> list[HaccpRule]:
	"""Create one default active HACCP rule for each chamber without one."""
	chamber_ids = session.scalars(select(Chamber.chamber_id)).all()
	if not chamber_ids:
		return []

	existing_ids = set(
		session.scalars(
			select(HaccpRule.chamber_id).where(HaccpRule.chamber_id.in_(chamber_ids))
		).all()
	)
	new_rules = [
		HaccpRule(
			chamber_id=chamber_id,
			modified_by_user_id=modified_by_user_id,
			**DEFAULT_RULE_VALUES,
		)
		for chamber_id in chamber_ids
		if chamber_id not in existing_ids
	]
	if new_rules:
		session.add_all(new_rules)
		session.commit()
	return new_rules


def get_active_rule(session: Session, chamber_id: int) -> HaccpRule | None:
	"""Return the active HACCP rule assigned to a chamber."""
	return session.scalar(
		select(HaccpRule).where(
			HaccpRule.chamber_id == chamber_id,
			HaccpRule.is_active.is_(True),
		)
	)
