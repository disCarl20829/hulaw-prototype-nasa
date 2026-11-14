from datetime import date
from typing import Literal

from pydantic import BaseModel

class Coordinates(BaseModel):
    latitude: float
    longitude: float


class SoilMoistureResponse(BaseModel):
    source: str
    dataset: str
    version: str

    date: date

    requested_location: Coordinates
    grid_location: Coordinates | None

    soil_moisture: float | None
    unit: str

    quality_flag: int | None
    distance_km: float | None
    retrieval_period: Literal["AM", "PM"] | None

    status: Literal["valid", "no_data"]

    filename: str | None
    note: str