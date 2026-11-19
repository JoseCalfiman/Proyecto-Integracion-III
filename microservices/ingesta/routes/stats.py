"""Estadística descriptiva de todas las lecturas del período, sin paginación."""
from datetime import date, datetime, timedelta, timezone
from statistics import fmean, median, pstdev
from math import fsum
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from database import get_db
from models import Chamber, GeneratedAlert, SavingRecommendation, SensorData
from routes.historial import _as_utc
from schemas import ChamberStats, DescriptiveStats, ChamberSummary, StatsSummary, StatsRankings, StatsRankingEntry

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


def parse_period(desde, hasta):
    try:
        start_value = date.fromisoformat(desde) if len(desde) == 10 else datetime.fromisoformat(desde.replace("Z", "+00:00"))
        end_value = date.fromisoformat(hasta) if len(hasta) == 10 else datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        start, end = _as_utc(start_value), _as_utc(end_value)
    except (ValueError, OverflowError):
        raise HTTPException(status_code=422, detail="desde y hasta deben ser fechas ISO 8601")
    if start > end:
        raise HTTPException(status_code=422, detail="desde debe ser menor o igual que hasta")

    return start, end, end_value


def filter_period(query, column, start, end, end_value):
    query = query.filter(column >= start)
    if isinstance(end_value, datetime):
        query = query.filter(column <= end)
    elif end_value == date.max:
        query = query.filter(column <= datetime.max.replace(tzinfo=timezone.utc))
    else:
        query = query.filter(column < end + timedelta(days=1))
    return query


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
    start, end, end_value = parse_period(desde, hasta)
    query = filter_period(
        db.query(SensorData.temperature, SensorData.consumption_kw).filter(
            SensorData.id_chamber == id_chamber),
        SensorData.timestamp, start, end, end_value,
    )
    rows = query.all()
    return ChamberStats(
        id_chamber=id_chamber,
        temperature=summarize(row.temperature for row in rows),
        consumption_kw=summarize(row.consumption_kw for row in rows),
    )


@router.get("/summary", response_model=StatsSummary)
def get_stats_summary(
    desde: str = Query(...),
    hasta: str = Query(...),
    top: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Resumen de cámaras activas; rankings descendentes, desempate por UUID.

    Total de consumo = suma de muestras en kW, no energía en kWh.
    Alertas por fecha de generación (cualquier estado); recomendaciones
    actualmente pendientes creadas en el período.
    """
    start, end, end_value = parse_period(desde, hasta)
    chambers = db.query(Chamber.id_chamber, Chamber.name).filter(
        Chamber.active.is_(True)).order_by(Chamber.id_chamber).all()

    def in_period(query, column):
        return filter_period(query, column, start, end, end_value)

    readings = in_period(db.query(
        SensorData.id_chamber, SensorData.temperature, SensorData.consumption_kw,
    ).join(Chamber, Chamber.id_chamber == SensorData.id_chamber).filter(
        Chamber.active.is_(True)), SensorData.timestamp).all()
    grouped = defaultdict(list)
    for row in readings:
        grouped[row.id_chamber].append(row)

    alerts = {row[0]: (row[1], row[2]) for row in in_period(db.query(
        GeneratedAlert.id_chamber, func.count(),
        func.sum(case((GeneratedAlert.severity == "critical", 1), else_=0)),
    ).join(Chamber, Chamber.id_chamber == GeneratedAlert.id_chamber).filter(
        Chamber.active.is_(True)), GeneratedAlert.generation_date
    ).group_by(GeneratedAlert.id_chamber).all()}
    pending = dict(in_period(db.query(
        SavingRecommendation.id_chamber, func.count(),
    ).join(Chamber, Chamber.id_chamber == SavingRecommendation.id_chamber).filter(
        Chamber.active.is_(True), SavingRecommendation.status == "pending"),
        SavingRecommendation.created_at,
    ).group_by(SavingRecommendation.id_chamber).all())

    summaries = []
    for chamber in chambers:
        rows = grouped[chamber.id_chamber]
        powers = [float(row.consumption_kw) for row in rows if row.consumption_kw is not None]
        count, critical = alerts.get(chamber.id_chamber, (0, 0))
        summaries.append(ChamberSummary(
            id_chamber=chamber.id_chamber, name=chamber.name,
            temperature=summarize(row.temperature for row in rows),
            consumption_kw=summarize(powers),
            consumption_total_kw=fsum(powers) if powers else None,
            alerts=count, critical_alerts=critical,
            pending_recommendations=pending.get(chamber.id_chamber, 0),
        ))

    def ranking(metric):
        candidates = [item for item in summaries if getattr(item, metric) is not None]
        candidates.sort(key=lambda item: (-getattr(item, metric), str(item.id_chamber)))
        return [StatsRankingEntry(id_chamber=item.id_chamber, name=item.name,
                                  value=getattr(item, metric)) for item in candidates[:top]]

    return StatsSummary(chambers=summaries, rankings=StatsRankings(
        top_alerts=ranking("alerts"), top_consumption=ranking("consumption_total_kw")))
