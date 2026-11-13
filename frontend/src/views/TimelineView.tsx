import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Region } from "../types";
import Timeline from "../components/Timeline";
import { ndviScore, ndviStatus, precipScore, precipStatus, soilScore, soilStatus, trend } from "../utils/analysis";

export default function TimelineView({ region, index, onChange }: { region: Region; index: number; onChange: (i: number) => void }) {
  const r = region.records.slice(0, index + 1);
  const data = r.map((x) => ({ m: x.month, Rainfall: +precipScore(x.precipAnomalyMm).toFixed(2), "Soil moisture": +soilScore(x.soilMoisturePctile).toFixed(2), Vegetation: +ndviScore(x.ndviAnomaly).toFixed(2) }));
  const metrics = [
    { n: "Rainfall", below: r.filter((x) => precipStatus(x.precipAnomalyMm) === "below").length, t: trend(r.map((x) => x.precipAnomalyMm), 15) },
    { n: "Soil moisture", below: r.filter((x) => soilStatus(x.soilMoisturePctile) === "below").length, t: trend(r.map((x) => x.soilMoisturePctile), 5) },
    { n: "Vegetation", below: r.filter((x) => ndviStatus(x.ndviAnomaly) === "below").length, t: trend(r.map((x) => x.ndviAnomaly), 0.03) },
  ];
  return (
    <div className="page">
      <h2>Drought development and recovery timeline: {region.name}</h2>
      <p className="lead">Which indicator changed first, and which is recovering? Orders differ between regions, so read the evidence rather than assume a sequence.</p>
      <Timeline region={region} index={index} onChange={onChange} floating={false} />
      <div className="panel"><h3>Aligned dryness signal by indicator (+1 dry, −1 wet)</h3>
        <ResponsiveContainer width="100%" height={240}><LineChart data={data}><CartesianGrid stroke="#ffffff12" /><XAxis dataKey="m" stroke="#8b9bab" fontSize={11} /><YAxis domain={[-1, 1]} stroke="#8b9bab" fontSize={11} width={34} /><Tooltip /><Legend /><ReferenceLine y={0} stroke="#8b9bab" />
          <Line dataKey="Rainfall" stroke="#3bb3b0" strokeWidth={2} /><Line dataKey="Soil moisture" stroke="#d6b84a" strokeWidth={2} strokeDasharray="6 3" /><Line dataKey="Vegetation" stroke="#6fbf8b" strokeWidth={2} strokeDasharray="2 3" /></LineChart></ResponsiveContainer></div>
      <div className="cards">{metrics.map((m) => (
        <div className="panel card" key={m.n}><strong>{m.n}</strong><span>{m.below} of {r.length} months below baseline</span><span className="note">Recent direction: {m.t}</span></div>))}</div>
      <p className="note">“Recovery” here means movement toward seasonal norms, not that economic, ecological or water impacts have ended. Values are illustrative.</p>
    </div>
  );
}
