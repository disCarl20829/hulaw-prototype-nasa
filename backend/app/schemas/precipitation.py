from pydantic import BaseModel

class PrecipitationObservation(BaseModel):
    date: str
    precipitation_mm: float | None


class PrecipitationResponse(BaseModel):
    source: str
    dataset: str
    parameter: str
    latitude: float
    longitude: float
    unit: str
    time_standard: str
    observations: list[PrecipitationObservation]