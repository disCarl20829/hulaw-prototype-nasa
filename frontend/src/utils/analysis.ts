import type { MonthRecord, Trend } from "../types";

// "nodata" means there was no usable observation for that month. It is never treated as zero.
export type Status = "below" | "normal" | "above" | "nodata";
type Value = number | null | undefined;
const missing = (v: Value): v is null | undefined => v == null || Number.isNaN(v);

export const precipStatus = (v: Value): Status => (missing(v) ? "nodata" : v < -30 ? "below" : v > 30 ? "above" : "normal");
export const soilStatus = (v: Value): Status => (missing(v) ? "nodata" : v < 25 ? "below" : v > 75 ? "above" : "normal");
export const ndviStatus = (v: Value): Status => (missing(v) ? "nodata" : v < -0.05 ? "below" : v > 0.05 ? "above" : "normal");
export const STATUS_LABEL: Record<Status, string> = { below: "Below normal", normal: "Near normal", above: "Above normal", nodata: "No data" };

const mean = (a: number[]) => a.reduce((s, x) => s + x, 0) / a.length;

/** Direction of the latest value against the three before it. null when there are too few observations. */
export function trend(values: Value[], tol: number): Trend | null {
  const v = values.filter((x): x is number => !missing(x));
  if (v.length < 4 || missing(values[values.length - 1])) return null;
  const recent = v[v.length - 1];
  const before = mean(v.slice(-4, -1));
  return recent - before > tol ? "improving" : recent - before < -tol ? "worsening" : "stable";
}
export const trendLabel = (t: Trend | null) => t ?? "not enough data";

export const fmt = (v: Value, digits = 0, suffix = "") => (missing(v) ? "No data" : `${v.toFixed(digits)}${suffix}`);
export const fmtSigned = (v: Value, digits = 0, suffix = "") => (missing(v) ? "No data" : `${v > 0 ? "+" : ""}${v.toFixed(digits)}${suffix}`);

function lowest(records: MonthRecord[], pick: (r: MonthRecord) => Value): MonthRecord | null {
  let best: MonthRecord | null = null;
  for (const r of records) {
    const v = pick(r);
    if (missing(v)) continue;
    if (!best || v < (pick(best) as number)) best = r;
  }
  return best;
}

// Rule-based summary built only from the selected data (never hard-coded text).
export function buildSummary(records: MonthRecord[], upTo: number): string {
  const r = records.slice(0, upTo + 1);
  const has = (pick: (x: MonthRecord) => Value) => r.some((x) => !missing(pick(x)));
  if (!has((x) => x.precipAnomalyMm) && !has((x) => x.soilMoisturePctile) && !has((x) => x.ndviAnomaly)) return "No observations are available for this period yet.";
  const parts: string[] = [];
  if (has((x) => x.precipAnomalyMm)) {
    const firstDry = r.find((x) => precipStatus(x.precipAnomalyMm) === "below");
    parts.push(firstDry ? `Rainfall first fell clearly below its baseline in ${firstDry.month}.` : "No month so far shows a clear rainfall deficit.");
  } else parts.push("Rainfall has no usable observations in this period.");
  const soilMin = lowest(r, (x) => x.soilMoisturePctile);
  if (soilMin && soilStatus(soilMin.soilMoisturePctile) === "below") parts.push(`Surface soil wetness was lowest in ${soilMin.month} (${fmt(soilMin.soilMoisturePctile)}th percentile).`);
  const ndviMin = lowest(r, (x) => x.ndviAnomaly);
  if (ndviMin && ndviStatus(ndviMin.ndviAnomaly) === "below") parts.push(`Vegetation greenness dipped most in ${ndviMin.month}; other causes such as crop cycles or clouds are possible.`);
  const tr: [string, Trend | null][] = [
    ["rainfall", trend(r.map((x) => x.precipAnomalyMm), 15)],
    ["soil wetness", trend(r.map((x) => x.soilMoisturePctile), 5)],
    ["vegetation", trend(r.map((x) => x.ndviAnomaly), 0.03)],
  ];
  parts.push(`Latest direction: ${tr.map(([k, v]) => `${k} ${trendLabel(v)}`).join(", ")}.`);
  const gaps = r.filter((x) => missing(x.precipAnomalyMm) || missing(x.soilMoisturePctile) || missing(x.ndviAnomaly)).length;
  if (gaps) parts.push(`${gaps} of ${r.length} months have at least one indicator without data.`);
  return parts.join(" ");
}

// Signed scores in [-1, 1]: +1 = extreme dryness signal, -1 = strong wetness signal. null = no data.
const clip = (x: number) => Math.max(-1, Math.min(1, x));
export const precipScore = (mm: Value) => (missing(mm) ? null : clip(-mm / 90));
export const soilScore = (pct: Value) => (missing(pct) ? null : clip((50 - pct) / 40));
export const ndviScore = (v: Value) => (missing(v) ? null : clip(-v / 0.2));

export const THRESHOLDS = {
  precip: "below baseline if anomaly < -30 mm; above if > +30 mm",
  soil: "below normal if percentile < 25; above if > 75",
  ndvi: "below baseline if NDVI anomaly < -0.05; above if > +0.05",
};
export const statusFns = { precip: precipStatus, soil: soilStatus, ndvi: ndviStatus };
