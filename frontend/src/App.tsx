import { useState } from "react";
import GlobeMap from "./components/GlobeMap";
import LayerPanel from "./components/LayerPanel";
import RegionPanel from "./components/RegionPanel";
import Timeline from "./components/Timeline";
import Dashboard from "./views/Dashboard";
import Analytics from "./views/Analytics";
import Reports from "./views/Reports";
import TimelineView from "./views/TimelineView";
import { philippines } from "./data/sampleRegion";
import { ROUTES, useHashRoute } from "./hooks/useHashRoute";
import type { LayerKey } from "./types";

export default function App() {
  const region = philippines; // Static local sample data for the frontend prototype.
  const route = useHashRoute();
  const [index, setIndex] = useState(region.records.length - 1);
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ combined: true, precip: true, soil: false, ndvi: true });
  const [selectedCountry, setSelectedCountry] = useState<{ iso: string; name: string } | null>(null);

  return (
    <div className="app">
      <header>
        <div className="brand">
          <img src={`${import.meta.env.BASE_URL}hulaw-logo.webp`} alt="Hulaw logo" />
          <div><h1>Hulaw</h1><span>Global Drought Intelligence</span></div>
        </div>
        <nav aria-label="Main">
          {ROUTES.map((r) => <a key={r.id} href={`#/${r.id}`} aria-current={route === r.id ? "page" : undefined}>{r.label}</a>)}
        </nav>
      </header>
      <main className={route === "map" ? "map-page" : "scroll-page"}>
        {route === "map" && (<>
          <GlobeMap region={region} layers={layers} index={index} selectedIso={selectedCountry?.iso ?? null} onCountrySelect={(iso, name) => setSelectedCountry(iso && name ? { iso, name } : null)} />
          <div className="left">
            <input className="panel search" type="search" placeholder="Search region" aria-label="Search region" />
            <LayerPanel layers={layers} onToggle={(k) => setLayers((l) => ({ ...l, [k]: !l[k] }))} />
            {selectedCountry && <div className="panel selected-country">
              <div><span className="note">Selected country</span><strong>{selectedCountry.name}</strong><span className="note">{selectedCountry.iso} · highlighted on globe</span></div>
              <button type="button" onClick={() => setSelectedCountry(null)}>Clear</button>
            </div>}
            <div className="panel legend" aria-label="Drought severity legend"><b>Drought severity index</b><div className="ramp" /><span>Extreme drought</span><span>Excess wetness</span></div>
          </div>
          <RegionPanel region={region} upTo={index} />
          <Timeline region={region} index={index} onChange={setIndex} />
        </>)}
        {route === "dashboard" && <Dashboard region={region} index={index} />}
        {route === "analytics" && <Analytics region={region} index={index} />}
        {route === "reports" && <Reports region={region} index={index} />}
        {route === "timeline" && <TimelineView region={region} index={index} onChange={setIndex} />}
      </main>
      <footer><span>© Hulaw project team · Data: NASA GPM, SMAP, MODIS · Not an official drought warning</span><span id="cesium-credits" /></footer>
    </div>
  );
}
