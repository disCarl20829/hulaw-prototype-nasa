from pydantic import BaseModel

class IndicatorInfo(BaseModel):
    id: str
    name: str
    dataset: str
    description: str
    unit: str


class IndicatorListResponse(BaseModel):
    indicators: list[IndicatorInfo]
    count: int
