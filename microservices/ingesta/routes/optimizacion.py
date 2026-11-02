from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import PredictedConsumption, SavingRecommendation
from schemas import ConsumptionForecastRead, SavingRecommendationRead

router = APIRouter(prefix="/optimizacion", tags=["optimizacion"])


@router.get("/recommendations", response_model=List[SavingRecommendationRead])
def recommendations(id_chamber: Optional[UUID] = None, db: Session = Depends(get_db)):
    """Ahorros pendientes, más recientes primero; opcionalmente de una cámara."""
    query = db.query(SavingRecommendation).filter(SavingRecommendation.status == "pending")
    if id_chamber is not None:
        query = query.filter(SavingRecommendation.id_chamber == id_chamber)
    rows = query.order_by(
        SavingRecommendation.created_at.desc(), SavingRecommendation.id_recommendation.desc()
    ).all()
    return [SavingRecommendationRead(
        id=row.id_recommendation,
        id_chamber=row.id_chamber,
        titulo=row.action,
        descripcion=row.rationale,
        porcentaje_ahorro=row.expected_saving_pct,
        monto_clp=row.expected_saving_amount,
        status=row.status,
        created_at=row.created_at,
    ) for row in rows]


@router.get("/forecast", response_model=List[ConsumptionForecastRead])
def forecast(id_chamber: Optional[UUID] = None, db: Session = Depends(get_db)):
    """Pronóstico diario en kWh, sumado por fecha para las cámaras seleccionadas.

    El worker persiste kWh diarios en la columna histórica predicted_consumption_kw.
    No hay datos históricos ni bandas de confianza en esta tabla.
    """
    query = db.query(
        PredictedConsumption.prediction_date,
        func.sum(PredictedConsumption.predicted_consumption_kw).label("pronostico"),
    ).filter(PredictedConsumption.prediction_date.isnot(None))
    if id_chamber is not None:
        query = query.filter(PredictedConsumption.id_chamber == id_chamber)
    rows = query.group_by(PredictedConsumption.prediction_date).order_by(
        PredictedConsumption.prediction_date.asc()
    ).all()
    return [ConsumptionForecastRead(date=row.prediction_date, pronostico=row.pronostico) for row in rows]
