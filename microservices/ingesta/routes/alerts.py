"""Alertas HACCP: asignación, resolución, auditoría y consulta acotada."""
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import func, text, tuple_
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from auth import manager, shared, technician
from database import get_db
from models import AlertAudit, Chamber, GeneratedAlert, Report, Sensor, User
from schemas import AlertAction, AlertAuditRead, AlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])
Severity = Literal["low", "medium", "high", "critical"]
AlertState = Literal["active", "acknowledged", "resolved"]


class ResolveAction(BaseModel):
    note: str = Field(min_length=15, max_length=500)
    intervention: str = Field(default="Otra intervención", min_length=1, max_length=80)
    id_sensor: Optional[int] = Field(default=None, ge=1)


def _company_alerts(db, user):
    if user.id_company is None:
        raise HTTPException(403, "Usuario sin empresa asignada")
    return db.query(GeneratedAlert).join(Chamber, GeneratedAlert.id_chamber == Chamber.id_chamber).filter(
        Chamber.id_company == user.id_company
    )


def _timeout(db, write=False):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
        if write:
            db.execute(text("SET LOCAL lock_timeout = '3000ms'"))


def _handle_db_error(db, exc):
    db.rollback()
    code = getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)
    if code in ("55P03", "40P01", "40001"):
        raise HTTPException(409, "La alerta está siendo modificada por otra operación. Actualiza e intenta nuevamente.") from exc
    if code == "57014":
        raise HTTPException(503, "Consulta demasiado extensa. Intenta con un período menor o más tarde.") from exc
    raise exc


def _bounded_all(db, query):
    try:
        _timeout(db)
        return query.all()
    except DBAPIError as exc:
        _handle_db_error(db, exc)


def _names(db, ids, company_id):
    ids = {i for i in ids if i is not None}
    if not ids:
        return {}
    return dict(db.query(User.id_user, User.name).filter(User.id_user.in_(ids), User.id_company == company_id).all())


def _reads(db, rows, user):
    names = _names(db, (uid for a in rows for uid in (a.id_user_acknowledged, a.id_user_resolved)), user.id_company)
    return [AlertRead.model_validate(a).model_copy(update={
        "acknowledged_by": names.get(a.id_user_acknowledged), "resolved_by": names.get(a.id_user_resolved)
    }) for a in rows]


def _get_alert_or_404(db, id_alert, user, lock=False):
    query = _company_alerts(db, user).filter(GeneratedAlert.id_alert == id_alert)
    if lock:
        # PostgreSQL bloquea únicamente generated_alerts, no las tablas del JOIN.
        query = query.with_for_update(of=GeneratedAlert).populate_existing()
    alert = query.one_or_none()
    if alert is None:
        raise HTTPException(404, "Alerta no encontrada")
    return alert


def _transition(db, id_alert, user, required, new_status, detail, sensor_id=None):
    try:
        _timeout(db, write=True)
        alert = _get_alert_or_404(db, id_alert, user, lock=True)
        if alert.status != required:
            raise HTTPException(409, f"La alerta debe estar en estado '{required}' (estado actual: '{alert.status}')")
        if new_status == "resolved" and alert.id_user_acknowledged != user.id_user:
            raise HTTPException(403, "Solo el técnico que asumió esta alerta puede resolverla")
        if sensor_id is not None:
            sensor = db.query(Sensor.id_sensor).filter(Sensor.id_sensor == sensor_id, Sensor.id_chamber == alert.id_chamber).first()
            if sensor is None:
                raise HTTPException(422, "El sensor seleccionado no pertenece a la cámara de la alerta")
        now = datetime.now(timezone.utc)
        alert.status = new_status
        if new_status == "acknowledged":
            alert.id_user_acknowledged = user.id_user
            alert.acknowledgment_date = now
        else:
            alert.id_user_resolved = user.id_user
            alert.resolution_date = now
        db.add(AlertAudit(id_alert=alert.id_alert, id_user=user.id_user, action=new_status,
                          action_date=now, detail=detail))
        db.flush()
        result = _reads(db, [alert], user)[0]
        db.commit()  # Estado y auditoría se confirman juntos.
        return result
    except HTTPException:
        db.rollback()
        raise
    except DBAPIError as exc:
        _handle_db_error(db, exc)


@router.get("", response_model=List[AlertRead])
def list_alerts(
    id_chamber: Optional[UUID] = None,
    severity: Optional[Severity] = None,
    alert_status: Optional[AlertState] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    id_alert: Optional[int] = Query(default=None, ge=1),
    mine: bool = False,
    user=Depends(shared), db: Session = Depends(get_db),
):
    query = _company_alerts(db, user)
    if id_chamber is not None:
        query = query.filter(GeneratedAlert.id_chamber == id_chamber)
    if severity is not None:
        query = query.filter(GeneratedAlert.severity == severity)
    if alert_status is not None:
        query = query.filter(GeneratedAlert.status == alert_status)
    if id_alert is not None:
        query = query.filter(GeneratedAlert.id_alert == id_alert)
    if mine:
        query = query.filter(GeneratedAlert.id_user_acknowledged == user.id_user)
    rows = _bounded_all(db, query.order_by(GeneratedAlert.generation_date.desc(), GeneratedAlert.id_alert.desc()).offset(offset).limit(limit))
    return _reads(db, rows, user)


@router.get("/manager/summary")
def manager_summary(user=Depends(manager), db: Session = Depends(get_db)):
    """Cuenta estados de alertas generadas en las últimas 24 horas."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    query = (_company_alerts(db, user).with_entities(GeneratedAlert.status, GeneratedAlert.severity, func.count())
        .filter(GeneratedAlert.generation_date >= start, GeneratedAlert.generation_date < end)
        .group_by(GeneratedAlert.status, GeneratedAlert.severity))
    counts = {"active": 0, "acknowledged": 0, "resolved": 0, "high_priority_open": 0}
    for state, severity, count in _bounded_all(db, query):
        counts[state] += count
        if state != "resolved" and severity in ("high", "critical"):
            counts["high_priority_open"] += count
    return {**counts, "from": start, "to": end}


def _history_query(db, user, date_from, date_to, id_chamber, severity, alert_status, id_alert, resolved_by):
    if not timedelta(0) < date_to - date_from <= timedelta(days=31):
        raise HTTPException(422, "El período debe ser positivo y no superar 31 días")
    query = _company_alerts(db, user).filter(GeneratedAlert.generation_date >= date_from, GeneratedAlert.generation_date < date_to)
    for field, value in ((GeneratedAlert.id_chamber, id_chamber), (GeneratedAlert.severity, severity),
                         (GeneratedAlert.status, alert_status), (GeneratedAlert.id_alert, id_alert),
                         (GeneratedAlert.id_user_resolved, resolved_by)):
        if value is not None:
            query = query.filter(field == value)
    return query


@router.get("/manager/history")
def manager_history(
    date_from: AwareDatetime, date_to: AwareDatetime,
    id_chamber: Optional[UUID] = None, severity: Optional[Severity] = None,
    alert_status: Optional[AlertState] = Query(default=None, alias="status"),
    before_date: Optional[AwareDatetime] = None,
    before_id: Optional[int] = Query(default=None, ge=1),
    id_alert: Optional[int] = Query(default=None, ge=1),
    resolved_by: Optional[UUID] = None,
    user=Depends(manager), db: Session = Depends(get_db),
):
    query = _history_query(db, user, date_from, date_to, id_chamber, severity, alert_status, id_alert, resolved_by)
    if (before_date is None) != (before_id is None):
        raise HTTPException(422, "Cursor incompleto")
    if before_date is not None:
        if not date_from <= before_date < date_to:
            raise HTTPException(422, "Cursor fuera del período")
        query = query.filter(tuple_(GeneratedAlert.generation_date, GeneratedAlert.id_alert) < tuple_(before_date, before_id))
    rows = _bounded_all(db, query.order_by(GeneratedAlert.generation_date.desc(), GeneratedAlert.id_alert.desc()).limit(21))
    page = rows[:20]
    cursor = {"before_date": page[-1].generation_date, "before_id": str(page[-1].id_alert)} if len(rows)>20 else None
    return {"items": _reads(db, page, user), "next_cursor": cursor}


@router.get("/manager/technicians")
def manager_technicians(user=Depends(manager), db: Session = Depends(get_db)):
    """Identidades de quienes cerraron alertas (incluye cuentas hoy inactivas)."""
    from models import Role
    rows = db.query(User.id_user, User.name).join(Role, User.id_role == Role.id_role).filter(
        User.id_company == user.id_company, Role.role_name == 'tecnico').order_by(User.name).limit(500).all()
    return [{"id": r.id_user, "name": r.name} for r in rows]


def _csv_cell(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))):
        return "'" + value  # Evita fórmulas inyectadas desde texto libre en Excel.
    return value


@router.get("/manager/report")
def manager_report(
    date_from: AwareDatetime, date_to: AwareDatetime,
    id_chamber: Optional[UUID] = None, severity: Optional[Severity] = None,
    alert_status: Optional[AlertState] = Query(default=None, alias="status"),
    id_alert: Optional[int] = Query(default=None, ge=1), resolved_by: Optional[UUID] = None,
    user=Depends(manager), db: Session = Depends(get_db),
):
    query = _history_query(db, user, date_from, date_to, id_chamber, severity, alert_status, id_alert, resolved_by)
    rows = _bounded_all(db, query.order_by(GeneratedAlert.generation_date.desc(), GeneratedAlert.id_alert.desc()).limit(1001))
    if len(rows)>1000:
        raise HTTPException(422, "El reporte supera 1000 alertas. Reduce el período o aplica filtros.")
    alerts = _reads(db, rows, user)
    # Una sola evidencia de resolución por alerta (la última). No descarga la auditoría completa.
    evidence = {}
    if alerts:
        ranked = db.query(AlertAudit.id_alert, AlertAudit.detail, func.row_number().over(
            partition_by=AlertAudit.id_alert, order_by=(AlertAudit.action_date.desc(), AlertAudit.id_audit.desc())).label('rn')).filter(
            AlertAudit.id_alert.in_([a.id_alert for a in alerts]), AlertAudit.action == 'resolved').subquery()
        evidence = dict(_bounded_all(db, db.query(ranked.c.id_alert, ranked.c.detail).filter(ranked.c.rn == 1)))
    out = io.StringIO(newline='')
    writer = csv.writer(out, delimiter=';')
    writer.writerow(['ID alerta','ID cámara','Cámara','Severidad','Estado','Descripción','Generada','ID responsable','Responsable','Fecha atención','ID cierre','Cerrada por','Fecha resolución','Evidencia','Respuesta (min)','Resolución (min)'])
    def minutes(end, start):
        return round((end-start).total_seconds()/60, 2) if end and start else None
    for a in alerts:
        writer.writerow([_csv_cell(v) for v in (a.id_alert, a.id_chamber, a.chamber_name, a.severity, a.status, a.message, a.generation_date,
            a.id_user_acknowledged, a.acknowledged_by, a.acknowledgment_date, a.id_user_resolved, a.resolved_by, a.resolution_date,
            evidence.get(a.id_alert), minutes(a.acknowledgment_date,a.generation_date), minutes(a.resolution_date,a.generation_date))])
    # Se registra la generación, sin almacenar archivos en el disco efímero del pod.
    db.add(Report(id_company=user.id_company, id_user=user.id_user, report_type='haccp_interventions', format='csv',
                  range_start_date=date_from.astimezone(timezone.utc).date(), range_end_date=date_to.astimezone(timezone.utc).date()))
    try:
        db.commit()
    except DBAPIError as exc:
        _handle_db_error(db, exc)
    return Response(content='\ufeff'+out.getvalue(), media_type='text/csv; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename="intervenciones-haccp.csv"', 'Cache-Control': 'no-store'})


@router.get("/{id_alert}", response_model=AlertRead)
def get_alert(id_alert: int, user=Depends(shared), db: Session = Depends(get_db)):
    return _reads(db, [_get_alert_or_404(db, id_alert, user)], user)[0]


@router.get("/{id_alert}/audit", response_model=List[AlertAuditRead])
def get_alert_audit(id_alert: int, user=Depends(shared), db: Session = Depends(get_db)):
    _get_alert_or_404(db, id_alert, user)
    rows = _bounded_all(db, db.query(AlertAudit).filter(AlertAudit.id_alert == id_alert).order_by(AlertAudit.action_date.desc(), AlertAudit.id_audit.desc()).limit(100))
    names = _names(db, (r.id_user for r in rows), user.id_company)
    return [AlertAuditRead.model_validate(r).model_copy(update={'user_name':names.get(r.id_user)}) for r in reversed(rows)]


@router.put("/{id_alert}/acknowledge", response_model=AlertRead)
def acknowledge_alert(id_alert: int, data: AlertAction, user=Depends(technician), db: Session = Depends(get_db)):
    return _transition(db, id_alert, user, 'active', 'acknowledged', (data.note or '').strip() or 'El técnico asumió la alerta.')


@router.put("/{id_alert}/resolve", response_model=AlertRead)
def resolve_alert(id_alert: int, data: ResolveAction, user=Depends(technician), db: Session = Depends(get_db)):
    note = data.note.strip()
    action = data.intervention.strip()
    if len(note)<15 or not action:
        raise HTTPException(422, 'Describe la intervención y verificación de cierre (mínimo 15 caracteres).')
    sensor = f'Sensor intervenido: {data.id_sensor}' if data.id_sensor is not None else 'Sensor intervenido: no identificado / no aplica'
    detail = f'Intervención: {action}\n{sensor}\nEvidencia: {note}'
    return _transition(db, id_alert, user, 'acknowledged', 'resolved', detail, data.id_sensor)