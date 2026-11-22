import logging
import asyncio
import os
import re
import time
from fastapi import FastAPI, Header, HTTPException, Request
from components import COMPONENTS, LATENCY_THRESHOLD_MS
from health_checker import collect_status
from kubernetes_manager import KubernetesManager, RestartError
from schemas import HealthResponse, RestartResponse, RolloutResponse, SystemStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("system-controller")

k8s = KubernetesManager()

app = FastAPI(title="System Controller", version="0.2.0")

# Nombres válidos de recursos de Kubernetes.
_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
# Espera mínima entre dos reinicios del mismo componente.
RESTART_COOLDOWN_SECONDS = float(os.getenv("RESTART_COOLDOWN_SECONDS", "30"))
_last_restart: dict = {}


def _resolve_restartable(name: str):
    """Valida el nombre y devuelve el componente SOLO si se puede reiniciar.
    400 = nombre mal formado, 404 = no existe, 403 = existe pero no está permitido."""
    if len(name) > 63 or not _NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Nombre de componente inválido")
    component = next((c for c in COMPONENTS if c.name == name), None)
    if component is None:
        raise HTTPException(status_code=404, detail=f"Componente '{name}' no existe")
    if not component.restartable:
        raise HTTPException(status_code=403, detail=f"El componente '{name}' no se puede reiniciar")
    return component


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health():
    return HealthResponse()


@app.get("/api/v1/system/status", response_model=SystemStatus, tags=["system"])
async def system_status():
    try:
        return await collect_status(COMPONENTS, k8s, LATENCY_THRESHOLD_MS)
    except Exception:
        logger.exception("No se pudo calcular el estado del sistema")
        raise HTTPException(status_code=503, detail="No se pudo calcular el estado del sistema")

@app.post(
    "/api/v1/system/components/{name}/restart",
    response_model=RestartResponse,
    status_code=202,
    tags=["system"],
)
async def restart_component(name: str, request: Request):
    component = _resolve_restartable(name)

    origin = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?"))

    # Espera entre reinicios: se marca ANTES de llamar a Kubernetes (no hay await entre medio).
    now = time.monotonic()
    wait = RESTART_COOLDOWN_SECONDS - (now - _last_restart.get(component.name, -1e9))
    if wait > 0:
        logger.warning("Reinicio de '%s' rechazado por espera (%.0fs) desde %s", component.name, wait, origin)
        raise HTTPException(
            status_code=429,
            detail=f"'{component.name}' ya se reinició hace poco. Espera {int(wait) + 1} s.",
            headers={"Retry-After": str(int(wait) + 1)},
        )
    _last_restart[component.name] = now

    try:
        outcome = await asyncio.to_thread(k8s.restart_workload, component.name)
    except RestartError as exc:
        _last_restart.pop(component.name, None)  # si falló, se puede reintentar de inmediato
        logger.warning("Reinicio de '%s' falló (%s) pedido desde %s", component.name, exc.reason, origin)
        if exc.reason == "not_allowed":
            raise HTTPException(status_code=403, detail=f"El componente '{component.name}' no se puede reiniciar")
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail=f"El workload '{component.name}' no existe en Kubernetes")
        if exc.reason == "forbidden":
            raise HTTPException(
                status_code=503,
                detail=f"El Controller no tiene permiso en Kubernetes para reiniciar '{component.name}'",
            )
        raise HTTPException(status_code=503, detail="No se pudo contactar la API de Kubernetes")

    logger.info("Reinicio solicitado: %s (%s) desde %s", component.name, outcome.kind, origin)
    return RestartResponse(name=component.name, requested_at=outcome.requested_at)


@app.get(
    "/api/v1/system/components/{name}/rollout",
    response_model=RolloutResponse,
    tags=["system"],
)
async def rollout_status(name: str):
    """Feedback del reinicio: IN_PROGRESS mientras Kubernetes recrea los pods, COMPLETE al terminar."""
    component = _resolve_restartable(name)
    try:
        info = await asyncio.to_thread(k8s.get_rollout_status, component.name)
    except RestartError as exc:
        if exc.reason == "not_allowed":
            raise HTTPException(status_code=403, detail=f"El componente '{component.name}' no se puede reiniciar")
        if exc.reason == "not_found":
            raise HTTPException(status_code=404, detail=f"El workload '{component.name}' no existe en Kubernetes")
        raise HTTPException(status_code=503, detail="No se pudo contactar la API de Kubernetes")
    return RolloutResponse(name=component.name, phase=info.phase, desired=info.desired,
                           updated=info.updated, ready=info.ready, available=info.available,
                           message=info.message)