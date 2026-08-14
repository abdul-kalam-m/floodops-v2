// Types mirroring the pipeline's §7 web data contracts (OPERATING_GUIDE.md).
// V2 is deliberately NOT v1's schema with fields renamed -- it has no gauge, no WSE.
// Phase 7 (§5.6) added an OPTIONAL, per-town point-depth layer at facilities only:
// towns that pass the MHHW->NAVD88 datum gate (§5.6.2) get the 4-tier status model
// below and a real depth_ft; towns that don't keep the original 3-tier, depth_ft:
// null model. Roads never get a computed depth (§2.2, locked) -- RoadStatus stays
// 2-tier regardless of a town's depth_available value.

export type AssetStatus = "operational" | "access-threatened" | "isolated" | "exposed";
export type RoadStatus = "open" | "closed";
export type StatusModel = "3-tier" | "4-tier";

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

export interface DatumSource {
  vdatum_ft: number | null;
  vdatum_uncertainty_ft: number | null;
  coops_station_id: string | null;
  coops_station_name: string | null;
  coops_dist_km: number | null;
  coops_ft: number | null;
  coops_epoch: string | null;
  retrieved_utc: string;
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
  // Phase 7 (§5.6/§7.2) -- depth_available=false towns are functionally unaffected
  // by Phase 7: status_model stays "3-tier", mhhw_navd88_ft/datum_source stay null.
  depth_available: boolean;
  status_model: StatusModel;
  mhhw_navd88_ft: number | null;
  datum_source: DatumSource | null;
  ffo_default_ft: number;
  generated_utc: string;
}

export interface AssetExposure {
  status: AssetStatus;
  access_lost: boolean;
  // null for every asset in a depth_available:false town. 0 means "computed, and the
  // water surface does not reach this facility's ground elevation" -- a real result,
  // distinct from "not computed." Never displayed at finer than 0.5 ft (§5.6.3).
  depth_ft: number | null;
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
