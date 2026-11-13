from fastapi import FastAPI

from app.api.indicators import router as indicators_router
from app.api.precipitation import router as precipitation_router

app = FastAPI(
    title="Hulaw World",
    description="Global Drought Intelligence Platform",
    version="0.1.0"
)

app.include_router(indicators_router)
app.include_router(precipitation_router)

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
        "service": "Hulaw World API",
    }