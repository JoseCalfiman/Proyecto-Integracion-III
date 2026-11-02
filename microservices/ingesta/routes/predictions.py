from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, lazyload

from database import get_db
from models import Chamber, Prediction
from schemas import PredictionRead

router = APIRouter(prefix="/predictions", tags=["predictions"])


def _predictions_for_chamber(db: Session, id_chamber: UUID):
    if db.get(Chamber, id_chamber) is None:
        raise HTTPException(status_code=404, detail="Cámara no encontrada")
    return (
        db.query(Prediction)
        .options(lazyload(Prediction.chamber))
        .filter(Prediction.id_chamber == id_chamber)
        .order_by(Prediction.calculation_date.desc().nullslast(), Prediction.id_prediction.desc())
    )


@router.get("/latest", response_model=PredictionRead)
def latest_prediction(id_chamber: UUID, db: Session = Depends(get_db)):
    """Última predicción por fecha de cálculo, con desempate por ID."""
    prediction = _predictions_for_chamber(db, id_chamber).first()
    if prediction is None:
        raise HTTPException(status_code=404, detail="No hay predicciones para esta cámara")
    return prediction


@router.get("/history", response_model=List[PredictionRead])
def prediction_history(
    id_chamber: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Historial por cámara, desde la predicción más reciente; vacío si aún no hay cálculos."""
    return _predictions_for_chamber(db, id_chamber).offset(offset).limit(limit).all()
