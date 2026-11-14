from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.baseline import RainfallBaselineResponse
from app.services.baseline_service import (
    calculate_rainfall_baseline
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Drought Analysis"]
)

@router.get(
    "/rainfall/baseline",
    response_model=RainfallBaselineResponse
)
async def rainfall_baseline(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    month: int = Query(..., ge=1, le=12),
    start_year: int = Query(..., ge=2001),
    end_year: int = Query(..., ge=2001)
):
    if end_year < start_year:
        raise HTTPException(
            status_code=400,
            detail="End year must be after start year"
        )

    if end_year - start_year + 1 > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum baseline range is 10 years"
        )

    # Avoid requesting an incomplete current month
    current_month = date.today().replace(day=1)
    last_requested_month = date(end_year, month, 1)

    if last_requested_month >= current_month:
        raise HTTPException(
            status_code=400,
            detail="Baseline must use completed months"
        )

    return await calculate_rainfall_baseline(
        latitude=latitude,
        longitude=longitude,
        month=month,
        start_year=start_year,
        end_year=end_year
    )
