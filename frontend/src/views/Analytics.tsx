import type { ReactNode } from "react";
import type { Region } from "../types";
import RegionPanel from "../components/RegionPanel";
import { fmt, fmtSigned, ndviStatus, precipStatus, soilStatus, THRESHOLDS } from "../utils/analysis";

const G = { below: "▼", normal: "•", above: "▲", nodata: "–" };

export default function Analytics({ region, index, dateControls }: { region: Region; index: number; dateControls?: ReactNode }) {
  return (
    <div className="page analytics">
      <h2>Regional analysis: {region.name}</h2>
      <p className="lead">Aligned rainfall, soil wetness and vegetation charts, each against its own baseline. Showing months up to {region.records[index]?.month}.</p>
      {dateControls}
      <div className="two wide">
        <RegionPanel region={region} upTo={index} tall />
        <div>
          <div className="panel"><h3>Indicator table</h3><div className="scroll"><table><thead><tr><th>Month</th><th>Rain anomaly (mm)</th><th>Soil wetness (pctile)</th><th>NDVI anomaly</th></tr></thead><tbody>
            {region.records.slice(0, index + 1).map((r) => <tr key={r.month}><td>{r.month}</td>
              <td>{G[precipStatus(r.precipAnomalyMm)]} {fmtSigned(r.precipAnomalyMm, 1)}</td><td>{G[soilStatus(r.soilMoisturePctile)]} {fmt(r.soilMoisturePctile, 0)}</td><td>{G[ndviStatus(r.ndviAnomaly)]} {fmtSigned(r.ndviAnomaly, 3)}</td></tr>)}
          </tbody></table></div></div>
          <div className="panel"><h3>Thresholds used</h3><ul><li>Rainfall: {THRESHOLDS.precip}</li><li>Soil: {THRESHOLDS.soil}</li><li>Vegetation: {THRESHOLDS.ndvi}</li></ul></div>
          <div className="panel"><h3>Agricultural exposure</h3><p>Not enabled. This overlay needs a validated cropland dataset with known source, date and accuracy. When connected, overlap will be reported as “agricultural area exposed to observed anomaly”, not confirmed crop damage.</p></div>
        </div>
      </div>
    </div>
  );
}
