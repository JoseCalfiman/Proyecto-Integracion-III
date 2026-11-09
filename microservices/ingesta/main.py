from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from routes import (
    alerts,
    chambers,
    dashboard,
    gemini,
    haccp,
    optimization,
    optimizacion,
    predictions,
)

from mqtt_client import start as start_mqtt
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

# Routers
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(optimization.router, prefix="/api/v1")
app.include_router(haccp.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(chambers.router, prefix="/api/v1")
app.include_router(gemini.router, prefix="/api/v1")
app.include_router(optimizacion.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")


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
