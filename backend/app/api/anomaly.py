from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.anomaly import RainfallAnomalyResponse
from app.services.anomaly_service import (
    calculate_rainfall_anomaly
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Drought Analysis"]
)

@router.get(
    "/rainfall/anomaly",
    response_model=RainfallAnomalyResponse
)
async def rainfall_anomaly(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    year: int = Query(..., ge=2001, le=2100),
    month: int = Query(..., ge=1, le=12),
    baseline_start: int = Query(..., ge=2001),
    baseline_end: int = Query(..., ge=2001)
):
    # Validate historical reference
    if baseline_end < baseline_start:
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline year range"
        )

    if baseline_end >= year:
        raise HTTPException(
            status_code=400,
            detail="Baseline must end before the observed year"
        )

    if baseline_end - baseline_start + 1 > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum baseline range is 10 years"
        )

    # Avoid incomplete months
    selected_month = date(year, month, 1)
    current_month = date.today().replace(day=1)

    if selected_month >= current_month:
        raise HTTPException(
            status_code=400,
            detail="Select a completed historical month"
        )

    return await calculate_rainfall_anomaly(
        latitude=latitude,
        longitude=longitude,
        year=year,
        month=month,
        baseline_start=baseline_start,
        baseline_end=baseline_end
    )
