from fastapi import APIRouter, Query, Response

from app.schemas.overview import (
    AreaSeriesRequest,
    AreaSeriesResponse,
    OverviewResponse,
)
from app.services.overview_service import build_area_series, build_overview

router = APIRouter(
    prefix="/api/overview",
    tags=["Drought Overview"]
)


@router.get("", response_model=OverviewResponse)
async def overview(
    response: Response,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    end_month: str | None = Query(
        None,
        pattern=r"^\d{4}-\d{2}$",
        description="Last month of the 12-month window (YYYY-MM). "
                    "Default: the latest completed month."
    ),
    baseline_start: int | None = Query(None, ge=1981, le=2100),
    baseline_end: int | None = Query(None, ge=1981, le=2100),
    refresh: bool = Query(
        False,
        description="Ignore cached results and fetch from NASA again"
    )
):
    """12 completed months of rainfall, soil wetness and vegetation for
    one point, each compared with its own baseline, plus an experimental
    combined index."""
    result = await build_overview(
        latitude=latitude,
        longitude=longitude,
        refresh=refresh,
        end_month=end_month,
        baseline_start=baseline_start,
        baseline_end=baseline_end
    )

    # Completed months do not change, so the browser may reuse a complete
    # answer for a few minutes (page reloads, switching back to an area).
    # A result with a failed NASA request is never reused.
    complete = not any(
        "failed" in item or "could not" in item
        for item in result["warnings"]
    )
    response.headers["Cache-Control"] = (
        "private, max-age=600" if complete and not refresh else "no-store"
    )

    return result


@router.post("/areas", response_model=AreaSeriesResponse)
async def overview_areas(request: AreaSeriesRequest):
    """Rainfall anomaly and soil percentile per month for many areas in
    one call. The map uses this to colour each boundary by its own value."""
    return await build_area_series(
        points=[point.model_dump() for point in request.points],
        refresh=request.refresh,
        end_month=request.end_month,
        baseline_start=request.baseline_start,
        baseline_end=request.baseline_end
    )
