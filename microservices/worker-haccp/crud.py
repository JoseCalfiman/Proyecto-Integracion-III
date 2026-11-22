from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Chamber, GeneratedAlert, HaccpRule, Prediction


# ============================================================
# Valores por defecto según el MER oficial
# ============================================================
DEFAULT_RULE_VALUES = {
    "max_absolute_temp": Decimal("4.00"),
    "min_absolute_temp": Decimal("-30.00"),
    "tolerance_time_min": 15,
    "severity": "medium",
    "active": True,
}


def create_default_rules_for_all_chambers(
    session: Session,
    modified_by_user_id: UUID | None = None,
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


def get_active_rule(session: Session, chamber_id: UUID) -> HaccpRule | None:
    """Devuelve la regla activa más recientemente revisada para una cámara."""
    return session.scalar(
        select(HaccpRule)
        .where(
            HaccpRule.id_chamber == chamber_id,
            HaccpRule.active.is_(True),
        )
        .order_by(HaccpRule.review_date.desc())
    )


def lock_prediction_and_get_alert(
    session: Session,
    prediction_id: int,
) -> GeneratedAlert | None:
    """Serializa por predicción la búsqueda de una alerta ya creada."""
    session.scalar(
        select(Prediction.id_prediction)
        .where(Prediction.id_prediction == prediction_id)
        .with_for_update()
    )
    return session.scalar(
        select(GeneratedAlert)
        .where(GeneratedAlert.id_prediction == prediction_id)
        .order_by(GeneratedAlert.id_alert)
        .limit(1)
    )