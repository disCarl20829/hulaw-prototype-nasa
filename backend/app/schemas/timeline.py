from typing import Literal

from pydantic import BaseModel

from app.schemas.rainfall_analysis import LocationInfo
from app.schemas.baseline import BaselinePeriod

class TimelinePeriod(BaseModel):
    year: int
    start_month: int
    end_month: int


class TimelineRecord(BaseModel):
    date: str

    observed_rainfall_mm: float | None
    baseline_rainfall_mm: float | None
    anomaly_mm: float | None
    percent_departure: float | None

    condition: Literal[
        "below_baseline",
        "above_baseline",
        "equal_to_baseline",
        "insufficient_data"
    ]

    observed_days: int
    expected_days: int
    valid_baseline_years: int


class TimelineSummary(BaseModel):
    months_requested: int
    months_with_data: int
    months_below_baseline: int
    months_above_baseline: int


class RainfallTimelineResponse(BaseModel):
    location: LocationInfo
    period: TimelinePeriod
    baseline_period: BaselinePeriod

    source: str
    dataset: str
    parameter: str
    unit: str

    timeline: list[TimelineRecord]
    summary: TimelineSummary
    note: str
