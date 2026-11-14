from pydantic import BaseModel

from app.schemas.rainfall_analysis import LocationInfo

class BaselinePeriod(BaseModel):
    start_year: int
    end_year: int


class HistoricalRainfallRecord(BaseModel):
    year: int
    month: int
    rainfall_mm: float | None
    complete: bool


class RainfallBaselineResponse(BaseModel):
    location: LocationInfo
    month: int

    baseline_period: BaselinePeriod
    baseline_rainfall_mm: float | None
    unit: str

    source: str
    parameter: str

    valid_years: int
    requested_years: int
    sufficient_data: bool

    historical_data: list[HistoricalRainfallRecord]
    note: str
