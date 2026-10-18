import logging

from fastapi import FastAPI, HTTPException

from components import COMPONENTS, LATENCY_THRESHOLD_MS
from health_checker import collect_status
from kubernetes_manager import KubernetesManager
from schemas import HealthResponse, SystemStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("system-controller")

k8s = KubernetesManager()

app = FastAPI(title="System Controller", version="0.1.0")


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
