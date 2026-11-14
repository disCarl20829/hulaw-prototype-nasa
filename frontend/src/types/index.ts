export interface MonthRecord {
  month: string;                      // YYYY-MM
  precipAnomalyMm: number | null;     // monthly rainfall total minus calendar-month baseline
  soilMoisturePctile: number | null;  // surface soil wetness percentile (0-100)
  ndviAnomaly: number | null;         // NDVI anomaly vs calendar-month baseline
  // Raw values behind the anomalies. null = no usable observation; never treat as 0.
  precipMm: number | null;
  precipBaselineMm: number | null;
  soilWetness: number | null;         // 0-1 fraction
  ndvi: number | null;
  ndviBaseline: number | null;
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
  location?: { latitude: number; longitude: number };
  period?: AppliedPeriod; // what the backend actually used
  warnings?: string[];
  generatedAt?: string;
}
/** Period chosen in the controls. Empty = latest 12 completed months with the default 5-year baseline. */
export interface DataQuery { endMonth?: string; baselineStart?: number; baselineEnd?: number }
export interface AppliedPeriod { endMonth: string; baselineStart: number; baselineEnd: number }
export type LayerKey = "combined" | "precip" | "soil" | "ndvi";
export type Trend = "improving" | "stable" | "worsening";
export type MascotMood = "default" | "happy" | "moderate" | "negative";
export type DataStatus = "loading" | "ready" | "error";
