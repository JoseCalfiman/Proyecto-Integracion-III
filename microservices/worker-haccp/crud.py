from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Chamber, HaccpRule


# ============================================================
# Valores por defecto según el MER oficial
# ============================================================
DEFAULT_RULE_VALUES = {
    "max_absolute_temp": Decimal("4.00"),
    "min_absolute_temp": Decimal("-30.00"),
    "tolerance_time_min": 15,
    "active": True,
}


def create_default_rules_for_all_chambers(
    session: Session,
    modified_by_user_id: str | None = None,
) -> list[HaccpRule]:
    """Crea una regla HACCP por defecto para cada cámara sin regla."""
    chamber_ids = session.scalars(select(Chamber.id_chamber)).all()
    if not chamber_ids:
        return []

    existing_ids = set(
        session.scalars(
            select(HaccpRule.id_chamber).where(HaccpRule.id_chamber.in_(chamber_ids))
        ).all()
    )
    new_rules = [
        HaccpRule(
            id_chamber=chamber_id,
            id_user_modified=modified_by_user_id,
            **DEFAULT_RULE_VALUES,
        )
        for chamber_id in chamber_ids
        if chamber_id not in existing_ids
    ]
    if new_rules:
        session.add_all(new_rules)
        session.commit()
    return new_rules


def get_active_rule(session: Session, chamber_id: str) -> HaccpRule | None:
    """Devuelve la regla HACCP activa de una cámara."""
    return session.scalar(
        select(HaccpRule).where(
            HaccpRule.id_chamber == chamber_id,
            HaccpRule.active.is_(True),
        )
    )