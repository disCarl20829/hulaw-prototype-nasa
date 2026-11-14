from app.schemas.indicator import IndicatorInfo

def get_available_indicators() -> list[IndicatorInfo]:
    """Indicators served by /api/overview, described as they are computed."""
    return [
        IndicatorInfo(
            id="precipitation",
            name="Rainfall anomaly",
            dataset="NASA POWER daily precipitation (PRECTOTCORR)",
            description=(
                "Monthly rainfall total minus the mean of the same calendar "
                "month in the baseline years. Not GPM IMERG."
            ),
            unit="mm"
        ),
        IndicatorInfo(
            id="soil_moisture",
            name="Surface soil wetness",
            dataset="NASA POWER surface soil wetness (GWETTOP)",
            description=(
                "Percentile of the monthly mean surface soil wetness among "
                "the same calendar month in the reference years. Model-based "
                "estimate, not a SMAP retrieval. SMAP point observations "
                "remain available at /api/soil-moisture where files exist."
            ),
            unit="percentile"
        ),
        IndicatorInfo(
            id="vegetation",
            name="Vegetation anomaly",
            dataset="NASA MODIS MOD13Q1 NDVI (ORNL DAAC)",
            description=(
                "Monthly mean NDVI minus the mean of the same calendar "
                "month in the baseline years."
            ),
            unit="unitless"
        )
    ]
