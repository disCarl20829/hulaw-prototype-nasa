import type { MonthRecord, Region } from "../types";
import { ALL_LAYERS, countryScore, label } from "../data/severity";
import { buildSummary, ndviStatus, precipStatus, soilStatus, STATUS_LABEL, THRESHOLDS } from "./analysis";

export interface ReportArea { level: string; code: string; name: string }

export interface ReportRow extends MonthRecord {
  rainfallStatus: string; soilStatus: string; vegetationStatus: string;
  combinedIndex: number | null; combinedLabel: string;
}

/** Records up to the selected month, with status labels and the experimental combined index. */
export function buildRows(region: Region, upTo: number): ReportRow[] {
  return region.records.slice(0, upTo + 1).map((r, i) => {
    const combined = countryScore("PHL", i, region, ALL_LAYERS);
    return {
      ...r,
      rainfallStatus: STATUS_LABEL[precipStatus(r.precipAnomalyMm)],
      soilStatus: STATUS_LABEL[soilStatus(r.soilMoisturePctile)],
      vegetationStatus: STATUS_LABEL[ndviStatus(r.ndviAnomaly)],
      combinedIndex: combined == null ? null : +combined.toFixed(3),
      combinedLabel: label(combined),
    };
  });
}

const slug = (text: string) => text.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "location";

/** e.g. hulaw-bukidnon-2025-11_to_2026-10 */
export function reportFileName(region: Region, rows: ReportRow[], area?: ReportArea | null): string {
  const period = rows.length ? `${rows[0].month}_to_${rows[rows.length - 1].month}` : "no-data";
  return `hulaw-${slug(area?.name ?? region.name)}-${period}`;
}

// One tidy table: a single header row, one row per month, units in the column names, empty cell = no data.
const CSV_COLUMNS: [string, (r: ReportRow) => string | number | null][] = [
  ["month", (r) => r.month],
  ["rainfall_observed_mm", (r) => r.precipMm],
  ["rainfall_baseline_mm", (r) => r.precipBaselineMm],
  ["rainfall_anomaly_mm", (r) => r.precipAnomalyMm],
  ["rainfall_status", (r) => r.rainfallStatus],
  ["soil_wetness_fraction", (r) => r.soilWetness],
  ["soil_wetness_percentile", (r) => r.soilMoisturePctile],
  ["soil_status", (r) => r.soilStatus],
  ["ndvi", (r) => r.ndvi],
  ["ndvi_baseline", (r) => r.ndviBaseline],
  ["ndvi_anomaly", (r) => r.ndviAnomaly],
  ["vegetation_status", (r) => r.vegetationStatus],
  ["combined_index_experimental", (r) => r.combinedIndex],
  ["combined_label", (r) => r.combinedLabel],
];

function csvCell(value: string | number | null | undefined): string {
  if (value == null) return "";
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export function buildCsv(region: Region, rows: ReportRow[], area?: ReportArea | null): string {
  const fixed: [string, string | number | null][] = [
    ["location", area?.name ?? region.name],
    ["admin_level", area?.level ?? ""],
    ["psgc_code", area?.code ?? ""],
    ["latitude", region.location ? +region.location.latitude.toFixed(4) : null],
    ["longitude", region.location ? +region.location.longitude.toFixed(4) : null],
  ];
  const header = [...fixed.map(([name]) => name), ...CSV_COLUMNS.map(([name]) => name)];
  const lines = rows.map((r) => [...fixed.map(([, value]) => value), ...CSV_COLUMNS.map(([, pick]) => pick(r))].map(csvCell).join(","));
  // BOM + CRLF so Excel opens it with the right encoding and row breaks.
  return "﻿" + [header.join(","), ...lines].join("\r\n") + "\r\n";
}

export function buildJson(region: Region, rows: ReportRow[], upTo: number, area?: ReportArea | null): string {
  const report = {
    report: {
      title: "Hulaw drought indicator report",
      generated_at: new Date().toISOString(),
      data_retrieved_at: region.generatedAt ?? null,
      disclaimer: "Exploratory decision-support output. Not an official drought classification or warning. Values describe one point, not an area average.",
    },
    location: {
      name: area?.name ?? region.name,
      admin_level: area?.level ?? null,
      psgc_code: area?.code ?? null,
      latitude: region.location?.latitude ?? null,
      longitude: region.location?.longitude ?? null,
    },
    period: { start_month: rows[0]?.month ?? null, end_month: rows[rows.length - 1]?.month ?? null, months: rows.length },
    baseline_years: region.period ? { start_year: region.period.baselineStart, end_year: region.period.baselineEnd } : null,
    summary: buildSummary(region.records, upTo),
    fields: {
      "rainfall.observed_mm": "Monthly rainfall total (mm)",
      "rainfall.baseline_mm": "Mean total for the same calendar month in the baseline years (mm)",
      "rainfall.anomaly_mm": "Observed minus baseline (mm); negative = rainfall deficit",
      "soil.wetness_fraction": "Monthly mean surface soil wetness, 0-1",
      "soil.percentile": "Percentile of that mean among the same calendar month in the reference years, 0-100",
      "vegetation.ndvi": "Monthly mean NDVI of quality-filtered composites",
      "vegetation.anomaly": "NDVI minus baseline NDVI; negative = less green than usual",
      "combined.index": "Experimental: mean of the available signed indicator scores, -1 (wetter) to +1 (drier)",
      null_values: "No usable observation. Never interpret as zero.",
    },
    thresholds: THRESHOLDS,
    sources: region.sources,
    data_warnings: region.warnings ?? [],
    records: rows.map((r) => ({
      month: r.month,
      rainfall: { observed_mm: r.precipMm, baseline_mm: r.precipBaselineMm, anomaly_mm: r.precipAnomalyMm, status: r.rainfallStatus },
      soil: { wetness_fraction: r.soilWetness, percentile: r.soilMoisturePctile, status: r.soilStatus },
      vegetation: { ndvi: r.ndvi, baseline_ndvi: r.ndviBaseline, anomaly: r.ndviAnomaly, status: r.vegetationStatus },
      combined: { index: r.combinedIndex, label: r.combinedLabel },
    })),
  };
  return JSON.stringify(report, null, 2) + "\n";
}

export function download(name: string, text: string, type: string) {
  const a = document.createElement("a");
  const url = URL.createObjectURL(new Blob([text], { type }));
  a.href = url; a.download = name; a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Print with the report file name as the document title, so "Save as PDF" suggests a useful name. */
export function printReport(fileName: string) {
  const previous = document.title;
  const restore = () => { document.title = previous; window.removeEventListener("afterprint", restore); };
  window.addEventListener("afterprint", restore);
  document.title = fileName;
  window.print();
}
