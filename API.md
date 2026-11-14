# Hulaw — Frontend API Documentation & Integration Guide

**Handoff edition:** November 14, 2026  
**Backend:** Python / FastAPI  
**Frontend:** React + TypeScript (Vite), optional CesiumJS  
**Local API:** `http://127.0.0.1:8000`  
**Interactive API docs:** `http://127.0.0.1:8000/docs`  
**Machine-readable schema:** `http://127.0.0.1:8000/openapi.json`

> **Source of truth:** The running FastAPI `/openapi.json` describes the exact code currently installed. The contract below was assembled from the project's implemented route/schema examples and successfully tested responses. If an endpoint differs, follow `/openapi.json`, or reconcile its backend schema before integrating. Never treat illustrative values as real measurements.

## 1. Status and dataset limitations

| Feature | Endpoint | Status |
|---|---|---|
| Service information | `GET /` | Tested |
| Service health | `GET /api/health` | Tested |
| Indicator catalog | `GET /api/indicators` | Tested |
| Daily rainfall | `GET /api/precipitation` | Tested |
| Monthly rainfall | `GET /api/analysis/rainfall/monthly` | Tested |
| Rainfall baseline | `GET /api/analysis/rainfall/baseline` | Tested |
| Rainfall anomaly | `GET /api/analysis/rainfall/anomaly` | Tested |
| Rainfall timeline | `GET /api/analysis/rainfall/timeline` | Tested |
| SMAP single observation | `GET /api/soil-moisture` | Tested |
| SMAP history | `GET /api/soil-moisture/history` | Tested |
| MODIS NDVI/EVI history | `GET /api/vegetation/history` | Tested |
| 12-month drought overview | `GET /api/overview` | Rainfall and soil confirmed live (14 Nov 2026); vegetation depends on the ORNL MODIS service responding |
| Per-area map series | `POST /api/overview/areas` | Tested with simulated NASA responses only |
| Hulaworld AI chat | `POST /api/hulaworld/chat` | Needs Azure OpenAI settings in `backend/.env` |

**Interpretation caveats**

- **Rainfall** is NASA POWER daily precipitation (`PRECTOTCORR`) — **not** GPM IMERG. Daily values have `mm/day` units, aggregated monthly totals have `mm`. The rainfall baseline is a preliminary historical comparison (commonly 2019–2023 in the current prototype), **not** an official climatological normal or drought classification.
- **Soil moisture** is NASA SMAP `SPL3SMP_E` Version `006`, near-surface volumetric soil moisture in `m3/m3`. Requests read **locally downloaded HDF5 files**, not a live on-demand worldwide data API. A response of `no_data` is valid. A single measurement is **not** a drought diagnosis; a defensible historical SMAP anomaly has been **deferred**. Retrievals can be AM or PM, with different geographic grid cells and a 20 km nearest-accepted-cell filter in the current prototype.
- **Vegetation** is NASA ORNL DAAC MODIS `MOD13Q1` NDVI/EVI, 16-day composites with a nominal 250 m grid. Data values are scaled vegetation indices, not percentages. `qa_value` stores the source's bit-encoded quality information. The stricter prototype QA filter was retested successfully; `product_version` currently may be `null` and should **not** be guessed. NDVI/EVI changes alone do not prove drought impacts.
- All three sources have **different spatial and time resolutions**. Charts and maps must label dates, units, dataset, quality, source availability, and missing data separately. Do not present satellite data as official warnings or field-scale certainty.

## 2. Local setup (frontend and backend)

### Backend — from `backend/`

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

### CORS — `backend/app/main.py`

Add middleware **once**, just after `app = FastAPI(...)`, retaining all `include_router(...)` calls:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

This middleware is now in `backend/app/main.py`. `POST` is allowed for the AI chat and map-series routes. To allow other origins (a deployed frontend, a teammate's machine), set `HULAW_CORS_ORIGINS` in `backend/.env` to a comma-separated list of exact origins instead of editing the code.

For another Vite port, add its exact origin (host + port). No browser API key is required for the currently described read-only routes.

### Frontend — `frontend/.env`

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The provided `src/services/hulaw-api.ts` reads this value. Restart the Vite server after modifying `.env`.

> **Important:** `127.0.0.1` refers to the computer running the browser. For a teammate on a separate machine, deploy the backend or provide a trusted-network endpoint, set `VITE_API_BASE_URL` accordingly, add the frontend's exact origin to backend CORS, and configure network/firewall permissions. Do **not** expose NASA Earthdata credentials, HDF5 paths, tokens, or `.netrc` to the browser. A remote backend needs access to its own SMAP data files.

## 3. API conventions

- Method: **GET** for all currently implemented routes.
- Dates: API query dates are `YYYY-MM-DD`; history records use `YYYY-MM-DD` or rainfall monthly `YYYY-MM` as indicated.
- Coordinates: decimal degrees; `latitude` from -90 to 90, `longitude` from -180 to 180.
- Missing values: `null` in numeric fields; do **not** convert to zero or connect through missing chart points.
- `status: "no_data"` is a successful API response representing unavailable/unsuitable satellite observations. A non-2xx HTTP status is a request or service error, not an observed drought condition.
- Relevant HTTP errors: `400` invalid date combination/business validation; `422` missing or invalid query parameter; `500` local HDF5 processing error; `502` upstream NASA service failed/returned an unexpected response. Handle all in UI.
- Upstream NASA requests may be slow; show loading states and cache repeated queries on the frontend where sensible.

## 4. API endpoint reference

### `GET /`

Basic API information. Example response:

```json
{"project":"Hulaw","description":"Global Drought Intelligence Platform","status":"running"}
```

### `GET /api/health`

Check backend reachability.

```json
{"status":"healthy","service":"Hulaw Backend"}
```

### `GET /api/indicators`

No query parameters. Returns the available indicator descriptions. Schema:

```ts
type IndicatorList = {
  indicators: { id: string; name: string; dataset: string; description: string; unit: string }[];
  count: number;
};
```

The indicator descriptions are metadata; they do not assert that observations exist for the selected date and location.

### `GET /api/precipitation`

**Purpose:** daily NASA POWER `PRECTOTCORR` precipitation for a point.  
**Required query:** `latitude`, `longitude`, `start`, `end`  
**Date format:** `YYYY-MM-DD`  
**Limit:** at most 31 calendar days (difference no more than 30 days) in the implementation.

Example:

```text
/api/precipitation?latitude=14.5995&longitude=120.9842&start=2024-01-01&end=2024-01-07
```

Response shape:

```ts
type DailyPrecipitation = {
  source: string;
  dataset: string;
  parameter: string; // PRECTOTCORR
  latitude: number;
  longitude: number;
  unit: string; // mm/day
  time_standard: string; // UTC
  observations: { date: string; precipitation_mm: number | null }[]; // YYYYMMDD
};
```

`precipitation_mm` is daily precipitation in millimeters; `null` means a missing daily value. The observed values must come from the API, never from example JSON.

### `GET /api/analysis/rainfall/monthly`

**Purpose:** sum complete daily precipitation records for one calendar month.  
**Required query:** `latitude`, `longitude`, `year`, `month`  
**Limit:** past, completed months only.

Example:

```text
/api/analysis/rainfall/monthly?latitude=14.5995&longitude=120.9842&year=2024&month=1
```

Response shape:

```ts
type MonthlyRainfall = {
  location: Coordinates;
  period: { year: number; month: number };
  source: string;
  dataset: string;
  parameter: string;
  unit: string; // mm
  monthly_rainfall_mm: number | null;
  observed_days: number;
  expected_days: number;
  complete: boolean;
  daily_observations: { date: string; precipitation_mm: number | null }[];
};
```

If `complete` is false, `monthly_rainfall_mm` is `null`, not a partial sum dressed up as a monthly total.

### `GET /api/analysis/rainfall/baseline`

**Purpose:** same-calendar-month mean precipitation across earlier years.  
**Required query:** `latitude`, `longitude`, `month`, `start_year`, `end_year`  
**Limits:** 10-year maximum in prototype; at least 3 complete years needed for a numeric baseline; requests must use completed months.

Example:

```text
/api/analysis/rainfall/baseline?latitude=14.5995&longitude=120.9842&month=1&start_year=2019&end_year=2023
```

Response shape:

```ts
type RainfallBaseline = {
  location: Coordinates;
  month: number;
  baseline_period: { start_year: number; end_year: number };
  baseline_rainfall_mm: number | null;
  unit: string;
  source: string;
  parameter: string;
  valid_years: number;
  requested_years: number;
  sufficient_data: boolean;
  historical_data: { year: number; month: number; rainfall_mm: number | null; complete: boolean }[];
  note: string;
};
```

### `GET /api/analysis/rainfall/anomaly`

**Purpose:** observed rainfall minus historical baseline.  
**Required query:** `latitude`, `longitude`, `year`, `month`, `baseline_start`, `baseline_end`  
**Limits:** reference years end before observed year; max 10 historical years; completed observation month.

Example:

```text
/api/analysis/rainfall/anomaly?latitude=14.5995&longitude=120.9842&year=2024&month=1&baseline_start=2019&baseline_end=2023
```

Response shape:

```ts
type RainfallAnomaly = {
  location: Coordinates;
  period: { year: number; month: number };
  baseline_period: { start_year: number; end_year: number };
  observed_rainfall_mm: number | null;
  baseline_rainfall_mm: number | null;
  rainfall_anomaly_mm: number | null;
  percent_departure: number | null;
  condition: "below_normal" | "above_normal" | "near_normal" | "insufficient_data";
  source: string;
  dataset: string;
  parameter: string;
  unit: string;
  observed_days: number;
  expected_days: number;
  valid_baseline_years: number;
  note: string;
};
```

Formula: `anomaly_mm = observed_rainfall_mm - baseline_rainfall_mm`; `percent_departure = anomaly_mm / baseline * 100`, only when baseline > 0. These condition labels are exploratory departures, **not official drought severity**.

### `GET /api/analysis/rainfall/timeline`

**Purpose:** monthly rainfall/baseline/anomaly series over a portion of one historical year.  
**Required query:** `latitude`, `longitude`, `year`, `start_month`, `end_month`, `baseline_start`, `baseline_end`  
**Limits:** `1 ≤ start_month ≤ end_month ≤ 12`; 3–10 baseline years, ending before observed year; only completed months.

Example:

```text
/api/analysis/rainfall/timeline?latitude=14.5995&longitude=120.9842&year=2024&start_month=1&end_month=6&baseline_start=2019&baseline_end=2023
```

Response shape:

```ts
type RainfallTimeline = {
  location: Coordinates;
  period: { year: number; start_month: number; end_month: number };
  baseline_period: { start_year: number; end_year: number };
  source: string;
  dataset: string;
  parameter: string;
  unit: string; // mm
  timeline: {
    date: string; // YYYY-MM
    observed_rainfall_mm: number | null;
    baseline_rainfall_mm: number | null;
    anomaly_mm: number | null;
    percent_departure: number | null;
    condition: "below_baseline" | "above_baseline" | "equal_to_baseline" | "insufficient_data";
    observed_days: number;
    expected_days: number;
    valid_baseline_years: number;
  }[];
  summary: {
    months_requested: number;
    months_with_data: number;
    months_below_baseline: number;
    months_above_baseline: number;
  };
  note: string;
};
```

**Recommended primary rainfall dashboard endpoint.** Plot monthly observed rainfall and baseline, plus an anomaly chart. Display the baseline years and source for transparency.

### `GET /api/soil-moisture`

**Purpose:** one observation on a chosen date from locally downloaded SMAP files.  
**Required query:** `latitude`, `longitude`, `observation_date`  
**Date format:** `YYYY-MM-DD`.

Verified test URL:

```text
/api/soil-moisture?latitude=15.7&longitude=120.9&observation_date=2024-01-16
```

Verified selected fields from the user's test:

```json
{
  "date": "2024-01-16",
  "soil_moisture": 0.4414,
  "unit": "m3/m3",
  "quality_flag": 8,
  "distance_km": 4.88,
  "retrieval_period": "AM",
  "status": "valid"
}
```

**Note:** This is a *partial excerpt*, not the full JSON response.

Full response shape:

```ts
type SoilMoistureObservation = {
  source: string;
  dataset: string;
  version: string;
  date: string;
  requested_location: Coordinates;
  grid_location: Coordinates | null;
  soil_moisture: number | null; // m3/m3
  unit: string;
  quality_flag: number | null; // current accepted values: 0, 8
  distance_km: number | null;
  retrieval_period: "AM" | "PM" | null;
  status: "valid" | "no_data";
  filename: string | null;
  note: string;
};
```

`status: "no_data"` and a `null` measurement are valid outcomes. Current policy selects the nearest acceptable AM or PM retrieval within 20 km; these periods should not be averaged or compared as a baseline without further controls.

### `GET /api/soil-moisture/history`

**Purpose:** SMAP observations and missing-day records for a short historical range using locally downloaded HDF5 files.  
**Required query:** `latitude`, `longitude`, `start_date`, `end_date`  
**Limit:** 14 calendar days inclusive.

Example:

```text
/api/soil-moisture/history?latitude=15.7&longitude=120.9&start_date=2024-01-15&end_date=2024-01-17
```

Response shape:

```ts
type SoilMoistureHistory = {
  location: Coordinates;
  start_date: string;
  end_date: string;
  source: string;
  dataset: string;
  version: string;
  unit: string;
  observations: SoilMoistureObservation[];
  summary: {
    days_requested: number;
    days_valid: number;
    days_missing_file: number;
    days_missing_retrieval: number;
    am_retrievals: number;
    pm_retrievals: number;
  };
  note: string;
};
```

In the confirmed January 2024 test, Jan 15 was `no_data` and Jan 16 had a valid `0.4414 m3/m3` reading. The screenshot did not establish Jan 17's status. **Frontend scope:** this endpoint is useful for a short regional pilot demo, not worldwide real-time soil-moisture queries.

### `GET /api/vegetation/history`

**Purpose:** MODIS `MOD13Q1` NDVI/EVI observations at a point (16-day composites).  
**Required query:** `latitude`, `longitude`, `start_date`, `end_date`  
**Limit:** 121 calendar days inclusive by route, and no more than 10 composite dates in the service.

Verified test URL:

```text
/api/vegetation/history?latitude=15.7&longitude=120.9&start_date=2024-01-01&end_date=2024-04-30
```

Response shape:

```ts
type VegetationHistory = {
  source: string;
  dataset: string; // MOD13Q1
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
  temporal_resolution: string; // "16-day composite"
  spatial_resolution_m: number; // 250
  observations: {
    date: string;
    modis_date: string; // AYYYYDDD
    ndvi: number | null;
    evi: number | null;
    qa_value: number | null;
    status: "valid" | "no_data";
    product_version: string | null;
  }[];
  count: number;
  note: string;
};
```

Verified example observations (from the user's successful local test):

| Composite start | NDVI | EVI | QA | Status |
|---|---:|---:|---:|---|
| 2024-01-01 | 0.2864 | 0.1498 | 2116 | valid |
| 2024-01-17 | 0.3040 | 0.1537 | 2116 | valid |
| 2024-02-02 | 0.3168 | 0.1659 | 2116 | valid |
| 2024-02-18 | 0.5291 | 0.3795 | 2116 | valid |

Current `product_version` may be `null`; display “version not supplied” rather than implying a version. **NDVI and EVI are not percentages or direct crop-yield measures.**

### `GET /api/overview`

**Purpose:** the single endpoint the frontend uses for every page. Returns the 12 most recent completed months for one point, with each indicator compared with its own baseline, an experimental combined index, and the mascot mood.  
**Required query:** `latitude`, `longitude`  
**Optional query:**

- `end_month=YYYY-MM`: last month of the 12-month window. Must be a completed month, `2007-01` or later. Default: the latest completed month.
- `baseline_start`, `baseline_end`: baseline years for rainfall and vegetation (send both). 3 to 10 years, starting 2001 or later, ending before the first year of the window. Default: the 5 years before the window.
- `refresh=true`: ignore cached results and fetch from NASA again.

Invalid period values return `400` with a message. The soil percentile always uses the 20 years before the window.

Example:

```text
/api/overview?latitude=15.7&longitude=120.9
```

Sources and methods:

- **Rainfall:** NASA POWER `PRECTOTCORR`, summed per month (complete months only). Baseline is the mean of the same calendar month over the 5 years before the observation window (at least 3 complete years needed).
- **Soil:** NASA POWER `GWETTOP` surface soil wetness (model-based, 0-1 fraction), monthly mean (at least 20 valid days). Percentile is the rank of that mean among the same calendar month over the 20 years before the window (at least 10 needed). This is **not** SMAP.
- **Vegetation:** MODIS `MOD13Q1` NDVI from the ORNL DAAC subset API, monthly mean of quality-filtered composites. Baseline is the same calendar month over the same 5 years (at least 3 needed).
- **Combined index (experimental):** mean of the available signed scores, each clipped to -1..+1: rainfall `-anomaly_mm/90`, soil `(50 - percentile)/40`, vegetation `-anomaly/0.2`. Positive means drier. Missing indicators are skipped, never counted as zero.
- **Mascot mood** (`latest.mood`): `default` when no index is available, `happy` for index <= 0.1, `moderate` for <= 0.33, `negative` above that. It uses the most recent month that has an index.

Response shape:

```ts
type Status = "below" | "normal" | "above" | "no_data";
type Overview = {
  location: Coordinates;
  period: { start_month: string; end_month: string; months: number }; // YYYY-MM
  baseline_period: { start_year: number; end_year: number };
  soil_reference_period: { start_year: number; end_year: number };
  records: {
    month: string; // YYYY-MM
    rainfall: { observed_mm: number | null; baseline_mm: number | null; anomaly_mm: number | null; percent_departure: number | null; observed_days: number; expected_days: number; valid_baseline_years: number; status: Status };
    soil: { wetness: number | null; baseline_wetness: number | null; percentile: number | null; valid_days: number; expected_days: number; valid_reference_years: number; status: Status };
    vegetation: { ndvi: number | null; baseline_ndvi: number | null; anomaly: number | null; composites_valid: number; composites_total: number; valid_baseline_years: number; status: Status };
    combined: { index: number | null; label: string; indicators_used: string[] };
  }[];
  latest: { month: string | null; combined_index: number | null; label: string; mood: "default" | "happy" | "moderate" | "negative" };
  sources: Record<"precip" | "soil" | "ndvi", { dataset: string; variable: string; unit: string; baseline_period: string; native_resolution: string; limitation: string }>;
  thresholds: Record<string, string>;
  warnings: string[]; // months without data, failed upstream requests
  generated_at: string; // ISO timestamp, UTC
  cached: boolean;
  experimental: true;
  note: string;
};
```

Behaviour notes:

- A NASA POWER failure returns `502`. A MODIS failure does **not** fail the request: vegetation values are `null` and `warnings` explains why.
- Results are cached on disk in `backend/data/cache/api/` (ignored by git): the whole overview for 12 hours, and MODIS composites older than 120 days permanently. The first request for a new location needs about 16 MODIS requests and can take up to a minute; later requests are fast. Delete that folder or pass `refresh=true` to refetch.
- Values describe one point (the frontend sends the center of the selected area), not an area average.

### `POST /api/overview/areas`

**Purpose:** rainfall anomaly and soil wetness percentile per month for many areas in one call. The map uses it to colour each boundary by its own value.  
**Body (JSON):**

```ts
{
  points: { id: string; latitude: number; longitude: number }[]; // 1 to 150, id is the PSGC code
  end_month?: string;       // same rules as GET /api/overview
  baseline_start?: number;
  baseline_end?: number;
  refresh?: boolean;
}
```

**Response:**

```ts
{
  months: string[];           // the 12 months, YYYY-MM
  baseline_period: { start_year: number; end_year: number };
  soil_reference_period: { start_year: number; end_year: number };
  grid_degrees: number;       // 0.25
  indicators: ["rainfall", "soil"];
  areas: {
    id: string; latitude: number; longitude: number; // the snapped point actually read
    status: "ok" | "error";
    rainfall_anomaly_mm: (number | null)[];          // one value per month
    soil_percentile: (number | null)[];
  }[];
  failed: number;
  note: string;
}
```

Notes: each point is snapped to a 0.25 degree grid so neighbouring areas share one NASA POWER request, with up to 4 requests at a time. Results are cached for 7 days. Vegetation is not included because it needs many slow requests per point. A point whose request fails has `status: "error"` and `null` values; the call itself still returns `200`.

### `POST /api/hulaworld/chat`

**Purpose:** AI assistant reply for the chat panel.  
**Body (JSON):** `{ "message": string (1-1000 chars), "latitude"?: number, "longitude"?: number }`. Latitude and longitude must be sent together.  
**Response:** `{ "agent": string, "reply": string, "tools_used": string[] }`  
**Errors:** `503` when the Azure OpenAI settings are missing, `502` when the AI provider fails, `400`/`422` for invalid input.

## 5. Frontend data-display rules

1. **Use one selected location** for each request and show that location in the UI. A globe click should pass latitude/longitude, but warn when the selected place is unsupported by local SMAP data.
2. **Rainfall:** use a **monthly** axis and display units as **mm**, not `mm/day`, for monthly totals/anomalies. Negative anomaly is a rainfall deficit, not a definitive drought rating.
3. **SMAP:** show each actual observation date, AM/PM period, and `m3/m3` unit. Do not convert missing days to 0, and do not present a single measurement as a historical anomaly.
4. **MODIS:** plot by actual composite dates, label it 16-day composite NDVI/EVI, and show gaps for `null` quality-filtered values. Do not connect observations as if daily.
5. **Do not combine metrics into an unsupported 0–100 drought score.** For now place indicators in separate but coordinated cards/charts.
6. **Data transparency:** show product, original parameter, quality, date, selected baseline years, and a brief limitations tooltip or methodology link.
7. **States:** distinguish `loading`, `success`, `no_data`, `invalid parameters (400/422)`, and `provider/server error (500/502)`.
8. **Date windows differ:** SMAP history ≤ 14 days; vegetation ≤ 121 days and ≤ 10 composites; rainfall timeline up to 12 months in one year. The UI should use dataset-specific date controls rather than one unvalidated universal range.

## 6. Minimal React usage

Copy the companion `hulaw-api.ts` into `frontend/src/services/hulaw-api.ts` and update `frontend/.env` as above.

```tsx
import { useEffect, useState } from "react";
import { hulawApi, type SoilMoistureObservation } from "./services/hulaw-api";

export function SoilMoistureDemo() {
  const [result, setResult] = useState<SoilMoistureObservation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    hulawApi.soilMoisture(15.7, 120.9, "2024-01-16")
      .then(data => { if (!cancelled) setResult(data); })
      .catch(err => { if (!cancelled) setError(String(err)); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p>API error: {error}</p>;
  if (!result) return <p>Loading…</p>;
  if (result.status === "no_data") return <p>No valid SMAP retrieval: {result.note}</p>;

  return (
    <article>
      <h2>SMAP soil moisture</h2>
      <p>{result.soil_moisture} {result.unit}</p>
      <small>{result.date} · {result.retrieval_period} · flag {result.quality_flag}</small>
    </article>
  );
}
```

The TypeScript client also has functions for every other endpoint.

## 7. Frontend handoff checklist

- [ ] Backend responds at `GET /api/health`.
- [ ] React Vite origin added to CORS in `backend/app/main.py`.
- [ ] `frontend/.env` points to the correct running backend URL.
- [ ] Copy `hulaw-api.ts` to `frontend/src/services/hulaw-api.ts`.
- [ ] Test rainfall timeline, vegetation history, and SMAP history independently.
- [ ] Handle `null` values, unavailable local SMAP files, and explicit error states.
- [ ] Label dates, source products, baselines, spatial scales, and units on charts.
- [ ] Verify `/openapi.json` against the shipped backend code before merging.
- [ ] Test with teammate's own computer or deployed backend, not just your local loopback address.

## 8. Outstanding work / non-goals

- **Deferred:** long-term SMAP baseline and soil-moisture anomalies due to insufficient geographically and temporally comparable observations.
- **Not yet built:** cross-indicator combined assessment, verified agricultural exposure overlay, automatic SMAP ingestion for arbitrary locations, globe raster layers, deployment, and official alerts.
- **Metadata cleanup:** confirm/version MODIS source metadata; preserve raw provenance and quality fields.
- **Performance:** add server-side caching to avoid repeat NASA upstream requests and HDF5 grid scans.
- **Scientific validation:** compare products with independent observations; do not claim official drought warnings or predictive accuracy.

## 9. Helpful references

- FastAPI built-in local docs: `http://127.0.0.1:8000/docs`
- FastAPI local OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- NASA POWER: https://power.larc.nasa.gov/
- NASA SMAP NSIDC: https://nsidc.org/data/spl3smp_e
- ORNL DAAC MODIS subset API: https://modis.ornl.gov/rst/api/v1/
- NASA MODIS land products: https://lpdaac.usgs.gov/

**Handoff conclusion:** The backend has tested rainfall, SMAP, and MODIS endpoints. The frontend can integrate and display the three sources now, with clear gaps and scientific limitations. The running backend schema remains the authoritative contract.
