import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import type { LayerKey, Region } from "../types";
import { COUNTRY_NAMES, countryScore, scoreColor } from "../data/severity";

interface Props { region: Region; layers: Record<LayerKey, boolean>; index: number }

// Label anchor points (lon, lat) for the countries we shade.
const LABEL_AT: Record<string, [number, number]> = {
  PHL: [122.5, 12.8], VNM: [106.3, 15.2], THA: [101, 15.5], KHM: [104.9, 12.7], LAO: [103.9, 19.2], MMR: [96.5, 21],
  MYS: [102, 4.2], IDN: [113, -1.5], CHN: [104, 34], TWN: [121, 23.8], IND: [79, 22], BGD: [90.3, 23.9], AUS: [134, -25],
};

export default function GlobeMap({ region, layers, index }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer>();
  const source = useRef<Cesium.GeoJsonDataSource>();

  useEffect(() => {
    const v = new Cesium.Viewer(el.current!, {
      // Bundled low-res base layer: stays visible if the online imagery fails to load.
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"))),
      baseLayerPicker: false, geocoder: false, homeButton: false, timeline: false, animation: false,
      sceneModePicker: false, navigationHelpButton: false, fullscreenButton: false, infoBox: false, selectionIndicator: false,
      creditContainer: document.getElementById("cesium-credits") ?? undefined,
    });

    // High-detail satellite imagery (Esri World Imagery; attribution is shown in the footer).
    const esri = v.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
      url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      maximumLevel: 12,
      credit: "Imagery © Esri, Maxar, Earthstar Geographics",
    }));
    esri.brightness = 0.85; esri.saturation = 0.9; esri.contrast = 1.05;

    const s = v.scene;
    s.backgroundColor = Cesium.Color.fromCssColorString("#070b10");
    s.globe.baseColor = Cesium.Color.fromCssColorString("#0d1a26");
    s.globe.showGroundAtmosphere = true;
    s.globe.maximumScreenSpaceError = 1.5;           // sharper tiles
    s.globe.enableLighting = false;
    if (s.skyAtmosphere) s.skyAtmosphere.show = true;
    s.postProcessStages.fxaa.enabled = true;
    v.resolutionScale = Math.min(window.devicePixelRatio, 2);
    s.screenSpaceCameraController.minimumZoomDistance = 150_000;

    v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(113, 10, 8_500_000), duration: 2 });
    viewer.current = v;

    Cesium.GeoJsonDataSource.load(`${import.meta.env.BASE_URL}data/countries.geojson`, {
      stroke: Cesium.Color.WHITE.withAlpha(0.55), strokeWidth: 1.2,
    }).then((ds) => { source.current = ds; v.dataSources.add(ds); paint(); });

    Object.entries(LABEL_AT).forEach(([iso, [lon, lat]]) => v.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat),
      label: {
        text: COUNTRY_NAMES[iso], font: iso === "PHL" ? "600 15px 'IBM Plex Sans', sans-serif" : "500 12px 'IBM Plex Sans', sans-serif",
        fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK.withAlpha(0.8), outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE, disableDepthTestDistance: Number.POSITIVE_INFINITY,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, iso === "PHL" ? 14_000_000 : 11_000_000),
      },
    }));
    return () => v.destroy();
    // eslint-disable-next-line
  }, []);

  const paint = () => {
    const ds = source.current; if (!ds) return;
    ds.entities.values.forEach((e) => {
      const iso = e.properties?.iso?.getValue();
      const sc = countryScore(iso, index, region, layers);
      if (!e.polygon) return;
      e.polygon.material = new Cesium.ColorMaterialProperty(
        sc === null ? Cesium.Color.TRANSPARENT : Cesium.Color.fromCssColorString(scoreColor(sc)).withAlpha(iso === "PHL" ? 0.62 : 0.45));
    });
  };
  useEffect(paint, [region, layers, index]);

  return <div ref={el} className="globe" role="img" aria-label="3D satellite globe with country outlines shaded by illustrative drought severity" />;
}
