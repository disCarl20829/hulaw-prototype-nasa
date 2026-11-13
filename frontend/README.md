# Hulaw frontend — static prototype

This is a frontend-only React/Vite prototype. It runs entirely with local illustrative sample data and does not require a backend, API server, database, or network service.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually http://localhost:5173).

## Build

```bash
npm run build
npm run preview
```

## Static data

- `src/data/sampleRegion.ts` contains the illustrative Philippines dataset used by the interface.
- `public/data/countries.geojson` contains the map geography.
- All dashboard calculations and summaries are performed in the frontend.

The sample values are placeholders for demonstration only; they are not verified satellite observations or official drought measurements.

No backend or API integration is included. A future backend can be connected later while preserving the current frontend structure.
