from pydantic import BaseModel

from app.schemas.precipitation import PrecipitationObservation

class LocationInfo(BaseModel):
    latitude: float
    longitude: float


class PeriodInfo(BaseModel):
    year: int
    month: int


class MonthlyRainfallResponse(BaseModel):
    location: LocationInfo
    period: PeriodInfo

    source: str
    dataset: str
    parameter: str
    unit: str

    monthly_rainfall_mm: float | None

    observed_days: int
    expected_days: int
    complete: bool

    daily_observations: list[PrecipitationObservation]
