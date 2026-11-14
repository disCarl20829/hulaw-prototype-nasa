import type { AppliedPeriod, DataQuery, MascotMood, MonthRecord, Region, SourceMeta } from "../types";

// Backend address. Override in frontend/.env with VITE_API_BASE_URL=http://host:port
export const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

type ApiStatus = "below" | "normal" | "above" | "no_data";
interface ApiSource { dataset: string; variable: string; unit: string; baseline_period: string; native_resolution: string; limitation: string }
export interface OverviewResponse {
  location: { latitude: number; longitude: number };
  period: { start_month: string; end_month: string; months: number };
  baseline_period: { start_year: number; end_year: number };
  soil_reference_period: { start_year: number; end_year: number };
  records: {
    month: string;
    rainfall: { observed_mm: number | null; baseline_mm: number | null; anomaly_mm: number | null; percent_departure: number | null; observed_days: number; expected_days: number; valid_baseline_years: number; status: ApiStatus };
    soil: { wetness: number | null; baseline_wetness: number | null; percentile: number | null; valid_days: number; expected_days: number; valid_reference_years: number; status: ApiStatus };
    vegetation: { ndvi: number | null; baseline_ndvi: number | null; anomaly: number | null; composites_valid: number; composites_total: number; valid_baseline_years: number; status: ApiStatus };
    combined: { index: number | null; label: string; indicators_used: string[] };
  }[];
  latest: { month: string | null; combined_index: number | null; label: string; mood: MascotMood };
  sources: Record<"precip" | "soil" | "ndvi", ApiSource>;
  thresholds: Record<string, string>;
  warnings: string[];
  generated_at: string;
  cached: boolean;
  experimental: boolean;
  note: string;
}
export interface ChatResponse { agent: string; reply: string; tools_used: string[] }

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(`Cannot reach the Hulaw backend at ${API_BASE}. Check that it is running.`);
  }
  if (!response.ok) {
    let detail = "";
    try { const body = await response.json(); detail = typeof body?.detail === "string" ? body.detail : ""; } catch { /* non-JSON error body */ }
    throw new ApiError(detail || `The backend returned HTTP ${response.status}.`, response.status);
  }
  return response.json() as Promise<T>;
}

export function fetchOverview(latitude: number, longitude: number, options: { query?: DataQuery; refresh?: boolean; signal?: AbortSignal } = {}) {
  const query = new URLSearchParams({ latitude: latitude.toFixed(4), longitude: longitude.toFixed(4) });
  if (options.query?.endMonth) query.set("end_month", options.query.endMonth);
  if (options.query?.baselineStart != null && options.query?.baselineEnd != null) {
    query.set("baseline_start", String(options.query.baselineStart));
    query.set("baseline_end", String(options.query.baselineEnd));
  }
  if (options.refresh) query.set("refresh", "true");
  return request<OverviewResponse>(`/api/overview?${query}`, { signal: options.signal });
}

export interface AreaSeries { id: string; latitude: number; longitude: number; status: "ok" | "error"; rainfall_anomaly_mm: (number | null)[]; soil_percentile: (number | null)[] }
export interface AreaSeriesResponse { months: string[]; grid_degrees: number; indicators: string[]; areas: AreaSeries[]; failed: number; note: string }

/** Rainfall and soil series for many areas at once; the map colours each boundary from this. */
export function fetchAreaSeries(points: { id: string; latitude: number; longitude: number }[], query: DataQuery = {}, signal?: AbortSignal) {
  return request<AreaSeriesResponse>("/api/overview/areas", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      points: points.map((p) => ({ id: p.id, latitude: +p.latitude.toFixed(4), longitude: +p.longitude.toFixed(4) })),
      ...(query.endMonth ? { end_month: query.endMonth } : {}),
      ...(query.baselineStart != null && query.baselineEnd != null ? { baseline_start: query.baselineStart, baseline_end: query.baselineEnd } : {}),
    }),
  });
}

export function sendChat(message: string, location?: { latitude: number; longitude: number }) {
  return request<ChatResponse>("/api/hulaworld/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(location ? { message, latitude: location.latitude, longitude: location.longitude } : { message }),
  });
}

const toSource = (s: ApiSource): SourceMeta => ({ dataset: s.dataset, variable: s.variable, unit: s.unit, baselinePeriod: s.baseline_period, nativeResolution: s.native_resolution, limitation: s.limitation });

/** Convert the backend overview into the Region shape the views use. Missing values stay null. */
export function overviewToRegion(data: OverviewResponse, id: string, name: string): Region {
  const records: MonthRecord[] = data.records.map((r) => ({
    month: r.month,
    precipAnomalyMm: r.rainfall.anomaly_mm,
    soilMoisturePctile: r.soil.percentile,
    ndviAnomaly: r.vegetation.anomaly,
    precipMm: r.rainfall.observed_mm,
    precipBaselineMm: r.rainfall.baseline_mm,
    soilWetness: r.soil.wetness,
    ndvi: r.vegetation.ndvi,
    ndviBaseline: r.vegetation.baseline_ndvi,
  }));
  return {
    id, name, bbox: [116, 4.5, 127, 21.5], records, isIllustrative: false,
    sources: { precip: toSource(data.sources.precip), soil: toSource(data.sources.soil), ndvi: toSource(data.sources.ndvi) },
    location: data.location, warnings: data.warnings, generatedAt: data.generated_at,
    period: { endMonth: data.period.end_month, baselineStart: data.baseline_period.start_year, baselineEnd: data.baseline_period.end_year },
  };
}

/** The latest fully completed month (YYYY-MM). */
export function lastCompletedMonth(now = new Date()): string {
  const month = now.getMonth(); // 0-based, so this is the previous month as 1-based
  return month === 0 ? `${now.getFullYear() - 1}-12` : `${now.getFullYear()}-${String(month).padStart(2, "0")}`;
}

/** The `count` months ending at endMonth (YYYY-MM), matching the backend's window. */
export function monthsEnding(endMonth: string, count = 12): string[] {
  const months: string[] = [];
  let [year, month] = endMonth.split("-").map(Number);
  for (let i = 0; i < count; i++) {
    months.unshift(`${year}-${String(month).padStart(2, "0")}`);
    month -= 1;
    if (month === 0) { year -= 1; month = 12; }
  }
  return months;
}

export const MIN_END_MONTH = "2007-01";
export const MIN_BASELINE_YEAR = 2001;

/** The period the backend will use for a query: latest 12 completed months and the 5 years before them unless chosen otherwise. */
export function resolvePeriod(query: DataQuery = {}): AppliedPeriod {
  const endMonth = query.endMonth ?? lastCompletedMonth();
  const firstYear = Number(monthsEnding(endMonth)[0].slice(0, 4));
  const baselineEnd = query.baselineEnd ?? firstYear - 1;
  return { endMonth, baselineStart: query.baselineStart ?? baselineEnd - 4, baselineEnd };
}

/** Same rules as the backend, so mistakes are caught before a request is sent. null = valid. */
export function validatePeriod(p: AppliedPeriod): string | null {
  if (!/^\d{4}-\d{2}$/.test(p.endMonth)) return "Choose the last month of the period.";
  if (p.endMonth > lastCompletedMonth()) return `The last month must be completed (${lastCompletedMonth()} or earlier).`;
  if (p.endMonth < MIN_END_MONTH) return `The last month must be ${MIN_END_MONTH} or later.`;
  if (!Number.isInteger(p.baselineStart) || !Number.isInteger(p.baselineEnd)) return "Enter both baseline years.";
  const years = p.baselineEnd - p.baselineStart + 1;
  if (years < 3 || years > 10) return "Use between 3 and 10 baseline years.";
  if (p.baselineStart < MIN_BASELINE_YEAR) return `The baseline cannot start before ${MIN_BASELINE_YEAR}.`;
  const firstYear = Number(monthsEnding(p.endMonth)[0].slice(0, 4));
  if (p.baselineEnd >= firstYear) return `The baseline must end before ${firstYear}, the first year of the period.`;
  return null;
}

const PENDING: SourceMeta = { dataset: "Not loaded", variable: "", unit: "", baselinePeriod: "not available", nativeResolution: "not available", limitation: "No data has been loaded from the backend yet." };

/** Placeholder with no values, shown while loading or when the backend cannot be reached. */
export function emptyRegion(id: string, name: string, endMonth = lastCompletedMonth()): Region {
  return {
    id, name, bbox: [116, 4.5, 127, 21.5], isIllustrative: false,
    records: monthsEnding(endMonth).map((month) => ({ month, precipAnomalyMm: null, soilMoisturePctile: null, ndviAnomaly: null, precipMm: null, precipBaselineMm: null, soilWetness: null, ndvi: null, ndviBaseline: null })),
    sources: { precip: PENDING, soil: PENDING, ndvi: PENDING },
  };
}
