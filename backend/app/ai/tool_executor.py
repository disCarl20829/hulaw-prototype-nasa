import math
from datetime import date
from typing import Any

import httpx

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)


# ---------------------------------------
# VALIDATION
# ---------------------------------------

class LocationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(
        ge=-90,
        le=90,
        allow_inf_nan=False
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        allow_inf_nan=False
    )


class RainfallArgs(LocationArgs):
    year: int = Field(ge=2001, le=2100)
    start_month: int = Field(ge=1, le=12)
    end_month: int = Field(ge=1, le=12)
    baseline_start: int = Field(ge=2001)
    baseline_end: int = Field(ge=2001)

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_month > self.end_month:
            raise ValueError("Invalid month range")

        if self.baseline_end >= self.year:
            raise ValueError(
                "Baseline must precede observation year"
            )

        baseline_count = (
            self.baseline_end - self.baseline_start + 1
        )

        if not 3 <= baseline_count <= 10:
            raise ValueError(
                "Use a baseline of 3 to 10 years"
            )

        # Limit requests to 12 completed months.
        selected_end = date(
            self.year,
            self.end_month,
            1
        )

        if selected_end >= date.today().replace(day=1):
            raise ValueError(
                "Only completed historical months supported"
            )

        return self


class HistoryArgs(LocationArgs):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_date < self.start_date:
            raise ValueError("Invalid date range")

        if self.end_date > date.today():
            raise ValueError(
                "Future observations unavailable"
            )

        return self


# ---------------------------------------
# FIXED, APPROVED API DESTINATIONS
# ---------------------------------------

ENDPOINTS = {
    "get_rainfall_timeline":
        "/api/analysis/rainfall/timeline",

    "get_soil_moisture_history":
        "/api/soil-moisture/history",

    "get_vegetation_history":
        "/api/vegetation/history"
}


def clean_json(value: Any):
    """
    Return only JSON-compatible data.
    Remove non-finite numeric values.
    """

    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value

    if isinstance(value, list):
        return [clean_json(x) for x in value]

    if isinstance(value, dict):
        return {
            str(k): clean_json(v)
            for k, v in value.items()
        }

    return value


def sanitize_result(name: str, data: dict):
    """
    Whitelist fields needed for environmental
    explanations, excluding filenames and
    other unnecessary backend metadata.
    """

    common = {
        "source",
        "dataset",
        "version",
        "parameter",
        "unit",
        "note",
        "location",
        "start_date",
        "end_date"
    }

    if name == "get_rainfall_timeline":
        keys = common | {
            "period",
            "baseline_period",
            "timeline",
            "summary"
        }

    elif name == "get_soil_moisture_history":
        keys = common | {
            "observations",
            "summary"
        }

    elif name == "get_vegetation_history":
        keys = common | {
            "latitude",
            "longitude",
            "temporal_resolution",
            "spatial_resolution_m",
            "observations",
            "count"
        }

    else:
        raise ValueError("Unapproved result type")

    result = {
        key: value
        for key, value in data.items()
        if key in keys
    }

    # Remove local satellite file names.
    if name == "get_soil_moisture_history":
        observations = result.get("observations", [])

        result["observations"] = [
            {
                k: v
                for k, v in obs.items()
                if k != "filename"
            }
            for obs in observations
            if isinstance(obs, dict)
        ]

    return clean_json(result)


# ---------------------------------------
# EXECUTE APPROVED API REQUEST
# ---------------------------------------

async def execute_tool(
    name: str,
    arguments: dict
):
    if name not in ENDPOINTS:
        raise ValueError(
            "This tool is not permitted"
        )

    if not isinstance(arguments, dict):
        raise ValueError(
            "Invalid tool arguments"
        )

    if name == "get_rainfall_timeline":
        args = RainfallArgs.model_validate(arguments)

    else:
        args = HistoryArgs.model_validate(arguments)

        days = (
            args.end_date - args.start_date
        ).days + 1

        if name == "get_soil_moisture_history":
            if days > 7:
                raise ValueError(
                    "SMAP range limited to seven days"
                )

        if name == "get_vegetation_history":
            if days > 45:
                raise ValueError(
                    "MODIS range limited to 45 days"
                )

    params = args.model_dump(mode="json")

    # Delayed import avoids circular imports
    # during FastAPI router initialization.
    from app.main import app

    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=False
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://hulaw-internal",
        timeout=45.0,
        follow_redirects=False
    ) as client:

        response = await client.get(
            ENDPOINTS[name],
            params=params
        )

    if response.status_code != 200:
        return {
            "status": "unavailable",
            "source": name,
            "message": (
                "The environmental data service "
                "could not complete this request."
            ),
            "http_status": response.status_code
        }

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError(
            "Unexpected NASA API response"
        )

    return sanitize_result(name, data)
