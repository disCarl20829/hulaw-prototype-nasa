import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.indicators import router as indicators_router
from app.api.precipitation import router as precipitation_router
from app.api.rainfall_analysis import router as rainfall_analysis_router
from app.api.baseline import router as baseline_router
from app.api.anomaly import router as anomaly_router
from app.api.timeline import router as timeline_router 
from app.api.soil_moisture import router as soil_moisture_router
from app.api.soil_moisture_history import router as smap_history_router
from app.api.vegetation import router as vegetation_router
from app.api.hulaworld import router as hulaworld_router
from app.api.overview import router as overview_router

app = FastAPI(
    title="Hulaw World",
    description="Global Drought Intelligence Platform",
    version="0.1.0"
)

# Browser origins allowed to call this API. For a deployed or teammate
# frontend, set HULAW_CORS_ORIGINS to a comma-separated list of exact origins,
# for example: HULAW_CORS_ORIGINS=https://hulaw.example.com,http://192.168.1.20:5173

DEFAULT_ORIGINS = (
    "https://hulaw.vercel.app,"
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "HULAW_CORS_ORIGINS",
        DEFAULT_ORIGINS
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(hulaworld_router) # ("/api/hulaworld")
app.include_router(overview_router) # ("/api/overview")

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