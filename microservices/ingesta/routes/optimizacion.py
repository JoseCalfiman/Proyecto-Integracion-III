import json
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from database import get_db
from models import PredictedConsumption, SavingRecommendation
from schemas import (
    ConsumptionForecastRead,
    SavingRecommendationRead,
    SavingRecommendationStatusUpdate,
)

router = APIRouter(prefix="/optimizacion", tags=["optimizacion"])

EQUIPMENT_NAMES = {
    "camaras_2_y_3": "Cámaras 2 y 3",
    "eq_climatizacion_zona_b": "Climatización zona B",
}


def _recommendation_is_actionable():
    return or_(
        and_(
            SavingRecommendation.expected_saving_pct.isnot(None),
            SavingRecommendation.expected_saving_pct > 0,
            SavingRecommendation.expected_saving_amount.isnot(None),
            SavingRecommendation.expected_saving_amount > 0,
        ),
        SavingRecommendation.rationale.like('%"exception_reason"%'),
    )


def _recommendation_details(record: SavingRecommendation) -> dict[str, Any]:
    """Adapta el registro persistido al contrato consumido por el dashboard."""
    rationale: dict[str, Any] = {}
    try:
        parsed = json.loads(record.rationale or "{}")
        if isinstance(parsed, dict):
            rationale = parsed
    except (TypeError, json.JSONDecodeError):
        pass

    equipment = rationale.get("equipment")
    equipment_name = EQUIPMENT_NAMES.get(equipment, equipment or "equipo")
    action_code = rationale.get("action_code") or record.action or "optimizar"
    action = str(action_code).replace("_", " ")
    title = rationale.get("title") or record.action
    if not title:
        title = f"{action.capitalize()} {equipment_name}"

    return {
        "id": record.id_recommendation,
        "id_chamber": record.id_chamber,
        "titulo": title,
        "descripcion": record.rationale,
        "prioridad": rationale.get("priority", "media"),
        "porcentaje_ahorro": (
            float(record.expected_saving_pct)
            if record.expected_saving_pct is not None else None
        ),
        "monto_clp": (
            float(record.expected_saving_amount)
            if record.expected_saving_amount is not None else None
        ),
        "icono": "thermometer" if "climatizacion" in str(equipment) else "snowflake",
        "status": record.status,
        "created_at": record.created_at,
    }


@router.get("/recommendations", response_model=List[SavingRecommendationRead])
def recommendations(id_chamber: Optional[UUID] = None, db: Session = Depends(get_db)):
    """Devuelve recomendaciones pendientes con ahorro o justificación explícita."""
    actionable = _recommendation_is_actionable()
    query = db.query(SavingRecommendation).filter(
        SavingRecommendation.status == "pending",
        actionable,
    )
    if id_chamber is not None:
        query = query.filter(SavingRecommendation.id_chamber == id_chamber)
    rows = query.order_by(
        SavingRecommendation.id_recommendation.desc()
    ).all()
    return [SavingRecommendationRead.model_validate(_recommendation_details(row)) for row in rows]


@router.patch(
    "/recommendations/{id_recommendation}/status",
    response_model=SavingRecommendationRead,
)
def update_recommendation_status(
    id_recommendation: int,
    data: SavingRecommendationStatusUpdate,
    db: Session = Depends(get_db),
):
    """Persiste el cierre de una recomendación pendiente."""
    recommendation = db.get(SavingRecommendation, id_recommendation)
    if recommendation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recomendación no encontrada")
    if recommendation.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La recomendación debe estar en estado 'pending' (estado actual: '{recommendation.status}')",
        )

    recommendation.status = data.status
    recommendation.applied_at = (
        datetime.now(timezone.utc) if data.status == "applied" else None
    )
    db.commit()
    db.refresh(recommendation)
    return SavingRecommendationRead.model_validate(_recommendation_details(recommendation))


@router.get("/forecast", response_model=List[ConsumptionForecastRead])
def forecast(id_chamber: Optional[UUID] = None, db: Session = Depends(get_db)):
    """Pronóstico diario en kWh, sumado por fecha para las cámaras seleccionadas.

    El worker persiste energía diaria (kWh) en la columna histórica
    ``predicted_consumption_kw``; el sufijo ``_kw`` es legado y no representa
    potencia instantánea.
    No hay datos históricos ni bandas de confianza en esta tabla.
    """
    query = db.query(
        PredictedConsumption.prediction_date,
        func.sum(PredictedConsumption.predicted_consumption_kw).label("pronostico"),
    ).filter(
        PredictedConsumption.prediction_date.isnot(None),
        or_(
            PredictedConsumption.predicted_consumption_kw.is_(None),
            PredictedConsumption.predicted_consumption_kw >= 0,
        ),
    )
    if id_chamber is not None:
        query = query.filter(PredictedConsumption.id_chamber == id_chamber)
    rows = query.group_by(PredictedConsumption.prediction_date).order_by(
        PredictedConsumption.prediction_date.asc()
    ).all()
    return [ConsumptionForecastRead(date=row.prediction_date, pronostico=row.pronostico) for row in rows]
