import type { Region } from "../types";
import RegionPanel from "../components/RegionPanel";
import { ndviStatus, precipStatus, soilStatus, THRESHOLDS } from "../utils/analysis";

const G = { below: "▼", normal: "•", above: "▲" };

export default function Analytics({ region, index }: { region: Region; index: number }) {
  return (
    <div className="page analytics">
      <h2>Regional analysis: {region.name}</h2>
      <p className="lead">Aligned rainfall, soil moisture and vegetation charts, each against its own baseline. Showing months up to {region.records[index].month}.</p>
      <div className="two wide">
        <RegionPanel region={region} upTo={index} tall />
        <div>
          <div className="panel"><h3>Indicator table</h3><div className="scroll"><table><thead><tr><th>Month</th><th>Rain (mm)</th><th>Soil (pctile)</th><th>NDVI</th></tr></thead><tbody>
            {region.records.slice(0, index + 1).map((r) => <tr key={r.month}><td>{r.month}</td>
              <td>{G[precipStatus(r.precipAnomalyMm)]} {r.precipAnomalyMm}</td><td>{G[soilStatus(r.soilMoisturePctile)]} {r.soilMoisturePctile}</td><td>{G[ndviStatus(r.ndviAnomaly)]} {r.ndviAnomaly}</td></tr>)}
          </tbody></table></div></div>
          <div className="panel"><h3>Thresholds used</h3><ul><li>Rainfall: {THRESHOLDS.precip}</li><li>Soil: {THRESHOLDS.soil}</li><li>Vegetation: {THRESHOLDS.ndvi}</li></ul></div>
          <div className="panel"><h3>Agricultural exposure</h3><p>Not enabled. This overlay needs a validated cropland dataset with known source, date and accuracy. When connected, overlap will be reported as “agricultural area exposed to observed anomaly”, not confirmed crop damage.</p></div>
        </div>
      </div>
    </div>
  );
}
