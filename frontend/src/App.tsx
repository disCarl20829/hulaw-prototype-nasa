import { useState } from "react";
import GlobeMap from "./components/GlobeMap";
import LayerPanel from "./components/LayerPanel";
import RegionPanel from "./components/RegionPanel";
import Timeline from "./components/Timeline";
import { philippines } from "./data/sampleRegion";
import type { LayerKey } from "./types";

export default function App() {
  const region = philippines; // TODO: load from GET /api/areas/{id} + /api/indicators
  const [index, setIndex] = useState(region.records.length - 1);
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ combined: true, precip: true, soil: false, ndvi: true });

  return (
    <div className="app">
      <header>
        <h1>Hulaw <span>Global Drought Intelligence</span></h1>
        <nav aria-label="Main"><a href="#">Dashboard</a><a href="#" aria-current="page">Map explorer</a><a href="#">Analytics</a><a href="#">Reports</a></nav>
      </header>
      <main>
        <GlobeMap region={region} layers={layers} />
        <div className="left">
          <input className="panel search" type="search" placeholder="Search region" aria-label="Search region" />
          <LayerPanel layers={layers} onToggle={(k) => setLayers((l) => ({ ...l, [k]: !l[k] }))} />
          <div className="panel legend" aria-label="Drought severity legend"><b>Drought severity</b><div className="ramp" /><span>Extreme drought</span><span>Excess wetness</span></div>
        </div>
        <RegionPanel region={region} upTo={index} />
        <Timeline region={region} index={index} onChange={setIndex} />
      </main>
      <footer>© Hulaw project team · Data: NASA GPM, SMAP, MODIS · Not an official drought warning</footer>
    </div>
  );
}
