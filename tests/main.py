
"""

API FastAPI para Smart Fridge. Corre en tu PC y se conecta a PostgreSQL
en la instancia EC2 (a traves de un tunel SSH).

Ejecutar:
    uvicorn main:app --reload
Documentacion interactiva: http://127.0.0.1:8000/docs

"""
import os
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv()  # lee un archivo .env si existe

pool: Optional[ThreadedConnectionPool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    password = os.environ.get("PGPASSWORD")
    if not password:
        raise RuntimeError("Falta PGPASSWORD (variable de entorno o archivo .env)")
    pool = ThreadedConnectionPool(
        1, 5,
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "miusuario"),
        dbname=os.environ.get("PGDATABASE", "miapp"),
        password=password,
        connect_timeout=8,
    )
    yield
    pool.closeall()


app = FastAPI(title="Smart Fridge API", lifespan=lifespan)


@contextmanager
def db():
    """Entrega un cursor; hace rollback si hay error y devuelve la conexion al pool."""
    conn = pool.getconn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield conn, cur
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ------------------------------------------------------------------ modelos
class Reading(BaseModel):
    sensor: str = Field(..., examples=["fridge/cam1/sensor01"], description="mqtt_identifier del sensor")
    temperature: float = Field(..., examples=[3.4])
    consumption_kw: Optional[float] = Field(None, examples=[1.25])
    timestamp: Optional[datetime] = Field(None, description="Si se omite, se usa la hora del servidor")


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    with db() as (conn, cur):
        cur.execute("SELECT version() AS pg, "
                    "(SELECT extversion FROM pg_extension WHERE extname='timescaledb') AS timescaledb")
        return {"status": "ok", **cur.fetchone()}


@app.get("/chambers")
def list_chambers():
    with db() as (conn, cur):
        cur.execute("""
            SELECT c.id_chamber, c.name, c.location, c.active,
                   r.min_absolute_temp::float AS min_temp,
                   r.max_absolute_temp::float AS max_temp,
                   r.tolerance_time_min
            FROM chambers c
            LEFT JOIN haccp_rules r ON r.id_chamber = c.id_chamber AND r.active
            ORDER BY c.name
        """)
        return cur.fetchall()


@app.get("/chambers/{id_chamber}/latest")
def latest_reading(id_chamber: UUID):
    with db() as (conn, cur):
        cur.execute("""
            SELECT timestamp, temperature::float, consumption_kw::float
            FROM sensor_data
            WHERE id_chamber = %s
            ORDER BY timestamp DESC LIMIT 1
        """, (str(id_chamber),))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Sin lecturas para esa camara")
        return row


@app.get("/chambers/{id_chamber}/readings")
def readings(
    id_chamber: UUID,
    hours: int = Query(1, ge=1, le=168, description="Ventana hacia atras"),
    bucket_minutes: int = Query(5, ge=1, le=1440, description="Tamano del bucket"),
):
    with db() as (conn, cur):
        cur.execute("""
            SELECT time_bucket(make_interval(mins => %s), timestamp) AS bucket,
                   round(avg(temperature), 2)::float AS temp_avg,
                   min(temperature)::float AS temp_min,
                   max(temperature)::float AS temp_max,
                   round(avg(consumption_kw), 3)::float AS kw_avg
            FROM sensor_data
            WHERE id_chamber = %s
              AND timestamp > now() - make_interval(hours => %s)
            GROUP BY 1 ORDER BY 1
        """, (bucket_minutes, str(id_chamber), hours))
        return cur.fetchall()


@app.get("/alerts")
def alerts(status: Optional[Literal["active", "acknowledged", "resolved"]] = "active"):
    with db() as (conn, cur):
        cur.execute("""
            SELECT a.id_alert, c.name AS chamber, a.alert_type, a.severity,
                   a.status, a.message, a.generation_date
            FROM generated_alerts a
            JOIN chambers c USING (id_chamber)
            WHERE (%s::text IS NULL OR a.status = %s)
            ORDER BY a.generation_date DESC
        """, (status, status))
        return cur.fetchall()


@app.get("/predictions/latest")
def latest_predictions():
    with db() as (conn, cur):
        cur.execute("""
            SELECT DISTINCT ON (p.id_chamber)
                   c.name AS chamber,
                   p.calculated_slope::float, p.projected_temperature::float,
                   p.remaining_time_min::float, p.risk_level, p.calculation_date
            FROM predictions p
            JOIN chambers c USING (id_chamber)
            ORDER BY p.id_chamber, p.calculation_date DESC
        """)
        return cur.fetchall()


@app.post("/ingest", status_code=201)
def ingest(r: Reading):
    """Inserta una lectura (equivalente a un mensaje MQTT) y la registra en ingestion_log."""
    with db() as (conn, cur):
        cur.execute("SELECT id_sensor, id_chamber FROM sensors WHERE mqtt_identifier = %s", (r.sensor,))
        sensor = cur.fetchone()

        if not sensor:
            cur.execute("""
                INSERT INTO ingestion_log (received_payload, processing_status, error_message)
                VALUES (%s, 'error', 'sensor desconocido')
            """, (r.model_dump_json(),))
            conn.commit()
            raise HTTPException(404, f"Sensor '{r.sensor}' no existe")

        try:
            cur.execute("""
                INSERT INTO sensor_data (timestamp, id_chamber, id_sensor, temperature, consumption_kw)
                VALUES (COALESCE(%s, now()), %s, %s, %s, %s)
            """, (r.timestamp, sensor["id_chamber"], sensor["id_sensor"],
                  r.temperature, r.consumption_kw))
        except psycopg2.DataError as e:  # p. ej. valor fuera del rango NUMERIC
            conn.rollback()
            cur.execute("""
                INSERT INTO ingestion_log (id_chamber, received_payload, processing_status, error_message)
                VALUES (%s, %s, 'error', %s)
            """, (sensor["id_chamber"], r.model_dump_json(), str(e).splitlines()[0]))
            conn.commit()
            raise HTTPException(422, "Valor invalido para la base de datos")

        cur.execute("""
            INSERT INTO ingestion_log (id_chamber, received_payload, processing_status)
            VALUES (%s, %s, 'success')
        """, (sensor["id_chamber"], r.model_dump_json()))
        conn.commit()
        return {"status": "ok", "id_chamber": sensor["id_chamber"]}