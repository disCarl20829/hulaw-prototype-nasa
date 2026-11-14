TOOLS = [
    {
        "type": "function",
        "name": "get_rainfall_timeline",
        "description": (
            "Get actual NASA POWER monthly rainfall, historical "
            "baseline, rainfall anomalies, percentage departures, "
            "and drought development timeline. Use when the user "
            "asks about observed rainfall for a specific year."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number"
                },
                "longitude": {
                    "type": "number"
                },
                "year": {
                    "type": "integer"
                },
                "start_month": {
                    "type": "integer",
                    "description": "First month, 1 to 12"
                },
                "end_month": {
                    "type": "integer",
                    "description": "Last month, 1 to 12"
                },
                "baseline_start": {
                    "type": "integer",
                    "description": "Historical baseline start year"
                },
                "baseline_end": {
                    "type": "integer",
                    "description": "Historical baseline end year"
                }
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
            "Get actual NASA SMAP near-surface soil moisture "
            "observations from the Hulaw backend. "
            "Dates must be formatted YYYY-MM-DD. "
            "Maximum seven consecutive calendar days."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number"
                },
                "longitude": {
                    "type": "number"
                },
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
            "Get actual NASA MODIS NDVI and EVI observations "
            "from the Hulaw backend for vegetation monitoring. "
            "Dates must be formatted YYYY-MM-DD. "
            "Maximum 45 consecutive calendar days."
        ),
        "strict": False,
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number"
                },
                "longitude": {
                    "type": "number"
                },
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
