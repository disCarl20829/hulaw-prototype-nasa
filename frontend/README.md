# Hulaw frontend

React + TypeScript (Vite) app. All drought values come from the Hulaw backend; there is no bundled sample data in use.

## Run locally

Start the backend first (see the root `README.md`), then:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually http://localhost:5173).

The backend address defaults to `http://127.0.0.1:8000`. To change it, create `frontend/.env` with `VITE_API_BASE_URL=http://host:port` and restart Vite.

## Build

```bash
npm run build
npm run preview
```

## How data flows

- `src/services/hulaw-api.ts` is the only place that talks to the backend.
- `src/hooks/useOverview.ts` loads `GET /api/overview` for one point and the chosen period. Every page (map, dashboard, analytics, reports, timelines) reads from it.
- With no area selected, the point is a reference location in Central Luzon. Selecting an area on the map sends the center of that area.
- The map also calls `POST /api/overview/areas` with the center of every visible boundary and colours each area by its own rainfall and soil wetness. Vegetation is not part of the map colours.
- The "Period and baseline" panel sets the last month of the 12-month period and the baseline years, and reloads all pages.
- Missing values are `null` and are shown as "No data". They are never treated as zero.
- While data is loading or the backend cannot be reached, pages show empty states with a banner and a Retry button.

## Pages

- **Map explorer:** Philippine regions, provinces and cities/municipalities. Selecting a region drills into its provinces; selecting a province drills into its cities and municipalities. Hovering shows that area's rainfall and soil values.
- **Dashboard:** latest month's indicators, the experimental combined index and recent history.
- **Analytics:** aligned indicator charts and a table.
- **Reports:** condition timeline, monthly table and exports. CSV has one row per month with units in the column names. JSON adds location, sources, thresholds and data notes. "Print or save as PDF" uses a light print layout.
- **Timelines:** the drought development and recovery timeline.

## Assistant and mascot

The floating assistant sends messages to `POST /api/hulaworld/chat` with the selected location. The mascot image in `public/hulaw-mascot/` follows the backend's combined index: `happy` (near normal or wetter), `moderate`, `negative` (severe), and `default` when there is no data.

## Map sources

- Boundaries: NAMRIA / PSA administrative boundaries distributed through OCHA COD-AB and the `faeldon/philippines-json-maps` project (loaded from GitHub at runtime, so an internet connection is needed).
- Imagery: Esri World Imagery, with Esri/source attribution.
- The Reports page uses a static outline at `public/philippines-outline.svg` as a geographic reference only.

## Limits

Values are read at one point, not averaged over an area. The combined index and its thresholds are experimental. Hulaw is not an official drought warning service.
