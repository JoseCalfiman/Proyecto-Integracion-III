"""Comprobaciones reales y acotadas de las dependencias de ingesta."""

import threading

from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from database import DATABASE_URL
from kafka_producer import producer

probe_engine: Engine | None = None
_probe_engine_lock = threading.Lock()


def get_probe_engine() -> Engine:
    """Construye el engine de readiness la primera vez que se ejecuta el check."""
    global probe_engine
    if probe_engine is None:
        with _probe_engine_lock:
            if probe_engine is None:
                probe_engine = create_engine(
                    DATABASE_URL,
                    poolclass=NullPool,
                    connect_args={
                        "connect_timeout": 2,
                        "options": "-c statement_timeout=2000",
                    },
                )
    return probe_engine


def ready():
    checks = {}
    try:
        engine = probe_engine if probe_engine is not None else get_probe_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"

    try:
        metadata = producer.list_topics(timeout=2)
        checks["kafka"] = "ok" if metadata.brokers else "error"
    except Exception:
        checks["kafka"] = "error"

    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": checks},
    )
