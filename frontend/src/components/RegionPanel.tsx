import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DataStatus, Region, SourceMeta } from "../types";

const label = (m: string) => new Date(m + "-01").toLocaleString("en", { month: "short" });
const Src = ({ s }: { s: SourceMeta }) => (
  <details className="src"><summary>Source and limits</summary>
    <p>{s.dataset}. {s.variable} ({s.unit}). Baseline: {s.baselinePeriod}. Resolution: {s.nativeResolution}. {s.limitation}</p></details>
);
const coord = (v: number, pos: string, neg: string) => `${Math.abs(v).toFixed(2)}°${v >= 0 ? pos : neg}`;
const tip = { contentStyle: { background: "#101e29", border: "1px solid #34505f", borderRadius: 8, color: "#e8f0f3" }, labelStyle: { color: "#a9c0cc" } };

interface Props { region: Region; upTo: number; tall?: boolean; selectedArea?: { code: string; name: string; level: string } | null; status?: DataStatus }

export default function RegionPanel({ region, upTo, tall = false, selectedArea, status = "ready" }: Props) {
  const data = region.records.slice(0, upTo + 1).map((r) => ({ ...r, m: label(r.month) }));
  const range = region.records.length ? `${region.records[0].month} to ${region.records[region.records.length - 1].month}` : "";
  const point = region.location ? `${coord(region.location.latitude, "N", "S")}, ${coord(region.location.longitude, "E", "W")}` : null;
  const none = (key: "precipAnomalyMm" | "soilMoisturePctile" | "ndviAnomaly") => status === "ready" && data.every((d) => d[key] == null);
  const Empty = () => <p className="chart-empty">No usable observations for these months.</p>;
  return (
    <aside className={`panel region ${tall ? "tall" : ""}`}>
      <h2>{selectedArea ? `${selectedArea.level}: ${selectedArea.name}` : region.name}</h2>
      <p className="note">{selectedArea ? `PSGC ${selectedArea.code}` : "Default reference point"} · {range}</p>
      {status === "loading" && <p className="data-inline loading">Loading NASA data for this location. The first load can take up to a minute.</p>}
      {status === "error" && <p className="data-inline error">Data could not be loaded, so the charts are empty.</p>}
      {status === "ready" && <div className="area-data-note">
        <div className="area-summary-heading"><strong>Location summary</strong><span className="area-level">{selectedArea ? selectedArea.level : "Reference point"}</span></div>
        <div className="area-summary-grid"><div><span>{selectedArea ? "Administrative area" : "Location"}</span><b>{selectedArea ? selectedArea.name : region.name}</b></div><div><span>Data point</span><b>{point ?? "Not available"}</b></div></div>
        <p>Values are read at this single point{selectedArea ? " (the center of the selected area)" : ""}. They are not an average over the whole area.</p>
      </div>}

      <h3>Rainfall anomaly (mm)</h3>
      {none("precipAnomalyMm") ? <Empty /> : <ResponsiveContainer width="100%" height={tall ? 220 : 120}>
        <BarChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis stroke="#8b9bab" fontSize={10} width={36} />
          <Tooltip {...tip} /><ReferenceLine y={0} stroke="#8b9bab" />
          <Bar dataKey="precipAnomalyMm" name="Anomaly (mm)">{data.map((d) => <Cell key={d.month} fill={(d.precipAnomalyMm ?? 0) < 0 ? "#e8644f" : "#3bb3b0"} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>}
      <Src s={region.sources.precip} />

      <h3>Surface soil wetness (percentile)</h3>
      {none("soilMoisturePctile") ? <Empty /> : <ResponsiveContainer width="100%" height={tall ? 200 : 110}>
        <AreaChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis domain={[0, 100]} stroke="#8b9bab" fontSize={10} width={36} />
          <Tooltip {...tip} /><Area dataKey="soilMoisturePctile" name="Percentile" stroke="#d6b84a" fill="#d6b84a55" connectNulls={false} dot={{ r: 2 }} /></AreaChart>
      </ResponsiveContainer>}
      <Src s={region.sources.soil} />

      <h3>Vegetation anomaly (NDVI)</h3>
      {none("ndviAnomaly") ? <Empty /> : <ResponsiveContainer width="100%" height={tall ? 200 : 110}>
        <AreaChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis stroke="#8b9bab" fontSize={10} width={36} />
          <Tooltip {...tip} /><ReferenceLine y={0} stroke="#8b9bab" /><Area dataKey="ndviAnomaly" name="NDVI anomaly" stroke="#6fbf8b" fill="#6fbf8b55" connectNulls={false} dot={{ r: 2 }} /></AreaChart>
      </ResponsiveContainer>}
      <Src s={region.sources.ndvi} />
    </aside>
  );
}
