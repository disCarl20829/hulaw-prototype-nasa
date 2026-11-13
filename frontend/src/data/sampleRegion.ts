import type { Region } from "../types";

// ILLUSTRATIVE PLACEHOLDER VALUES, NOT SATELLITE OBSERVATIONS.
// Replace with output from GET /api/indicators once the pipeline exists.
export const philippines: Region = {
  id: "ph", name: "Philippines", bbox: [116, 4.5, 127, 21.5], isIllustrative: true,
  records: [
    { month: "2025-08", precipAnomalyMm: 40, soilMoisturePctile: 55, ndviAnomaly: 0.05 },
    { month: "2025-09", precipAnomalyMm: -20, soilMoisturePctile: 48, ndviAnomaly: 0.02 },
    { month: "2025-10", precipAnomalyMm: -55, soilMoisturePctile: 38, ndviAnomaly: -0.01 },
    { month: "2025-11", precipAnomalyMm: -90, soilMoisturePctile: 27, ndviAnomaly: -0.05 },
    { month: "2025-12", precipAnomalyMm: -70, soilMoisturePctile: 18, ndviAnomaly: -0.09 },
    { month: "2026-01", precipAnomalyMm: -40, soilMoisturePctile: 12, ndviAnomaly: -0.14 },
    { month: "2026-02", precipAnomalyMm: -35, soilMoisturePctile: 9, ndviAnomaly: -0.18 },
    { month: "2026-03", precipAnomalyMm: 10, soilMoisturePctile: 14, ndviAnomaly: -0.2 },
    { month: "2026-04", precipAnomalyMm: 45, soilMoisturePctile: 26, ndviAnomaly: -0.16 },
    { month: "2026-05", precipAnomalyMm: 60, soilMoisturePctile: 41, ndviAnomaly: -0.1 },
    { month: "2026-06", precipAnomalyMm: 30, soilMoisturePctile: 52, ndviAnomaly: -0.04 },
    { month: "2026-07", precipAnomalyMm: 20, soilMoisturePctile: 58, ndviAnomaly: 0.0 },
  ],
  sources: {
    precip: { dataset: "NASA GPM IMERG (product/version TO CONFIRM)", variable: "Monthly precipitation anomaly", unit: "mm", baselinePeriod: "TO DEFINE", nativeResolution: "~10 km", limitation: "Early/Late/Final runs differ; satellite estimate, not gauge data." },
    soil: { dataset: "NASA SMAP (product TO CONFIRM)", variable: "Surface soil moisture percentile", unit: "percentile", baselinePeriod: "TO DEFINE", nativeResolution: "~9-36 km", limitation: "Top few cm only; gaps and quality flags apply." },
    ndvi: { dataset: "NASA MODIS NDVI (product TO CONFIRM)", variable: "NDVI anomaly", unit: "index", baselinePeriod: "TO DEFINE", nativeResolution: "250 m-1 km", limitation: "Also affected by clouds, harvest cycles and land-use change." },
  },
};

// Illustrative hotspots for the globe; real layers should come from tiles/COGs.
export const hotspots = [
  { lon: 105, lat: 16, radiusKm: 450, severity: 0.95 },
  { lon: 108, lat: 11, radiusKm: 300, severity: 0.8 },
  { lon: 114, lat: 0, radiusKm: 380, severity: 0.7 },
  { lon: 100, lat: 8, radiusKm: 260, severity: 0.6 },
  { lon: 121, lat: 14, radiusKm: 220, severity: 0.45 },
];
