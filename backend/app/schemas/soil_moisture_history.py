
from datetime import date

from pydantic import BaseModel

from app.schemas.soil_moisture import (
    Coordinates,
    SoilMoistureResponse
)


class SoilMoistureHistorySummary(BaseModel):
    days_requested: int
    days_valid: int
    days_missing_file: int
    days_missing_retrieval: int
    am_retrievals: int
    pm_retrievals: int


class SoilMoistureHistoryResponse(BaseModel):
    location: Coordinates

    start_date: date
    end_date: date

    source: str
    dataset: str
    version: str
    unit: str

    observations: list[SoilMoistureResponse]
    summary: SoilMoistureHistorySummary
    note: str
