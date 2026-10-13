from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import get_db
from models import Chamber, GeneratedAlert, SavingRecommendation, SensorData
from schemas import DashboardLive

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Una lectura se considera "en vivo" si llegó dentro de esta ventana
LIVE_WINDOW_MINUTES = 1


def _count_active_chambers(db: Session) -> int:
    """Cantidad de cámaras con active = true."""
    return db.query(func.count(Chamber.id_chamber)).filter(Chamber.active.is_(True)).scalar() or 0


def _count_active_alerts(db: Session) -> int:
    """Cantidad de alertas que aún no han sido reconocidas (status = active)."""
    return (
        db.query(func.count(GeneratedAlert.id_alert))
        .filter(GeneratedAlert.status == "active")
        .scalar()
        or 0
    )


def _current_consumption_kw(db: Session) -> float:
    """Potencia actual: suma de la última lectura de cada cámara dentro de la ventana en vivo."""
    since = datetime.now(timezone.utc) - timedelta(minutes=LIVE_WINDOW_MINUTES)
    latest_per_chamber = (
        db.query(SensorData.id_chamber, SensorData.consumption_kw)
        .filter(SensorData.timestamp >= since, SensorData.consumption_kw.isnot(None))
        .distinct(SensorData.id_chamber)
        .order_by(SensorData.id_chamber, SensorData.timestamp.desc())
        .subquery()
    )
    total = db.query(func.sum(latest_per_chamber.c.consumption_kw)).scalar()
    return float(total or 0)


def _estimated_savings_clp(db: Session) -> float:
    """Ahorro de la tanda más reciente de recomendaciones pendientes (evita sumar tandas antiguas)."""
    latest = (
        db.query(func.max(SavingRecommendation.created_at))
        .filter(SavingRecommendation.status == "pending")
        .scalar()
    )
    if latest is None:
        return 0.0
    total = (
        db.query(func.sum(SavingRecommendation.expected_saving_amount))
        .filter(
            SavingRecommendation.status == "pending",
            SavingRecommendation.created_at == latest,
        )
        .scalar()
    )
    return float(total or 0)


# Permisos: técnico y gerente (TODO: auth; el ahorro quizá solo para gerente)
@router.get("/live", response_model=DashboardLive)
def dashboard_live(db: Session = Depends(get_db)):
    """Métricas resumen para las tarjetas del dashboard."""
    return DashboardLive(
        active_chambers=_count_active_chambers(db),
        active_alerts=_count_active_alerts(db),
        total_consumption_kw=_current_consumption_kw(db),
        estimated_savings_clp=_estimated_savings_clp(db),
    )


# ============================================================
# SERIES DE TIEMPO PARA LOS GRÁFICOS (gerente y técnico)
# ============================================================
class TemperaturePoint(BaseModel):
    timestamp: datetime
    id_chamber: UUID
    chamber_name: Optional[str] = None
    temperature: float


class ConsumptionPoint(BaseModel):
    day: date
    kwh: float


# Zona horaria usada para agrupar por día (la BD guarda timestamptz en UTC)
LOCAL_TZ = "America/Santiago"


# Permisos: técnico y gerente
@router.get("/temperature", response_model=List[TemperaturePoint])
def dashboard_temperature(
    minutes: int = Query(default=120, ge=5, le=1440),
    db: Session = Depends(get_db),
):
    """Temperatura promedio por cámara en los últimos `minutes` minutos (~60 puntos por cámara)."""
    bucket_min = max(1, minutes // 60)
    rows = db.execute(
        text(
            """
            SELECT time_bucket(make_interval(mins => :bucket), s.timestamp) AS bucket,
                   s.id_chamber,
                   c.name AS chamber_name,
                   AVG(s.temperature) AS temperature
            FROM sensor_data s
            JOIN chambers c ON c.id_chamber = s.id_chamber
            WHERE s.timestamp >= now() - make_interval(mins => :minutes)
              AND s.temperature IS NOT NULL
            GROUP BY bucket, s.id_chamber, c.name
            ORDER BY bucket
            """
        ),
        {"bucket": bucket_min, "minutes": minutes},
    ).all()
    return [
        TemperaturePoint(
            timestamp=r.bucket,
            id_chamber=r.id_chamber,
            chamber_name=r.chamber_name,
            temperature=float(r.temperature),
        )
        for r in rows
    ]


# Permisos: técnico y gerente
@router.get("/consumption", response_model=List[ConsumptionPoint])
def dashboard_consumption(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Consumo eléctrico diario (kWh) de las últimas `days` jornadas, sumando todas las cámaras.

    kWh = suma de (kW x tiempo hasta la siguiente lectura). El tiempo se limita a 5 min por
    lectura para que un corte de datos no infle el consumo. Los días sin datos salen con 0.
    """
    rows = db.execute(
        text(
            """
            WITH r AS (
                SELECT timestamp, consumption_kw,
                       LEAD(timestamp) OVER (PARTITION BY id_chamber ORDER BY timestamp) AS next_ts
                FROM sensor_data
                WHERE timestamp >= now() - make_interval(days => :days + 1)
                  AND consumption_kw IS NOT NULL
            ),
            daily AS (
                SELECT CAST(timestamp AT TIME ZONE :tz AS date) AS day,
                       SUM(consumption_kw * LEAST(EXTRACT(EPOCH FROM (next_ts - timestamp)), 300) / 3600.0) AS kwh
                FROM r
                WHERE next_ts IS NOT NULL
                GROUP BY 1
            )
            SELECT CAST(now() AT TIME ZONE :tz AS date) - g.i AS day,
                   COALESCE(d.kwh, 0) AS kwh
            FROM generate_series(0, :days - 1) AS g(i)
            LEFT JOIN daily d ON d.day = CAST(now() AT TIME ZONE :tz AS date) - g.i
            ORDER BY day
            """
        ),
        {"days": days, "tz": LOCAL_TZ},
    ).all()
    return [ConsumptionPoint(day=r.day, kwh=round(float(r.kwh), 2)) for r in rows]
