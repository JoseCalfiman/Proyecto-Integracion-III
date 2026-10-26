"""Comprobaciones reales y acotadas de las dependencias de ingesta."""

from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from database import DATABASE_URL
from kafka_producer import producer

# Conexiones independientes: una conexión del pool no debe ocultar una caída
# de DB ni una probe debe esperar a que se libere el pool de la aplicación.
probe_engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={"connect_timeout": 2, "options": "-c statement_timeout=2000"},
)


def ready():
    checks = {}
    try:
        with probe_engine.connect() as connection:
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
