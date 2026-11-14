from datetime import date
from typing import Literal

from pydantic import BaseModel


class VegetationObservation(BaseModel):
    date: date
    modis_date: str

    ndvi: float | None
    evi: float | None

    qa_value: int | None
    status: Literal["valid", "no_data"]

    product_version: str | None


class VegetationHistoryResponse(BaseModel):
    source: str
    dataset: str

    latitude: float
    longitude: float

    start_date: date
    end_date: date

    temporal_resolution: str
    spatial_resolution_m: int

    observations: list[VegetationObservation]
    count: int
    note: str
