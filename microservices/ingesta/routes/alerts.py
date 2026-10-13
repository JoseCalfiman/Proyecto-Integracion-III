from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import AlertAudit, GeneratedAlert, User
from schemas import AlertAction, AlertAuditRead, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _get_alert_or_404(db: Session, id_alert: int) -> GeneratedAlert:
    """Busca una alerta por id; si no existe responde 404."""
    alert = db.get(GeneratedAlert, id_alert)
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alerta no encontrada")
    return alert


def _transition(
    db: Session,
    alert: GeneratedAlert,
    required: str,
    new_status: str,
    data: AlertAction,
) -> GeneratedAlert:
    """Cambia el estado de la alerta, guarda quién y cuándo, y registra la auditoría."""
    if alert.status != required:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La alerta debe estar en estado '{required}' (estado actual: '{alert.status}')",
        )
    if db.get(User, data.id_user) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    now = datetime.now(timezone.utc)
    alert.status = new_status
    if new_status == "acknowledged":
        alert.id_user_acknowledged = data.id_user
        alert.acknowledgment_date = now
    else:
        alert.id_user_resolved = data.id_user
        alert.resolution_date = now

    db.add(
        AlertAudit(
            id_alert=alert.id_alert,
            id_user=data.id_user,
            action=new_status,
            detail=data.note or f"Alerta {new_status} por el usuario",
        )
    )
    db.commit()
    db.refresh(alert)
    return alert


# Permisos: técnico y gerente (TODO: agregar dependencia de auth cuando exista auth.py)
@router.get("", response_model=List[AlertRead])
def list_alerts(
    id_chamber: Optional[UUID] = None,
    severity: Optional[str] = None,
    alert_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Lista alertas, de la más reciente a la más antigua, con filtros y paginación."""
    query = db.query(GeneratedAlert)
    if id_chamber:
        query = query.filter(GeneratedAlert.id_chamber == id_chamber)
    if severity:
        query = query.filter(GeneratedAlert.severity == severity)
    if alert_status:
        query = query.filter(GeneratedAlert.status == alert_status)
    return (
        query.order_by(GeneratedAlert.generation_date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# Permisos: técnico y gerente
@router.get("/{id_alert}", response_model=AlertRead)
def get_alert(id_alert: int, db: Session = Depends(get_db)):
    """Devuelve una alerta por su id."""
    return _get_alert_or_404(db, id_alert)


# Permisos: técnico y gerente
@router.get("/{id_alert}/audit", response_model=List[AlertAuditRead])
def get_alert_audit(id_alert: int, db: Session = Depends(get_db)):
    """Devuelve el historial de acciones (auditoría) de una alerta."""
    _get_alert_or_404(db, id_alert)
    return (
        db.query(AlertAudit)
        .filter(AlertAudit.id_alert == id_alert)
        .order_by(AlertAudit.action_date)
        .all()
    )


# Permisos: solo técnico
@router.put("/{id_alert}/acknowledge", response_model=AlertRead)
def acknowledge_alert(id_alert: int, data: AlertAction, db: Session = Depends(get_db)):
    """Reconoce una alerta activa (active -> acknowledged)."""
    alert = _get_alert_or_404(db, id_alert)
    return _transition(db, alert, "active", "acknowledged", data)


# Permisos: solo técnico
@router.put("/{id_alert}/resolve", response_model=AlertRead)
def resolve_alert(id_alert: int, data: AlertAction, db: Session = Depends(get_db)):
    """Resuelve una alerta ya reconocida (acknowledged -> resolved)."""
    alert = _get_alert_or_404(db, id_alert)
    return _transition(db, alert, "acknowledged", "resolved", data)