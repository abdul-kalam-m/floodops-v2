import { useEffect, useRef } from "react";
import maplibregl, { type StyleSpecification } from "maplibre-gl";
import type { ExposureJson, FirstExposedMap, GeoJson } from "../types";
import { ASSET_COLORS, ASSET_STATUS_LABEL, EXPOSURE_FILL_COLOR, ROAD_COLORS } from "../lib/palette";

// Resilient raster basemap (Carto Positron), same choice as v1. Each tile is
// independent, so the app stays usable if the basemap is unreachable (§8.6).
const BASE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    basemap: {
      type: "raster",
      tiles: [
        "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "https://c.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors © CARTO",
    },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#eef0f2" } },
    { id: "basemap", type: "raster", source: "basemap" },
  ],
};

const EMPTY: GeoJson = { type: "FeatureCollection", features: [] };

export interface LayerVisibility {
  exposure: boolean;
  boundary: boolean;
  roads: boolean;
  assets: boolean;
}

interface Props {
  townSlug: string;
  townBbox: [number, number, number, number]; // [w, s, e, n]
  assetsGeo: GeoJson;
  roadsGeo: GeoJson;
  boundaryGeo: GeoJson | null;
  extentGeo: GeoJson | null;
  exposure: ExposureJson | null;
  firstExposed: FirstExposedMap;
  selectedAssetId: string | null;
  visibility: LayerVisibility;
  onSelectAsset: (id: string | null) => void;
}

interface AssetProps {
  id: string;
  name: string;
  category: string;
  ground_elev_ft: number;
  address?: string;
}

export default function MapView(props: Props) {
  const { townSlug, townBbox, assetsGeo, roadsGeo, boundaryGeo, extentGeo, exposure,
    firstExposed, selectedAssetId, visibility, onSelectAsset } = props;
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const readyRef = useRef(false);
  const prevTownRef = useRef<string | null>(null);
  const closedRoadIdsRef = useRef<Set<string>>(new Set());
  // Keep latest data in refs so the (once-created) map handlers read current values.
  const dataRef = useRef({ assetsGeo, exposure, firstExposed });
  dataRef.current = { assetsGeo, exposure, firstExposed };

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    // Construct with a plain center/zoom (v1's proven-reliable pattern), NOT `bounds` --
    // `bounds` at construction time needs MapLibre to compute a fitting zoom against the
    // container's CURRENT size, and if the container isn't laid out yet (0x0, common on
    // first mount before the flex layout settles), that computation can silently stall
    // and the map's `load` event never fires (confirmed via debug logging: the `load`
    // handler registers but never runs). fitBounds() is called explicitly below, after
    // the container is definitely sized, instead.
    const centerLon = (townBbox[0] + townBbox[2]) / 2;
    const centerLat = (townBbox[1] + townBbox[3]) / 2;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [centerLon, centerLat],
      zoom: 11,
      attributionControl: { compact: true },
      preserveDrawingBuffer: true, // allow canvas capture (case-study screenshots)
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");

    map.on("load", () => {
      map.addSource("exposure-extent", { type: "geojson", data: extentGeo ?? EMPTY });
      map.addSource("boundary", { type: "geojson", data: boundaryGeo ?? EMPTY });
      map.addSource("roads", { type: "geojson", data: roadsGeo, promoteId: "id" });
      map.addSource("assets", { type: "geojson", data: assetsGeo, promoteId: "id" });

      map.addLayer({
        id: "exposure-fill",
        type: "fill",
        source: "exposure-extent",
        paint: { "fill-color": EXPOSURE_FILL_COLOR, "fill-opacity": 0.45 },
      });
      map.addLayer({
        id: "exposure-outline",
        type: "line",
        source: "exposure-extent",
        paint: { "line-color": EXPOSURE_FILL_COLOR, "line-width": 1, "line-opacity": 0.8 },
      });

      map.addLayer({
        id: "boundary-line",
        type: "line",
        source: "boundary",
        paint: {
          "line-color": "#334155", "line-width": 2, "line-dasharray": [3, 2], "line-opacity": 0.8,
        },
      });

      map.addLayer({
        id: "roads-line",
        type: "line",
        source: "roads",
        layout: { "line-cap": "round" },
        paint: {
          "line-color": [
            "case",
            ["==", ["coalesce", ["feature-state", "status"], "open"], "closed"],
            ROAD_COLORS.closed,
            ROAD_COLORS.open,
          ],
          "line-width": [
            "interpolate", ["linear"], ["zoom"],
            12, ["case", ["get", "is_priority"], 2.2, 0.6],
            16, ["case", ["get", "is_priority"], 6, 2],
          ],
        },
      });

      map.addLayer({
        id: "assets-selected",
        type: "circle",
        source: "assets",
        filter: ["==", ["get", "id"], "__none__"],
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 10, 16, 15],
          "circle-color": "#2563eb",
          "circle-opacity": 0.25,
          "circle-stroke-color": "#2563eb",
          "circle-stroke-width": 2,
        },
      });

      map.addLayer({
        id: "assets-circle",
        type: "circle",
        source: "assets",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 5, 16, 9],
          "circle-color": [
            "match", ["coalesce", ["feature-state", "status"], "operational"],
            "exposed", ASSET_COLORS.exposed,
            "isolated", ASSET_COLORS.isolated,
            ASSET_COLORS.operational,
          ],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.5,
        },
      });

      map.fitBounds([[townBbox[0], townBbox[1]], [townBbox[2], townBbox[3]]], {
        padding: 40, duration: 0,
      });
      readyRef.current = true;
      prevTownRef.current = townSlug;
      applyExposure();
      applyVisibility();
      applySelection();
    });

    map.on("mouseenter", "assets-circle", () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", "assets-circle", () => (map.getCanvas().style.cursor = ""));
    map.on("click", "assets-circle", (e) => {
      const id = e.features?.[0]?.id;
      onSelectAsset(id != null ? String(id) : null);
    });
    map.on("click", (e) => {
      const hits = map.queryRenderedFeatures(e.point, { layers: ["assets-circle"] });
      if (hits.length === 0) onSelectAsset(null);
    });

    return () => {
      readyRef.current = false;
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sparse road-closure encoding (§13.2): only ids in exposure.roads are "closed"; every
  // other road id is implicitly open. Unlike v1 (every road listed every time), we must
  // explicitly clear the PREVIOUS level's closed set before applying the new one, or a
  // road closed at a higher level would stay red after dragging the slider back down.
  function applyExposure() {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const prevClosed = closedRoadIdsRef.current;
    const nextClosed = new Set(Object.keys(exposure?.roads ?? {}));
    for (const id of prevClosed) {
      if (!nextClosed.has(id)) map.setFeatureState({ source: "roads", id }, { status: "open" });
    }
    for (const id of nextClosed) {
      map.setFeatureState({ source: "roads", id }, { status: "closed" });
    }
    closedRoadIdsRef.current = nextClosed;

    for (const [id, a] of Object.entries(exposure?.assets ?? {})) {
      map.setFeatureState({ source: "assets", id }, { status: a.status });
    }
  }

  function applyVisibility() {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const set = (layer: string, on: boolean) =>
      map.getLayer(layer) && map.setLayoutProperty(layer, "visibility", on ? "visible" : "none");
    set("exposure-fill", visibility.exposure);
    set("exposure-outline", visibility.exposure);
    set("boundary-line", visibility.boundary);
    set("roads-line", visibility.roads);
    set("assets-circle", visibility.assets);
    set("assets-selected", visibility.assets);
  }

  function popupHTML(a: AssetProps): string {
    const { exposure: exp, firstExposed: fe } = dataRef.current;
    const status = exp?.assets[a.id]?.status ?? "operational";
    const color = ASSET_COLORS[status];
    const feLevel = fe[a.id];
    const cat = a.category.charAt(0).toUpperCase() + a.category.slice(1);
    return `
      <div style="font:13px system-ui, sans-serif; min-width:180px">
        <div style="font-weight:600; font-size:14px; margin-bottom:2px">${a.name}</div>
        <div style="color:#6b7280; margin-bottom:6px">${cat}${a.address ? " · " + a.address : ""}</div>
        <div style="display:inline-block; padding:1px 8px; border-radius:9999px; color:#fff;
             background:${color}; font-weight:600; margin-bottom:6px">${ASSET_STATUS_LABEL[status]}</div>
        <table style="width:100%; border-collapse:collapse">
          <tr><td style="color:#6b7280; padding:1px 0">Ground elev.</td>
              <td style="text-align:right; font-variant-numeric:tabular-nums">${a.ground_elev_ft.toFixed(1)} ft</td></tr>
          <tr><td style="color:#6b7280; padding:1px 0">First exposed at</td>
              <td style="text-align:right; font-variant-numeric:tabular-nums">${feLevel == null ? "—" : feLevel + " ft"}</td></tr>
        </table>
      </div>`;
  }

  function applySelection() {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    map.setFilter("assets-selected", ["==", ["get", "id"], selectedAssetId ?? "__none__"]);
    popupRef.current?.remove();
    popupRef.current = null;
    if (!selectedAssetId) return;
    const feat = dataRef.current.assetsGeo.features.find(
      (f) => (f.properties as { id?: string })?.id === selectedAssetId,
    );
    if (!feat) return;
    const coords = (feat.geometry as unknown as { coordinates: [number, number] }).coordinates;
    popupRef.current = new maplibregl.Popup({ offset: 12, closeButton: true, maxWidth: "260px" })
      .setLngLat(coords)
      .setHTML(popupHTML(feat.properties as unknown as AssetProps))
      .addTo(map);
    popupRef.current.on("close", () => {
      if (selectedAssetId) onSelectAsset(null);
    });
    map.easeTo({ center: coords, duration: 500 });
  }

  // Town switch: swap every source's data and re-fit bounds. Reset the closed-roads
  // tracker too -- it's per-town, a stale set from the previous town must not leak in.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    if (prevTownRef.current === townSlug) return;
    prevTownRef.current = townSlug;
    closedRoadIdsRef.current = new Set();
    (map.getSource("assets") as maplibregl.GeoJSONSource | undefined)?.setData(assetsGeo);
    (map.getSource("roads") as maplibregl.GeoJSONSource | undefined)?.setData(roadsGeo);
    (map.getSource("boundary") as maplibregl.GeoJSONSource | undefined)?.setData(boundaryGeo ?? EMPTY);
    (map.getSource("exposure-extent") as maplibregl.GeoJSONSource | undefined)?.setData(extentGeo ?? EMPTY);
    map.fitBounds([[townBbox[0], townBbox[1]], [townBbox[2], townBbox[3]]], {
      padding: 40, duration: 400,
    });
    applyExposure();
    applySelection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [townSlug]);

  // Same-town data refresh (initial load completing after the map itself is ready, or
  // an assets/roads/boundary array identity change that isn't a town switch).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current || prevTownRef.current !== townSlug) return;
    (map.getSource("assets") as maplibregl.GeoJSONSource | undefined)?.setData(assetsGeo);
    (map.getSource("roads") as maplibregl.GeoJSONSource | undefined)?.setData(roadsGeo);
    (map.getSource("boundary") as maplibregl.GeoJSONSource | undefined)?.setData(boundaryGeo ?? EMPTY);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetsGeo, roadsGeo, boundaryGeo]);

  useEffect(() => { applyExposure(); applySelection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exposure]);

  useEffect(() => { applySelection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAssetId]);

  useEffect(() => { applyVisibility();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibility]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    (map.getSource("exposure-extent") as maplibregl.GeoJSONSource | undefined)?.setData(
      extentGeo ?? EMPTY,
    );
  }, [extentGeo]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
