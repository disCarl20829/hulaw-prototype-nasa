from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["below", "normal", "above", "no_data"]
Mood = Literal["default", "happy", "moderate", "negative"]


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class YearRange(BaseModel):
    start_year: int
    end_year: int


class OverviewPeriod(BaseModel):
    start_month: str  # YYYY-MM
    end_month: str    # YYYY-MM
    months: int


class RainfallMonth(BaseModel):
    observed_mm: float | None
    baseline_mm: float | None
    anomaly_mm: float | None
    percent_departure: float | None
    observed_days: int
    expected_days: int
    valid_baseline_years: int
    status: Status


class SoilMonth(BaseModel):
    wetness: float | None            # 0-1 fraction, monthly mean
    baseline_wetness: float | None   # mean of the same calendar month
    percentile: float | None         # 0-100 within the reference years
    valid_days: int
    expected_days: int
    valid_reference_years: int
    status: Status


class VegetationMonth(BaseModel):
    ndvi: float | None               # mean of valid composites in the month
    baseline_ndvi: float | None
    anomaly: float | None
    composites_valid: int
    composites_total: int
    valid_baseline_years: int
    status: Status


class CombinedMonth(BaseModel):
    index: float | None              # -1 (wetter) to +1 (drier), experimental
    label: str
    indicators_used: list[str]


class OverviewRecord(BaseModel):
    month: str  # YYYY-MM
    rainfall: RainfallMonth
    soil: SoilMonth
    vegetation: VegetationMonth
    combined: CombinedMonth


class OverviewLatest(BaseModel):
    month: str | None
    combined_index: float | None
    label: str
    mood: Mood


class SourceInfo(BaseModel):
    dataset: str
    variable: str
    unit: str
    baseline_period: str
    native_resolution: str
    limitation: str


class OverviewSources(BaseModel):
    precip: SourceInfo
    soil: SourceInfo
    ndvi: SourceInfo


class OverviewResponse(BaseModel):
    location: Coordinates
    period: OverviewPeriod
    baseline_period: YearRange
    soil_reference_period: YearRange
    records: list[OverviewRecord]
    latest: OverviewLatest
    sources: OverviewSources
    thresholds: dict[str, str]
    warnings: list[str]
    generated_at: str
    cached: bool
    experimental: bool
    note: str


class AreaPoint(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class AreaSeriesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: list[AreaPoint] = Field(min_length=1, max_length=150)
    end_month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    baseline_start: int | None = Field(default=None, ge=1981, le=2100)
    baseline_end: int | None = Field(default=None, ge=1981, le=2100)
    refresh: bool = False


class AreaSeries(BaseModel):
    id: str
    latitude: float
    longitude: float
    status: Literal["ok", "error"]
    rainfall_anomaly_mm: list[float | None]
    soil_percentile: list[float | None]


class AreaSeriesResponse(BaseModel):
    months: list[str]
    baseline_period: YearRange
    soil_reference_period: YearRange
    grid_degrees: float
    indicators: list[str]
    areas: list[AreaSeries]
    failed: int
    note: str
