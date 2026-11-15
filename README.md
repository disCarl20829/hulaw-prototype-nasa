# Hulaw

Hulaw is an exploratory drought-intelligence web app with a Philippines-focused demo. It shows how rainfall, surface soil wetness and vegetation greenness have changed over 12 months at a selected location, each compared with its own baseline.

It is a decision-support prototype, not an official drought warning service.

## Parts

| Folder | What it is |
|---|---|
| `backend/` | Python / FastAPI service that reads NASA data and computes the indicators |
| `frontend/` | React + TypeScript (Vite) app with a Cesium map, charts, reports and the AI assistant |
| `API.md` | API reference and integration notes |
| `hulaw_context.md` | Project concept, scope and scientific constraints |

## Run locally

Backend, from `backend/`:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Frontend, from `frontend/`:

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls the backend at `http://127.0.0.1:8000` unless `VITE_API_BASE_URL` is set in `frontend/.env`.

## Data

| Indicator | Source | Notes |
|---|---|---|
| Rainfall anomaly | NASA POWER daily precipitation (`PRECTOTCORR`) | Monthly total minus the same month's mean in the baseline years |
| Surface soil wetness | NASA POWER (`GWETTOP`) | Model-based estimate, shown as a percentile; not a SMAP retrieval |
| Vegetation anomaly | NASA MODIS `MOD13Q1` NDVI via ORNL DAAC | Quality-filtered 16-day composites; often missing in cloudy months |

Values are read at one point (the center of the selected area), not averaged over the area. The combined index is experimental.

## Configuration

`backend/.env` (not committed):

- Azure OpenAI settings for the AI assistant (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_DEPLOYMENT`).
- `HULAW_CORS_ORIGINS` (optional): comma-separated browser origins allowed to call the API. Defaults to the local Vite addresses.

## Tests

```bash
cd backend
python -m pytest tests -q
```

The tests replace the NASA services with small fakes, so they run offline. `pytest` is not in `requirements.txt`; install it with `pip install pytest`.

SMAP-based soil moisture with a baseline, an agricultural exposure overlay, area-averaged values, deployment, and scientific validation of the thresholds and the combined index.

## Deployment

| Part | Host | Notes |
|---|---|---|
| Frontend | Vercel, root directory `frontend/` | `VITE_API_BASE_URL=https://hulaw-prototype-nasa.onrender.com`. The root `vercel.json` is not used with this root directory. |
| Backend | Render (Docker, `backend/Dockerfile`) | Health check path `/api/health`. Azure OpenAI variables are set in the Render dashboard. |

Backend environment variables (all optional):

## Environment Variables
- HULAWORLD_PROVIDER
- AZURE_OPENAI_BASE_URL
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_DEPLOYMENT
- EARTHDATA_USERNAME
- EARTHDATA_PASSWORD!

- `HULAW_CORS_ORIGINS` - comma-separated exact origins. Default: `hulaw.earth`, `www.hulaw.earth`, `hulaw.vercel.app` and local Vite.
- `HULAW_CORS_ORIGIN_REGEX` - pattern for changing origins such as Vercel previews.
- `HULAW_CACHE_DIR` - folder for the NASA cache. Point it at a persistent disk on a paid plan.
- `HULAW_PREWARM=1` - load the default overview at start-up (set in the Dockerfile).

On Render's free plan the instance sleeps when idle and loses its cache. `.github/workflows/keep-warm.yml` pings `/api/health` every 10 minutes to prevent that.
