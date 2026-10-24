from datetime import date, datetime, time, timedelta, timezone
from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SensorData
from schemas import HistoricalMeasurement

router = APIRouter(prefix="/historial", tags=["historial"])


def _as_utc(value: Union[datetime, date]) -> datetime:
    if not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.get("", response_model=List[HistoricalMeasurement])
def get_historial(
    id_chamber: UUID,
    desde: str = Query(...),
    hasta: str = Query(...),
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """Lecturas por timestamp, en orden ascendente y con extremos incluidos.

    Las fechas sin hora usan UTC; `hasta` sin hora incluye el día completo.
    Una cámara sin lecturas devuelve una lista vacía.
    """
    try:
        desde = date.fromisoformat(desde) if len(desde) == 10 else datetime.fromisoformat(desde.replace("Z", "+00:00"))
        hasta = date.fromisoformat(hasta) if len(hasta) == 10 else datetime.fromisoformat(hasta.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="desde y hasta deben ser fechas ISO 8601")
    start, end = _as_utc(desde), _as_utc(hasta)
    if start > end:
        raise HTTPException(status_code=422, detail="desde debe ser menor o igual que hasta")

    query = db.query(SensorData).filter(
        SensorData.id_chamber == id_chamber,
        SensorData.timestamp >= start,
    )
    if isinstance(hasta, datetime):
        query = query.filter(SensorData.timestamp <= end)
    else:
        # Evita desbordar el último día representable.
        if hasta == date.max:
            query = query.filter(SensorData.timestamp <= datetime.max.replace(tzinfo=timezone.utc))
        else:
            query = query.filter(SensorData.timestamp < end + timedelta(days=1))
    return query.order_by(SensorData.timestamp.asc(), SensorData.id_data.asc()).limit(limit).all()
