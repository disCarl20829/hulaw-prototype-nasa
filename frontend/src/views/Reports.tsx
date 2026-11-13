import type { Region } from "../types";
import { buildSummary, THRESHOLDS } from "../utils/analysis";

function download(name: string, text: string, type: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}

export default function Reports({ region, index }: { region: Region; index: number }) {
  const rows = region.records.slice(0, index + 1);
  const csv = ["month,precip_anomaly_mm,soil_moisture_percentile,ndvi_anomaly", ...rows.map((r) => `${r.month},${r.precipAnomalyMm},${r.soilMoisturePctile},${r.ndviAnomaly}`)].join("\n");
  const json = JSON.stringify({ region: region.name, illustrative: region.isIllustrative, generatedAt: new Date().toISOString(), sources: region.sources, thresholds: THRESHOLDS, summary: buildSummary(region.records, index), records: rows }, null, 2);
  return (
    <div className="page">
      <h2>Reports and methodology</h2>
      <p className="lead">Export the current selection with its source details and caveats.</p>
      <div className="panel"><h3>Export {region.name}, up to {rows[rows.length - 1].month}</h3>
        {region.isIllustrative && <p className="warn">This export contains illustrative placeholder values, not satellite observations.</p>}
        <p className="summary">{buildSummary(region.records, index)}</p>
        <button onClick={() => download("hulaw-summary.csv", csv, "text/csv")}>Download CSV</button>{" "}
        <button onClick={() => download("hulaw-summary.json", json, "application/json")}>Download JSON</button>{" "}
        <button onClick={() => window.print()}>Print or save as PDF</button></div>
      <div className="two">
        <div className="panel"><h3>Methodology</h3><ul><li>Anomaly = observed monthly value minus the baseline for the same calendar month.</li><li>Baseline periods: to be defined and recorded per dataset.</li><li>Recovery = movement toward seasonal norms.</li><li>The combined index averages signed scores and stays experimental until validated.</li></ul></div>
        <div className="panel"><h3>Data sources and limits</h3><ul>{Object.values(region.sources).map((s) => <li key={s.dataset}><b>{s.dataset}</b>: {s.nativeResolution}. {s.limitation}</li>)}</ul></div>
      </div>
      <p className="note">Hulaw is an exploratory decision-support tool, not an official warning service. Credit NASA and other data providers when sharing.</p>
    </div>
  );
}
