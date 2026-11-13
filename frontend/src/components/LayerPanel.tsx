import type { LayerKey } from "../types";

const LABELS: Record<LayerKey, string> = {
  combined: "Combined drought index", precip: "Precipitation anomaly",
  soil: "Soil moisture", ndvi: "Vegetation health",
};
interface Props { layers: Record<LayerKey, boolean>; onToggle: (k: LayerKey) => void }

export default function LayerPanel({ layers, onToggle }: Props) {
  return (
    <fieldset className="panel layers">
      <legend>Active layer</legend>
      {(Object.keys(LABELS) as LayerKey[]).map((k) => (
        <label key={k}><input type="checkbox" checked={layers[k]} onChange={() => onToggle(k)} /> {LABELS[k]}</label>
      ))}
      <p className="note">Combined index is experimental until validated.</p>
    </fieldset>
  );
}
