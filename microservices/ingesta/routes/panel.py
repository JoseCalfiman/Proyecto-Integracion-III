"""Inventario real del panel técnico; ausencia de telemetría no implica conexión."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import technician
from database import get_db
from models import Chamber, Sensor, SensorData, GeneratedAlert
from schemas import PanelGateway, PanelSensor, PanelAlert, PanelHealth

router = APIRouter(prefix="/panel", tags=["panel"], dependencies=[Depends(technician)])


@router.get("/gateways", response_model=list[PanelGateway])
def gateways(db: Session = Depends(get_db)):
    """Una entrada por cámara, incluyendo inactivas; no inventa MCUs."""
    latest = db.query(SensorData.id_chamber, func.max(SensorData.timestamp).label("last_seen")).group_by(SensorData.id_chamber).subquery()
    counts = db.query(Sensor.id_chamber, func.count().label("total")).group_by(Sensor.id_chamber).subquery()
    rows = db.query(Chamber, latest.c.last_seen, counts.c.total).outerjoin(
        latest, latest.c.id_chamber == Chamber.id_chamber).outerjoin(
        counts, counts.c.id_chamber == Chamber.id_chamber).order_by(Chamber.id_chamber).all()
    return [PanelGateway(id=c.id_chamber, nombre=c.name, active=c.active,
                         estado="unknown", ultima_conexion=last_seen,
                         sensores=total or 0) for c, last_seen, total in rows]


@router.get("/sensores", response_model=list[PanelSensor])
def sensors(db: Session = Depends(get_db)):
    latest = db.query(SensorData.id_sensor, func.max(SensorData.timestamp).label("last_seen")).group_by(SensorData.id_sensor).subquery()
    rows = db.query(Sensor, Chamber.name, latest.c.last_seen).outerjoin(
        Chamber, Chamber.id_chamber == Sensor.id_chamber).outerjoin(
        latest, latest.c.id_sensor == Sensor.id_sensor).order_by(Sensor.id_sensor).all()
    return [PanelSensor(id=s.id_sensor, id_chamber=s.id_chamber, ubicacion=name,
                        tipo=s.sensor_type, modelo=s.model, mqtt_identifier=s.mqtt_identifier,
                        estado=s.status, ultima_lectura=last_seen) for s, name, last_seen in rows]


@router.get("/alertas", response_model=list[PanelAlert])
def alerts(db: Session = Depends(get_db)):
    rows = db.query(GeneratedAlert).order_by(
        GeneratedAlert.generation_date.desc().nullslast(), GeneratedAlert.id_alert.desc()).all()
    return [PanelAlert(id=a.id_alert, id_chamber=a.id_chamber,
                       tipo="critica" if a.severity == "critical" else
                            "advertencia" if a.severity in ("high", "medium") else "info",
                       codigo=a.severity, mensaje=a.message, fecha=a.generation_date,
                       estado=a.status, alert_type=a.alert_type) for a in rows]


@router.get("/health", response_model=PanelHealth)
def health():
    # Reutiliza probes acotados de DB/Kafka y la conexión MQTT de este proceso.
    from readiness import ready
    from mqtt_client import client

    checks = json.loads(ready().body)["checks"]
    checks["mqtt"] = "ok" if client.is_connected() else "error"
    return PanelHealth(status="ok" if all(v == "ok" for v in checks.values()) else "degraded",
                       checked_at=datetime.now(timezone.utc), checks=checks)
