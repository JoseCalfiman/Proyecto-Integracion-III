from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
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