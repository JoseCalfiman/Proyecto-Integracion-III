import logging
import asyncio
from fastapi import FastAPI, Header, HTTPException, Request
from components import COMPONENTS, LATENCY_THRESHOLD_MS
from health_checker import collect_status
from kubernetes_manager import KubernetesManager, RestartError
from schemas import HealthResponse, RestartResponse, SystemStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("system-controller")

k8s = KubernetesManager()

app = FastAPI(title="System Controller", version="0.2.0")


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
async def restart_component(
    name: str,
    request: Request,
):
    component = next((c for c in COMPONENTS if c.name == name), None)
    if component is None:
        raise HTTPException(status_code=404, detail=f"Componente '{name}' no existe")
    if not component.restartable:
        raise HTTPException(status_code=403, detail=f"El componente '{name}' no se puede reiniciar")

    origin = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?"))
    try:
        outcome = await asyncio.to_thread(k8s.restart_workload, component.name)
    except RestartError as exc:
        logger.warning("Reinicio de '%s' falló (%s) pedido desde %s", component.name, exc.reason, origin)
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
