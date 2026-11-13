from fastapi import APIRouter

from app.schemas.indicator import IndicatorListResponse
from app.services.indicator_service import get_available_indicators

router = APIRouter(
    prefix="/api/indicators",
    tags=["Drought Indicators"]
)

@router.get("", response_model=IndicatorListResponse)
def list_indicators():
    indicators = get_available_indicators()

    return IndicatorListResponse(
        indicators=indicators,
        count=len(indicators)
    )