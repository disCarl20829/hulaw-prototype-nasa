import { useEffect, useState } from "react";
import GlobeMap from "./components/GlobeMap";
import type { AreaSelection } from "./components/GlobeMap";
import HulawAssistant from "./components/HulawAssistant";
import LayerPanel from "./components/LayerPanel";
import RegionPanel from "./components/RegionPanel";
import Timeline from "./components/Timeline";
import DateRangeControls from "./components/DateRangeControls";
import Dashboard from "./views/Dashboard";
import Analytics from "./views/Analytics";
import Reports from "./views/Reports";
import TimelineView from "./views/TimelineView";
import { useOverview, type DataLocation } from "./hooks/useOverview";
import { ROUTES, useHashRoute } from "./hooks/useHashRoute";
import { resolvePeriod } from "./services/hulaw-api";
import type { DataQuery, LayerKey } from "./types";

// Data is read at one point. With no area selected, this reference point is used.
// Central Luzon (Nueva Ecija) is an agricultural area and the project's pilot location.
const DEFAULT_LOCATION: DataLocation = { id: "ph-default", name: "Philippines · Central Luzon reference point", latitude: 15.7, longitude: 120.9 };

export default function App() {
  const route = useHashRoute();
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ combined: true, precip: true, soil: false, ndvi: true });
  const [selectedArea, setSelectedArea] = useState<AreaSelection | null>(null);
  const [showTimeline, setShowTimeline] = useState(false);

  // The selected area's center point drives every data request.
  const location: DataLocation = selectedArea?.center
    ? { id: selectedArea.code, name: selectedArea.name, latitude: selectedArea.center.latitude, longitude: selectedArea.center.longitude }
    : DEFAULT_LOCATION;
  const [query, setQuery] = useState<DataQuery>({}); // period and baseline chosen in the controls
  const { region, mood, status, error, reload } = useOverview(location, query);

  const last = region.records.length - 1;
  const [index, setIndex] = useState(last);
  useEffect(() => { setIndex(last); }, [region, last]); // show the latest month whenever new data arrives
  const safeIndex = Math.min(Math.max(index, 0), last);
  const isDefaultPeriod = !query.endMonth && query.baselineStart == null;
  const dateControls = <DateRangeControls applied={region.period ?? resolvePeriod(query)} isDefault={isDefaultPeriod} busy={status === "loading"} onApply={setQuery} />;

  const banner = status === "loading"
    ? <div className="data-banner loading" role="status"><span className="spinner" aria-hidden="true" />Loading NASA data for {location.name}. The first load for a location can take up to a minute.</div>
    : status === "error"
      ? <div className="data-banner error" role="alert"><span><b>Data could not be loaded.</b> {error}</span><button type="button" onClick={() => reload()}>Retry</button></div>
      : null;

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="brand-logo"><img src={`${import.meta.env.BASE_URL}hulaw-logo.webp`} alt="Hulaw logo" /></span>
        </div>
        <nav aria-label="Main">
          {ROUTES.map((r) => <a key={r.id} href={`#/${r.id}`} aria-current={route === r.id ? "page" : undefined}>{r.label}</a>)}
        </nav>
      </header>
      <main className={route === "map" ? `map-page ${showTimeline ? "timeline-open" : ""}` : "scroll-page"}>
        {banner}
        {route === "map" && (<>
          <GlobeMap region={region} layers={layers} index={safeIndex} query={query} selectedArea={selectedArea} onAreaSelect={setSelectedArea} />
          <div className="left">
            <div className="panel map-intro"><strong>Philippines drought map</strong><span>Explore regions, provinces, cities and municipalities</span></div>
            <LayerPanel layers={layers} onToggle={(k) => setLayers((l) => ({ ...l, [k]: !l[k] }))} />
            {dateControls}
            {selectedArea && <div className="panel selected-country">
              <div><span className="note">Selected {selectedArea.level}</span><strong>{selectedArea.name}</strong><span className="note">PSGC {selectedArea.code} · highlighted</span></div>
              <button type="button" onClick={() => setSelectedArea(null)}>Clear</button>
            </div>}
          </div>
          <RegionPanel region={region} upTo={safeIndex} selectedArea={selectedArea} status={status} />
          {showTimeline
            ? <Timeline region={region} index={safeIndex} onChange={setIndex} onHide={() => setShowTimeline(false)} />
            : <button className="timeline-toggle" type="button" onClick={() => setShowTimeline(true)} aria-expanded={false}>Show drought development and recovery timeline</button>}
        </>)}
        {route === "dashboard" && <Dashboard region={region} index={safeIndex} />}
        {route === "analytics" && <Analytics region={region} index={safeIndex} dateControls={dateControls} />}
        {route === "reports" && <Reports region={region} index={safeIndex} dateControls={dateControls} selectedArea={selectedArea} status={status} />}
        {route === "timeline" && <TimelineView region={region} index={safeIndex} onChange={setIndex} dateControls={dateControls} />}
      </main>
      <HulawAssistant mood={mood} location={location} />
      <footer><span>© Hulaw project team · Data: NASA POWER, MODIS · Not an official drought warning</span><span id="cesium-credits" /></footer>
    </div>
  );
}
