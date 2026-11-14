
from datetime import date
import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.soil_moisture_history import (
    SoilMoistureHistoryResponse
)

from app.services.smap_history_service import (
    calculate_soil_moisture_history
)


router = APIRouter(
    prefix="/api/soil-moisture",
    tags=["NASA Soil Moisture"]
)


@router.get(
    "/history",
    response_model=SoilMoistureHistoryResponse
)
def soil_moisture_history(
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

    if (end_date - start_date).days > 13:
        raise HTTPException(
            status_code=400,
            detail="Maximum date range is 14 days"
        )

    try:
        return calculate_soil_moisture_history(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date
        )

    except (OSError, ValueError, KeyError):
        logging.exception("SMAP history extraction failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to process SMAP history"
        )
