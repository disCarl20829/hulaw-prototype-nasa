# Hulaw

Hulaw is an exploratory drought-intelligence web app with a Philippines-focused demo. It shows how rainfall, surface soil wetness and vegetation greenness have changed over 12 months at a selected location, each compared with its own baseline.

It is a decision-support prototype, not an official drought warning service.

## Parts

| Path | What it is |
|---|---|
| `backend/` | Python / FastAPI service that reads NASA data, computes the indicators and runs the AI assistant |
| `frontend/` | React + TypeScript (Vite) app with a CesiumJS map, Recharts charts, reports and the AI assistant |
| `API.md` | API reference and integration notes |
| `hulaw_context.md` | Project concept, scope and scientific constraints |
| `frontend/README.md` | Frontend pages, data flow and map sources |

## Run locally

Backend, from `backend/` (Windows PowerShell; on macOS/Linux use `source .venv/bin/activate`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Frontend, from `frontend/`:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls the backend at `http://127.0.0.1:8000` unless `VITE_API_BASE_URL` is set in `frontend/.env`. API docs are at `http://127.0.0.1:8000/docs`.

## Data

| Indicator | Source | Notes |
|---|---|---|
| Rainfall anomaly | NASA POWER daily precipitation (`PRECTOTCORR`) | Monthly total minus the same month's mean in the baseline years (default: the 5 years before the period) |
| Surface soil wetness | NASA POWER (`GWETTOP`) | Model-based estimate, shown as a percentile against the 20 years before the period; not a SMAP retrieval |
| Vegetation anomaly | NASA MODIS `MOD13Q1` NDVI via ORNL DAAC | Quality-filtered 16-day composites, centre pixel; often missing in cloudy months |

Values are read at one point (the centre of the selected area), not averaged over the area. The combined index is experimental. The map colours areas by rainfall and soil only.

The backend also has standalone endpoints for daily/monthly rainfall, SMAP `SPL3SMP_E` soil moisture (from local HDF5 files or optional on-demand download) and MODIS NDVI/EVI history. The app does not chart these; the AI assistant uses some of them. See `API.md`.

## Configuration

Backend settings go in `backend/.env` (not committed; loaded at start-up) or the host's environment. All are optional.

| Variable | Purpose |
|---|---|
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_DEPLOYMENT` | AI assistant (Azure OpenAI). The base URL must end in `/openai/v1`. Without them the chat returns 503. |
| `HULAW_CORS_ORIGINS` | Comma-separated exact browser origins. Replaces the default: `https://hulaw.earth`, `https://www.hulaw.earth`, `https://hulaw.vercel.app` and local Vite (`localhost:5173`, `127.0.0.1:5173`). |
| `HULAW_CORS_ORIGIN_REGEX` | Pattern for changing origins such as Vercel previews. |
| `HULAW_CACHE_DIR` | Folder for the NASA cache. Default `backend/data/cache/api/`. |
| `HULAW_PREWARM=1` | Load the default overview at start-up (set in the Dockerfile). |
| `HULAW_SMAP_ON_DEMAND=1` | Download missing SMAP files (~650 MB each) in the background for the SMAP endpoints. Needs `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD`. |
| `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` | NASA Earthdata login, used only for SMAP downloads. |
| `HULAW_SMAP_MAX_FILES` / `HULAW_SMAP_MAX_QUEUE` | SMAP files kept on disk (default 2) / dates queued at once (default 7). |

Frontend: `VITE_API_BASE_URL` in `frontend/.env`.

## Tests

```bash
cd backend
python -m pytest tests -q
```

The tests (`backend/tests/test_overview.py`) replace the NASA services with small fakes, so they run offline. `pytest` is not in `requirements.txt`; install it with `pip install pytest`.

## Deployment

| Part | Host | Notes |
|---|---|---|
| Frontend | Vercel, root directory `frontend/` | `VITE_API_BASE_URL=https://hulaw-prototype-nasa.onrender.com`. The root `vercel.json` is not used with this root directory. |
| Backend | Render (Docker, `backend/Dockerfile`, Python 3.14) | Health check path `/api/health`. Azure OpenAI variables are set in the Render dashboard. |

On Render's free plan the instance sleeps when idle and loses its cache. `.github/workflows/keep-warm.yml` pings `/api/health` every 10 minutes to prevent that. On a paid plan, point `HULAW_CACHE_DIR` at a persistent disk.

## Not built yet

SMAP-based soil moisture with a baseline, an agricultural exposure overlay, area-averaged values, real data for countries other than the Philippines on the globe, and scientific validation of the thresholds and the combined index.
