from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import chambers, alerts
from routes import haccp, dashboard

app = FastAPI(title="Ingesta - Smart Fridge Monitoring")

app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(haccp.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(chambers.router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}