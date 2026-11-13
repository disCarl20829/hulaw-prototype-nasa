import type { MonthRecord, Trend } from "../types";

export type Status = "below" | "normal" | "above";
export const precipStatus = (v: number): Status => (v < -30 ? "below" : v > 30 ? "above" : "normal");
export const soilStatus = (v: number): Status => (v < 25 ? "below" : v > 75 ? "above" : "normal");
export const ndviStatus = (v: number): Status => (v < -0.05 ? "below" : v > 0.05 ? "above" : "normal");

const mean = (a: number[]) => a.reduce((s, x) => s + x, 0) / a.length;

export function trend(values: number[], tol: number): Trend {
  if (values.length < 4) return "stable";
  const recent = values[values.length - 1];
  const before = mean(values.slice(-4, -1));
  return recent - before > tol ? "improving" : recent - before < -tol ? "worsening" : "stable";
}

// Rule-based summary built only from the selected data (never hard-coded text).
export function buildSummary(records: MonthRecord[], upTo: number): string {
  const r = records.slice(0, upTo + 1);
  const firstDry = r.find((x) => precipStatus(x.precipAnomalyMm) === "below");
  const soilMin = r.reduce((m, x) => (x.soilMoisturePctile < m.soilMoisturePctile ? x : m), r[0]);
  const ndviMin = r.reduce((m, x) => (x.ndviAnomaly < m.ndviAnomaly ? x : m), r[0]);
  const tr = {
    rainfall: trend(r.map((x) => x.precipAnomalyMm), 15),
    "soil moisture": trend(r.map((x) => x.soilMoisturePctile), 5),
    vegetation: trend(r.map((x) => x.ndviAnomaly), 0.03),
  };
  const parts: string[] = [];
  parts.push(firstDry ? `Rainfall first fell clearly below its baseline in ${firstDry.month}.` : "No month so far shows a clear rainfall deficit.");
  if (soilStatus(soilMin.soilMoisturePctile) === "below") parts.push(`Surface soil moisture was lowest in ${soilMin.month} (${soilMin.soilMoisturePctile}th percentile).`);
  if (ndviStatus(ndviMin.ndviAnomaly) === "below") parts.push(`Vegetation greenness dipped most in ${ndviMin.month}; other causes such as crop cycles or clouds are possible.`);
  parts.push(`Latest direction: ${Object.entries(tr).map(([k, v]) => `${k} ${v}`).join(", ")}.`);
  return parts.join(" ");
}
