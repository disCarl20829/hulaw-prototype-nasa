HULAW — MASTER PROJECT CONTEXT & AI HANDOFF
Version: 1.1 | Prepared: 13 November 2026 | Updated to match the code: 17 November 2026
Document type: Plain-text project brief, team reference, and reusable AI prompt context
Status: WORKING PROTOTYPE (see section 01A) plus concept and proposals for later phases. Sections other than 01A, 09A, 10A, 12 and 13 still describe the concept; they are not a declaration of completed functionality.

======================================================================
01. HOW TO USE THIS DOCUMENT
======================================================================
This file is the shared source of context for Hulaw. Teammates can paste its content into an AI assistant before asking for implementation help, or keep it in the repository as PROJECT_CONTEXT.txt. Sections marked "DECIDED DIRECTION" record the concept selected in the discussion; sections marked "PROPOSED" are recommendations that the team can change; items marked "TO VALIDATE" are deliberately not asserted as finished or scientifically proven.

IMPORTANT: Hulaw has been selected over two other project ideas (Urban Heat Intelligence and EarthPulse). A working prototype exists and is deployed (section 01A). No team roles, user interviews, scientific validation, or trained prediction model have been confirmed. AI assistants must not claim these exist without new evidence.

======================================================================
01A. CURRENT PROTOTYPE — WHAT THE CODE DOES (AS OF 17 NOVEMBER 2026)
======================================================================
This section is the authoritative summary of what is built. API.md has the full endpoint reference; README.md has setup and configuration.

DATA ACTUALLY USED BY THE APP (all read at ONE point, not an area average):
- Rainfall: NASA POWER daily precipitation, parameter PRECTOTCORR (NOT GPM IMERG). Summed per month (complete months only). Anomaly = monthly total minus the mean of the same calendar month over the baseline years (default: the 5 years before the 12-month period; 3-10 years allowed; at least 3 complete years needed).
- Soil: NASA POWER GWETTOP surface soil wetness (model-based, 0-1 fraction; NOT a SMAP retrieval). Monthly mean (at least 20 valid days), expressed as an empirical percentile among the same calendar month over the 20 years before the period (at least 10 needed).
- Vegetation: NASA MODIS MOD13Q1 NDVI (16-day, 250 m) from the ORNL DAAC subset API, centre pixel, strict quality filter. Monthly mean minus the same calendar month over the baseline years (at least 3 needed).
- Experimental combined index (-1 wetter to +1 drier): mean of the available clipped scores — rainfall -anomaly/90, soil (50 - percentile)/40, vegetation -anomaly/0.2. Missing indicators are skipped, never treated as zero. Status thresholds: rainfall +/-30 mm; soil percentile <25 / >75; NDVI anomaly +/-0.05. These thresholds and the index are NOT validated and NOT an official classification.

SMAP: the backend has separate endpoints that read NASA SMAP SPL3SMP_E version 006 HDF5 files (nearest AM/PM cell within 20 km, quality flag 0 or 8). Files come from backend/data/smap/ or an optional background download (HULAW_SMAP_ON_DEMAND with an Earthdata login). There is no SMAP baseline or anomaly, and the frontend does not chart SMAP; the AI assistant can query it.

FRONTEND (React + TypeScript + Vite, CesiumJS globe, Recharts):
- Pages (hash routes): Map explorer (default), Dashboard, Analytics, Reports, Timelines.
- Default location: Central Luzon reference point (latitude 15.7, longitude 120.9). Selecting a Philippine region, province or city/municipality (PSGC boundaries) sends that area's centre point.
- Every page reads GET /api/overview. The map colours every visible boundary from POST /api/overview/areas (rainfall and soil only).
- "Period and baseline" controls choose the last month of the 12-month window and the baseline years.
- Drought development & recovery timeline, rule-based text summary, CSV/JSON export and print-to-PDF reports.
- Other countries on the globe use an ILLUSTRATIVE placeholder profile, not real data.
- "Hulaworld" AI assistant with a mascot whose mood follows the combined index.

BACKEND (Python 3.14, FastAPI):
- Server-side two-tier cache (memory + JSON files) for NASA POWER, MODIS and overview results.
- AI assistant: Azure OpenAI Responses API with three tools (rainfall timeline, SMAP history, MODIS history), only when a location is supplied.
- Offline tests in backend/tests/ with fake NASA services.

DEPLOYMENT:
- Frontend on Vercel at https://hulaw.earth (also hulaw.vercel.app); backend on Render (Docker) at hulaw-prototype-nasa.onrender.com, kept awake by a GitHub Actions ping.

NOT BUILT: GPM IMERG, GRACE-FO, ECOSTRESS, SMAP baseline/anomaly, area-averaged values, agricultural exposure overlay, gridded raster layers, region comparison, alerts, predictive models, PostgreSQL/PostGIS.

======================================================================
02. EXECUTIVE SUMMARY
======================================================================
PROJECT NAME: Hulaw
WORKING DESCRIPTOR: Global Drought Intelligence
WORKING TAGLINE: "Beyond detecting drought: understanding its development, impacts, and recovery."
PROJECT TYPE: Earth-observation / environmental intelligence / geospatial decision-support web application
PRIMARY TOPIC: Drought, agriculture, water resources, climate resilience
DECIDED DIRECTION: A global drought-monitoring and analysis platform with a Philippines-focused demonstration, built around a visually compelling interactive map or 3D globe.

ONE-SENTENCE DESCRIPTION:
Hulaw is a proposed interactive geospatial platform that combines satellite-based rainfall, soil moisture, vegetation, and optional regional water-storage observations to explain where drought-related conditions are unusual, how they evolve over time, which agricultural areas may be exposed, and whether the indicators show recovery.

ELEVATOR PITCH:
Many drought dashboards display colored severity maps but provide limited explanation of what changes are occurring in rainfall, soil moisture, crops, and regional water storage. Hulaw aims to help users inspect the evidence behind emerging or easing dry conditions. Through a location-based timeline, consistent historical comparisons, and transparent satellite-derived indicators, users can investigate drought development and recovery and identify where additional global assessment could be worthwhile.

CORE PROMISE:
Not just "Where is it dry?" but "How did conditions change, which indicators support that interpretation, what land uses may be exposed, and are conditions recovering?"

======================================================================
03. PROBLEM STATEMENT AND MOTIVATION
======================================================================
Drought is a slow-onset environmental hazard, and it is not adequately described by a short period without rain. It may include:
- Meteorological drought: persistent rainfall deficits relative to global historical conditions.
- Agricultural drought: insufficient moisture to meet crop and vegetation needs.
- Hydrological drought: reduced water in rivers, reservoirs, groundwater, or other stores.

These conditions can develop and recover at different speeds. A region may experience a rainfall deficit before vegetation changes become visible; rainfall recovery may occur before soil or water storage recovers. These are possible patterns, not fixed causal sequences.

Pain points Hulaw is designed to address:
1. Multiple relevant observations exist across separate scientific data products and interfaces.
2. Raw satellite maps and technical units are difficult for non-specialists to interpret.
3. A current drought label alone cannot explain historical context or the changing state of the water cycle.
4. Agricultural decision-makers need geographical context for where crops and farmland may be exposed.
5. Water and disaster-planning offices need understandable, documented evidence—not unsupported certainty—to prioritize global validation.

WHAT THE PLATFORM DOES NOT PROMISE:
- It will not know the precise soil moisture of each individual farm from coarse satellite pixels.
- It will not claim to directly measure household water shortages or exact groundwater levels from GRACE-FO.
- It will not assert crop yield loss solely from changes in vegetation indices.
- It will not equate satellite indicators with an official drought declaration without a validated standard and appropriate agency data.
- It will not automatically assert drought causation or a reliable forecast without an evaluated predictive model.

======================================================================
04. TARGET USERS AND MARKET
======================================================================
PRIMARY USERS (recommended initial focus):
A. Global agriculture offices and regional agricultural planners.
   Job to be done: identify agricultural areas where rainfall/soil-moisture/vegetation observations warrant additional monitoring.
B. LGU disaster risk reduction and management offices (DRRM) and environmental planning teams.
   Job to be done: monitor changes over time, explain indicators, and prepare evidence-informed briefings.
C. Water resource and irrigation managers.
   Job to be done: compare available rainfall, soil moisture, and verified global river/reservoir observations.

SECONDARY USERS:
- Farmers' organizations/cooperatives: accessible regional information, not a substitute for field measurements.
- Environmental scientists/researchers/universities: explore, compare, and export indicators.
- NGOs/humanitarian and food-security organizations: screen areas for follow-up field assessment.
- Agricultural insurers and finance stakeholders: contextual risk research, subject to substantial validation before financial decisions.
- General public and educators: learn how drought indicators evolve.

GEOGRAPHIC STRATEGY:
- Product aspiration: global exploration wherever the selected datasets provide valid coverage.
- First credible demonstration: a defined agricultural study area in the Philippines.
- The exact pilot province, municipality, geographic boundary, stakeholder, crops, and historical case remain TO BE SELECTED.

POSITIONING / POTENTIAL VALUE:
- Low-friction, explainable access to satellite observations.
- Evidence trail including dataset name, version, observation date, spatial resolution, and gaps.
- Planning-focused interpretation rather than a decorative globe.
- Start as a research/demo/decision-support application; no verified commercial revenue model exists yet.

======================================================================
05. INNOVATION AND DIFFERENTIATION
======================================================================
CRUCIAL TRUTH: Satellite-based drought monitoring, multi-indicator drought assessment, and global drought mapping already exist. The novelty claim MUST NOT be "we are the first to combine NASA data" or "we invented drought maps."

PROPOSED SIGNATURE FEATURE: DROUGHT DEVELOPMENT & RECOVERY TIMELINE.
When a user selects an area, Hulaw should display how each indicator deviated from its seasonal/historical baseline over several time points, and whether the pattern is worsening, stabilizing, or improving. It should provide clear evidence labels and source dates rather than unsubstantiated narratives.

Differentiation opportunities:
1. Explainability by default: every interpretation is traceable to a rainfall, soil moisture, or vegetation time series and its baseline.
2. Multi-indicator but not opaque: show individual measurements before any composite assessment.
3. Development and recovery in one interface: make improvement and lagging recovery as visible as worsening conditions.
4. Agricultural exposure overlay: intersect the selected drought indicators with available, appropriately resolved agricultural land-cover information.
5. Local planning workflow: select place -> inspect historical changes -> compare indicators -> locate exposed farmland -> export a transparent summary.
6. Accessible visual storytelling: globe/map, comparative charts, and plain-language definitions for non-expert users.
7. This should be also global, optional Philippine localization: local administrative boundaries, seasonal baselines, crop/planting calendars and agency datasets when available and authorized. 

INNOVATION TEST:
A compelling project demo must answer a question that is difficult to answer with a single existing map, such as: "In this selected agricultural area, what did precipitation, soil moisture, and vegetation show over the last several months, and which observations recovered first?"

======================================================================
06. SATELLITE / ENVIRONMENTAL DATA INVENTORY
======================================================================
A. MVP REQUIRED DATASETS (recommended minimum):

1. NASA GPM / IMERG — PRECIPITATION
   Role: rainfall accumulation, rainfall anomaly, dry-period indicators, seasonal comparison.
   Questions: Is precipitation lower than expected for this place and period? For how long?
   Practical notes: IMERG offers half-hourly precipitation estimates with multiple access products (Early/Late/Final) and historical observations. For an MVP, daily-to-monthly aggregation is more interpretable than raw 30-minute images. Choose a single version/run for each comparison where feasible and document latency. Near-real-time and research-grade products may differ.
   Primary NASA references:
   https://gpm.nasa.gov/data/imerg
   https://gpm.nasa.gov/data/directory

2. NASA SMAP — SURFACE SOIL MOISTURE
   Role: estimated top-layer soil wetness and anomalies.
   Questions: Is the surface soil drier than its usual seasonal condition?
   Practical notes: SMAP measures near-surface soil moisture, not the entire plant-root zone. Depending on product, gridded estimates may be on the scale of kilometers. Must account for missing/flagged observations and changes in mission/data availability. Verify CURRENT exact product continuity, quality flags and processing level before implementation. A SMOS-based SMAP product is one possible continuity-related dataset, not an automatic drop-in replacement.
   Reference:
   https://nsidc.org/data
   Example of 2026 product update:
   https://nsidc.org/data/user-resources/data-announcements/data-set-updates-smos-based-smap-l2-radiometer-half-orbit-9-km-ease-grid-soil-moisture-and-smapsmos

3. NASA MODIS — VEGETATION INDICES (NDVI/EVI)
   Role: vegetation greenness and relative condition over time.
   Questions: Are vegetated areas showing unusual changes that might be consistent with water stress?
   Practical notes: NDVI/EVI are indirect proxies. Crop harvesting, crop phenology, clouds, land clearing, pests, and land-use changes can all affect indices; do not automatically label any NDVI decline as drought damage. Decide on a suitable product, compositing period, quality masks, and vegetation baseline.
   Reference/data portal:
   https://lpdaac.usgs.gov/
   https://appeears.earthdatacloud.nasa.gov/

B. OPTIONAL / LATER-PHASE DATASETS:

4. NASA GRACE-FO — REGIONAL TERRESTRIAL WATER STORAGE
   Role: regional total water-storage anomalies over time, which may reflect a mixture of groundwater, soil water, snow, and surface water changes.
   Constraint: very coarse effective spatial resolution; appropriate for large regions, not individual fields, towns, street-level groundwater readings, or exact reservoir levels.
   Add only when scale and interpretation are suitable.
   Reference: https://grace.jpl.nasa.gov/

5. ECOSTRESS — EVAPOTRANSPIRATION / LAND SURFACE TEMPERATURE
   Role: supplemental vegetation water-use, surface temperature, or water-stress context.
   Constraint: intermittent coverage and variable scene availability; it is NOT guaranteed to be available continuously for every location.
   Reference: https://ecostress.jpl.nasa.gov/

6. LOCAL / ANCILLARY DATA:
   - Agricultural land-cover or crop-type polygons (source, date, and accuracy verified).
   - Administrative boundaries for selecting regions.
   - River, reservoir, streamflow, groundwater or irrigation observations from reputable global sources.
   - Historic climatology, seasonality, meteorological station observations, elevation, and land cover.
   - Crop calendars and information on global agricultural practices where available.
   - Optional population data for contextual analysis; avoid presenting population overlap as direct harm evidence.

PROTOTYPE NOTE: The built prototype uses NASA POWER PRECTOTCORR instead of GPM IMERG for rainfall, and NASA POWER GWETTOP (model-based) instead of SMAP for the soil indicator in the main overview. SMAP SPL3SMP_E v006 is available only through separate point endpoints. MODIS MOD13Q1 via ORNL DAAC is used for vegetation. See section 01A.

DATA MODEL RULE:
Every measure should record dataset/product, variable, unit, coverage, acquisition/processing timestamp, spatial resolution or scale, quality mask, baseline period, and missing-data status.

======================================================================
07. PROPOSED FEATURE CATALOG
======================================================================
MUST-HAVE MVP:
F01. Region selection: search or click a study area, display boundary and location details.
F02. 2D/3D geospatial map: show drought-related anomaly layers and legends.
F03. Rainfall history: monthly precipitation totals and departures from an appropriate seasonal baseline.
F04. Soil moisture history: values/anomalies and clearly labeled observation gaps.
F05. Vegetation history: NDVI/EVI trends with quality filtering and cautions.
F06. Signature drought timeline: align observed changes over time without asserting that all regions follow the same order.
F07. Explainable regional summary: concise narrative grounded in the selected metrics, dates, and thresholds.
F08. Source transparency: show exact product, observation date, time period, and limitations.
F09. Agricultural land-cover overlay IF an appropriate validated source is available; otherwise clearly label as experimental or defer.

NEXT-PHASE FEATURES:
F10. Region comparison: two areas side by side with shared chart scales and baselines.
F11. Drought persistence and recovery metrics: duration of deviations and changes toward normal conditions.
F12. Downloadable report: PDF/CSV/PNG with methodology and source metadata.
F13. Optional composite assessment: only after selecting, documenting, and validating methodology and weights.
F14. Water-resource dashboard: global records and cautiously interpreted regional GRACE-FO changes.
F15. Alert subscriptions: only for validated rules; avoid claiming official warnings.
F16. Local language support and mobile-friendly low-bandwidth view.
F17. Optional predictive analytics: only if backed by data, backtesting, uncertainty analysis, and clear forecast horizons.

OUT OF SCOPE FOR INITIAL MVP:
- Unverified real-time farm-level diagnosis.
- Crop-specific irrigation prescriptions.
- Official drought proclamations.
- Satellite-derived direct household water availability.
- Precise groundwater mapping from GRACE-FO.
- AI forecasting presented as a confirmed capability before calibration.
- A comprehensive worldwide operational warning service.

======================================================================
08. USER EXPERIENCE AND DEMO FLOW
======================================================================
SUGGESTED SCREENS:
1. Landing/Overview: what Hulaw measures, what it does not measure, and entry point to explore.
2. Explore Globe/Map: search area, map layers, timeline control, legend, data-source labels.
3. Regional Analysis: aligned precipitation, soil moisture, and vegetation charts.
4. Drought Story Timeline: evidence-based narrative of indicators over chosen months.
5. Agricultural Exposure: show overlay and selected statistics with scale caveats.
6. Export/Methodology: shareable summaries and transparent calculation notes.

DEMO STORY (ILLUSTRATIVE ONLY; NOT REAL OBSERVATIONS):
- Choose a known agricultural region and historical date range.
- Display rainfall anomalies: several months show below-baseline rainfall.
- Show the soil moisture response and any temporal lag, if observed.
- Show NDVI/EVI trend and explicitly discuss alternative explanations.
- Overlay agricultural land use to identify where additional global checks may be prioritized.
- Shift the time slider forward to show whether the indicators return toward seasonal norms.
- Export a summary with actual observation timestamps and caveats.
Do not fake measurements or present this hypothetical sequence as a measured historical event.

UX PRINCIPLES:
- Accessible design; indicators should not rely exclusively on color.
- Clear anomaly legends, units, baseline dates and data quality notes.
- Keep interpretation separate from raw observations.
- Default to a regional, not street-level, scale appropriate to the data.
- Mobile responsiveness, fast layer loading, and graceful failure if a provider is offline.

======================================================================
09. RECOMMENDED TECH STACK (PROPOSED, NOT FINALIZED)
======================================================================
FRONTEND:
- React + TypeScript, ideally with Vite for a focused client application.
- CesiumJS for interactive 3D globe, imagery/terrain and geospatial overlays.
- Optional Leaflet/MapLibre for lightweight 2D mode if time/bandwidth limits matter.
- Tailwind CSS or standard CSS modules for UI styling.
- Recharts, ECharts, or Plotly for time-series graphs; choose ONE preferred charting library.
- TanStack Query or similar client data caching.

BACKEND:
- Python + FastAPI for REST endpoints and scientific analysis services.
- Pydantic schemas, data validation and consistent API response types.
- NumPy, pandas, xarray for numerical and time-series operations.
- Rasterio/rioxarray for gridded/raster data; GeoPandas/Shapely for spatial intersections.
- Dask if large-scale processing exceeds regular in-memory workloads.
- Optional Celery/RQ or scheduled jobs for asynchronous heavy ingestion/preprocessing; not required for small fixed-area MVP.

DATA STORAGE / INFRASTRUCTURE:
- Initial prototype: static preprocessed GeoTIFF/COG/GeoJSON/JSON plus a small PostgreSQL database, as needed.
- When geospatial queries demand it: PostgreSQL + PostGIS.
- File/object storage for precomputed grids, metadata and time-series exports.
- Raster tiles served through a compatible tile service or pre-generated COG-derived tiles; Cesium is a renderer, not a satellite analysis engine.
- Docker for reproducible dev environments; Git/GitHub for collaboration; GitHub Actions for testing/linting.
- Hosting: deploy frontend, API, storage and database according to budget; provider selection is TO BE DECIDED.

DATA ACCESS OPTIONS (CHOOSE AFTER TECHNICAL TEST):
- NASA Earthdata services and downloadable product archives.
- NASA GES DISC and/or NASA Giovanni for IMERG exploration.
- LP DAAC / AppEEARS for supported vegetation data and subsets.
- NASA NSIDC data systems for SMAP-related soil-moisture data.
- Google Earth Engine where approved and permitted, for prototyping/reduction of processing complexity. Verify dataset availability, access eligibility and current terms rather than assuming every product is included.

IMPORTANT ARCHITECTURAL DECISION:
Prefer precomputed monthly anomalies and cached spatial subsets for the demonstration. Do not fetch and process multi-year global raw satellite rasters inside each user's browser request.

======================================================================
09A. STACK AS BUILT
======================================================================
FRONTEND: React 18 + TypeScript + Vite; CesiumJS (vite-plugin-cesium) with Esri World Imagery; Recharts; plain CSS (src/styles.css); hash routing; no TanStack Query (a small in-memory cache in src/hooks/useOverview.ts).
BACKEND: Python 3.14 + FastAPI + Pydantic; httpx (one pooled async client); h5py + NumPy for SMAP HDF5; earthaccess for SMAP downloads; openai SDK for Azure OpenAI. Not used: pandas, xarray, rasterio, GeoPandas, Dask, Celery.
STORAGE: no database. JSON file cache (backend/data/cache/api/ or HULAW_CACHE_DIR) plus an in-memory LRU; SMAP HDF5 files in backend/data/smap/.
DATA ACCESS: NASA POWER daily point API; ORNL DAAC MODIS REST API; NASA Earthdata (earthaccess) for SMAP. No Earth Engine, AppEEARS or Giovanni.
HOSTING: Vercel (frontend) and Render Docker (backend); GitHub Actions keep-warm ping. No CI test workflow yet.

======================================================================
10. PROPOSED SYSTEM ARCHITECTURE
======================================================================
DATA SOURCES
  GPM/IMERG + SMAP + MODIS (+ optional GRACE-FO, ECOSTRESS, global GIS)
         |
         v
INGESTION / VALIDATION
  Download/subset, check product version, quality flags, units, timestamps
         |
         v
PREPROCESSING / ANALYSIS (Python)
  Reproject to agreed coordinate systems; temporal aggregation; seasonally
  matched baselines; anomaly calculations; mask invalid observations;
  preserve native resolution limitations; spatial summaries
         |
         v
STORAGE / CACHE
  Metadata and statistics (PostgreSQL/PostGIS or simple files for MVP)
  Gridded layers (COGs/tiles), region summaries, time-series JSON
         |
         v
API (FastAPI)
  Areas, indicators, charts, quality flags, layer descriptions, reports
         |
         v
CLIENT (React + CesiumJS + charts)
  Globe/map + region selector + timeline + indicator panels + export

ACTUAL ARCHITECTURE (PROTOTYPE):
  NASA POWER (PRECTOTCORR, GWETTOP) + ORNL DAAC MODIS MOD13Q1 (+ SMAP files)
         |  fetched on request, cached on the server (memory + JSON files)
         v
  FastAPI (backend/app): /api/overview, /api/overview/areas, rainfall/SMAP/MODIS
  point endpoints, /api/hulaworld/chat (Azure OpenAI)
         |
         v
  React + CesiumJS + Recharts (frontend/src): map, dashboard, analytics,
  reports, timelines, assistant

ACTUAL REPOSITORY ORGANIZATION:
  README.md, API.md, hulaw_context.md, vercel.json, requirements*.txt
  .github/workflows/keep-warm.yml
  backend/
    Dockerfile, requirements.txt
    app/main.py
    app/api/        (route modules)
    app/schemas/    (Pydantic response models)
    app/services/   (NASA POWER, MODIS, SMAP, overview, cache, HTTP client)
    app/ai/         (Hulaworld prompts, tools, tool executor, service)
    scripts/        (SMAP download/inspection and Azure test scripts)
    tests/          (test_overview.py, offline)
    data/           (cache/ and smap/, git-ignored)
  frontend/
    src/components, src/views, src/hooks, src/services, src/types,
    src/utils, src/data
    public/         (logo, mascot images, Philippines outline, countries.geojson)

ORIGINAL PROPOSED REPOSITORY ORGANIZATION (not followed exactly):
Hulaw/
  README.md
  PROJECT_CONTEXT.txt
  docs/
    methodology.md
    data_dictionary.md
    architecture.md
    decisions.md
  frontend/
    src/
      components/
      pages/
      services/
      hooks/
      types/
  backend/
    app/
      main.py
      api/
      schemas/
      services/
      models/
    tests/
  pipelines/
    ingestion/
    preprocessing/
    validation/
  data/
    sample/             # small redistributable development examples
    metadata/
  infra/
    docker/
  .github/workflows/

Do not commit credentials, Earthdata tokens, huge raw imagery archives, or restricted datasets.

======================================================================
11. SCIENTIFIC METHODS AND COMPUTATIONS (PROPOSALS)
======================================================================
A. HISTORICAL BASELINE
- Define a seasonally comparable baseline, e.g., calendar-month climatology over a documented multiyear period supported by the actual product record.
- Do not assume all datasets have equal historical lengths; choose an overlapping period only if needed for strict comparison.
- Record baseline years and missing observations. Revisions/reprocessing may affect consistency.

B. PRECIPITATION METRICS
- Monthly rainfall total (mm).
- Rainfall anomaly (mm) = observed monthly precipitation - historical mean for that calendar month.
- Percent of normal = observed / historical mean * 100, only when baseline mean is meaningfully nonzero.
- Optional standardized anomalies or SPI: use a scientifically appropriate distribution, reference period, and validation; SPI is NOT a trivial percent-of-normal conversion.

C. SOIL MOISTURE METRICS
- Raw volumetric soil moisture in product units.
- Soil moisture anomaly = observation - seasonal baseline at compatible location/scale.
- Percentile based on sufficient comparable historical observations when feasible.
- Respect quality flags and near-surface measurement scope.

D. VEGETATION METRICS
- Quality-filtered NDVI or EVI.
- Relative seasonal vegetation anomaly, with adjustments for cropping cycle and land cover when feasible.
- Exclude masked cloud/invalid pixels and explain uncertainty.

E. TREND / DEVELOPMENT / RECOVERY
- Present time-aligned indicator changes, durations above/below predefined thresholds, and direction of recent change.
- "Recovery" should be an explicitly defined movement toward seasonal norms, not an assertion that all economic, ecological, or water impacts have ended.
- Define the time windows (e.g., 1, 3, 6 months) and avoid mixing incomparable timestamps.

F. AGRICULTURAL EXPOSURE
- Intersect administrative agricultural land polygons or raster cropland maps with indicator anomaly areas.
- Describe overlap as "agricultural area exposed to observed anomaly" rather than confirmed crop damage.
- Report area and the source/resolution/accuracy of the land-cover dataset.

G. COMPOSITE INDEX (EXPERIMENTAL VERSION BUILT; NOT VALIDATED)
- The prototype has an experimental -1..+1 combined index (section 01A). It is labeled experimental in the API and UI and has not been validated.
- If scoring is attempted, document normalization, directionality, weights, thresholds, missing-data policy and scientific rationale.
- Validate against independent drought products and global observations.
- Include an "insufficient data" state instead of silently imputing everything.
- Avoid presenting a proprietary, arbitrary 0–100 number as authoritative drought severity.

======================================================================
12. API (IMPLEMENTED) AND FURTHER DESIGN IDEAS
======================================================================
IMPLEMENTED (full reference in API.md; all point-based, by latitude/longitude):
GET  /                                   Service information.
GET  /api/health                         Service status.
GET  /api/indicators                     Descriptions of the three overview indicators.
GET  /api/overview                       12 completed months for one point: rainfall,
                                         soil wetness, NDVI vs baselines, experimental
                                         combined index, sources, warnings, mascot mood.
                                         Optional end_month, baseline_start/end, refresh.
POST /api/overview/areas                 Rainfall anomaly + soil percentile per month
                                         for up to 150 points (map colours).
GET  /api/precipitation                  Daily NASA POWER rainfall (<= 31 days).
GET  /api/analysis/rainfall/monthly      Monthly total.
GET  /api/analysis/rainfall/baseline     Same-month mean over <= 10 years.
GET  /api/analysis/rainfall/anomaly      Monthly anomaly.
GET  /api/analysis/rainfall/timeline     Monthly anomaly series within one year.
GET  /api/soil-moisture                  One SMAP SPL3SMP_E observation.
GET  /api/soil-moisture/history          SMAP observations (<= 14 days).
GET  /api/vegetation/history             MODIS NDVI/EVI (<= 121 days, <= 10 composites).
POST /api/hulaworld/chat                 AI assistant reply (Azure OpenAI).
Report export (CSV/JSON/print) is done in the frontend, not by the API.

NOT IMPLEMENTED (earlier design sketch, kept as ideas):
GET /api/areas?query=<name>, GET /api/areas/{area_id}   (area search/geometry; the
  frontend loads PSGC boundaries directly from GitHub)
GET /api/layers?date=YYYY-MM&indicator=...               (raster/tile layers)
GET /api/assessment?area_id=...                           (server-side summary)
GET /api/exposure?area_id=...&date=...                   (cropland overlap)
POST /api/reports                                         (server-side export)

EXAMPLE INDICATOR RECORD FIELDS (design guidance):
  area_id, date, metric, value, unit, baseline_value, anomaly,
  baseline_period, dataset, product_version, source_url,
  native_resolution, computed_at, quality_status, notes

API rules: all dates/units explicit; no interpolation without labeling;
no response should imply fresher data than the source's actual timestamp.

======================================================================
13. MVP SCOPE / BUILD ORDER
======================================================================
PROGRESS (17 November 2026):
- Phase 0: partly done — reference point in Central Luzon chosen; products chosen (NASA POWER, MODIS MOD13Q1, SMAP SPL3SMP_E v006); default baselines defined. Historical case study and validation data not yet chosen.
- Phase 1: done for one point at a time (see 01A).
- Phase 2: done — map/globe, charts, period controls, development & recovery timeline, source labels, warnings and generated-at timestamps.
- Phase 3: partly done — exportable summary (CSV/JSON/print) exists; agricultural overlay and validation do not.
- Phase 4: not started, except the experimental combined index.

PHASE 0 — RESEARCH AND SCIENTIFIC FEASIBILITY
- Choose Philippine pilot area and historical study case.
- Confirm exact GPM, SMAP and MODIS products, dates, access methods, licenses, availability, and quality flags.
- Check satellite product resolution against the intended geographic scale.
- Select historical baseline periods and methodology.
- Find independent reference data or expert input for validation.

PHASE 1 — DATA PROOF OF CONCEPT
- Download sample area/time-range observations.
- Compute consistent precipitation and soil moisture anomalies and vegetation trends.
- Produce a single reproducible regional time-series output with metadata.
- Inspect missing data, dates, and coordinate consistency.

PHASE 2 — MINIMUM WEB APP
- Build selectable map/globe and location summary.
- Integrate API-backed regional charts and time controls.
- Create the explainable Drought Development & Recovery Timeline.
- Add source labels, uncertainty notes, and data freshness timestamps.

PHASE 3 — PRACTICAL DECISION SUPPORT
- Add verified agricultural-area overlay and exportable summary.
- Validate findings against global records or existing drought monitor publications.
- Make the demo accessible, responsive, and robust under incomplete data.

PHASE 4 — OPTIONAL EXPANSION
- Regional water resource panels; multi-region comparison; validated index;
  scheduled update pipeline; alerts; optional machine learning evaluation.

SCOPE DISCIPLINE:
A complete, credible 1-region historical demo is better than a superficially global system with invented accuracy. Global exploration can be gradually expanded as data processing, delivery, and scientific quality permit.

======================================================================
14. TESTING, VALIDATION, AND SUCCESS METRICS
======================================================================
DATA QUALITY:
- Product versions, units, coordinate reference systems and timestamps are correct.
- Quality/missing-data flags are respected.
- Seasonal comparisons match calendar months and locations.
- No visually over-resolved maps suggesting farm-level precision from kilometer-scale grids.

SCIENTIFIC VALIDATION:
- Compare monthly precipitation aggregates with available rainfall stations or credible reference products.
- Compare soil moisture trends with independent observations or accepted regional products, when feasible.
- Compare interpretations with credible historical drought episodes, official bulletins, or scientific literature.
- Report agreement/disagreement and uncertainty instead of cherry-picking a success case.

SOFTWARE QUALITY:
- Unit tests for anomaly calculations and edge cases.
- Integration tests for API data schema and invalid geographic/date requests.
- UI tests for map layer switching, chart synchronization, and offline/missing-source behavior.
- Performance measures for initial load, layer response and common region queries.

DEMO SUCCESS CRITERIA:
1. A selected area displays real, traceable observations from at least GPM, SMAP and MODIS or clearly documented substitutes.
2. Every chart communicates units, date ranges, and historical baseline.
3. A user can recognize one or more observed changes over time without reading raw satellite files.
4. Users can identify data limitations and distinguish observations from interpretations.
5. Map, timeline, and summary agree with the same underlying dataset.
6. Agricultural exposure is enabled only when appropriate land-cover data are available.

NO FABRICATED PERFORMANCE CLAIMS:
Do not invent prediction accuracy, affected hectares, economic savings, users, adoption, or detection latency. Measure or cite these before publication.

======================================================================
15. EXISTING TECHNOLOGIES AND COMPETITIVE POSITION
======================================================================
EXISTING WORK TO RESEARCH / BENCHMARK:
- Copernicus Global Drought Observatory: existing global multi-indicator drought-monitoring platform.
  https://drought.emergency.copernicus.eu/
- U.S. Drought Monitor: expert-informed weekly U.S. drought classification using many types of evidence.
  https://droughtmonitor.unl.edu/
- NASA Worldview: browse Earth imagery and environmental layers.
  https://worldview.earthdata.nasa.gov/
- Google Earth Engine: extensive geospatial analysis/data infrastructure, not a directly identical end-user drought app.
  https://earthengine.google.com/

POSITIONING STATEMENT:
"Unlike a simple satellite imagery viewer, Hulaw is intended to present an evidence-linked account of drought indicators over time and their agricultural context. Unlike an official drought-declaration service, it is a transparent exploratory decision-support and educational interface."

DO NOT CLAIM:
- That existing platforms have no timeline, indicator integration, agricultural overlay or historical comparison; many already provide such features.
- That Hulaw has a patented, first-ever algorithm.

POSSIBLE DIFFERENTIATOR TO DEMONSTRATE:
One unusually clear workflow combining temporal narrative, comparable indicator charts, quality/uncertainty visibility, and a Philippine agricultural use case with user testing.

======================================================================
16. RISKS, CONSTRAINTS, AND MITIGATIONS
======================================================================
RISK: Satellite products have very different spatial and temporal resolutions.
MITIGATION: Resample only for visualization/aggregate analysis with labels; never imply new physical precision.

RISK: Dataset latency, unavailable scenes, algorithm updates and product discontinuity.
MITIGATION: Cache versioned data, show timestamps, preserve missingness, implement source health checks.

RISK: Anomalies are mistaken for official warnings or causally attributed to drought.
MITIGATION: Define interpretation rules, display confidence and alternative explanations, cite global agencies.

RISK: Vegetation indices change for reasons besides dryness.
MITIGATION: Crop-season context, quality masks, land-cover comparison and careful wording.

RISK: GRACE-FO is interpreted at inappropriate global scale.
MITIGATION: Restrict to regional water-storage narratives and label its spatial limitations.

RISK: A 3D globe consumes development time but adds little to scientific value.
MITIGATION: Complete the indicator/timeline analysis first; keep a fast fallback 2D view.

RISK: Huge satellite data requests overload the browser/backend.
MITIGATION: Precompute subsets, cache, tile, aggregate, and restrict initial demo scope.

RISK: Data provider authentication/licensing/quotas.
MITIGATION: Confirm terms, establish authorized access, and keep tokens server-side.

RISK: Synthetic or demo data accidentally presented as actual observations.
MITIGATION: Label demonstrations conspicuously and separate them from production data paths.

======================================================================
17. ETHICAL / COMMUNICATION STANDARDS
======================================================================
- Attribute NASA and all other data providers appropriately and use their required citations.
- Clearly separate observations, calculated anomalies, interpretations, and forecasts.
- Avoid alarmist language, false precision, or guaranteed recommendations.
- Hulaw should support—not replace—official global advisories or field assessments.
- Be careful with financial, agricultural, and emergency implications.
- Publish a methodology page and honest limitations.
- If stakeholders will use this beyond demonstration, obtain relevant domain review.

======================================================================
18. OPEN DECISIONS FOR THE TEAM
======================================================================
Status as of 17 November 2026: [x] = decided in the code; [~] = partly decided.
[~] Select pilot Philippine region and relevant historical drought period. (Default reference point: Central Luzon, 15.7 N 120.9 E; no historical drought period chosen.)
[ ] Specify target primary user and their highest-priority decision.
[ ] Assign project owner, backend, frontend, geospatial/data and documentation/testing responsibilities.
[~] Confirm selected MODIS, SMAP and IMERG product IDs and versions. (MODIS MOD13Q1 and SMAP SPL3SMP_E v006 in use; rainfall uses NASA POWER PRECTOTCORR instead of IMERG.)
[x] Decide Earthdata/AppEEARS/Earth Engine data retrieval path after access tests. (NASA POWER API, ORNL DAAC MODIS API, earthaccess for SMAP.)
[~] Define precipitation, soil moisture and vegetation anomaly baselines. (Defaults: 5 years before the period for rainfall/NDVI, 20 years for soil percentile; not validated.)
[x] Decide whether CesiumJS 3D view is an MVP requirement or a follow-on feature. (CesiumJS is used.)
[ ] Source and evaluate agricultural land-use data suitable for the pilot.
[~] Choose hosting approach and cost limits. (Vercel + Render free plan; cost limits not set.)
[ ] Decide acceptable update frequency and how data freshness is displayed.
[ ] Select comparison/reference data for scientific validation.
[ ] Validate project name, logo, domain and legal/trademark availability before public launch.
[ ] Agree on measurable acceptance criteria and a demo schedule.

======================================================================
19. READY-TO-PASTE MASTER PROMPT FOR AN AI ASSISTANT
======================================================================
You are assisting with the Hulaw project. Treat this document as the project context and maintain its scientific and technical constraints.

Project: Hulaw — a proposed global drought intelligence and geospatial decision-support web app, with a Philippines-focused demo.

Purpose: integrate rainfall, soil moisture and vegetation indicators, with optional GRACE-FO regional water storage and ECOSTRESS context, to explain drought-related conditions over time and potential agricultural exposure. The current prototype uses NASA POWER PRECTOTCORR rainfall, NASA POWER GWETTOP surface soil wetness (model-based, not SMAP) and MODIS MOD13Q1 NDVI, read at one point and compared with same-month baselines; SMAP SPL3SMP_E v006 is available only through separate point endpoints. GPM/IMERG is a possible later replacement for rainfall.

Distinctive concept: the evidence-linked Drought Development & Recovery Timeline, not merely a static drought severity map. Explain multi-indicator patterns, baseline deviations, temporal change, uncertainty and source details. Do NOT assert a rigid order of drought stages, automatic causation, or scientifically unverified composite scores.

Stack in use: React + TypeScript + Vite + CesiumJS + Recharts frontend; Python 3.14 + FastAPI backend with httpx, h5py/NumPy and a JSON file cache; Azure OpenAI for the assistant; Vercel + Render hosting. No database. See section 01A and API.md for what is built.

Implementation priorities: choose a real pilot area and period, verify actual NASA products, prepare validated example data, produce a traceable location-based timeline, then build map and chart workflows and an optional agricultural overlay. Favor a trustworthy focused MVP over broad, superficial features.

Rules for all answers:
1. Distinguish confirmed project decisions from recommendations and not-yet-built features.
2. Never invent satellite measurements, citations, real-time access, model accuracy, or external partnerships.
3. Preserve source metadata, units, dates, spatial scale, baseline, quality flags and missing observations.
4. Avoid describing NDVI decline as proof of drought, GRACE-FO as field-level groundwater measurement, or Hulaw as an official warning service.
5. When writing code, specify each file's path within the actual repository structure (section 10).
6. Provide practical, modular, testable code and explain dependencies and assumptions.
7. When recommending APIs, versions, SDKs or datasets, verify against current official documentation.
8. If uncertainty remains, identify what needs testing or domain validation.
9. Keep outputs suited to student/research project feasibility unless new requirements change that scope.
10. Build a product that makes complex environmental evidence understandable, not just aesthetically impressive.

When asked to create a feature, begin by connecting it to Hulaw's main workflow; then propose the simplest scientifically defensible implementation and clear acceptance tests. Treat all unconfirmed decisions as open, not settled.

======================================================================
20. SHORT CONTEXT PROMPT (FOR QUICK SHARING)
======================================================================
Hulaw is our selected environmental technology project: a global drought intelligence platform with a Philippines-focused demo. The working prototype uses NASA POWER rainfall (PRECTOTCORR), NASA POWER surface soil wetness (GWETTOP, model-based, not SMAP) and MODIS MOD13Q1 NDVI at one point, compared with same-month baselines, plus an experimental combined index, to help users examine unusual dryness, seasonal anomalies and drought development/recovery over time. SMAP point data is available through separate endpoints; GPM/IMERG is not used yet. GRACE-FO regional water storage, ECOSTRESS and cropland overlays are optional later additions. Its main proposed innovation is an explainable Drought Development & Recovery Timeline that aligns indicators and communicates evidence, uncertainty, location, source dates and possible agricultural exposure—not another static drought map. Primary users include agriculture offices, LGUs/DRRM offices and water managers. Stack: React/TypeScript/Vite/CesiumJS/Recharts + Python/FastAPI, deployed on Vercel and Render, with an Azure OpenAI assistant (Hulaworld). Focus first on one well-validated Philippine case study; never invent satellite data, official warnings or predictive accuracy. Features beyond the prototype in section 01A remain proposals.

======================================================================
21. SELECTED SOURCES AND REFERENCE LINKS
======================================================================
NASA POWER (used): https://power.larc.nasa.gov/
ORNL DAAC MODIS subset API (used): https://modis.ornl.gov/rst/api/v1/
NASA SMAP SPL3SMP_E (used): https://nsidc.org/data/spl3smp_e
NASA IMERG overview: https://gpm.nasa.gov/data/imerg
NASA GPM data directory: https://gpm.nasa.gov/data/directory
NASA Earthdata: https://www.earthdata.nasa.gov/
NASA NSIDC: https://nsidc.org/data
NASA LP DAAC: https://lpdaac.usgs.gov/
NASA AppEEARS: https://appeears.earthdatacloud.nasa.gov/
NASA GRACE: https://grace.jpl.nasa.gov/
NASA ECOSTRESS: https://ecostress.jpl.nasa.gov/
CesiumJS: https://cesium.com/platform/cesiumjs
Copernicus Global Drought Observatory: https://drought.emergency.copernicus.eu/
U.S. Drought Monitor: https://droughtmonitor.unl.edu/
NASA Worldview: https://worldview.earthdata.nasa.gov/
Google Earth Engine: https://earthengine.google.com/

Source note: URLs are supporting entry points, not a complete peer-reviewed methodology. Always consult the exact product's current official documentation, DOI, algorithm description and terms before implementing.

======================================================================
END OF HULAW MASTER PROJECT CONTEXT
======================================================================
