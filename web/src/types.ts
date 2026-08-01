// Types mirroring the pipeline's §7 web data contracts (OPERATING_GUIDE.md).
// V2 is deliberately NOT v1's schema with fields renamed -- it has no gauge, no WSE,
// no depth anywhere, and a different (3-tier/2-tier) status vocabulary (§5.3/§5.4).

export type AssetStatus = "operational" | "isolated" | "exposed";
export type RoadStatus = "open" | "closed";

export interface TownEntry {
  slug: string;
  name: string;
  mun: string;
  center: [number, number]; // [lat, lon]
  bbox: [number, number, number, number]; // [w, s, e, n]
}

export interface LevelEntry {
  level_ft: number;
  files: { exposure: string; extent: string };
}

export interface TownIndexJson {
  town: string;
  slug: string;
  county: string;
  state: string;
  levels: LevelEntry[];
  hazard_source: string;
  fim_mode: "extent-only";
  roads_encoding: "sparse-closed-only";
  generated_utc: string;
}

export interface AssetExposure {
  status: AssetStatus;
  access_lost: boolean;
}

// Sparse (§13.2 decision): only CLOSED roads appear here. A road id absent from this
// map is open. Never assume every road.geojson id has an entry.
export interface RoadExposureSparse {
  status: "closed";
}

export interface ExposureJson {
  level_ft: number;
  town: string;
  assets: Record<string, AssetExposure>;
  roads: Record<string, RoadExposureSparse>;
  summary: {
    by_asset_status: Partial<Record<AssetStatus, number>>;
    road_closed_count: number;
    road_closed_miles: number;
  };
}

// first_exposed.json: first level (ascending) at which an asset's status != operational.
export type FirstExposedMap = Record<string, number | null>;

// Use the standard @types/geojson FeatureCollection so it interops with MapLibre.
export type GeoJson = GeoJSON.FeatureCollection;
