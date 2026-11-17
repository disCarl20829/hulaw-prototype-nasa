# Hulaw — API Reference & Frontend Integration Guide

**Updated:** 17 November 2026 (checked against the code in `backend/app/` and `frontend/src/`)  
**Backend:** Python / FastAPI (`backend/app/main.py`, app title "Hulaw World", version 0.1.0)  
**Frontend:** React + TypeScript (Vite), CesiumJS globe, Recharts charts  
**Local API:** `http://127.0.0.1:8000`  
**Deployed frontend:** `https://hulaw.earth` (Vercel)  
**Deployed API:** `https://hulaw-prototype-nasa.onrender.com` (Render, Docker)  
**Interactive API docs:** `/docs` · **Machine-readable schema:** `/openapi.json`

> **Source of truth:** the running backend's `/openapi.json`. This document describes the code as it is now; if the two disagree, follow `/openapi.json` and update this file. Example values below are illustrative unless marked as a tested result.

## 1. Endpoints and status

| Feature | Endpoint | Used by the frontend? | Notes |
|---|---|---|---|
| Service information | `GET /` | No | |
| Service health | `GET /api/health` | No (used by Render and the keep-warm workflow) | |
| Indicator catalog | `GET /api/indicators` | No | Describes the three `/api/overview` indicators |
| Daily rainfall | `GET /api/precipitation` | No | NASA POWER, ≤ 31 days |
| Monthly rainfall | `GET /api/analysis/rainfall/monthly` | No | |
| Rainfall baseline | `GET /api/analysis/rainfall/baseline` | No | |
| Rainfall anomaly | `GET /api/analysis/rainfall/anomaly` | No | |
| Rainfall timeline | `GET /api/analysis/rainfall/timeline` | No (used by the AI assistant) | |
| SMAP single observation | `GET /api/soil-moisture` | No | Needs local HDF5 files or on-demand download |
| SMAP history | `GET /api/soil-moisture/history` | No (used by the AI assistant) | ≤ 14 days |
| MODIS NDVI/EVI history | `GET /api/vegetation/history` | No (used by the AI assistant) | ≤ 121 days and ≤ 10 composites |
| **12-month drought overview** | `GET /api/overview` | **Yes — every page** | Main endpoint |
| **Per-area map series** | `POST /api/overview/areas` | **Yes — map colours** | Rainfall and soil only |
| Hulaworld AI chat | `POST /api/hulaworld/chat` | Yes — assistant panel | Needs Azure OpenAI settings |

The frontend client (`frontend/src/services/hulaw-api.ts`) only wraps the last three. The other routes are for direct use, testing and the AI assistant's tools.

**Interpretation caveats**

- **Rainfall** is NASA POWER daily precipitation (`PRECTOTCORR`, community `AG`, UTC) — **not** GPM IMERG. Daily values are `mm/day`; monthly totals are `mm`. Baselines are short exploratory comparisons (by default the 5 years before the period), **not** official climatological normals or drought classifications.
- **Soil in `/api/overview`** is NASA POWER `GWETTOP` surface soil wetness (model-based, 0–1 fraction), expressed as a percentile. It is **not** SMAP.
- **SMAP endpoints** (`/api/soil-moisture*`) read NASA SMAP `SPL3SMP_E` version `006` HDF5 files (near-surface volumetric soil moisture, `m3/m3`). Files are either already in `backend/data/smap/` or downloaded on demand in the background when that is enabled (see §4). There is no SMAP baseline or anomaly. `no_data` and `pending` are valid responses.
- **Vegetation** is MODIS `MOD13Q1` NDVI/EVI (16-day composites, 250 m) from the ORNL DAAC subset API, centre pixel only, with a strict QA filter, so cloudy periods are often missing. `qa_value` is the raw bit-encoded QA. `product_version` may be `null`. NDVI/EVI changes alone do not prove drought impacts.
- All values are for **one point**, not an area average. Sources have different spatial and time resolutions.

## 2. Local setup

### Backend — from `backend/`

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

`backend/.env` is loaded automatically at start-up (by `app/ai/service.py`, which is imported by `main.py`), so every variable in §2.3 can be set there.

### CORS and compression — already in `backend/app/main.py`

No code change is needed. `main.py` adds `GZipMiddleware` (responses ≥ 1000 bytes) and `CORSMiddleware` with:

- `allow_origins` from `HULAW_CORS_ORIGINS` (comma-separated exact origins). Default: `https://hulaw.earth`, `https://www.hulaw.earth`, `https://hulaw.vercel.app`, `http://localhost:5173`, `http://127.0.0.1:5173`. Setting the variable **replaces** the default list.
- `allow_origin_regex` from `HULAW_CORS_ORIGIN_REGEX` (optional), e.g. `https://hulaw-[a-z0-9-]+\.vercel\.app` for Vercel previews.
- `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=False`.

No browser API key is needed.

### Backend environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `AZURE_OPENAI_API_KEY` | `app/ai/service.py` | Azure OpenAI key for the chat. Missing → chat returns `503`. |
| `AZURE_OPENAI_BASE_URL` | `app/ai/service.py` | Must be `https://…` and end in `/openai/v1`. |
| `AZURE_OPENAI_DEPLOYMENT` | `app/ai/service.py` | Model deployment name. |
| `HULAW_CORS_ORIGINS` | `app/main.py` | See above. |
| `HULAW_CORS_ORIGIN_REGEX` | `app/main.py` | See above. |
| `HULAW_CACHE_DIR` | `app/services/cache_service.py` | Cache folder. Default `backend/data/cache/api/`. |
| `HULAW_PREWARM` | `app/main.py` | `1`/`true`/`yes`: load the overview for the default point (15.7, 120.9) at start-up. Set in the Dockerfile. |
| `HULAW_SMAP_ON_DEMAND` | `app/services/smap_fetch_service.py` | `1`/`true`/`yes`: download missing SMAP files in the background. Also needs the two Earthdata variables. |
| `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` | `smap_fetch_service.py` (via `earthaccess`) | NASA Earthdata login for SMAP downloads. |
| `HULAW_SMAP_MAX_FILES` | `smap_fetch_service.py` | SMAP files kept on disk (default 2, about 1.3 GB). |
| `HULAW_SMAP_MAX_QUEUE` | `smap_fetch_service.py` | Dates queued or downloading at once (default 7). |

### Frontend — `frontend/.env`

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

`src/services/hulaw-api.ts` reads it (trailing slashes removed; default `http://127.0.0.1:8000`). Restart Vite after changing it. The deployed frontend (Vercel) uses `https://hulaw-prototype-nasa.onrender.com`.

> `127.0.0.1` is the computer running the browser. For another machine, point `VITE_API_BASE_URL` at a reachable backend and add the frontend's exact origin to `HULAW_CORS_ORIGINS`. Never expose Earthdata credentials, Azure keys or `.netrc` to the browser.

## 3. API conventions

- Methods: `GET` for all routes except `POST /api/overview/areas` and `POST /api/hulaworld/chat` (JSON bodies).
- Dates: query dates are `YYYY-MM-DD`; months are `YYYY-MM`; `/api/precipitation` observation dates are `YYYYMMDD`.
- Coordinates: decimal degrees, `latitude` −90…90, `longitude` −180…180 (validated → `422`).
- Missing values are `null`. Never convert them to zero or draw a line through them.
- `status: "no_data"` (and `"pending"` for SMAP) are successful responses, not errors.
- Errors (body `{"detail": "..."}`):
  - `400` — invalid date/period combination or business rule (messages are user-readable).
  - `422` — missing or badly typed parameter, or unknown field in a POST body.
  - `500` — SMAP HDF5 file could not be processed.
  - `502` — upstream NASA (POWER or MODIS) failed or returned something unexpected; or the AI provider failed.
  - `503` — AI chat not configured.
- NASA requests can be slow. All upstream calls share one pooled HTTP client (`app/services/http_client.py`, 90 s timeout).

### Server-side caching

`app/services/cache_service.py` keeps a two-tier cache: an in-memory LRU (512 entries, values ≤ 100 kB) and JSON files in `HULAW_CACHE_DIR` (default `backend/data/cache/api/`, git-ignored). Files older than 90 days are deleted at start-up. Concurrent identical requests share one upstream call.

| What | Lifetime |
|---|---|
| NASA POWER daily data used by `/api/overview` and `/api/overview/areas` | 30 days |
| Whole `/api/overview` result | 12 hours (not stored if any upstream request failed) |
| `/api/overview/areas` series per grid cell | 7 days |
| MODIS date list per point | 24 hours |
| MODIS composite blocks | 24 hours; permanently once the last composite is > 120 days old |
| SMAP point values (on-demand mode only) | Permanent |

The older routes (`/api/precipitation`, `/api/analysis/rainfall/*`, `/api/vegetation/history`) are **not** cached.

## 4. Endpoint reference

### `GET /`

```json
{"project":"Hulaw","description":"Global Drought Intelligence Platform","status":"running"}
```

### `GET /api/health`

```json
{"status":"healthy","service":"hulaw-backend"}
```

### `GET /api/indicators`

No parameters. Describes the three indicators served by `/api/overview` (`precipitation`, `soil_moisture`, `vegetation`).

```ts
type IndicatorList = {
  indicators: { id: string; name: string; dataset: string; description: string; unit: string }[];
  count: number;
};
```

Metadata only; it does not say whether observations exist for a place or date.

### `GET /api/precipitation`

Daily NASA POWER `PRECTOTCORR` for a point.  
**Query:** `latitude`, `longitude`, `start`, `end` (`YYYY-MM-DD`).  
**Rules:** `end ≥ start`; at most 31 days (`end − start ≤ 30`), else `400`.

```text
/api/precipitation?latitude=14.5995&longitude=120.9842&start=2024-01-01&end=2024-01-07
```

```ts
type DailyPrecipitation = {
  source: string;          // "NASA POWER"
  dataset: string;         // "NASA POWER daily precipitation"
  parameter: string;       // "PRECTOTCORR"
  latitude: number;
  longitude: number;
  unit: string;            // "mm/day"
  time_standard: string;   // "UTC"
  observations: { date: string; precipitation_mm: number | null }[]; // date YYYYMMDD
};
```

NASA POWER's negative fill values (−999) are returned as `null`.

### `GET /api/analysis/rainfall/monthly`

Total rainfall for one calendar month.  
**Query:** `latitude`, `longitude`, `year` (2000–2100), `month` (1–12).  
**Rules:** completed months only (`400` otherwise).

```ts
type MonthlyRainfall = {
  location: { latitude: number; longitude: number };
  period: { year: number; month: number };
  source: string; dataset: string; parameter: string;
  unit: string; // "mm"
  monthly_rainfall_mm: number | null;
  observed_days: number;
  expected_days: number;
  complete: boolean;
  daily_observations: { date: string; precipitation_mm: number | null }[];
};
```

If any day is missing, `complete` is `false` and `monthly_rainfall_mm` is `null` (no partial sums).

### `GET /api/analysis/rainfall/baseline`

Mean rainfall for the same calendar month across earlier years.  
**Query:** `latitude`, `longitude`, `month`, `start_year` (≥ 2001), `end_year` (≥ 2001).  
**Rules:** `end_year ≥ start_year`; at most 10 years; the last requested month must be completed. A numeric baseline needs at least 3 complete years, otherwise `baseline_rainfall_mm` is `null` and `sufficient_data` is `false`. Years are fetched one after another, so 10 years means 10 NASA calls.

```ts
type RainfallBaseline = {
  location: { latitude: number; longitude: number };
  month: number;
  baseline_period: { start_year: number; end_year: number };
  baseline_rainfall_mm: number | null;
  unit: string;        // "mm"
  source: string;      // "NASA POWER"
  parameter: string;   // "PRECTOTCORR"
  valid_years: number;
  requested_years: number;
  sufficient_data: boolean;
  historical_data: { year: number; month: number; rainfall_mm: number | null; complete: boolean }[];
  note: string;
};
```

### `GET /api/analysis/rainfall/anomaly`

Observed monthly rainfall minus the baseline.  
**Query:** `latitude`, `longitude`, `year` (2001–2100), `month`, `baseline_start`, `baseline_end` (≥ 2001).  
**Rules:** `baseline_end ≥ baseline_start`; `baseline_end < year`; at most 10 baseline years; completed month.

```ts
type RainfallAnomaly = {
  location: { latitude: number; longitude: number };
  period: { year: number; month: number };
  baseline_period: { start_year: number; end_year: number };
  observed_rainfall_mm: number | null;
  baseline_rainfall_mm: number | null;
  rainfall_anomaly_mm: number | null;
  percent_departure: number | null;
  condition: "below_normal" | "above_normal" | "near_normal" | "insufficient_data";
  source: string; dataset: string; parameter: string;
  unit: string; // "mm"
  observed_days: number;
  expected_days: number;
  valid_baseline_years: number;
  note: string;
};
```

`anomaly = observed − baseline`; `percent_departure = anomaly / baseline × 100` only when baseline > 0. `condition` is just the sign of the anomaly (`near_normal` only when it is exactly 0) — there is no tolerance band and it is **not** an official drought severity.

### `GET /api/analysis/rainfall/timeline`

Monthly rainfall, baseline and anomaly for a range of months within one year.  
**Query:** `latitude`, `longitude`, `year` (2001–2100), `start_month`, `end_month`, `baseline_start`, `baseline_end` (≥ 2001).  
**Rules:** `start_month ≤ end_month`; 3–10 baseline years ending before `year`; `end_month` of `year` must be completed. Fetches the observed year and each baseline year in parallel (up to 4 at a time).

```ts
type RainfallTimeline = {
  location: { latitude: number; longitude: number };
  period: { year: number; start_month: number; end_month: number };
  baseline_period: { start_year: number; end_year: number };
  source: string; dataset: string; parameter: string;
  unit: string; // "mm"
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
  summary: { months_requested: number; months_with_data: number; months_below_baseline: number; months_above_baseline: number };
  note: string;
};
```

The AI assistant uses this endpoint as its `get_rainfall_timeline` tool. The frontend charts use `/api/overview` instead.

### `GET /api/soil-moisture`

One SMAP observation for one date.  
**Query:** `latitude`, `longitude`, `observation_date` (`YYYY-MM-DD`, not in the future).

```text
/api/soil-moisture?latitude=15.7&longitude=120.9&observation_date=2024-01-16
```

Tested result (excerpt, from a local run with the file present):

```json
{"date":"2024-01-16","soil_moisture":0.4414,"unit":"m3/m3","quality_flag":8,"distance_km":4.88,"retrieval_period":"AM","status":"valid"}
```

```ts
type SoilMoistureObservation = {
  source: string;     // "NASA NSIDC"
  dataset: string;    // "SMAP SPL3SMP_E"
  version: string;    // "006"
  date: string;
  requested_location: { latitude: number; longitude: number };
  grid_location: { latitude: number; longitude: number } | null;
  soil_moisture: number | null; // m3/m3
  unit: string;
  quality_flag: number | null;  // accepted: 0 or 8
  distance_km: number | null;
  retrieval_period: "AM" | "PM" | null;
  status: "valid" | "no_data" | "pending";
  filename: string | null;
  note: string;
};
```

How it works (`app/services/smap_service.py`):

- Looks for `backend/data/smap/SMAP_L3_SM_P_E_<YYYYMMDD>_*.h5` and picks the nearest AM or PM cell within **20 km** with a value in 0–1 and quality flag 0 or 8.
- **File missing, on-demand off** (default): `status: "no_data"`, note "No downloaded SMAP file exists for this date."
- **File missing, on-demand on** (`HULAW_SMAP_ON_DEMAND=1` plus Earthdata login): the date is queued for a background download (~650 MB per file) and the response is `status: "pending"`. Ask again a few minutes later; once the file arrives the value is extracted and cached, so it survives after the file is deleted to make room (at most `HULAW_SMAP_MAX_FILES` files are kept). If the queue is full, NASA has no file for that date, or the download failed, the response is `no_data` with an explanatory note. Failed dates are retried after 15 minutes.

### `GET /api/soil-moisture/history`

One SMAP observation per day for a short range.  
**Query:** `latitude`, `longitude`, `start_date`, `end_date`.  
**Rules:** `end_date ≥ start_date`; not in the future; at most 14 days inclusive.

```ts
type SoilMoistureHistory = {
  location: { latitude: number; longitude: number };
  start_date: string;
  end_date: string;
  source: string; dataset: string; version: string; unit: string;
  observations: SoilMoistureObservation[];
  summary: {
    days_requested: number;
    days_valid: number;
    days_missing_file: number;      // includes pending days (no file yet)
    days_missing_retrieval: number;
    days_pending: number;
    am_retrievals: number;
    pm_retrievals: number;
  };
  note: string;
};
```

Tested result (local, January 2024): 15 Jan was `no_data`; 16 Jan was valid at `0.4414 m3/m3`. Useful for short pilot checks, not worldwide real-time soil moisture.

### `GET /api/vegetation/history`

MODIS `MOD13Q1` NDVI/EVI for a point.  
**Query:** `latitude`, `longitude`, `start_date`, `end_date`.  
**Rules:** `end_date ≥ start_date`; not in the future; at most 121 days inclusive; more than 10 composites in the range → `400` ("Select a shorter period"). An ORNL failure → `502`. Not cached.

```text
/api/vegetation/history?latitude=15.7&longitude=120.9&start_date=2024-01-01&end_date=2024-04-30
```

```ts
type VegetationHistory = {
  source: string;               // "NASA ORNL DAAC"
  dataset: string;              // "MOD13Q1"
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
  temporal_resolution: string;  // "16-day composite"
  spatial_resolution_m: number; // 250
  observations: {
    date: string;               // composite start, YYYY-MM-DD
    modis_date: string;         // AYYYYDDD
    ndvi: number | null;
    evi: number | null;
    qa_value: number | null;    // raw VI Quality bits
    status: "valid" | "no_data";
    product_version: string | null;
  }[];
  count: number;
  note: string;
};
```

Values are raw × 0.0001, accepted only when the raw value is −2000…10000 **and** the VI Quality bits pass all of: MODLAND QA = 00, usefulness ≤ 2, aerosol quantity ≤ 1, no adjacent cloud, no mixed clouds, land/water flag = land, no snow/ice, no shadow. `status` is `valid` only when both NDVI and EVI pass.

Tested result (local, earlier QA version; values may differ under the current filter):

| Composite start | NDVI | EVI | QA | Status |
|---|---:|---:|---:|---|
| 2024-01-01 | 0.2864 | 0.1498 | 2116 | valid |
| 2024-01-17 | 0.3040 | 0.1537 | 2116 | valid |
| 2024-02-02 | 0.3168 | 0.1659 | 2116 | valid |
| 2024-02-18 | 0.5291 | 0.3795 | 2116 | valid |

### `GET /api/overview`

The endpoint every page uses. Returns the 12 most recent completed months for one point, each indicator against its own baseline, an experimental combined index and the mascot mood.

**Query:**

- `latitude`, `longitude` (required).
- `end_month=YYYY-MM` — last month of the 12-month window. Must be completed and `2007-01` or later. Default: the latest completed month.
- `baseline_start`, `baseline_end` — baseline years for rainfall and vegetation; send both or neither. 3–10 years, starting 2001 or later, ending before the first year of the window. Default: the 5 years before the window. (The query accepts ≥ 1981, but the service rejects anything before 2001 with `400`.)
- `refresh=true` — ignore cached results and fetch from NASA again.

The soil percentile always uses the **20 years** before the window, whatever baseline is chosen.

```text
/api/overview?latitude=15.7&longitude=120.9
```

Methods (`app/services/overview_service.py`):

- **Rainfall:** NASA POWER `PRECTOTCORR`, summed per month (complete months only). Baseline = mean of the same calendar month in the baseline years (≥ 3 complete years needed). Status: `below` if anomaly < −30 mm, `above` if > +30 mm.
- **Soil:** NASA POWER `GWETTOP`, monthly mean (≥ 20 valid days). Percentile = empirical rank among the same calendar month in the 20 reference years (≥ 10 needed). Status: `below` < 25, `above` > 75. Not SMAP.
- **Vegetation:** MODIS `MOD13Q1` NDVI from ORNL DAAC (same QA filter as above), monthly mean of valid composites; baseline over the same years as rainfall (≥ 3 needed). Status: `below` if anomaly < −0.05, `above` if > +0.05.
- **Combined index (experimental):** mean of the available signed scores, each clipped to −1…+1: rainfall `−anomaly_mm/90`, soil `(50 − percentile)/40`, vegetation `−anomaly/0.2`. Positive = drier. Missing indicators are skipped, never counted as zero. Labels: > 0.66 "Extreme dryness signal", > 0.33 "Severe dryness signal", > 0.1 "Moderate dryness signal", ≥ −0.1 "Near normal", otherwise "Wetter than normal"; `null` → "Insufficient data".
- **Mascot mood** (`latest.mood`), from the most recent month that has an index: `default` (no index), `happy` (≤ 0.1), `moderate` (≤ 0.33), `negative` (> 0.33).

```ts
type Status = "below" | "normal" | "above" | "no_data";
type Overview = {
  location: { latitude: number; longitude: number };
  period: { start_month: string; end_month: string; months: number }; // YYYY-MM
  baseline_period: { start_year: number; end_year: number };
  soil_reference_period: { start_year: number; end_year: number };
  records: {
    month: string; // YYYY-MM
    rainfall: { observed_mm: number | null; baseline_mm: number | null; anomaly_mm: number | null; percent_departure: number | null; observed_days: number; expected_days: number; valid_baseline_years: number; status: Status };
    soil: { wetness: number | null; baseline_wetness: number | null; percentile: number | null; valid_days: number; expected_days: number; valid_reference_years: number; status: Status };
    vegetation: { ndvi: number | null; baseline_ndvi: number | null; anomaly: number | null; composites_valid: number; composites_total: number; valid_baseline_years: number; status: Status };
    combined: { index: number | null; label: string; indicators_used: string[] }; // "rainfall" | "soil" | "vegetation"
  }[];
  latest: { month: string | null; combined_index: number | null; label: string; mood: "default" | "happy" | "moderate" | "negative" };
  sources: Record<"precip" | "soil" | "ndvi", { dataset: string; variable: string; unit: string; baseline_period: string; native_resolution: string; limitation: string }>;
  thresholds: Record<"precip" | "soil" | "ndvi" | "combined", string>;
  warnings: string[];   // months without data, failed MODIS requests
  generated_at: string; // ISO timestamp, UTC
  cached: boolean;
  experimental: boolean; // always true
  note: string;
};
```

Behaviour:

- One NASA POWER request covers rainfall and soil for the whole range (earliest of soil/baseline start through the end month). A POWER failure returns `502`.
- MODIS: the provider's date list is split into fixed blocks of 10 composites and only blocks containing wanted months are requested, so blocks are reused across periods and baselines. At most 3 MODIS requests run at once **for the whole server**; each is retried once. A MODIS failure does **not** fail the request: affected values are `null` and `warnings` explains why.
- The result is cached for 12 hours unless a request failed. The response carries `Cache-Control: private, max-age=600` when complete (and not a refresh), otherwise `no-store`.
- The first load for a new point can take up to about a minute; later loads are fast.

### `POST /api/overview/areas`

Rainfall anomaly and soil percentile per month for many areas in one call. The map colours each boundary with it.

**Body (JSON, unknown fields → `422`):**

```ts
{
  points: { id: string; latitude: number; longitude: number }[]; // 1–150 points; id 1–40 chars (the frontend sends the PSGC code)
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
  indicators: string[];       // ["rainfall", "soil"]
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

Each point is snapped to a 0.25° grid so neighbouring areas share one NASA POWER request; up to 4 requests run at a time. Results are cached for 7 days per grid cell. Vegetation is not included. A point whose request fails has `status: "error"` and `null` values; the call still returns `200`. Invalid period values return `400`.

### `POST /api/hulaworld/chat`

AI assistant ("Hulaworld") reply for the chat panel.

**Body (JSON, unknown fields → `422`):** `{ "message": string (1–1000 chars), "latitude"?: number, "longitude"?: number }`. Send latitude and longitude together or not at all.  
**Response:** `{ "agent": "Hulaworld", "reply": string, "tools_used": string[] }`  
**Errors:** `503` when Azure OpenAI settings are missing or invalid; `502` when the AI provider fails; `400`/`422` for invalid input.

How it works (`app/ai/`):

- Uses the Azure OpenAI **Responses API** through the `openai` SDK (`max_output_tokens` 650, `store=false`), with the system prompt in `prompts.py`.
- NASA tools are offered **only when a location is sent**; the frontend's coordinates always override the model's. Without a location the model answers generally and asks for one if measurements are needed.
- Tools (`tools.py`, executed by `tool_executor.py` against this same API in-process):
  - `get_rainfall_timeline` → `/api/analysis/rainfall/timeline` (3–10 baseline years, completed months).
  - `get_soil_moisture_history` → `/api/soil-moisture/history`, at most 7 days.
  - `get_vegetation_history` → `/api/vegetation/history`, at most 45 days.
- If the message mentions rainfall/precipitation, soil moisture/SMAP, or vegetation/NDVI/EVI/MODIS, those tools are forced. At most 3 tool calls per message. SMAP filenames are stripped from tool results.
- `tools_used` lists only tools that returned usable data.

## 5. Frontend data-display rules

1. Use one location per request and show it. With no area selected the app uses the Central Luzon reference point (15.7, 120.9); selecting an area sends its centre.
2. Rainfall: monthly axis, monthly totals and anomalies in **mm** (not mm/day). A negative anomaly is a deficit, not a drought rating.
3. Soil (overview): label it as **NASA POWER surface soil wetness percentile**, not SMAP.
4. Vegetation: label as MODIS NDVI, and show gaps for `null`. Mention that crop cycles, clouds and land use also change NDVI.
5. The combined index is **experimental** (−1…+1, positive = drier). Show the individual indicators alongside it; never present it as an official 0–100 severity score.
6. Show dataset, variable, baseline years, resolution and limitations (from `sources`) and any `warnings`.
7. Distinguish `loading`, `success`, `no_data`, `400/422` and `502/503` states. The app shows a banner with a Retry button on errors.
8. Date limits differ per route: overview 12 months; SMAP history ≤ 14 days; vegetation history ≤ 121 days and ≤ 10 composites; rainfall timeline within one year.

## 6. Frontend client

`frontend/src/services/hulaw-api.ts` is the only file that talks to the backend. It exports:

- `fetchOverview(latitude, longitude, { query?, refresh?, signal? })` → `GET /api/overview`
- `fetchAreaSeries(points, query?, signal?)` → `POST /api/overview/areas`
- `sendChat(message, location?)` → `POST /api/hulaworld/chat`
- `overviewToRegion(...)`, `emptyRegion(...)` — convert to the `Region` shape the views use
- `resolvePeriod(...)`, `validatePeriod(...)`, `lastCompletedMonth()`, `monthsEnding(...)` — the same period rules as the backend
- `ApiError` — thrown with the backend's `detail` message and HTTP status

`src/hooks/useOverview.ts` wraps `fetchOverview` with an in-memory cache per location and period, abort on change, and a `reload(refresh?)` function.

Minimal use:

```tsx
import { useEffect, useState } from "react";
import { fetchOverview, type OverviewResponse } from "./services/hulaw-api";

export function OverviewDemo() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchOverview(15.7, 120.9, { signal: controller.signal })
      .then(setData)
      .catch((err) => { if (!controller.signal.aborted) setError(String(err.message ?? err)); });
    return () => controller.abort();
  }, []);

  if (error) return <p>API error: {error}</p>;
  if (!data) return <p>Loading…</p>;

  return (
    <article>
      <h2>{data.latest.month ?? "No month with data"}</h2>
      <p>{data.latest.label} ({data.latest.combined_index ?? "no index"}) · experimental</p>
      <small>Baseline {data.baseline_period.start_year}–{data.baseline_period.end_year}</small>
    </article>
  );
}
```

## 7. Integration checklist

- [ ] `GET /api/health` responds.
- [ ] The frontend's origin is allowed (default list or `HULAW_CORS_ORIGINS` / `HULAW_CORS_ORIGIN_REGEX`).
- [ ] `frontend/.env` (or the Vercel variable) points to the right backend.
- [ ] `/api/overview` loads for the default point; `/api/overview/areas` colours the map.
- [ ] Azure OpenAI variables are set if the assistant is needed.
- [ ] `null` values, warnings and error states are handled and visible.
- [ ] Charts label dates, sources, baselines, units and resolution.
- [ ] `/openapi.json` matches this document.

## 8. Not built / known gaps

- SMAP baseline or anomaly; SMAP is not used by the frontend.
- Area-averaged values (everything is read at one point).
- Agricultural exposure overlay, gridded/raster map layers, alerts, multi-region comparison.
- Other countries on the globe use an illustrative placeholder profile (`frontend/src/data/severity.ts`), not real data.
- Scientific validation of the thresholds and the combined index.
- `product_version` for MODIS is often `null`.

## 9. References

- NASA POWER: https://power.larc.nasa.gov/
- NASA SMAP SPL3SMP_E (NSIDC): https://nsidc.org/data/spl3smp_e
- ORNL DAAC MODIS subset API: https://modis.ornl.gov/rst/api/v1/
- NASA LP DAAC (MODIS products): https://lpdaac.usgs.gov/
