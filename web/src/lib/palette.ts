// Okabe-Ito-based, colorblind-safe status palette (v1's convention, reused).
// Road status stays 2-tier and the map fill stays single-class (not v1's 4-class
// depth ramp) regardless of a town's depth availability -- roads never get a
// computed depth (§2.2, locked), and the ramp is locked out for payload reasons
// (§7.4), not portfolio-distinguishability. Asset status now has 4 possible values
// for depth_available towns (§5.3) -- reuses v1's own 4-tier color tokens verbatim
// (implementation convenience, same design-token source already shared per §6.2;
// NOT a portfolio-pairing signal, see the guide's §16 changelog). The worst tier
// keeps V2's pre-existing "exposed" label rather than adopting v1's
// "facility-flooded" -- already shipped in the CSV/URL/report vocabulary before
// Phase 7, and its condition now matches v1's facility-flooded exactly (§5.3).
import type { AssetStatus, RoadStatus } from "../types";

export const ASSET_COLORS: Record<AssetStatus, string> = {
  operational: "#009E73",
  "access-threatened": "#E69F00",
  isolated: "#CC79A7",
  exposed: "#D55E00",
};

export const ROAD_COLORS: Record<RoadStatus, string> = {
  open: "#9ca3af",
  closed: "#991b1b",
};

export const ASSET_STATUS_LABEL: Record<AssetStatus, string> = {
  operational: "Operational",
  "access-threatened": "Access threatened",
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

// Municipal boundary line. Black -- both prior attempts (#334155 slate, then #7c3aed
// violet) still read as "just another road" against ROAD_COLORS/the basemap in
// practice (owner-reported, 2026-07-31 x2); black is the one value that can't be
// confused with any road-casing or basemap tone. Single source of truth -- MapView's
// map layer and Legend's swatch both import this rather than hardcoding the color twice.
export const BOUNDARY_COLOR = "#000000";

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
