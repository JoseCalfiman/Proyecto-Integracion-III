import json
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import SavingRecommendation
from schemas import SavingRecommendationRead

router = APIRouter(prefix="/optimizacion", tags=["optimizacion"])

EQUIPMENT_NAMES = {
    "camaras_2_y_3": "Cámaras 2 y 3",
    "eq_climatizacion_zona_b": "Climatización zona B",
}


def _recommendation_details(record: SavingRecommendation) -> dict[str, Any]:
    """Adapta una recomendación persistida al contrato de la vista de ahorro."""
    rationale: dict[str, Any] = {}
    try:
        parsed = json.loads(record.rationale or "{}")
        if isinstance(parsed, dict):
            rationale = parsed
    except (TypeError, json.JSONDecodeError):
        pass

    equipment = rationale.get("equipment")
    equipment_name = EQUIPMENT_NAMES.get(equipment, equipment or "equipo")
    action = (record.action or "optimizar").replace("_", " ")
    title = f"{action.capitalize()} {equipment_name}"

    window = rationale.get("window") or []
    hours = rationale.get("hours")
    target_date = rationale.get("target_date")
    details = [f"Acción recomendada: {action} {equipment_name}."]
    if hours is not None:
        details.append(f"Duración estimada: {hours} horas.")
    if len(window) == 2:
        details.append(f"Ventana de alto costo: {window[0]}–{window[1]}.")
    if target_date:
        details.append(f"Fecha de aplicación sugerida: {target_date}.")

    icon = "thermometer" if "climatizacion" in str(equipment) else "snowflake"
    return {
        "id": record.id_recommendation,
        "titulo": title,
        "descripcion": " ".join(details),
        "prioridad": "media",
        "porcentaje_ahorro": float(record.expected_saving_pct or 0),
        "monto_clp": float(record.expected_saving_amount or 0),
        "icono": icon,
        "status": record.status,
        "created_at": record.created_at,
    }


@router.get("/recomendaciones", response_model=List[SavingRecommendationRead])
def list_saving_recommendations(db: Session = Depends(get_db)):
    """Devuelve las recomendaciones pendientes de la última optimización."""
    latest = (
        db.query(func.max(SavingRecommendation.created_at))
        .filter(SavingRecommendation.status == "pending")
        .scalar()
    )
    if latest is None:
        return []

    records = (
        db.query(SavingRecommendation)
        .filter(
            SavingRecommendation.status == "pending",
            SavingRecommendation.created_at == latest,
        )
        .order_by(SavingRecommendation.id_recommendation)
        .all()
    )
    return [_recommendation_details(record) for record in records]
