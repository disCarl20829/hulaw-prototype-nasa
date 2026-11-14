"""Tests for /api/overview and /api/overview/areas.

NASA services are replaced with small fakes, so these run offline:

    cd backend
    python -m pytest tests -q
"""
import asyncio
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.cache_service as cache_service  # noqa: E402
import app.services.overview_service as ov  # noqa: E402
from app.main import app  # noqa: E402

TODAY = date(2026, 11, 14)
DRY_START, DRY_END = date(2026, 1, 1), date(2026, 4, 30)


def make_power(calls, soil_lag_days=0, fail=False):
    async def fake_power(latitude, longitude, start, end, parameters):
        calls["power"] += 1

        if fail:
            raise HTTPException(502, "down")

        rain, soil = {}, {}
        day = date(int(start[:4]), 1, 1)
        last = date(int(end[:4]), int(end[4:6]), int(end[6:]))

        while day <= last:
            key = day.strftime("%Y%m%d")
            dry = DRY_START <= day <= DRY_END
            rain[key] = 1.0 if dry else 5.0
            soil[key] = 0.2 if dry else round(0.6 + 0.1 * math.sin(day.year), 3)

            if day > last - timedelta(days=soil_lag_days):
                soil[key] = None

            day += timedelta(days=1)

        rain["20260815"] = None  # one missing day makes August incomplete

        return {"PRECTOTCORR": rain, "GWETTOP": soil}

    return fake_power


def modis_dates():
    return [
        f"A{year}{doy:03d}"
        for year in range(2001, 2027)
        for doy in range(1, 366, 16)
        if date(year, 1, 1) + timedelta(days=doy - 1) <= TODAY
    ]


def make_modis(calls, fail_subsets=0, dead=False):
    state = {"fail": fail_subsets}

    async def fake_get_json(client, url, params=None):
        if dead:
            raise HTTPException(502, "NASA MODIS request failed: ConnectTimeout")

        if url.endswith("/dates"):
            calls["dates"] += 1
            return {"dates": [{"modis_date": item} for item in modis_dates()]}

        calls["subset"] += 1

        if state["fail"] > 0:
            state["fail"] -= 1
            raise HTTPException(502, "boom")

        wanted = [
            item for item in modis_dates()
            if params["startDate"] <= item <= params["endDate"]
        ]
        assert 1 <= len(wanted) <= 10  # ORNL limit per request
        subset = []

        for item in wanted:
            year, doy = int(item[1:5]), int(item[5:])
            ndvi = 3000 if (year == 2026 and doy < 120) else 6000
            qa = 2117 if (year == 2026 and 150 < doy < 185) else 2116  # June 2026 fails QA

            for band, value in (
                ("250m_16_days_NDVI", ndvi),
                ("250m_16_days_EVI", 3000),
                ("250m_16_days_VI_Quality", qa),
            ):
                subset.append({"modis_date": item, "band": band, "data": [value]})

        return {"nrows": 1, "ncols": 1, "subset": subset}

    return fake_get_json


@pytest.fixture
def calls(tmp_path, monkeypatch):
    counters = {"power": 0, "dates": 0, "subset": 0}
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(ov, "get_power_daily", make_power(counters))
    monkeypatch.setattr(ov, "get_json", make_modis(counters))

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(ov.asyncio, "sleep", no_sleep)

    return counters


def run(**kwargs):
    return asyncio.run(ov.build_overview(15.7, 120.9, today=TODAY, **kwargs))


def by_month(result):
    return {record["month"]: record for record in result["records"]}


def test_default_window_and_baselines(calls):
    result = run()

    assert result["period"] == {"start_month": "2025-11", "end_month": "2026-10", "months": 12}
    assert result["baseline_period"] == {"start_year": 2020, "end_year": 2024}
    assert result["soil_reference_period"] == {"start_year": 2005, "end_year": 2024}
    assert result["cached"] is False


def test_indicator_maths(calls):
    january = by_month(run())["2026-01"]

    assert january["rainfall"]["observed_mm"] == 31.0
    assert january["rainfall"]["baseline_mm"] == 155.0
    assert january["rainfall"]["anomaly_mm"] == -124.0
    assert january["rainfall"]["percent_departure"] == -80.0
    assert january["rainfall"]["status"] == "below"
    assert january["soil"]["percentile"] == 0.0
    assert january["soil"]["status"] == "below"
    assert january["vegetation"]["ndvi"] == 0.3
    assert january["vegetation"]["anomaly"] == -0.3
    assert january["combined"]["index"] == 1.0
    assert january["combined"]["label"] == "Extreme dryness signal"


def test_missing_values_stay_null(calls):
    months = by_month(run())

    # One missing day: no monthly total, and rainfall is left out of the index.
    assert months["2026-08"]["rainfall"]["observed_mm"] is None
    assert months["2026-08"]["rainfall"]["status"] == "no_data"
    assert "rainfall" not in months["2026-08"]["combined"]["indicators_used"]
    # Quality-filtered composite: no NDVI for June.
    assert months["2026-06"]["vegetation"]["ndvi"] is None


def test_soil_lag_does_not_break_the_response(calls, monkeypatch):
    monkeypatch.setattr(ov, "get_power_daily", make_power(calls, soil_lag_days=61))
    result = run()
    last = result["records"][-1]

    assert last["soil"]["percentile"] is None
    assert last["combined"]["index"] is not None
    assert any(item.startswith("Soil wetness") for item in result["warnings"])


def test_cache_and_refresh(calls):
    run()
    before = dict(calls)

    assert run()["cached"] is True
    assert calls == before

    run(refresh=True)
    assert calls["power"] == before["power"] + 1


def test_modis_request_is_retried(calls, monkeypatch):
    monkeypatch.setattr(ov, "get_json", make_modis(calls, fail_subsets=1))

    warnings = run()["warnings"]
    assert not any("failed" in item for item in warnings), warnings


def test_modis_down_keeps_rainfall_and_soil(calls, monkeypatch):
    monkeypatch.setattr(ov, "get_json", make_modis(calls, dead=True))
    result = run()

    assert all(record["vegetation"]["ndvi"] is None for record in result["records"])
    assert result["records"][2]["rainfall"]["anomaly_mm"] is not None
    assert any("ConnectTimeout" in item for item in result["warnings"])
    # A failed result must not be cached, so the next call can recover.
    assert run()["cached"] is False


def test_custom_period_and_baseline(calls):
    result = run(end_month="2024-06", baseline_start=2015, baseline_end=2022)

    assert result["period"]["start_month"] == "2023-07"
    assert result["period"]["end_month"] == "2024-06"
    assert result["baseline_period"] == {"start_year": 2015, "end_year": 2022}
    assert result["soil_reference_period"] == {"start_year": 2003, "end_year": 2022}


@pytest.mark.parametrize("kwargs", [
    {"end_month": "2026-11"},                                   # not completed yet
    {"end_month": "2005-01"},                                   # too early
    {"end_month": "2024-13"},                                   # not a month
    {"baseline_start": 2020},                                   # only one bound
    {"baseline_start": 2023, "baseline_end": 2024},             # too few years
    {"baseline_start": 2010, "baseline_end": 2024},             # too many years
    {"baseline_start": 2021, "baseline_end": 2025},             # overlaps the window
])
def test_invalid_period_is_rejected(calls, kwargs):
    with pytest.raises(HTTPException) as error:
        run(**kwargs)

    assert error.value.status_code == 400


def test_area_series_shares_grid_cells(calls):
    points = [
        {"id": "a", "latitude": 15.70, "longitude": 120.90},
        {"id": "b", "latitude": 15.74, "longitude": 120.92},  # same 0.25 degree cell as a
        {"id": "c", "latitude": 8.00, "longitude": 125.00},
    ]
    result = asyncio.run(ov.build_area_series(points, today=TODAY))

    assert calls["power"] == 2
    assert result["months"][0] == "2025-11" and len(result["months"]) == 12
    assert [area["id"] for area in result["areas"]] == ["a", "b", "c"]
    assert result["areas"][0]["rainfall_anomaly_mm"][2] == -124.0  # January 2026
    assert result["areas"][0]["soil_percentile"][2] == 0.0
    assert result["failed"] == 0

    asyncio.run(ov.build_area_series(points, today=TODAY))
    assert calls["power"] == 2  # second call is served from the cache


def test_area_series_reports_failed_points(calls, monkeypatch):
    monkeypatch.setattr(ov, "get_power_daily", make_power(calls, fail=True))
    result = asyncio.run(ov.build_area_series(
        [{"id": "a", "latitude": 15.7, "longitude": 120.9}], today=TODAY
    ))

    assert result["failed"] == 1
    assert result["areas"][0]["status"] == "error"
    assert result["areas"][0]["rainfall_anomaly_mm"] == [None] * 12


def test_http_routes(calls, monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return TODAY

    monkeypatch.setattr(ov, "date", FixedDate)
    client = TestClient(app)
    origin = {"Origin": "http://localhost:5173"}

    response = client.get("/api/overview", params={"latitude": 15.7, "longitude": 120.9}, headers=origin)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert len(response.json()["records"]) == 12

    assert client.get("/api/overview", params={"latitude": 95, "longitude": 1}).status_code == 422
    assert client.get("/api/overview", params={"latitude": 1, "longitude": 1, "end_month": "2030-01"}).status_code == 400

    areas = client.post("/api/overview/areas", json={"points": [{"id": "x", "latitude": 15.7, "longitude": 120.9}]}, headers=origin)
    assert areas.status_code == 200
    assert areas.json()["areas"][0]["status"] == "ok"
    assert client.post("/api/overview/areas", json={"points": []}).status_code == 422

    preflight = client.options("/api/hulaworld/chat", headers={
        **origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert preflight.status_code == 200


def test_power_failure_is_a_502(calls, monkeypatch):
    monkeypatch.setattr(ov, "get_power_daily", make_power(calls, fail=True))

    with pytest.raises(HTTPException) as error:
        run()

    assert error.value.status_code == 502
