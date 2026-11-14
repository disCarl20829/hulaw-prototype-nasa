import type { ReactNode } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Region } from "../types";
import Timeline from "../components/Timeline";
import { ndviScore, ndviStatus, precipScore, precipStatus, soilScore, soilStatus, trend, trendLabel } from "../utils/analysis";

export default function TimelineView({ region, index, onChange, dateControls }: { region: Region; index: number; onChange: (i: number) => void; dateControls?: ReactNode }) {
  const r = region.records.slice(0, index + 1);
  const round = (v: number | null) => (v == null ? null : +v.toFixed(2)); // null stays a gap in the chart
  const data = r.map((x) => ({ m: x.month, Rainfall: round(precipScore(x.precipAnomalyMm)), "Soil wetness": round(soilScore(x.soilMoisturePctile)), Vegetation: round(ndviScore(x.ndviAnomaly)) }));
  const observed = (pick: (x: typeof r[number]) => number | null) => r.filter((x) => pick(x) != null).length;
  const metrics = [
    { n: "Rainfall", below: r.filter((x) => precipStatus(x.precipAnomalyMm) === "below").length, of: observed((x) => x.precipAnomalyMm), t: trend(r.map((x) => x.precipAnomalyMm), 15) },
    { n: "Soil wetness", below: r.filter((x) => soilStatus(x.soilMoisturePctile) === "below").length, of: observed((x) => x.soilMoisturePctile), t: trend(r.map((x) => x.soilMoisturePctile), 5) },
    { n: "Vegetation", below: r.filter((x) => ndviStatus(x.ndviAnomaly) === "below").length, of: observed((x) => x.ndviAnomaly), t: trend(r.map((x) => x.ndviAnomaly), 0.03) },
  ];
  return (
    <div className="page">
      <h2>Drought development and recovery timeline: {region.name}</h2>
      <p className="lead">Which indicator changed first, and which is recovering? Orders differ between regions, so read the evidence rather than assume a sequence.</p>
      {dateControls}
      <Timeline region={region} index={index} onChange={onChange} floating={false} />
      <div className="panel"><h3>Aligned dryness signal by indicator (+1 dry, −1 wet)</h3>
        <ResponsiveContainer width="100%" height={240}><LineChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={11} /><YAxis domain={[-1, 1]} stroke="#8b9bab" fontSize={11} width={34} /><Tooltip /><Legend /><ReferenceLine y={0} stroke="#8b9bab" />
          <Line dataKey="Rainfall" stroke="#3bb3b0" strokeWidth={2} /><Line dataKey="Soil wetness" stroke="#d6b84a" strokeWidth={2} strokeDasharray="6 3" /><Line dataKey="Vegetation" stroke="#6fbf8b" strokeWidth={2} strokeDasharray="2 3" /></LineChart></ResponsiveContainer></div>
      <div className="cards">{metrics.map((m) => (
        <div className="panel card" key={m.n}><strong>{m.n}</strong><span>{m.below} of {m.of} months with data below baseline</span><span className="note">Recent direction: {trendLabel(m.t)}</span></div>))}</div>
      <p className="note">“Recovery” here means movement toward seasonal norms, not that economic, ecological or water impacts have ended. Gaps in a line mean there was no usable observation for that month.</p>
    </div>
  );
}
