from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import manager
from database import get_db
from models import Chamber, HaccpRule, User
from schemas import HaccpRuleRead, HaccpRuleUpdate

router = APIRouter(prefix="/haccp", tags=["haccp"])

# Valores sugeridos para prellenar el formulario de una cámara que todavía no
# tiene regla. No se guardan ni se aplican: la cámara no se monitorea hasta que
# el gerente guarde una regla (la respuesta trae has_rule=false y active=false).
DEFAULT_RULE = {
    "max_absolute_temp": 4.0,
    "min_absolute_temp": -30.0,
    "tolerance_time_min": 15,
    "severity": "medium",
}

# Orden de "regla vigente": la más reciente, con desempate determinista por id.
RULE_ORDER = (HaccpRule.review_date.desc(), HaccpRule.id_rule.desc())


def _user_names(db: Session, ids: Iterable[Optional[UUID]]) -> Dict[UUID, Optional[str]]:
    """Resuelve id_user -> nombre (mismo patrón que routes/alerts.py)."""
    ids = {uid for uid in ids if uid}
    if not ids:
        return {}
    return dict(db.query(User.id_user, User.name).filter(User.id_user.in_(ids)).all())


def _build_read(chamber: Chamber, rule: Optional[HaccpRule], names: Dict[UUID, Optional[str]]) -> Dict[str, Any]:
    """Une cámara y regla vigente. Sin regla: valores sugeridos, has_rule=false y active=false."""
    data: Dict[str, Any] = {
        "id_chamber": chamber.id_chamber,
        "chamber_name": chamber.name,
        "has_rule": False,
        "id_rule": None,
        "review_date": None,
        "id_user_modified": None,
        "modified_by_name": None,
        "active": False,
        **DEFAULT_RULE,
    }
    if rule is not None:
        data.update(
            has_rule=True,
            id_rule=rule.id_rule,
            max_absolute_temp=rule.max_absolute_temp,
            min_absolute_temp=rule.min_absolute_temp,
            tolerance_time_min=rule.tolerance_time_min,
            severity=rule.severity,
            active=bool(rule.active),
            review_date=rule.review_date,
            id_user_modified=rule.id_user_modified,
            modified_by_name=names.get(rule.id_user_modified),
        )
    return data


def _get_chamber_or_404(db: Session, id_chamber: UUID) -> Chamber:
    """Busca una cámara activa por id; si no existe o está inactiva responde 404."""
    chamber = db.get(Chamber, id_chamber)
    if chamber is None or not chamber.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cámara no encontrada")
    return chamber


def _get_rule(db: Session, id_chamber: UUID) -> Optional[HaccpRule]:
    """Devuelve la regla vigente (la más reciente) de la cámara, o None si no tiene."""
    return (
        db.query(HaccpRule)
        .filter(HaccpRule.id_chamber == id_chamber)
        .order_by(*RULE_ORDER)
        .first()
    )


def _same_values(rule: HaccpRule, data: HaccpRuleUpdate) -> bool:
    """True si los valores enviados coinciden con los guardados (temperaturas con 2 decimales, como NUMERIC(5,2))."""
    return (
        rule.max_absolute_temp is not None
        and rule.min_absolute_temp is not None
        and round(float(rule.max_absolute_temp), 2) == round(data.max_absolute_temp, 2)
        and round(float(rule.min_absolute_temp), 2) == round(data.min_absolute_temp, 2)
        and rule.tolerance_time_min == data.tolerance_time_min
        and rule.severity == data.severity
        and bool(rule.active) == data.active
    )


# Permisos: técnico y gerente
@router.get("/rules", response_model=List[HaccpRuleRead])
def list_rules(db: Session = Depends(get_db)):
    """Una fila por cámara activa, con su regla vigente o sin regla (has_rule=false), ordenadas por nombre."""
    chambers = (
        db.query(Chamber)
        .filter(Chamber.active.is_(True))
        .order_by(Chamber.name, Chamber.id_chamber)
        .all()
    )
    current: Dict[UUID, HaccpRule] = {}
    if chambers:
        rules = (
            db.query(HaccpRule)
            .filter(HaccpRule.id_chamber.in_([c.id_chamber for c in chambers]))
            .order_by(HaccpRule.id_chamber, *RULE_ORDER)
            .all()
        )
        for rule in rules:
            current.setdefault(rule.id_chamber, rule)
    names = _user_names(db, (r.id_user_modified for r in current.values()))
    return [_build_read(c, current.get(c.id_chamber), names) for c in chambers]


# Permisos: técnico y gerente
@router.get("/rules/{id_chamber}", response_model=HaccpRuleRead)
def get_rule(id_chamber: UUID, db: Session = Depends(get_db)):
    """Devuelve la regla HACCP vigente de una cámara activa."""
    chamber = _get_chamber_or_404(db, id_chamber)
    rule = _get_rule(db, id_chamber)
    names = _user_names(db, [rule.id_user_modified] if rule else [])
    return _build_read(chamber, rule, names)


# Permisos: solo gerente
@router.put("/rules/{id_chamber}", response_model=HaccpRuleRead)
def update_rule(id_chamber: UUID, data: HaccpRuleUpdate, user=Depends(manager), db: Session = Depends(get_db)):
    """Guarda la regla vigente de la cámara (la crea si no tiene) y desactiva las demás reglas de esa cámara."""
    chamber = _get_chamber_or_404(db, id_chamber)

    rule = _get_rule(db, id_chamber)
    if rule is not None and _same_values(rule, data):
        # Sin cambios: no se toca review_date ni id_user_modified.
        return _build_read(chamber, rule, _user_names(db, [rule.id_user_modified]))

    if rule is None:
        rule = HaccpRule(id_chamber=id_chamber)
        db.add(rule)

    for field, value in data.model_dump().items():
        setattr(rule, field, value)
    rule.id_user_modified = user.id_user
    rule.review_date = datetime.now(timezone.utc)
    db.flush()  # asigna id_rule a una regla nueva antes de desactivar las demás

    # Una sola regla activa por cámara: el worker aplica la misma que muestra la UI.
    db.query(HaccpRule).filter(
        HaccpRule.id_chamber == id_chamber,
        HaccpRule.id_rule != rule.id_rule,
        HaccpRule.active.is_(True),
    ).update({HaccpRule.active: False}, synchronize_session=False)

    db.commit()
    db.refresh(rule)
    return _build_read(chamber, rule, _user_names(db, [rule.id_user_modified]))
