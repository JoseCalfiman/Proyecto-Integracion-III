"""Comprobaciones reales y acotadas de las dependencias de ingesta."""

import logging

from fastapi.responses import JSONResponse
from sqlalchemy import text

from database import get_engine
from kafka_producer import producer

logger = logging.getLogger(__name__)


def ready():
    checks = {}
    try:
        with get_engine().connect() as connection:
            # SET LOCAL se revierte al devolver la conexión al pool.
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            connection.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        logger.warning("Readiness DB falló (%s)", type(exc).__name__)
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