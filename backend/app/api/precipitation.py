from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.precipitation import PrecipitationResponse
from app.services.nasa_service import get_precipitation

router = APIRouter(
    prefix="/api/precipitation",
    tags=["NASA Precipitation"]
)

@router.get("", response_model=PrecipitationResponse)
async def precipitation(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    start: date = Query(...),
    end: date = Query(...)
):
    if end < start:
        raise HTTPException(
            status_code=400,
            detail="End date must be after or equal to start date"
        )

    if (end - start).days > 30:
        raise HTTPException(
            status_code=400,
            detail="Maximum date range is 31 days"
        )

    return await get_precipitation(
        latitude=latitude,
        longitude=longitude,
        start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d")
    )