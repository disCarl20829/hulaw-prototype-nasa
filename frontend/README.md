# Hulaw frontend - static interactive prototype

This is a frontend-only React/Vite prototype. It uses local illustrative sample data and a bundled country GeoJSON file; no backend, API server, or database is required.

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

## Globe interactions

- Click a bundled country polygon to highlight it and show its name and ISO code.
- The Esri World Boundaries and Places reference overlay supplies global country borders, administrative boundaries and populated-place/city labels. Labels and boundary detail vary with zoom.
- Esri World Imagery is requested up to zoom level 19; actual detail depends on regional source coverage and network availability.
- Use the mouse wheel or trackpad to zoom. Zoom is limited to 150 km minimum and 18,000 km maximum camera distance.
- Online Esri reference and imagery layers require an internet connection and retain Esri/source attribution.
- The logo is bundled at `public/hulaw-logo.webp`.

## Static data

`src/data/sampleRegion.ts` contains illustrative placeholder values, not verified satellite observations or official drought measurements. Country boundaries are bundled in `public/data/countries.geojson`.

No backend or API integration is included. Backend services can be connected later while retaining this frontend.
