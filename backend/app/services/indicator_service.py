from app.schemas.indicator import IndicatorInfo

def get_available_indicators() -> list[IndicatorInfo]:
    return [
        IndicatorInfo(
            id="precipitation",
            name="Precipitation",
            dataset="NASA GPM / IMERG",
            description="Satellite-estimated rainfall and rainfall anomalies.",
            unit="mm"
        ),
        IndicatorInfo(
            id="soil_moisture",
            name="Surface Soil Moisture",
            dataset="NASA SMAP",
            description="Near-surface soil moisture estimates and anomalies.",
            unit="m³/m³"
        ),
        IndicatorInfo(
            id="vegetation",
            name="Vegetation Index",
            dataset="NASA MODIS",
            description="Vegetation greenness based on NDVI.",
            unit="unitless"
        )
    ]
