export interface MonthRecord {
  month: string;              // YYYY-MM
  precipAnomalyMm: number;    // GPM/IMERG monthly total minus calendar-month baseline
  soilMoisturePctile: number; // SMAP near-surface soil moisture percentile (0-100)
  ndviAnomaly: number;        // MODIS NDVI anomaly vs seasonal baseline
}
export interface SourceMeta {
  dataset: string; variable: string; unit: string; baselinePeriod: string;
  nativeResolution: string; limitation: string;
}
export interface Region {
  id: string; name: string; bbox: [number, number, number, number]; // west,south,east,north
  records: MonthRecord[];
  sources: Record<"precip" | "soil" | "ndvi", SourceMeta>;
  isIllustrative: boolean;
}
export type LayerKey = "combined" | "precip" | "soil" | "ndvi";
export type Trend = "improving" | "stable" | "worsening";
