from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Chamber, HaccpRule, User
from schemas import HaccpRuleRead, HaccpRuleUpdate

router = APIRouter(prefix="/haccp", tags=["haccp"])

# Valores por defecto: los mismos que usa worker-haccp al crear reglas
DEFAULT_RULE = {
    "max_absolute_temp": 4.0,
    "min_absolute_temp": -30.0,
    "tolerance_time_min": 15,
    "severity": "medium",
    "active": True,
}


def _build_read(chamber: Chamber, rule: Optional[HaccpRule]) -> Dict[str, Any]:
    """Une cámara y regla en un solo diccionario; si no hay regla, usa los valores por defecto."""
    data: Dict[str, Any] = {
        "id_chamber": chamber.id_chamber,
        "chamber_name": chamber.name,
        "id_rule": None,
        "review_date": None,
        "id_user_modified": None,
        **DEFAULT_RULE,
    }
    if rule is not None:
        data.update(
            id_rule=rule.id_rule,
            max_absolute_temp=rule.max_absolute_temp,
            min_absolute_temp=rule.min_absolute_temp,
            tolerance_time_min=rule.tolerance_time_min,
            severity=rule.severity,
            active=rule.active,
            review_date=rule.review_date,
            id_user_modified=rule.id_user_modified,
        )
    return data


def _get_chamber_or_404(db: Session, id_chamber: UUID) -> Chamber:
    """Busca una cámara por id; si no existe responde 404."""
    chamber = db.get(Chamber, id_chamber)
    if chamber is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    return chamber


def _get_rule(db: Session, id_chamber: UUID) -> Optional[HaccpRule]:
    """Devuelve la regla más reciente de la cámara, o None si no tiene."""
    return (
        db.query(HaccpRule)
        .filter(HaccpRule.id_chamber == id_chamber)
        .order_by(HaccpRule.review_date.desc())
        .first()
    )


# Permisos: técnico y gerente (TODO: agregar dependencia de auth cuando exista auth.py)
@router.get("/rules", response_model=List[HaccpRuleRead])
def list_rules(db: Session = Depends(get_db)):
    """Lista todas las cámaras activas con su regla HACCP (o los valores por defecto si no tienen)."""
    rows = (
        db.query(Chamber, HaccpRule)
        .outerjoin(HaccpRule, HaccpRule.id_chamber == Chamber.id_chamber)
        .filter(Chamber.active.is_(True))
        .order_by(Chamber.name)
        .all()
    )
    return [_build_read(chamber, rule) for chamber, rule in rows]


# Permisos: técnico y gerente
@router.get("/rules/{id_chamber}", response_model=HaccpRuleRead)
def get_rule(id_chamber: UUID, db: Session = Depends(get_db)):
    """Devuelve la regla HACCP de una cámara."""
    chamber = _get_chamber_or_404(db, id_chamber)
    return _build_read(chamber, _get_rule(db, id_chamber))


# Permisos: técnico y gerente
@router.put("/rules/{id_chamber}", response_model=HaccpRuleRead)
def update_rule(id_chamber: UUID, data: HaccpRuleUpdate, db: Session = Depends(get_db)):
    """Actualiza la regla de la cámara; si todavía no tiene una, la crea."""
    chamber = _get_chamber_or_404(db, id_chamber)

    if data.id_user_modified and db.get(User, data.id_user_modified) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    rule = _get_rule(db, id_chamber)
    if rule is None:
        rule = HaccpRule(id_chamber=id_chamber)
        db.add(rule)

    for field, value in data.model_dump().items():
        setattr(rule, field, value)
    rule.review_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rule)
    return _build_read(chamber, rule)