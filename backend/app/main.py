from fastapi import FastAPI

from app.api.indicators import router as indicators_router
from app.api.precipitation import router as precipitation_router
from app.api.rainfall_analysis import router as rainfall_analysis_router
from app.api.baseline import router as baseline_router
from app.api.anomaly import router as anomaly_router
from app.api.timeline import router as timeline_router 
from app.api.soil_moisture import router as soil_moisture_router
from app.api.soil_moisture_history import router as smap_history_router
from app.api.vegetation import router as vegetation_router

app = FastAPI(
    title="Hulaw World",
    description="Global Drought Intelligence Platform",
    version="0.1.0"
)

app.include_router(indicators_router) # ("/api/indicators")
app.include_router(precipitation_router) # ("/api/precipitation")
app.include_router(rainfall_analysis_router) # ("/api/analysis/rainfall/monthly")
app.include_router(baseline_router) # ("/api/analysis/rainfall/baseline")
app.include_router(anomaly_router) # ("/api/analysis/rainfall/anomaly")
app.include_router(timeline_router) # ("/api/analysis/rainfall/timeline")
app.include_router(soil_moisture_router) # ("/api/soil-moisture")
app.include_router(smap_history_router) # ("/api/soil-moisture/history")
app.include_router(vegetation_router) # ("/api/vegetation")

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
        "service": "Check healthy-en healthy static.",
    }