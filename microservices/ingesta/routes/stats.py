"""Estadística descriptiva de todas las lecturas del período, sin paginación."""
from datetime import date, datetime, timedelta, timezone
from statistics import fmean, median, pstdev
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import SensorData
from routes.historial import _as_utc
from schemas import ChamberStats, DescriptiveStats

router = APIRouter(prefix="/stats", tags=["stats"])


def summarize(values) -> DescriptiveStats:
    values = sorted(float(value) for value in values if value is not None)
    n = len(values)
    if not n:
        return DescriptiveStats(n=0)

    def percentile(p):
        position = (n - 1) * p
        lower = int(position)
        upper = min(lower + 1, n - 1)
        return values[lower] + (values[upper] - values[lower]) * (position - lower)

    q1, q3 = percentile(0.25), percentile(0.75)
    return DescriptiveStats(
        n=n, media=fmean(values), mediana=median(values),
        minimo=values[0], maximo=values[-1], desviacion_estandar=pstdev(values),
        q1=q1, q3=q3, iqr=q3 - q1,
    )


@router.get("/chambers/{id_chamber}", response_model=ChamberStats)
def get_chamber_stats(
    id_chamber: UUID,
    desde: str = Query(...),
    hasta: str = Query(...),
    db: Session = Depends(get_db),
):
    """Desviación poblacional y cuartiles lineales (posición (n-1)*p).

    Fechas sin zona usan UTC. `hasta` sin hora incluye todo el día;
    con hora es inclusivo. Nulos se excluyen por variable. Sin datos se
    devuelve n=0 y métricas null; con un dato, desviación e IQR son cero.
    """
    try:
        start_value = date.fromisoformat(desde) if len(desde) == 10 else datetime.fromisoformat(desde.replace("Z", "+00:00"))
        end_value = date.fromisoformat(hasta) if len(hasta) == 10 else datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        start, end = _as_utc(start_value), _as_utc(end_value)
    except (ValueError, OverflowError):
        raise HTTPException(status_code=422, detail="desde y hasta deben ser fechas ISO 8601")
    if start > end:
        raise HTTPException(status_code=422, detail="desde debe ser menor o igual que hasta")

    query = db.query(SensorData.temperature, SensorData.consumption_kw).filter(
        SensorData.id_chamber == id_chamber, SensorData.timestamp >= start,
    )
    if isinstance(end_value, datetime):
        query = query.filter(SensorData.timestamp <= end)
    elif end_value == date.max:
        query = query.filter(SensorData.timestamp <= datetime.max.replace(tzinfo=timezone.utc))
    else:
        query = query.filter(SensorData.timestamp < end + timedelta(days=1))
    rows = query.all()
    return ChamberStats(
        id_chamber=id_chamber,
        temperature=summarize(row.temperature for row in rows),
        consumption_kw=summarize(row.consumption_kw for row in rows),
    )
