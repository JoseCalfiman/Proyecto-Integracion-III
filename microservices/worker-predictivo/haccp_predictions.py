import logging
from typing import Optional
from sqlalchemy import MetaData, Table, select
from db import engine
from models import GeneratedPrediction

_metadata = MetaData()
_haccp_rules_table: Optional[Table] = None

def _get_haccp_rules_table() -> Table:
    global _haccp_rules_table
    if _haccp_rules_table is None:
        _haccp_rules_table = Table(
            "haccp_rules", _metadata, autoload_with=engine
        )
    return _haccp_rules_table

def obtener_regla_haccp_activa(session, chamber_id) -> Optional[dict]:
    try:
        haccp_rules = _get_haccp_rules_table()
        stmt = (
            select(
                haccp_rules.c.max_absolute_temp,
                haccp_rules.c.tolerance_time_min,
                haccp_rules.c.severity,
            )
            .where(haccp_rules.c.id_chamber == chamber_id)
            .where(haccp_rules.c.active.is_(True))
            .order_by(haccp_rules.c.review_date.desc())
            .limit(1)
        )
        fila = session.execute(stmt).first()
    except Exception:
        logging.exception(
            f"No se pudo leer haccp_rules para id_chamber={chamber_id}"
        )
        return None

    if fila is None:
        return None

    return {
        "max_absolute_temp": float(fila.max_absolute_temp),
        "tolerance_time_min": (
            float(fila.tolerance_time_min)
            if fila.tolerance_time_min is not None
            else None
        ),
        "severity": fila.severity or "medium",
    }

def guardar_prediccion(session, chamber_id, calculated_slope: Optional[float], projected_temperature: Optional[float],
    remaining_time_min: Optional[float],
    risk_level: str, ) -> GeneratedPrediction:
    
    prediccion = GeneratedPrediction(
        chamber_id=chamber_id,
        calculated_slope=calculated_slope,
        projected_temperature=projected_temperature,
        remaining_time_min=remaining_time_min,
        risk_level=risk_level,
    )
    session.add(prediccion)
    session.commit()
    session.refresh(prediccion)
    return prediccion