import os
from typing import Tuple

import psycopg2

from health_checker import CheckResult, layered_check


def _settings() -> dict:
    return dict(
        host=os.getenv("PGHOST") or os.getenv("DB_HOST", "timescaledb-service"),
        port=int(os.getenv("PGPORT") or os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("PGDATABASE") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB"),
        user=os.getenv("PGUSER") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER"),
        password=os.getenv("PGPASSWORD") or os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD"),
    )


def classify_connect_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "authentication failed" in msg or "no password supplied" in msg:
        return "Autenticación rechazada"
    if "does not exist" in msg:
        return "La base de datos o el usuario no existe"
    return "No se pudo abrir la conexión"


def _deep(timeout: float) -> Tuple[bool, str]:
    cfg = _settings()
    try:
        conn = psycopg2.connect(
            **cfg,
            connect_timeout=max(2, int(timeout)),  
            options="-c statement_timeout=2000",
            application_name="system-controller",
        )
    except psycopg2.OperationalError as exc:
        return False, classify_connect_error(exc)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    finally:
        conn.close()
    return True, "SELECT 1 OK"


async def check() -> CheckResult:
    cfg = _settings()
    return await layered_check(cfg["host"], cfg["port"], timeout=3.0, deep=_deep)
