import type { LayerKey, Region } from "../types";
import { ndviScore, precipScore, soilScore } from "../utils/analysis";

// Philippines is derived from its (illustrative) monthly records.
// Other countries use an ILLUSTRATIVE bell-shaped profile: placeholder until real gridded layers exist.
const profiles: Record<string, { peak: number; month: number; width: number }> = {
  VNM: { peak: 0.95, month: 5, width: 3 }, KHM: { peak: 0.85, month: 5, width: 3 },
  THA: { peak: 0.75, month: 4, width: 3 }, LAO: { peak: 0.7, month: 5, width: 3 },
  MMR: { peak: 0.5, month: 4, width: 3 }, CHN: { peak: 0.55, month: 6, width: 4 },
  MYS: { peak: 0.65, month: 6, width: 3 }, IDN: { peak: 0.6, month: 7, width: 3 },
  TWN: { peak: 0.4, month: 5, width: 3 }, IND: { peak: -0.4, month: 3, width: 4 },
  BGD: { peak: -0.5, month: 3, width: 3 }, AUS: { peak: 0.3, month: 8, width: 4 },
};

export function countryScore(iso: string, i: number, region: Region, active: Record<LayerKey, boolean>): number | null {
  if (iso === "PHL") {
    const r = region.records[i];
    const parts: number[] = [];
    if (active.combined || active.precip) parts.push(precipScore(r.precipAnomalyMm));
    if (active.combined || active.soil) parts.push(soilScore(r.soilMoisturePctile));
    if (active.combined || active.ndvi) parts.push(ndviScore(r.ndviAnomaly));
    return parts.length ? parts.reduce((a, b) => a + b, 0) / parts.length : null;
  }
  const p = profiles[iso];
  if (!p || !(active.combined || active.precip)) return p ? 0 : 0;
  return p.peak * Math.exp(-((i - p.month) ** 2) / (2 * p.width ** 2));
}

export const COUNTRY_NAMES: Record<string, string> = { PHL: "Philippines", VNM: "Vietnam", KHM: "Cambodia", THA: "Thailand", LAO: "Laos", MMR: "Myanmar", MYS: "Malaysia", IDN: "Indonesia", CHN: "China", TWN: "Taiwan", IND: "India", BGD: "Bangladesh", AUS: "Australia" };
export const label = (s: number) => (s > 0.66 ? "Extreme dryness signal" : s > 0.33 ? "Severe dryness signal" : s > 0.1 ? "Moderate dryness signal" : s >= -0.1 ? "Near normal" : "Wetter than normal");

// Ramp matches the legend: drought (red) -> normal (yellow/green) -> wet (blue)
const stops = ["#b42318", "#e8702a", "#f0c24b", "#7fc48a", "#3b82c4"];
export function scoreColor(s: number): string {
  const t = (1 - Math.max(-1, Math.min(1, s))) / 2 * (stops.length - 1);
  const a = Math.floor(t), b = Math.min(a + 1, stops.length - 1), f = t - a;
  const h = (c: string, k: number) => parseInt(c.slice(1 + k * 2, 3 + k * 2), 16);
  const m = (k: number) => Math.round(h(stops[a], k) + (h(stops[b], k) - h(stops[a], k)) * f);
  return `rgb(${m(0)},${m(1)},${m(2)})`;
}
