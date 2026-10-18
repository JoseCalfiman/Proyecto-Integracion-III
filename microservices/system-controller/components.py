import os
from typing import Awaitable, Callable, Optional

import database_checker
import kafka_checker
import mqtt_checker
from health_checker import CheckResult, Component, check_http

INGESTA_URL = os.getenv("INGESTA_URL", "http://ingesta-service:8000/health")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://dashboard-service:80/")
LATENCY_THRESHOLD_MS = int(os.getenv("LATENCY_THRESHOLD_MS", "1000"))

# Lista separada por comas. Si no se define, se usan los valores del contrato.
_ALLOWLIST_ENV = os.getenv("RESTART_ALLOWLIST")
_DEFAULT_RESTARTABLE = {"ingesta", "worker-predictivo", "worker-haccp", "worker-optimizacion"}
RESTART_ALLOWLIST = (
    {n.strip() for n in _ALLOWLIST_ENV.split(",") if n.strip()}
    if _ALLOWLIST_ENV is not None
    else _DEFAULT_RESTARTABLE
)


def _http_check(url: str, timeout: float) -> Callable[[], Awaitable[CheckResult]]:
    async def _check() -> CheckResult:
        return await check_http(url, timeout)

    return _check


def _optional_http_check(env_name: str, timeout: float = 2.0) -> Optional[Callable[[], Awaitable[CheckResult]]]:
    """Los workers hoy no tienen servidor HTTP. Si algún día exponen /health,
    basta con definir la variable (ej. WORKER_PREDICTIVO_HEALTH_URL) y se usa."""
    url = os.getenv(env_name)
    return _http_check(url, timeout) if url else None


COMPONENTS = [
    Component("ingesta", "microservice", critical=True, restartable="ingesta" in RESTART_ALLOWLIST,
              check=_http_check(INGESTA_URL, 2.0), timeout=2.0),
    Component("worker-predictivo", "worker", restartable="worker-predictivo" in RESTART_ALLOWLIST,
              check=_optional_http_check("WORKER_PREDICTIVO_HEALTH_URL")),
    Component("worker-haccp", "worker", restartable="worker-haccp" in RESTART_ALLOWLIST,
              check=_optional_http_check("WORKER_HACCP_HEALTH_URL")),
    Component("worker-optimizacion", "worker", restartable="worker-optimizacion" in RESTART_ALLOWLIST,
              check=_optional_http_check("WORKER_OPTIMIZACION_HEALTH_URL")),
    Component("dashboard", "frontend", restartable="dashboard" in RESTART_ALLOWLIST,
              check=_http_check(DASHBOARD_URL, 2.0), timeout=2.0),
    Component("kafka", "infra", critical=True, restartable="kafka" in RESTART_ALLOWLIST,
              check=kafka_checker.check, timeout=3.0),
    Component("timescaledb", "infra", critical=True, restartable="timescaledb" in RESTART_ALLOWLIST,
              check=database_checker.check, timeout=3.0),
    Component("mosquitto", "infra", critical=True, restartable="mosquitto" in RESTART_ALLOWLIST,
              check=mqtt_checker.check, timeout=3.0),
]
