from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.soil_moisture import (
    SoilMoistureResponse
)

from app.services.smap_service import (
    extract_soil_moisture
)


router = APIRouter(
    prefix="/api/soil-moisture",
    tags=["NASA Soil Moisture"]
)


@router.get(
    "",
    response_model=SoilMoistureResponse
)
def get_soil_moisture(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    observation_date: date = Query(...)
):
    if observation_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Observation date cannot be in the future"
        )

    try:
        return extract_soil_moisture(
            latitude=latitude,
            longitude=longitude,
            observation_date=observation_date
        )

    except (OSError, ValueError, KeyError) as exc:
        # Log the technical error in the server console.
        import logging
        logging.exception("SMAP extraction failed")

        raise HTTPException(
            status_code=500,
            detail="Unable to process the SMAP file"
        ) from exc