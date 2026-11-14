import type { ReactNode } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DataStatus, Region } from "../types";
import { buildSummary, fmt, fmtSigned, THRESHOLDS } from "../utils/analysis";
import { label } from "../data/severity";
import { buildCsv, buildJson, buildRows, download, printReport, reportFileName, type ReportArea } from "../utils/exportReport";

function monthName(month?: string) {
  return month ? new Date(`${month}-01T00:00:00`).toLocaleDateString("en-PH", { month: "long", year: "numeric" }) : "No period";
}
const coord = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(4)}°${v >= 0 ? pos : neg}`;

// Static geographic outline generated from the bundled Philippines MultiPolygon.
// It is a reference only: no drought severity is painted on it.
function PhilippinesMap() {
  return <img
    className="ph-report-map"
    src={`${import.meta.env.BASE_URL}philippines-outline.svg`}
    alt="Geographic outline of the Philippine archipelago; no drought-severity overlay is applied"
    loading="lazy"
    decoding="async"
  />;
}

interface Props { region: Region; index: number; dateControls?: ReactNode; selectedArea?: ReportArea | null; status?: DataStatus }

export default function Reports({ region, index, dateControls, selectedArea, status = "ready" }: Props) {
  const rows = buildRows(region, index);
  const recent = rows.slice(-6);
  const lastMonth = rows[rows.length - 1]?.month;
  const latestScore = rows[rows.length - 1]?.combinedIndex ?? null;
  const severitySeries = rows.map((r) => ({ month: r.month, score: r.combinedIndex }));
  const hasData = status === "ready" && rows.some((r) => r.precipAnomalyMm != null || r.soilMoisturePctile != null || r.ndviAnomaly != null);
  const fileName = reportFileName(region, rows, selectedArea);
  const summary = buildSummary(region.records, index);
  const placeName = selectedArea?.name ?? region.name;
  const point = region.location ? `${coord(region.location.latitude, "N", "S")}, ${coord(region.location.longitude, "E", "W")}` : "Not available";
  const generated = new Date().toLocaleString("en-PH", { dateStyle: "long", timeStyle: "short" });

  return <div className="page reports-page">
    {dateControls}

    {/* Shown only on paper / PDF */}
    <div className="print-only print-report-head">
      <div className="print-brand"><b>HULAW</b><span>Drought indicator report</span></div>
      <table className="print-meta"><tbody>
        <tr><th>Location</th><td>{placeName}{selectedArea ? ` (${selectedArea.level}, PSGC ${selectedArea.code})` : ""}</td></tr>
        <tr><th>Data point</th><td>{point}</td></tr>
        <tr><th>Period</th><td>{monthName(rows[0]?.month)} to {monthName(lastMonth)} ({rows.length} months)</td></tr>
        {region.period && <tr><th>Baseline</th><td>{region.period.baselineStart} to {region.period.baselineEnd} (rainfall, vegetation)</td></tr>}
        <tr><th>Generated</th><td>{generated}</td></tr>
      </tbody></table>
    </div>

    <div className="page-heading screen-only"><div><span className="eyebrow">HULAW · REPORT</span><h2>Drought assessment report: {placeName}</h2><p className="lead">A month-by-month view of rainfall, soil wetness and vegetation signals at the selected location.</p></div><span className="report-period">{monthName(lastMonth)}</span></div>

    <section className="panel national-report">
      <div className="section-heading"><div><span className="eyebrow">MONTHLY ASSESSMENT</span><h3>Condition timeline</h3><p className="note">{rows.length} monthly records · through {monthName(lastMonth)}</p></div><span className="report-count screen-only">{recent.length} MONTHS</span></div>
      <div className="severity-timeline" aria-label="Drought severity index timeline">
        <div className="severity-chart-heading"><div><h4>Experimental combined index over time</h4><p className="note">Mean of the available rainfall, soil-wetness and vegetation scores · positive values indicate dryness · gaps mean no data</p></div><div className="severity-current"><b>{latestScore == null ? "–" : latestScore.toFixed(2)}</b><span>{label(latestScore)}</span></div></div>
        <div className="severity-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={severitySeries} margin={{ top: 12, right: 14, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="rgba(145,170,185,.14)" strokeDasharray="3 4" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: "#91a6b2", fontSize: 10 }} tickLine={false} axisLine={{ stroke: "rgba(145,170,185,.25)" }} minTickGap={24} />
              <YAxis domain={[-1, 1]} ticks={[-1, -0.5, 0, 0.5, 1]} tick={{ fill: "#91a6b2", fontSize: 10 }} tickLine={false} axisLine={false} width={32} />
              <Tooltip contentStyle={{ background: "#101e29", border: "1px solid #34505f", borderRadius: 8, color: "#e8f0f3" }} labelStyle={{ color: "#a9c0cc" }} formatter={(value: number) => [value.toFixed(2), "Combined index"]} />
              <ReferenceLine y={0} stroke="#8296a1" strokeDasharray="4 4" />
              <ReferenceLine y={0.33} stroke="#d49a42" strokeDasharray="3 5" />
              <ReferenceLine y={0.66} stroke="#c45a50" strokeDasharray="3 5" />
              <Line type="monotone" dataKey="score" name="Combined index" stroke="#ef9a54" strokeWidth={2.5} connectNulls={false} dot={{ r: 2.5, fill: "#ef9a54", strokeWidth: 0 }} activeDot={{ r: 5, stroke: "#f5d5b7", strokeWidth: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="severity-chart-legend"><span><i className="dry"/> Higher dryness signal</span><span><i className="normal"/> Neutral baseline</span><span><i className="wet"/> Wetter signal</span></div>
      </div>
      <div className="month-snapshot-grid screen-only">{recent.map((r) => (
        <article className={`month-snapshot ${r.month === lastMonth ? "selected" : ""}`} key={r.month}>
          <div className="snapshot-top"><span>{monthName(r.month)}</span><span className="snapshot-tag">REFERENCE MAP</span></div>
          <div className="snapshot-map"><PhilippinesMap /></div>
          <div className="snapshot-bottom"><b>{r.combinedLabel}</b><span>Combined index · {r.combinedIndex == null ? "no data" : r.combinedIndex.toFixed(2)}</span></div>
        </article>
      ))}</div>
      <div className="snapshot-legend screen-only"><span><i style={{background:"#b42318"}}/> Dryness signal</span><span><i style={{background:"#f0c24b"}}/> Near normal</span><span><i style={{background:"#3b82c4"}}/> Wetter signal</span><small>The outline is a geographic reference only. The index describes the selected data point, not the whole country.</small></div>
    </section>

    <section className="panel report-export">
      <div className="section-heading"><div><span className="eyebrow">REPORT DATA</span><h3>{placeName} · {rows.length} monthly records</h3></div></div>
      <p className="summary"><b>Summary:</b> {summary}</p>
      {!!region.warnings?.length && <div className="report-warnings"><b>Data notes</b><ul>{region.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
      <div className="report-table-block">
      <div className="report-preview-heading"><div><h4>Monthly indicator table</h4><span className="note">“No data” means there was no usable observation; it is never counted as zero.</span></div><span className="preview-count screen-only">{rows.length} records</span></div>
      <div className="file-preview"><div className="table-preview"><table className="report-table">
        <thead>
          <tr><th rowSpan={2}>Month</th><th colSpan={4}>Rainfall (mm)</th><th colSpan={3}>Surface soil wetness</th><th colSpan={3}>Vegetation (NDVI)</th><th colSpan={2}>Combined (experimental)</th></tr>
          <tr><th>Observed</th><th>Baseline</th><th>Anomaly</th><th>Status</th><th>Fraction</th><th>Percentile</th><th>Status</th><th>NDVI</th><th>Anomaly</th><th>Status</th><th>Index</th><th>Label</th></tr>
        </thead>
        <tbody>{rows.map((r) => <tr key={r.month}>
          <td>{r.month}</td>
          <td>{fmt(r.precipMm, 1)}</td><td>{fmt(r.precipBaselineMm, 1)}</td><td>{fmtSigned(r.precipAnomalyMm, 1)}</td><td>{r.rainfallStatus}</td>
          <td>{fmt(r.soilWetness, 2)}</td><td>{fmt(r.soilMoisturePctile, 0)}</td><td>{r.soilStatus}</td>
          <td>{fmt(r.ndvi, 3)}</td><td>{fmtSigned(r.ndviAnomaly, 3)}</td><td>{r.vegetationStatus}</td>
          <td>{r.combinedIndex == null ? "No data" : fmtSigned(r.combinedIndex, 2)}</td><td>{r.combinedLabel}</td>
        </tr>)}</tbody>
      </table></div></div>
      </div>
      <div className="report-downloads">
        <button disabled={!hasData} onClick={() => download(`${fileName}.csv`, buildCsv(region, rows, selectedArea), "text/csv;charset=utf-8")}>Download CSV</button>
        <button disabled={!hasData} onClick={() => download(`${fileName}.json`, buildJson(region, rows, index, selectedArea), "application/json")}>Download JSON</button>
        <button disabled={!hasData} onClick={() => printReport(fileName)}>Print or save as PDF</button>
        {!hasData && <span className="note">{status === "loading" ? "Exports are available once the data has loaded." : "There is no data to export for this location yet."}</span>}
      </div>
      <p className="note screen-only">CSV: one row per month with units in the column names, ready for Excel. JSON: the same records plus location, sources, thresholds and data notes. PDF: a print layout of this report.</p>
    </section>
    <div className="two report-notes">
      <div className="panel"><h3>Methodology and interpretation</h3><ul><li>Rainfall anomaly compares the monthly total with the mean of the same calendar month in the baseline years ({THRESHOLDS.precip}).</li><li>Soil wetness is expressed as a percentile; lower values indicate a drier surface layer ({THRESHOLDS.soil}).</li><li>NDVI anomaly tracks vegetation greenness and may also reflect crop cycles, clouds and land-use change ({THRESHOLDS.ndvi}).</li><li>The combined index averages the available signed indicator scores. It is experimental and is not an official drought classification.</li></ul></div>
      <div className="panel"><h3>Data sources and limitations</h3><ul>{(["precip", "soil", "ndvi"] as const).map((k) => { const s = region.sources[k]; return <li key={k}><b>{s.dataset}</b>: {s.nativeResolution}. {s.limitation} Baseline: {s.baselinePeriod}.</li>; })}</ul></div>
    </div>
    <p className="note">Hulaw is an exploratory decision-support prototype, not an official warning service. Values describe one point, not an area average, and should be checked against local observations before any decision.</p>
  </div>;
}
