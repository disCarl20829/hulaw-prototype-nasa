import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Region, SourceMeta } from "../types";

const label = (m: string) => new Date(m + "-01").toLocaleString("en", { month: "short" });
const Src = ({ s }: { s: SourceMeta }) => (
  <details className="src"><summary>Source and limits</summary>
    <p>{s.dataset}. {s.variable} ({s.unit}). Baseline: {s.baselinePeriod}. Resolution: {s.nativeResolution}. {s.limitation}</p></details>
);

export default function RegionPanel({ region, upTo, tall = false }: { region: Region; upTo: number; tall?: boolean }) {
  const data = region.records.slice(0, upTo + 1).map((r) => ({ ...r, m: label(r.month) }));
  const range = `${region.records[0].month} to ${region.records[region.records.length - 1].month}`;
  return (
    <aside className={`panel region ${tall ? "tall" : ""}`}>
      <h2>Regional analysis: {region.name}</h2>
      <p className="note">{range}{region.isIllustrative && " · illustrative data"}</p>

      <h3>Precipitation anomaly (GPM/IMERG, mm)</h3>
      <ResponsiveContainer width="100%" height={tall ? 220 : 120}>
        <BarChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis stroke="#8b9bab" fontSize={10} width={32} />
          <Tooltip /><ReferenceLine y={0} stroke="#8b9bab" />
          <Bar dataKey="precipAnomalyMm" name="Anomaly (mm)">{data.map((d) => <Cell key={d.month} fill={d.precipAnomalyMm < 0 ? "#e8644f" : "#3bb3b0"} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
      <Src s={region.sources.precip} />

      <h3>Soil moisture percentile (SMAP)</h3>
      <ResponsiveContainer width="100%" height={tall ? 200 : 110}>
        <AreaChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis domain={[0, 100]} stroke="#8b9bab" fontSize={10} width={32} />
          <Tooltip /><Area dataKey="soilMoisturePctile" name="Percentile" stroke="#d6b84a" fill="#d6b84a55" /></AreaChart>
      </ResponsiveContainer>
      <Src s={region.sources.soil} />

      <h3>Vegetation anomaly (MODIS NDVI)</h3>
      <ResponsiveContainer width="100%" height={tall ? 200 : 110}>
        <AreaChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={10} /><YAxis stroke="#8b9bab" fontSize={10} width={32} />
          <Tooltip /><ReferenceLine y={0} stroke="#8b9bab" /><Area dataKey="ndviAnomaly" name="NDVI anomaly" stroke="#6fbf8b" fill="#6fbf8b55" /></AreaChart>
      </ResponsiveContainer>
      <Src s={region.sources.ndvi} />
    </aside>
  );
}
