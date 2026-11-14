import type { CSSProperties } from "react";
import type { Region } from "../types";
import { ALL_LAYERS, countryScore, label, scoreColor } from "../data/severity";
import { fmt, fmtSigned, ndviStatus, precipStatus, soilStatus, STATUS_LABEL, trend, trendLabel } from "../utils/analysis";

const monthLabel = (month: string) => new Date(`${month}-01T00:00:00`).toLocaleDateString("en-PH", { month: "short", year: "2-digit" });

export default function Dashboard({ region, index }: { region: Region; index: number }) {
  const records = region.records.slice(0, index + 1);
  const cur = records[records.length - 1];
  const score = countryScore("PHL", index, region, ALL_LAYERS);
  const cards = [
    { name: "Rainfall anomaly", value: fmtSigned(cur.precipAnomalyMm, 0, " mm"), status: precipStatus(cur.precipAnomalyMm), direction: trend(records.map(x => x.precipAnomalyMm), 15), source: region.sources.precip.dataset, hint: cur.precipMm != null && cur.precipBaselineMm != null ? `${fmt(cur.precipMm, 0)} mm observed vs ${fmt(cur.precipBaselineMm, 0)} mm baseline` : "Monthly departure from baseline" },
    { name: "Soil wetness", value: cur.soilMoisturePctile == null ? "No data" : `${fmt(cur.soilMoisturePctile, 0)}th`, status: soilStatus(cur.soilMoisturePctile), direction: trend(records.map(x => x.soilMoisturePctile), 5), source: region.sources.soil.dataset, hint: "Surface soil wetness percentile" },
    { name: "Vegetation anomaly", value: fmtSigned(cur.ndviAnomaly, 2), status: ndviStatus(cur.ndviAnomaly), direction: trend(records.map(x => x.ndviAnomaly), 0.03), source: region.sources.ndvi.dataset, hint: "Greenness departure from baseline" },
  ];
  const latestSix = records.slice(-6);
  return <div className="page dashboard-page">
    <section className="dashboard-hero">
      <div className="dashboard-hero-copy"><span className="eyebrow">HULAW · LOCATION OVERVIEW</span><h2>Drought dashboard: {region.name}</h2><p>Current dryness signals for the selected location, read from NASA data at one point and compared with the same months in earlier years.</p><div className="dashboard-meta"><span>Reporting month <b>{cur.month}</b></span><span className="data-status">{region.isIllustrative ? "Illustrative prototype dataset" : "NASA POWER and MODIS, read at one point"}</span></div></div>
      <div className="hero-index" style={{"--index-color":scoreColor(score)} as CSSProperties}><span>COMBINED INDEX</span><strong>{score == null ? "–" : score.toFixed(2)}</strong><b>{label(score)}</b><small>Experimental, not an official classification</small></div>
    </section>

    {region.isIllustrative && <div className="dashboard-caveat"><b>Data quality note</b><span>Values shown are illustrative sample data. They are not verified live satellite measurements and should not be used for operational decisions.</span></div>}

    <div className="dashboard-section-title"><div><span className="eyebrow">KEY INDICATORS</span><h3>Latest environmental readings</h3></div><span className="note">Selected month: {cur.month}</span></div>
    <section className="dashboard-kpis">{cards.map((c, i) => <article className="panel kpi-card" key={c.name}>
      <div className="kpi-card-head"><span className={`kpi-icon kpi-${i}`}>{["☂","◉","✳"][i]}</span><span className="note">{c.source}</span></div>
      <strong className="kpi-value">{c.value}</strong><h4>{c.name}</h4><p>{c.hint}</p>
      <div className="kpi-foot"><span className={`pill ${c.status}`}>{STATUS_LABEL[c.status]}</span><span className="kpi-trend">Trend: {trendLabel(c.direction)}</span></div>
    </article>)}</section>

    <div className="dashboard-section-title"><div><span className="eyebrow">RECENT HISTORY</span><h3>Drought signal by month</h3></div><span className="note">Combined indicator</span></div>
    <section className="panel dashboard-history">
      <div className="history-bars">{latestSix.map((r) => {
        const i = region.records.findIndex(x => x.month === r.month);
        const value = countryScore("PHL", i, region, ALL_LAYERS);
        return <div className={`history-item ${i === index ? "active" : ""}`} key={r.month} title={`${r.month}: ${label(value)}${value == null ? "" : ` (${value.toFixed(2)})`}`}>
          <div className="history-track">{value != null && <i style={{height:`${Math.max(8, Math.abs(value)*100)}%`, background:scoreColor(value), opacity:value < 0 ? .65 : 1}} />}</div><b>{value == null ? "–" : value.toFixed(2)}</b><span>{monthLabel(r.month)}</span>
        </div>;
      })}</div>
      <div className="history-caption"><span><i className="legend-dot dry"/> Dryness signal</span><span><i className="legend-dot normal"/> Near normal</span><span><i className="legend-dot wet"/> Wetter signal</span><small>Index range: −1 (wetter) to +1 (drier). Bars show magnitude; color shows direction and intensity.</small></div>
    </section>

    <div className="dashboard-section-title"><div><span className="eyebrow">HOW TO READ THE DASHBOARD</span><h3>What these indicators tell you</h3></div></div>
    <section className="dashboard-explainer">
      <article className="panel"><span className="explainer-number">01</span><h4>Rainfall</h4><p>Shows whether monthly rainfall is above or below its seasonal baseline. A deficit can indicate meteorological dryness.</p></article>
      <article className="panel"><span className="explainer-number">02</span><h4>Soil wetness</h4><p>Shows how wet or dry the surface soil layer is relative to the same month in earlier years. It is a model-based estimate, not a field measurement.</p></article>
      <article className="panel"><span className="explainer-number">03</span><h4>Vegetation</h4><p>Shows changes in vegetation greenness. Crop cycles, cloud cover and land use can influence this signal.</p></article>
    </section>
    <div className="dashboard-actions"><a className="btn" href="#/map">Choose a location on the map</a><a className="btn secondary" href="#/timeline">Open monthly timeline</a><a className="btn secondary" href="#/reports">View assessment report</a></div>
  </div>;
}
