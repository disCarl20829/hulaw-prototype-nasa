import type { Region } from "../types";
import { COUNTRY_NAMES, countryScore, label, scoreColor } from "../data/severity";
import { ndviStatus, precipStatus, soilStatus, trend } from "../utils/analysis";

export default function Dashboard({ region, index }: { region: Region; index: number }) {
  const r = region.records.slice(0, index + 1);
  const cur = r[r.length - 1];
  const cards = [
    { name: "Rainfall anomaly", v: `${cur.precipAnomalyMm} mm`, st: precipStatus(cur.precipAnomalyMm), tr: trend(r.map((x) => x.precipAnomalyMm), 15), src: "NASA GPM/IMERG" },
    { name: "Soil moisture percentile", v: `${cur.soilMoisturePctile}th`, st: soilStatus(cur.soilMoisturePctile), tr: trend(r.map((x) => x.soilMoisturePctile), 5), src: "NASA SMAP" },
    { name: "Vegetation anomaly", v: `${cur.ndviAnomaly}`, st: ndviStatus(cur.ndviAnomaly), tr: trend(r.map((x) => x.ndviAnomaly), 0.03), src: "NASA MODIS NDVI" },
  ];
  const all = { combined: true, precip: true, soil: true, ndvi: true };
  const rows = Object.keys(COUNTRY_NAMES).map((iso) => ({ iso, s: countryScore(iso, index, region, all) ?? 0 })).sort((a, b) => b.s - a.s);
  return (
    <div className="page">
      <h2>Beyond detecting drought: understanding its development, impacts, and recovery</h2>
      <p className="lead">Hulaw compares satellite rainfall, soil moisture and vegetation against seasonal baselines, so you can see how dry conditions developed and whether they are easing.</p>
      <div className="two">
        <div className="panel"><h3>What Hulaw measures</h3><ul><li>Rainfall departures from a seasonal baseline (GPM/IMERG)</li><li>Near-surface soil moisture (SMAP)</li><li>Vegetation greenness (MODIS NDVI/EVI)</li><li>Optional later: regional water storage (GRACE-FO)</li></ul></div>
        <div className="panel"><h3>What it does not do</h3><ul><li>Measure single farms or household water supply</li><li>Prove crop loss from NDVI alone</li><li>Issue official drought declarations or forecasts</li></ul></div>
      </div>
      <h3>{region.name}: latest selected month ({cur.month}){region.isIllustrative && " · illustrative data"}</h3>
      <div className="cards">{cards.map((c) => (
        <div className="panel card" key={c.name}><span className="note">{c.src}</span><strong>{c.v}</strong><span>{c.name}</span>
          <span className={`pill ${c.st}`}>{c.st === "below" ? "▼ below normal" : c.st === "above" ? "▲ above normal" : "• near normal"}</span><span className="note">Direction: {c.tr}</span></div>))}</div>
      <h3>Regional overview at {cur.month}</h3>
      <div className="panel"><table><thead><tr><th>Country</th><th>Severity signal</th><th>Score</th></tr></thead><tbody>
        {rows.map((x) => <tr key={x.iso}><td>{COUNTRY_NAMES[x.iso]}</td><td><i className="dot" style={{ background: scoreColor(x.s) }} /> {label(x.s)}</td><td>{x.s.toFixed(2)}</td></tr>)}
      </tbody></table><p className="note">Scores run from +1 (extreme dryness signal) to −1 (strong wetness signal). Experimental and illustrative until validated.</p></div>
      <p><a className="btn" href="#/map">Open map explorer</a> <a className="btn" href="#/timeline">View the timeline</a></p>
    </div>
  );
}
