from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.vegetation import (
    VegetationHistoryResponse
)

from app.services.modis_service import (
    get_vegetation_history
)


router = APIRouter(
    prefix="/api/vegetation",
    tags=["NASA MODIS Vegetation"]
)


@router.get(
    "/history",
    response_model=VegetationHistoryResponse
)
async def vegetation_history(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    start_date: date = Query(...),
    end_date: date = Query(...)
):
    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must not precede start date"
        )

    if end_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Cannot request future observations"
        )

    if (end_date - start_date).days > 120:
        raise HTTPException(
            status_code=400,
            detail="Maximum date range is 121 days"
        )

    return await get_vegetation_history(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date
    )
