from fastapi import FastAPI

from app.api.indicators import router as indicators_router
from app.api.precipitation import router as precipitation_router
from app.api.rainfall_analysis import router as rainfall_analysis_router
from app.api.baseline import router as baseline_router
from app.api.anomaly import router as anomaly_router

app = FastAPI(
    title="Hulaw World",
    description="Global Drought Intelligence Platform",
    version="0.1.0"
)

app.include_router(indicators_router)
app.include_router(precipitation_router)
app.include_router(rainfall_analysis_router)
app.include_router(baseline_router)
app.include_router(anomaly_router)

@app.get("/")
def root():
    return {
        "project": "Hulaw",
        "description": "Global Drought Intelligence Platform",
        "status": "running"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Check healthy-en healthy static",
    }