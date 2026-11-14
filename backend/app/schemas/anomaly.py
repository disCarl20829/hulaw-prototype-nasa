from pydantic import BaseModel

from app.schemas.rainfall_analysis import (
    LocationInfo,
    PeriodInfo
)

from app.schemas.baseline import BaselinePeriod

class RainfallAnomalyResponse(BaseModel):
    location: LocationInfo
    period: PeriodInfo
    baseline_period: BaselinePeriod

    observed_rainfall_mm: float | None
    baseline_rainfall_mm: float | None

    rainfall_anomaly_mm: float | None
    percent_departure: float | None

    condition: str

    source: str
    dataset: str
    parameter: str
    unit: str

    observed_days: int
    expected_days: int
    valid_baseline_years: int

    note: str
