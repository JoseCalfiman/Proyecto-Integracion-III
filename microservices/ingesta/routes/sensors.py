"""Inventario de sensores por cámara. No elimina mediciones ni crea tablas."""
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from auth import manager, shared
from database import get_db
from models import Chamber, Sensor, SensorData
from routes.chambers import _get_chamber_or_404

router = APIRouter(prefix="/chambers", tags=["sensors"])

class SensorForm(BaseModel):
    sensor_type: str = Field(min_length=1, max_length=50)
    mqtt_identifier: str = Field(min_length=1, max_length=100)
    model: str | None = Field(default=None, max_length=50)
    mcu_id: str | None = Field(default=None, max_length=50)
    firmware: str | None = Field(default=None, max_length=50)
    last_calibration: date | None = None
    status: Literal["active", "inactive", "maintenance"] = "active"

class SensorRead(SensorForm):
    model_config = ConfigDict(from_attributes=True)
    id_sensor: int
    id_chamber: UUID
    sensor_type: str | None = None
    mqtt_identifier: str | None = None
    status: str | None = None
    installation_date: datetime | None = None


def _sensor(db, chamber_id, sensor_id):
    sensor = db.query(Sensor).filter(Sensor.id_chamber == chamber_id, Sensor.id_sensor == sensor_id).one_or_none()
    if sensor is None:
        raise HTTPException(404, "Sensor no encontrado en esta cámara")
    return sensor


def _save(db, chamber, data, existing=None):
    values = data.model_dump()
    for field, value in values.items():
        if isinstance(value, str):
            values[field] = value.strip() or None
    if not values['sensor_type'] or not values['mqtt_identifier']:
        raise HTTPException(422, "Tipo e identificador MQTT son obligatorios")
    if db.get_bind().dialect.name == 'postgresql':
        # Serializa los registros/ediciones de un mismo identificador MQTT,
        # sin exigir una nueva restricción a instalaciones con datos antiguos.
        db.execute(text("SET LOCAL lock_timeout = '3000ms'"))
        try:
            db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:identifier))"), {'identifier': values['mqtt_identifier']})
        except DBAPIError as exc:
            db.rollback()
            if getattr(exc.orig, 'pgcode', None) == '55P03':
                raise HTTPException(409, 'Otra operación está modificando este sensor. Reintenta.') from exc
            raise
    duplicate = db.query(Sensor).filter(Sensor.id_chamber == chamber.id_chamber, Sensor.mqtt_identifier == values['mqtt_identifier'])
    if existing:
        duplicate = duplicate.filter(Sensor.id_sensor != existing.id_sensor)
    if duplicate.first():
        raise HTTPException(409, "Identificador MQTT ya registrado en esta cámara")
    sensor = existing if existing is not None else Sensor(id_chamber=chamber.id_chamber)
    for field, value in values.items():
        setattr(sensor, field, value)
    db.add(sensor)
    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        if getattr(exc.orig, 'pgcode', None) in ('55P03','57014'):
            raise HTTPException(409, 'Sensor ocupado por otra operación. Reintenta.') from exc
        raise
    db.refresh(sensor)
    return sensor

@router.get('/{id_chamber}/sensors')
def list_sensors(id_chamber: UUID, after_id: int = Query(0, ge=0), user=Depends(shared), db: Session=Depends(get_db)):
    _get_chamber_or_404(db, id_chamber, user)
    rows = db.query(Sensor).filter(Sensor.id_chamber == id_chamber, Sensor.id_sensor > after_id).order_by(Sensor.id_sensor).limit(21).all()
    return {'items': [SensorRead.model_validate(s) for s in rows[:20]], 'next_cursor': str(rows[19].id_sensor) if len(rows)>20 else None}

@router.post('/{id_chamber}/sensors', response_model=SensorRead, status_code=201)
def create_sensor(id_chamber: UUID, data: SensorForm, user=Depends(manager), db: Session=Depends(get_db)):
    chamber = _get_chamber_or_404(db, id_chamber, user)
    return _save(db, chamber, data)

@router.put('/{id_chamber}/sensors/{id_sensor}', response_model=SensorRead)
def update_sensor(id_chamber: UUID, id_sensor: int, data: SensorForm, user=Depends(manager), db: Session=Depends(get_db)):
    chamber = _get_chamber_or_404(db, id_chamber, user)
    return _save(db, chamber, data, _sensor(db, id_chamber, id_sensor))

@router.get('/{id_chamber}/sensors/{id_sensor}/diagnostics')
def diagnostics(id_chamber: UUID, id_sensor: int, user=Depends(shared), db: Session=Depends(get_db)):
    _get_chamber_or_404(db, id_chamber, user)
    sensor = _sensor(db, id_chamber, id_sensor)
    if db.get_bind().dialect.name == 'postgresql':
        db.execute(text("SET LOCAL statement_timeout = '5000ms'"))
    query = db.query(SensorData).filter(SensorData.id_chamber == id_chamber, SensorData.id_sensor == id_sensor)
    try:
        last = query.order_by(SensorData.timestamp.desc(), SensorData.id_data.desc()).first()
        recent = query.filter(SensorData.timestamp >= datetime.now(timezone.utc)-timedelta(hours=24)).order_by(SensorData.timestamp.desc(), SensorData.id_data.desc()).limit(20).all()
    except DBAPIError as exc:
        db.rollback()
        if getattr(exc.orig,'pgcode',None) == '57014':
            raise HTTPException(503, 'Consulta de telemetría excedió el tiempo permitido') from exc
        raise
    def reading(r):
        return {'timestamp':r.timestamp,'temperature':r.temperature,'consumption_kw':r.consumption_kw}
    return {'sensor':SensorRead.model_validate(sensor),'last_reading':reading(last) if last else None,'readings':[reading(r) for r in recent]}