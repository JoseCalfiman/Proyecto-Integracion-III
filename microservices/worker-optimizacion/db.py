from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator

logger = logging.getLogger(__name__)

try:  # psycopg2 es opcional para permitir tests y ejecucion sin BD.
    import psycopg2
except ImportError:  # pragma: no cover - dependencia opcional
    psycopg2 = None

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "")


def _dsn_kwargs() -> dict[str, Any]:
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASS,
        "connect_timeout": 5,
    }


@contextmanager
def get_connection() -> Iterator[Any]:
    """Entrega una conexion psycopg2 o ``None`` si la BD no esta disponible."""
    if psycopg2 is None:
        logger.warning("[db] psycopg2 no instalado; se omite la persistencia")
        yield None
        return

    try:
        conn = psycopg2.connect(**_dsn_kwargs())
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de conexion se degrada
        logger.warning("[db] no se pudo conectar a %s:%s: %s", DB_HOST, DB_PORT, exc)
        yield None
        return

    try:
        yield conn
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        logger.warning("[db] error en transaccion: %s", exc)
    finally:
        conn.close()


def get_latest_price() -> float | None:
    """Ultimo precio registrado en ``energy_price`` o ``None``."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price_clp_kwh FROM energy_price ORDER BY ts DESC LIMIT 1"
            )
            row = cur.fetchone()
    return float(row[0]) if row else None


def save_predicted_consumption(
    target_date: date | str,
    predicted_kwh: float,
    yhat_lower: float | None = None,
    yhat_upper: float | None = None,
    model: str = "prophet",
) -> bool:
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predicted_consumption
                    (target_date, predicted_kwh, yhat_lower, yhat_upper, model)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (target_date, predicted_kwh, yhat_lower, yhat_upper, model),
            )
    return True


def save_saving_recommendations(
    target_date: date | str,
    price_clp_kwh: float,
    recommendations: list[dict[str, Any]],
) -> bool:
    if not recommendations:
        return True

    rows = [
        (
            target_date,
            rec.get("equipment"),
            rec.get("action"),
            list(rec.get("window") or []),
            rec.get("hours", 0),
            rec.get("estimated_savings", 0),
            price_clp_kwh,
        )
        for rec in recommendations
    ]

    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO saving_recommendation
                    (target_date, equipment, action, time_window, hours,
                     estimated_savings, price_clp_kwh)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    return True


def save_report(report: dict[str, Any]) -> bool:
    """Persiste prediccion de consumo y recomendaciones de ahorro."""
    target_date = report.get("target_date")
    price = report.get("forecasted_kwh_cost") or report.get("price_clp_kwh") or 0.0

    ok = True
    predicted_kwh = report.get("forecasted_kwh")
    if predicted_kwh is not None:
        ok = save_predicted_consumption(
            target_date=target_date,
            predicted_kwh=predicted_kwh,
            yhat_lower=report.get("forecasted_kwh_lower"),
            yhat_upper=report.get("forecasted_kwh_upper"),
        ) and ok

    ok = save_saving_recommendations(
        target_date=target_date,
        price_clp_kwh=price,
        recommendations=report.get("recommendations", []),
    ) and ok
    return ok
