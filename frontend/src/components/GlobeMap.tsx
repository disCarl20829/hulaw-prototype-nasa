import { useEffect, useRef, useState } from "react";
import * as Cesium from "cesium";
import type { DataQuery, LayerKey, Region } from "../types";
import { scoreColor } from "../data/severity";
import { fmt, fmtSigned, precipScore, soilScore } from "../utils/analysis";
import { fetchAreaSeries, type AreaSeries } from "../services/hulaw-api";

export interface AreaSelection { code: string; name: string; level: "Region" | "Province" | "City / Municipality"; parentCode?: string; center?: { latitude: number; longitude: number } }
interface Props { region: Region; layers: Record<LayerKey, boolean>; index: number; query: DataQuery; selectedArea: AreaSelection | null; onAreaSelect: (area: AreaSelection | null) => void }
// Pinned to one commit so an upstream change to the boundary files cannot break the map.
const DATA = "https://raw.githubusercontent.com/faeldon/philippines-json-maps/680e32e62baeccbcd8845d3b1387bc67c1baf78a/latest/geojson";
const property = (entity: Cesium.Entity, key: string) => entity.properties?.[key]?.getValue() as string | number | undefined;
const cleanName = (value: unknown) => String(value ?? "Selected area").replace(/\s+/g, " ").trim();
const GOLD = Cesium.Color.fromCssColorString("#ffd45e");
const NEUTRAL = Cesium.Color.fromCssColorString("#2c8990").withAlpha(0.16); // area without data (yet)
/** PSGC code of a boundary polygon at whatever administrative level it belongs to. */
const entityCode = (entity: Cesium.Entity) => String(property(entity, "adm3_psgc") ?? property(entity, "adm2_psgc") ?? property(entity, "adm1_psgc") ?? entity.id ?? "");
type AreaStatus = "idle" | "loading" | "ready" | "error";

/** Map colour score for one area: rainfall and soil wetness only (vegetation is not available per area). */
function areaScore(series: AreaSeries | undefined, index: number, layers: Record<LayerKey, boolean>): number | null {
  if (!series) return null;
  const parts: number[] = [];
  const add = (score: number | null) => { if (score != null) parts.push(score); };
  if (layers.combined || layers.precip) add(precipScore(series.rainfall_anomaly_mm[index]));
  if (layers.combined || layers.soil) add(soilScore(series.soil_percentile[index]));
  return parts.length ? parts.reduce((a, b) => a + b, 0) / parts.length : null;
}

export default function GlobeMap({ region, layers, index, query, selectedArea, onAreaSelect }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer>();
  const sources = useRef<Cesium.GeoJsonDataSource[]>([]);
  const resetRef = useRef<() => void>(() => {});
  const currentLevel = useRef<AreaSelection["level"]>("Region");
  const lastHoverRef = useRef<{ id: string; x: number; y: number } | null>(null);
  // Per-area rainfall and soil series for the boundaries currently on the map, keyed by PSGC code.
  const areaData = useRef(new Map<string, AreaSeries>());
  const areaRequest = useRef(0);
  const [areaStatus, setAreaStatus] = useState<AreaStatus>("idle");
  const [areaFailed, setAreaFailed] = useState(0);
  // The map is created once, so its callbacks read the latest props through refs.
  const live = useRef({ index, layers, query, selectedArea });
  live.current = { index, layers, query, selectedArea };

  const recolor = () => {
    const { index: month, layers: active, selectedArea: selected } = live.current;
    sources.current.forEach((source) => source.entities.values.forEach((entity) => {
      if (!entity.polygon) return;
      const code = entityCode(entity);
      if (selected && code === selected.code) return; // keep the gold highlight
      const score = areaScore(areaData.current.get(code), month, active);
      entity.polygon.material = new Cesium.ColorMaterialProperty(score == null ? NEUTRAL : Cesium.Color.fromCssColorString(scoreColor(score)).withAlpha(0.5));
    }));
    viewer.current?.scene.requestRender();
  };

  /** Ask the backend for every visible boundary's own series, then colour each area by its own value. */
  const loadAreaData = async () => {
    const centers = new Map<string, { latitude: number; longitude: number; radius: number }>();
    sources.current.forEach((source) => source.entities.values.forEach((entity) => {
      const positions = entity.polygon?.hierarchy?.getValue(Cesium.JulianDate.now())?.positions;
      if (!positions?.length) return;
      const sphere = Cesium.BoundingSphere.fromPoints(positions);
      const carto = Cesium.Cartographic.fromCartesian(sphere.center);
      const code = entityCode(entity);
      // Areas made of several islands: use the largest piece.
      if (!carto || !code || (centers.get(code)?.radius ?? -1) >= sphere.radius) return;
      centers.set(code, { latitude: Cesium.Math.toDegrees(carto.latitude), longitude: Cesium.Math.toDegrees(carto.longitude), radius: sphere.radius });
    }));
    const points = [...centers].slice(0, 150).map(([id, c]) => ({ id, latitude: c.latitude, longitude: c.longitude }));
    const request = ++areaRequest.current;
    if (!points.length) return;
    setAreaStatus("loading");
    try {
      const response = await fetchAreaSeries(points, live.current.query);
      if (request !== areaRequest.current) return; // a newer request replaced this one
      areaData.current = new Map(response.areas.filter((a) => a.status === "ok").map((a) => [a.id, a]));
      setAreaFailed(response.failed);
      setAreaStatus(areaData.current.size ? "ready" : "error");
    } catch {
      if (request !== areaRequest.current) return;
      areaData.current = new Map();
      setAreaStatus("error");
    }
    recolor();
  };
  const loadAreaRef = useRef(loadAreaData);
  loadAreaRef.current = loadAreaData;
  const [hoverInfo, setHoverInfo] = useState<{ name: string; level: AreaSelection["level"]; code: string; x: number; y: number } | null>(null);

  useEffect(() => {
    const v = new Cesium.Viewer(el.current!, {
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"))),
      baseLayerPicker: false, geocoder: false, homeButton: false, timeline: false, animation: false,
      sceneModePicker: false, navigationHelpButton: false, fullscreenButton: false, infoBox: false, selectionIndicator: false,
      creditContainer: document.getElementById("cesium-credits") ?? undefined,
      requestRenderMode: true, maximumRenderTimeChange: Infinity,
      scene3DOnly: true, orderIndependentTranslucency: false,
    });
    const imagery = v.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
      url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", maximumLevel: 13,
      credit: "Imagery © Esri, Maxar, Earthstar Geographics",
    }));
    imagery.brightness = 0.85; imagery.saturation = 0.9; imagery.contrast = 1.05;
    v.scene.backgroundColor = Cesium.Color.fromCssColorString("#070b10");
    v.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0d1a26");
    v.scene.globe.showGroundAtmosphere = true; v.scene.globe.maximumScreenSpaceError = window.innerWidth < 768 ? 5 : 4; v.scene.globe.tileCacheSize = window.innerWidth < 768 ? 50 : 80;
    v.scene.globe.enableLighting = false; if (v.scene.skyAtmosphere) v.scene.skyAtmosphere.show = true;
    v.scene.postProcessStages.fxaa.enabled = false;
    // Cap GPU load on phones/tablets; Cesium renders on demand rather than continuously.
    v.resolutionScale = Math.min(window.devicePixelRatio || 1, window.innerWidth < 768 ? 0.9 : 1.15);
    v.scene.requestRender();
    const controller = v.scene.screenSpaceCameraController;
    controller.minimumZoomDistance = 120_000;
    controller.maximumZoomDistance = 7_500_000;
    // Allow drag-to-rotate, but keep the camera focused on the Philippine area.
    controller.enableRotate = true;
    controller.enableTranslate = true;
    controller.enableTilt = true;
    v.camera.moveEnd.addEventListener(() => {
      const view = v.camera.computeViewRectangle(v.scene.globe.ellipsoid);
      if (!view) return;
      const centerLon = Cesium.Math.toDegrees((view.west + view.east) / 2);
      const centerLat = Cesium.Math.toDegrees((view.south + view.north) / 2);
      if (centerLon < 112 || centerLon > 132 || centerLat < 1 || centerLat > 25) {
        const height = Math.max(500_000, v.camera.positionCartographic.height);
        v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(122, 12.2, height), duration: 0.65 });
      }
    });
    v.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(122, 12.2, 5_600_000) });
    viewer.current = v;

    const addBoundary = async (url: string, level: AreaSelection["level"]) => {
      try {
        const ds = await Cesium.GeoJsonDataSource.load(url, { stroke: Cesium.Color.fromCssColorString("#c8e5ed").withAlpha(0.95), strokeWidth: 1.7, fill: NEUTRAL });
        // The viewer can be torn down while the boundary file is still downloading (React dev double-mount, page change).
        if (v.isDestroyed()) return null;
        sources.current.push(ds); v.dataSources.add(ds);
        ds.entities.values.forEach((entity) => {
          if (!entity.polygon) return;
          entity.polygon.material = new Cesium.ColorMaterialProperty(NEUTRAL);
          entity.polygon.outline = new Cesium.ConstantProperty(true);
          entity.polygon.outlineColor = new Cesium.ConstantProperty(Cesium.Color.fromCssColorString("#d5edf1").withAlpha(0.95));
          const labelName = level === "Region" ? property(entity, "adm1_en") : level === "Province" ? property(entity, "adm2_en") : property(entity, "adm3_en");
          const hierarchy = entity.polygon.hierarchy?.getValue(Cesium.JulianDate.now());
          if (labelName && hierarchy?.positions?.length) {
            const sphere = Cesium.BoundingSphere.fromPoints(hierarchy.positions);
            entity.position = new Cesium.ConstantPositionProperty(sphere.center);
            entity.label = new Cesium.LabelGraphics({
              text: cleanName(labelName), font: level === "Region" ? "600 12px sans-serif" : "600 10px sans-serif",
              fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.fromCssColorString("#07131b"), outlineWidth: 3,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE, showBackground: true,
              backgroundColor: Cesium.Color.fromCssColorString("#07131b").withAlpha(0.72),
              backgroundPadding: new Cesium.Cartesian2(5, 3),
              // Keep the aerial view clean. Labels appear progressively as the user zooms in.
              distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, level === "Region" ? 2_400_000 : level === "Province" ? 1_150_000 : 480_000),
              scaleByDistance: new Cesium.NearFarScalar(180_000, 1.0, 2_400_000, 0.65),
              disableDepthTestDistance: 100_000,
            });
          }
        });
        v.scene.requestRender();
        void loadAreaRef.current(); // colour the new boundaries by their own data
        return ds;
      } catch (error) { if (!v.isDestroyed()) console.error("Unable to load Philippine administrative boundaries", error); return null; }
    };
    const resetToRegions = async () => {
      sources.current.forEach((old) => v.dataSources.remove(old, true)); sources.current = [];
      currentLevel.current = "Region";
      await addBoundary(`${DATA}/country/lowres/country.0.001.json`, "Region");
    };
    resetRef.current = () => { void resetToRegions(); };
    void resetToRegions();

    const clickHandler = new Cesium.ScreenSpaceEventHandler(v.scene.canvas);
    clickHandler.setInputAction((movement: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
      const picked = v.scene.pick(movement.endPosition);
      const entity = picked?.id as Cesium.Entity | undefined;
      if (!entity?.polygon) {
        if (lastHoverRef.current) { lastHoverRef.current = null; setHoverInfo(null); }
        return;
      }
      const hoverId = String(entity.id ?? entity.name ?? "");
      const previous = lastHoverRef.current;
      if (previous?.id === hoverId && Math.abs(previous.x - movement.endPosition.x) < 10 && Math.abs(previous.y - movement.endPosition.y) < 10) return;
      const adm3 = property(entity, "adm3_psgc") !== undefined;
      const adm2 = property(entity, "adm2_psgc") !== undefined;
      const level: AreaSelection["level"] = adm3 ? "City / Municipality" : adm2 ? "Province" : "Region";
      const code = String(property(entity, adm3 ? "adm3_psgc" : adm2 ? "adm2_psgc" : "adm1_psgc") ?? entity.id ?? "");
      const name = cleanName(property(entity, adm3 ? "adm3_en" : adm2 ? "adm2_en" : "adm1_en") ?? property(entity, "name") ?? entity.name);
      lastHoverRef.current = { id: hoverId, x: movement.endPosition.x, y: movement.endPosition.y };
      setHoverInfo({ name, level, code, x: movement.endPosition.x, y: movement.endPosition.y });
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
    clickHandler.setInputAction(async (movement: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = v.scene.pick(movement.position);
      const entity = picked?.id as Cesium.Entity | undefined;
      if (!entity?.polygon) return;
      lastHoverRef.current = null;
      setHoverInfo(null);
      const adm3 = property(entity, "adm3_psgc") !== undefined;
      const adm2 = property(entity, "adm2_psgc") !== undefined;
      const level: AreaSelection["level"] = adm3 ? "City / Municipality" : adm2 ? "Province" : "Region";
      const code = String(property(entity, adm3 ? "adm3_psgc" : adm2 ? "adm2_psgc" : "adm1_psgc") ?? entity.id ?? "");
      const name = cleanName(property(entity, adm3 ? "adm3_en" : adm2 ? "adm2_en" : "adm1_en") ?? property(entity, "name") ?? entity.name);
      const parentCode = String(property(entity, adm3 ? "adm2_psgc" : "adm1_psgc") ?? "");
      // Center point of the clicked polygon; the backend reads its data at this point.
      let center: AreaSelection["center"];
      const clickedPositions = entity.polygon.hierarchy?.getValue(Cesium.JulianDate.now())?.positions;
      if (clickedPositions?.length) {
        const carto = Cesium.Cartographic.fromCartesian(Cesium.BoundingSphere.fromPoints(clickedPositions).center);
        if (carto) center = { latitude: Cesium.Math.toDegrees(carto.latitude), longitude: Cesium.Math.toDegrees(carto.longitude) };
      }
      onAreaSelect({ code, name, level, parentCode, center });
      currentLevel.current = level === "Region" ? "Province" : level === "Province" ? "City / Municipality" : "City / Municipality";
      // Replace the prior administrative layer so only the current level remains selectable.
      sources.current.forEach((old) => v.dataSources.remove(old, true)); sources.current = [];
      entity.polygon.material = new Cesium.ColorMaterialProperty(GOLD.withAlpha(0.52));
      entity.polygon.outlineColor = new Cesium.ConstantProperty(GOLD);
      entity.polygon.outlineWidth = new Cesium.ConstantProperty(4);
      await v.flyTo(entity, { duration: 1.15, offset: new Cesium.HeadingPitchRange(0, -Cesium.Math.PI_OVER_FOUR, level === "Region" ? 850_000 : level === "Province" ? 390_000 : 150_000) });
      if (level === "Region") await addBoundary(`${DATA}/regions/lowres/provdists-region-${code}.0.001.json`, "Province");
      else if (level === "Province") await addBoundary(`${DATA}/provdists/lowres/municities-provdist-${code}.0.001.json`, "City / Municipality");
      v.scene.requestRender();
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => { clickHandler.destroy(); v.destroy(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Month, layer or selection changed: recolour from the data already loaded.
  useEffect(() => { recolor(); }, [index, layers, selectedArea]); // eslint-disable-line react-hooks/exhaustive-deps
  // Period or baseline changed: the per-area data must be fetched again.
  useEffect(() => { if (sources.current.length) void loadAreaData(); }, [query]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!viewer.current) return;
    if (!selectedArea) { if (currentLevel.current !== "Region") resetRef.current(); return; }
    const key = selectedArea.level === "Region" ? "adm1_psgc" : selectedArea.level === "Province" ? "adm2_psgc" : "adm3_psgc";
    const entity = sources.current.flatMap((s) => s.entities.values).find((e) => String(property(e, key) ?? e.id) === selectedArea.code);
    if (entity?.polygon) {
      entity.polygon.material = new Cesium.ColorMaterialProperty(GOLD.withAlpha(0.52));
      entity.polygon.outlineColor = new Cesium.ConstantProperty(GOLD);
      entity.polygon.outlineWidth = new Cesium.ConstantProperty(4);
    }
  }, [selectedArea]);


  return <>
    <div className="map-severity-legend" aria-label="Drought severity legend">
      <strong>Drought severity index</strong>
      <div className="map-severity-ramp" />
      <div><span>Extreme drought</span><span>Near normal / wet</span></div>
      <small>{areaStatus === "loading" ? "Loading each area’s rainfall and soil wetness…"
        : areaStatus === "error" ? "Per-area data could not be loaded, so the boundaries are not coloured."
        : `Each area is coloured by its own rainfall and soil wetness, read near its center. Vegetation is not included in map colours.${areaFailed ? ` ${areaFailed} area(s) could not be loaded.` : ""}`}</small>
    </div>
    <div ref={el} className="globe" role="application" aria-label="Interactive 3D globe focused on the Philippines. Drag to rotate, select a labeled region, province, city or municipality, and hover for a data summary." />
    {hoverInfo && <div className="globe-hover-card" style={{ left: Math.min(hoverInfo.x + 16, window.innerWidth - 290), top: Math.min(hoverInfo.y + 16, window.innerHeight - 190) }}>
      <div className="hover-card-top"><strong>{hoverInfo.name}</strong><span>{hoverInfo.level}</span></div>
      <div className="hover-card-code">PSGC {hoverInfo.code}</div>
      {(() => {
        const series = areaData.current.get(hoverInfo.code);
        const month = region.records[index]?.month;
        return series
          ? <><div className="hover-card-metrics"><div><span>Rainfall anomaly</span><b>{fmtSigned(series.rainfall_anomaly_mm[index], 1, " mm")}</b></div><div><span>Soil wetness percentile</span><b>{fmt(series.soil_percentile[index], 0, "%")}</b></div></div>
            <p>{month} · read near this area’s center. Click to load its full charts, including vegetation.</p></>
          : <p>{areaStatus === "loading" ? "Loading this area’s data…" : "No data loaded for this area. Click to load its charts."}</p>;
      })()}
    </div>}
  </>;
}
