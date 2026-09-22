from __future__ import annotations

import json
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

# Contexto de negocio requerido por el esquema (FK NOT NULL).
CHAMBER_ID = int(os.getenv("OPTIMIZATION_CHAMBER_ID", "1"))
COMPANY_ID = int(os.getenv("OPTIMIZATION_COMPANY_ID", "1"))


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
    """Ultimo precio registrado en ``energy_price`` (CLP/kWh) o ``None``."""
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price_kwh FROM energy_price ORDER BY queried_at DESC LIMIT 1"
            )
            row = cur.fetchone()
    return float(row[0]) if row else None


def get_latest_price_id() -> int | None:
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT price_id FROM energy_price ORDER BY queried_at DESC LIMIT 1"
            )
            row = cur.fetchone()
    return int(row[0]) if row else None


def save_predicted_consumption(
    target_date: date | str,
    predicted_kwh: float,
    chamber_id: int | None = None,
) -> bool:
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predicted_consumption
                    (chamber_id, prediction_date, predicted_consumption_kw)
                VALUES (%s, %s, %s)
                """,
                (chamber_id or CHAMBER_ID, target_date, predicted_kwh),
            )
    return True


def save_saving_recommendations(
    target_date: date | str,
    price_clp_kwh: float,
    recommendations: list[dict[str, Any]],
    price_id: int | None = None,
    company_id: int | None = None,
    chamber_id: int | None = None,
) -> bool:
    if not recommendations:
        return True

    rows = []
    for rec in recommendations:
        justification = json.dumps(
            {
                "target_date": str(target_date),
                "equipment": rec.get("equipment"),
                "window": rec.get("window"),
                "hours": rec.get("hours"),
                "price_clp_kwh": price_clp_kwh,
            },
            ensure_ascii=False,
        )
        rows.append(
            (
                company_id or COMPANY_ID,
                chamber_id or CHAMBER_ID,
                price_id,
                rec.get("action"),
                rec.get("estimated_savings", 0),
                justification,
                "pending",
            )
        )

    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO saving_recommendations
                    (company_id, chamber_id, price_id, action, amount_clp,
                     justification, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    return True


def save_report(report: dict[str, Any]) -> bool:
    """Persiste la prediccion de consumo y las recomendaciones de ahorro."""
    target_date = report.get("target_date")
    price = report.get("forecasted_kwh_cost") or report.get("price_clp_kwh") or 0.0

    ok = True
    predicted_kwh = report.get("forecasted_kwh")
    if predicted_kwh is not None:
        ok = save_predicted_consumption(
            target_date=target_date,
            predicted_kwh=predicted_kwh,
        ) and ok

    ok = save_saving_recommendations(
        target_date=target_date,
        price_clp_kwh=price,
        recommendations=report.get("recommendations", []),
        price_id=get_latest_price_id(),
    ) and ok
    return ok
