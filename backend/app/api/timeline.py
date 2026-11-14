from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.timeline import RainfallTimelineResponse
from app.services.timeline_service import (
    calculate_rainfall_timeline
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Drought Analysis"]
)

@router.get(
    "/rainfall/timeline",
    response_model=RainfallTimelineResponse
)
async def rainfall_timeline(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    year: int = Query(..., ge=2001, le=2100),
    start_month: int = Query(..., ge=1, le=12),
    end_month: int = Query(..., ge=1, le=12),
    baseline_start: int = Query(..., ge=2001),
    baseline_end: int = Query(..., ge=2001)
):
    if end_month < start_month:
        raise HTTPException(
            status_code=400,
            detail="End month must be after start month"
        )

    if baseline_end < baseline_start:
        raise HTTPException(
            status_code=400,
            detail="Invalid baseline year range"
        )

    baseline_years = baseline_end - baseline_start + 1

    if baseline_years < 3 or baseline_years > 10:
        raise HTTPException(
            status_code=400,
            detail="Use between 3 and 10 baseline years"
        )

    if baseline_end >= year:
        raise HTTPException(
            status_code=400,
            detail="Baseline must end before observation year"
        )

    # Only analyze completed months.
    current_month = date.today().replace(day=1)
    last_month = date(year, end_month, 1)

    if last_month >= current_month:
        raise HTTPException(
            status_code=400,
            detail="Select completed historical months"
        )

    return await calculate_rainfall_timeline(
        latitude=latitude,
        longitude=longitude,
        year=year,
        start_month=start_month,
        end_month=end_month,
        baseline_start=baseline_start,
        baseline_end=baseline_end
    )
