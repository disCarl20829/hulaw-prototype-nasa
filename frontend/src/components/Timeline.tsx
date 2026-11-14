import { useEffect, useState } from "react";
import type { MonthRecord, Region } from "../types";
import { buildSummary, ndviStatus, precipStatus, soilStatus, type Status } from "../utils/analysis";

const GLYPH: Record<Status, string> = { below: "▼", normal: "•", above: "▲", nodata: "–" }; // not colour-only
const WORDS: Record<Status, string> = { below: "below baseline", normal: "near baseline", above: "above baseline", nodata: "no data" };

interface Props { region: Region; index: number; onChange: (i: number) => void; floating?: boolean; onHide?: () => void }

export default function Timeline({ region, index, onChange, floating = true, onHide }: Props) {
  const [playing, setPlaying] = useState(false);
  const last = region.records.length - 1;
  const current = region.records[Math.min(index, last)];

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => onChange(index >= last ? 0 : index + 1), 900);
    return () => clearInterval(t);
  }, [playing, index, last, onChange]);

  const rows: [string, (r: MonthRecord) => Status][] = [
    ["Precipitation", (r) => precipStatus(r.precipAnomalyMm)],
    ["Soil wetness", (r) => soilStatus(r.soilMoisturePctile)],
    ["Vegetation", (r) => ndviStatus(r.ndviAnomaly)],
  ];

  return (
    <section className={`timeline panel ${floating ? "" : "static"}`}>
      <div className="timeline-head">
        <h2>Drought development and recovery timeline</h2>
        {onHide && <button className="timeline-hide" type="button" onClick={onHide} aria-expanded={true}>Hide timeline</button>}
      </div>
      <div className="controls">
        <button onClick={() => setPlaying((p) => !p)}>{playing ? "Pause" : "Play"}</button>
        <span>{region.records[0].month}</span>
        <input type="range" min={0} max={last} value={index} aria-label="Month" onChange={(e) => onChange(+e.target.value)} />
        <span>{region.records[last].month}</span>
        <strong>{current?.month}</strong>
      </div>
      <div className="strips">
        {rows.map(([name, fn]) => (
          <div className="strip" key={name}>
            <span>{name}</span>
            {region.records.map((r, i) => {
              const s = fn(r);
              return <i key={r.month} className={`cell ${s} ${i === index ? "now" : ""}`} title={`${r.month}: ${WORDS[s]}`} aria-label={`${name} ${r.month} ${WORDS[s]}`}>{GLYPH[s]}</i>;
            })}
          </div>
        ))}
      </div>
      <p className="summary"><b>Summary:</b> {buildSummary(region.records, index)}</p>
    </section>
  );
}
