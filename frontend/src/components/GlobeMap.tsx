import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import type { LayerKey, Region } from "../types";
import { hotspots } from "../data/sampleRegion";

interface Props { region: Region; layers: Record<LayerKey, boolean> }

// Offline imagery bundled with Cesium: no Ion token needed.
export default function GlobeMap({ region, layers }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer>();

  useEffect(() => {
    const v = new Cesium.Viewer(el.current!, {
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"))),
      baseLayerPicker: false, geocoder: false, homeButton: false, timeline: false,
      animation: false, sceneModePicker: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: false, selectionIndicator: false,
    });
    v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(112, 12, 9_000_000), duration: 1.5 });
    viewer.current = v;
    return () => v.destroy();
  }, []);

  useEffect(() => {
    const v = viewer.current; if (!v) return;
    v.entities.removeAll();
    const [w, s, e, n] = region.bbox;
    v.entities.add({ rectangle: { coordinates: Cesium.Rectangle.fromDegrees(w, s, e, n),
      material: Cesium.Color.WHITE.withAlpha(0.05), outline: true, outlineColor: Cesium.Color.WHITE } });
    if (layers.combined || layers.precip) {
      hotspots.forEach((h) => v.entities.add({
        position: Cesium.Cartesian3.fromDegrees(h.lon, h.lat),
        ellipse: { semiMajorAxis: h.radiusKm * 1000, semiMinorAxis: h.radiusKm * 1000,
          material: Cesium.Color.fromHsl(0.08 * (1 - h.severity), 0.95, 0.5, 0.55) },
      }));
    }
  }, [region, layers]);

  return <div ref={el} className="globe" role="img" aria-label="3D globe showing illustrative drought anomaly layers" />;
}
