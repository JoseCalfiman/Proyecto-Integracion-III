from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator
from uuid import UUID

logger = logging.getLogger(__name__)

try:  # psycopg2 es opcional para permitir tests y ejecucion sin BD.
    import psycopg2
except ImportError:  # pragma: no cover - dependencia opcional
    psycopg2 = None

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "frigorifico")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")

# UUID de cámara de ejemplo, definido en database/seeds.sql.
ID_CHAMBER = os.getenv(
    "OPTIMIZATION_CHAMBER_ID", "44444444-4444-4444-4444-444444444444"
)


def _normalize_chamber_id(id_chamber: str | None = None) -> str:
    """Valida y normaliza el UUID de cámara usado por las claves foráneas."""
    try:
        return str(UUID(id_chamber or ID_CHAMBER))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("id_chamber debe ser un UUID válido") from exc


def _dsn_kwargs() -> dict[str, Any]:
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
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
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def validate_schema(id_chamber: str | None = None) -> bool:
    """Comprueba la conexión y las columnas oficiales antes de optimizar.

    Las consultas ``LIMIT 0`` validan las columnas usadas tanto en lectura como
    en escritura sin modificar datos. También verifica que la cámara configurada
    exista, para detectar un UUID que no corresponda a la BD activa.
    """
    try:
        chamber_uuid = _normalize_chamber_id(id_chamber)
        with get_connection() as conn:
            if conn is None:
                return False
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT timestamp, id_chamber, consumption_kw "
                    "FROM sensor_data LIMIT 0"
                )
                cur.execute(
                    "SELECT id_price, price_kwh, queried_at "
                    "FROM energy_price LIMIT 0"
                )
                cur.execute(
                    "SELECT id_chamber, prediction_date, predicted_consumption_kw "
                    "FROM predicted_consumption LIMIT 0"
                )
                cur.execute(
                    "SELECT id_recommendation, id_chamber, id_price, action, "
                    "expected_saving_pct, expected_saving_amount, rationale, status "
                    "FROM saving_recommendation LIMIT 0"
                )
                cur.execute(
                    "SELECT 1 FROM chambers WHERE id_chamber = %s",
                    (chamber_uuid,),
                )
                if cur.fetchone() is None:
                    logger.error(
                        "[db] el UUID %s no existe en chambers.id_chamber",
                        chamber_uuid,
                    )
                    return False
    except Exception as exc:  # noqa: BLE001 - informa schema/BD no compatibles
        logger.error("[db] validación de esquema/conexión fallida: %s", exc)
        return False
    return True


def get_latest_energy_price() -> dict[str, Any] | None:
    """Ultimo ``id_price`` y ``price_kwh`` de ``energy_price`` por ``queried_at``."""
    row = None
    with get_connection() as conn:
        if conn is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id_price, price_kwh
                FROM energy_price
                ORDER BY queried_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
    if not row:
        return None
    return {"id_price": int(row[0]), "price_kwh": float(row[1])}


def get_latest_price() -> float | None:
    """Ultimo ``price_kwh`` (CLP) de ``energy_price`` o ``None``."""
    quote = get_latest_energy_price()
    return quote["price_kwh"] if quote else None


def get_latest_price_id() -> int | None:
    """Ultimo ``id_price`` de ``energy_price`` o ``None``."""
    quote = get_latest_energy_price()
    return quote["id_price"] if quote else None


def get_consumption_history(
    days: int = 7,
    id_chamber: str | None = None,
) -> list[dict[str, Any]]:
    """Consumo diario (kWh) de los ultimos ``days`` dias para una camara.

    Convierte cada lectura de potencia (kW) a energia (kWh) considerando un
    intervalo de muestreo de 10 segundos y agrega los resultados por dia,
    filtrando por ``id_chamber``. Devuelve una lista de
    ``{"date", "consumption_kwh"}`` o una lista vacia si la BD no esta disponible.
    """
    if days <= 0:
        raise ValueError("days debe ser mayor o igual a 1")
    chamber_uuid = _normalize_chamber_id(id_chamber)

    with get_connection() as conn:
        if conn is None:
            return []
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date_trunc('day', timestamp) AS day,
                       SUM(consumption_kw * 10.0 / 3600.0) AS total_kwh
                FROM sensor_data
                WHERE id_chamber = %s
                  AND timestamp >= NOW() - (%s * INTERVAL '1 day')
                GROUP BY day
                ORDER BY day
                """,
                (chamber_uuid, days),
            )
            rows = cur.fetchall()

    return [
        {"date": row[0], "consumption_kwh": float(row[1] or 0.0)} for row in rows
    ]


def save_predicted_consumption(
    target_date: date | str,
    predicted_kwh: float,
    id_chamber: str | None = None,
) -> bool:
    chamber_uuid = _normalize_chamber_id(id_chamber)
    with get_connection() as conn:
        if conn is None:
            return False
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO predicted_consumption
                    (id_chamber, prediction_date, predicted_consumption_kw)
                VALUES (%s, %s, %s)
                """,
                (chamber_uuid, target_date, predicted_kwh),
            )
    return True


def save_saving_recommendations(
    target_date: date | str,
    price_clp_kwh: float,
    recommendations: list[dict[str, Any]],
    id_price: int | None = None,
    id_chamber: str | None = None,
) -> bool:
    if not recommendations:
        return True

    chamber_uuid = _normalize_chamber_id(id_chamber)
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
                chamber_uuid,
                id_price,
                rec.get("action"),
                rec.get("savings_percentage"),
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
                INSERT INTO saving_recommendation
                    (id_chamber, id_price, action, expected_saving_pct,
                     expected_saving_amount, rationale, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    return True


def save_report(report: dict[str, Any]) -> bool:
    """Guarda predicción y recomendaciones dentro de una sola transacción."""

    target_date = report.get("prediction_date") or report.get("target_date")

    if target_date is None:
        raise ValueError(
            "el reporte debe incluir prediction_date o target_date"
        )

    chamber_uuid = _normalize_chamber_id(
        report.get("id_chamber")
    )

    price = report.get("price_kwh")

    if price is None:
        price = report.get("forecasted_kwh_cost")

    if price is None:
        price = report.get("price_clp_kwh", 0.0)

    price = float(price or 0.0)

    predicted_kwh = report.get("predicted_kwh")

    if predicted_kwh is None:
        predicted_kwh = report.get("forecasted_kwh")

    recommendations = report.get("recommendations", [])

    with get_connection() as conn:
        if conn is None:
            return False

        with conn.cursor() as cur:

            # ------------------------------------------------
            # Predicción diaria:
            # conservar una sola fila por cámara + fecha.
            # ------------------------------------------------
            if predicted_kwh is not None:

                cur.execute(
                    """
                    SELECT id_consumption_prediction
                    FROM predicted_consumption
                    WHERE id_chamber = %s
                      AND prediction_date = %s
                    ORDER BY
                        generation_date DESC,
                        id_consumption_prediction DESC
                    """,
                    (
                        chamber_uuid,
                        target_date,
                    ),
                )

                existing = cur.fetchall()

                if existing:

                    prediction_id = int(existing[0][0])

                    cur.execute(
                        """
                        UPDATE predicted_consumption
                        SET predicted_consumption_kw = %s,
                            generation_date = NOW()
                        WHERE id_consumption_prediction = %s
                        """,
                        (
                            predicted_kwh,
                            prediction_id,
                        ),
                    )

                    # Elimina duplicados históricos del mismo día.
                    if len(existing) > 1:
                        cur.execute(
                            """
                            DELETE FROM predicted_consumption
                            WHERE id_chamber = %s
                              AND prediction_date = %s
                              AND id_consumption_prediction <> %s
                            """,
                            (
                                chamber_uuid,
                                target_date,
                                prediction_id,
                            ),
                        )

                else:

                    cur.execute(
                        """
                        INSERT INTO predicted_consumption
                            (
                                id_chamber,
                                prediction_date,
                                predicted_consumption_kw
                            )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            chamber_uuid,
                            target_date,
                            predicted_kwh,
                        ),
                    )

            # ------------------------------------------------
            # Precio de energía
            # ------------------------------------------------

            id_price = report.get("id_price")

            if id_price is None:

                cur.execute(
                    """
                    SELECT id_price
                    FROM energy_price
                    ORDER BY queried_at DESC
                    LIMIT 1
                    """
                )

                latest_price = cur.fetchone()

                if latest_price:
                    id_price = int(latest_price[0])

            # ------------------------------------------------
            # Reemplazar recomendaciones PENDING generadas
            # para esta cámara y esta misma fecha.
            # ------------------------------------------------

            target_marker = (
                f'%"target_date": "{str(target_date)}"%'
            )

            cur.execute(
                """
                DELETE FROM saving_recommendation
                WHERE id_chamber = %s
                  AND status = 'pending'
                  AND rationale LIKE %s
                """,
                (
                    chamber_uuid,
                    target_marker,
                ),
            )

            rows = []

            for rec in recommendations:

                rationale = json.dumps(
                    {
                        "target_date": str(target_date),
                        "equipment": rec.get("equipment"),
                        "window": rec.get("window"),
                        "hours": rec.get("hours"),
                        "price_clp_kwh": price,
                    },
                    ensure_ascii=False,
                )

                rows.append(
                    (
                        chamber_uuid,
                        id_price,
                        rec.get("action"),
                        rec.get("savings_percentage"),
                        rec.get("estimated_savings", 0),
                        rationale,
                        "pending",
                    )
                )

            if rows:

                cur.executemany(
                    """
                    INSERT INTO saving_recommendation
                        (
                            id_chamber,
                            id_price,
                            action,
                            expected_saving_pct,
                            expected_saving_amount,
                            rationale,
                            status
                        )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    rows,
                )

    return True
