from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.rainfall_analysis import MonthlyRainfallResponse
from app.services.rainfall_analysis_service import (
    calculate_monthly_rainfall
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Drought Analysis"]
)

@router.get(
    "/rainfall/monthly",
    response_model=MonthlyRainfallResponse
)
async def monthly_rainfall(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12)
):
    selected_month = date(year, month, 1)

    current_month = date.today().replace(day=1)

    if selected_month >= current_month:
        raise HTTPException(
            status_code=400,
            detail="Select a completed historical month"
        )

    return await calculate_monthly_rainfall(
        latitude=latitude,
        longitude=longitude,
        year=year,
        month=month
    )