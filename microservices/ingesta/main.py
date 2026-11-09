from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from auth import shared
from routes import (
    admin,
    auth,
    historial,
    chambers,
    alerts,
    haccp,
    dashboard,
    gemini,
    optimizacion,
    predictions,
)

from mqtt_client import (
    start as start_mqtt,
)

from readiness import ready


app = FastAPI(
    title="Ingesta - Smart Fridge Monitoring"
)

app.add_api_route(
    "/ready",
    ready,
    methods=["GET"],
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
for router in (dashboard.router, haccp.router, alerts.router, chambers.router,
               gemini.router, optimizacion.router, predictions.router, historial.router):
    app.include_router(router, prefix="/api/v1", dependencies=[Depends(shared)])


# ============================================================
# MQTT
# ============================================================

@app.on_event("startup")
def startup_event():
    """
    Inicia el cliente MQTT
    en un hilo separado.
    """

    thread = threading.Thread(
        target=start_mqtt,
        daemon=True,
    )

    thread.start()

    print(
        "Cliente MQTT iniciado "
        "en segundo plano"
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }
