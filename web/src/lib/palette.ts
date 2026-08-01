// Okabe-Ito-based, colorblind-safe status palette (v1's convention, reused).
// V2's vocabulary is deliberately coarser than v1's (§5.3/§5.4, extent-only, no depth):
// 3-tier asset status, 2-tier road status, ONE exposure-fill color (not a 4-class depth
// ramp) -- never reuse v1's DEPTH_COLORS concept here, there is no depth to shade by.
import type { AssetStatus, RoadStatus } from "../types";

export const ASSET_COLORS: Record<AssetStatus, string> = {
  operational: "#009E73",
  isolated: "#CC79A7",
  exposed: "#D55E00",
};

export const ROAD_COLORS: Record<RoadStatus, string> = {
  open: "#9ca3af",
  closed: "#991b1b",
};

export const ASSET_STATUS_LABEL: Record<AssetStatus, string> = {
  operational: "Operational",
  isolated: "Isolated",
  exposed: "Exposed",
};

export const ROAD_STATUS_LABEL: Record<RoadStatus, string> = {
  open: "Open",
  closed: "Closed",
};

// Single exposure-fill color (distinct from v1's 4-class blue depth ramp on purpose --
// a V2 screenshot must never be mistakable for a v1 depth map, §8 of the guide).
export const EXPOSURE_FILL_COLOR = "#2563a3";

// Municipal boundary line. Deliberately violet -- the only hue family not already used
// by ASSET_COLORS/ROAD_COLORS/EXPOSURE_FILL_COLOR above, so the dashed boundary can
// never read as "just another gray road" against the basemap (owner-reported issue,
// 2026-07-31: the original #334155 slate sat too close to ROAD_COLORS.open/basemap
// road casing). Single source of truth -- MapView's map layer and Legend's swatch
// both import this rather than hardcoding the color twice.
export const BOUNDARY_COLOR = "#7c3aed";

// Single-letter marker glyph per category (encodes category without color alone).
export const CATEGORY_LETTER: Record<string, string> = {
  fire: "F",
  police: "P",
  ems: "E",
  hospital: "H",
  school: "S",
  community: "C",
  shelter: "R",
  library: "L",
  municipal: "M",
  airport: "A",
  port: "T",
};
