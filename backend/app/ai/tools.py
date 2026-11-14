import asyncio
from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)

from app.services.timeline_service import (
    calculate_rainfall_timeline
)
from app.services.smap_history_service import (
    calculate_soil_moisture_history
)
from app.services.modis_service import (
    get_vegetation_history
)


# -----------------------------------------
# VALIDATION SCHEMAS
# -----------------------------------------

class LocationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(
        ge=-90, le=90, allow_inf_nan=False
    )
    longitude: float = Field(
        ge=-180, le=180, allow_inf_nan=False
    )


class RainfallArgs(LocationArgs):
    year: int = Field(ge=2001, le=2100)
    start_month: int = Field(ge=1, le=12)
    end_month: int = Field(ge=1, le=12)
    baseline_start: int = Field(ge=2001)
    baseline_end: int = Field(ge=2001)

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_month < self.start_month:
            raise ValueError("Invalid month range")

        baseline_years = (
            self.baseline_end - self.baseline_start + 1
        )

        if not 3 <= baseline_years <= 10:
            raise ValueError(
                "Baseline must span 3 to 10 years"
            )

        if self.baseline_end >= self.year:
            raise ValueError(
                "Baseline must precede observation year"
            )

        current_month = date.today().replace(day=1)

        selected_month = date(
            self.year, self.end_month, 1
        )

        if selected_month >= current_month:
            raise ValueError(
                "Only completed months are supported"
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


# -----------------------------------------
# AZURE AI FUNCTION DEFINITIONS
# -----------------------------------------

TOOLS = [
    {
        "type": "function",
        "name": "get_rainfall_timeline",
        "description": (
            "Retrieve measured monthly NASA POWER rainfall, "
            "historical baselines, and rainfall anomalies. "
            "Use for rainfall analysis over completed months."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "year": {"type": "integer"},
                "start_month": {"type": "integer"},
                "end_month": {"type": "integer"},
                "baseline_start": {"type": "integer"},
                "baseline_end": {"type": "integer"}
            },
            "required": [
                "latitude",
                "longitude",
                "year",
                "start_month",
                "end_month",
                "baseline_start",
                "baseline_end"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_soil_moisture_history",
        "description": (
            "Retrieve daily NASA SMAP near-surface soil "
            "moisture measurements from downloaded HDF5 files. "
            "Maximum seven consecutive calendar days. "
            "Missing observations must not be invented."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD"
                }
            },
            "required": [
                "latitude",
                "longitude",
                "start_date",
                "end_date"
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_vegetation_history",
        "description": (
            "Retrieve NASA MODIS NDVI and EVI observations "
            "for a selected location and date range. "
            "Maximum 45 calendar days. "
            "Vegetation indices are not drought classifications."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD"
                }
            },
            "required": [
                "latitude",
                "longitude",
                "start_date",
                "end_date"
            ],
            "additionalProperties": False
        }
    }
]


# -----------------------------------------
# APPROVED TOOL EXECUTION
# -----------------------------------------

async def execute_tool(
    name: str,
    arguments: dict
):
    if not isinstance(arguments, dict):
        raise ValueError("Invalid tool arguments")

    if name == "get_rainfall_timeline":
        args = RainfallArgs.model_validate(arguments)

        return await calculate_rainfall_timeline(
            **args.model_dump()
        )

    if name == "get_soil_moisture_history":
        args = HistoryArgs.model_validate(arguments)

        if (args.end_date - args.start_date).days > 6:
            raise ValueError(
                "Maximum seven consecutive days"
            )

        return await asyncio.to_thread(
            calculate_soil_moisture_history,
            **args.model_dump()
        )

    if name == "get_vegetation_history":
        args = HistoryArgs.model_validate(arguments)

        if (args.end_date - args.start_date).days > 44:
            raise ValueError(
                "Maximum 45 consecutive days"
            )

        return await get_vegetation_history(
            **args.model_dump()
        )

    raise ValueError("Tool is not permitted")
