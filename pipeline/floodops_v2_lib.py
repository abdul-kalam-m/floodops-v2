"""Shared helpers for the FloodOps V2 pipeline (OPERATING_GUIDE.md §6).

V2 is deliberately simpler than v1's pipeline in one respect: no DEM, no depth
computation (§2.2, locked) -- the hazard source is used as extent-only exposure.
HTTP is cached + retried so every stage is idempotent, same discipline as v1.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Same PROJ_LIB/PROJ_DATA hygiene as v1's floodops_lib.py -- a system PROJ install
# (e.g. PostgreSQL/PostGIS) can otherwise break rasterio/GDAL/pyproj CRS ops.
for _v in ("PROJ_LIB", "PROJ_DATA"):
    os.environ.pop(_v, None)

import warnings
warnings.filterwarnings("ignore", message=r".*shape on a NumPy array.*")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

import requests

# --- paths -------------------------------------------------------------------
PIPELINE_DIR = Path(__file__).resolve().parent
REPO = PIPELINE_DIR.parent
RAW = REPO / "data" / "raw"
PROCESSED = REPO / "data" / "processed"
MANIFEST = REPO / "data" / "MANIFEST.json"

# --- CRS ---------------------------------------------------------------------
WGS84 = 4326
UTM18N = 26918  # analysis CRS (meters) -- same choice as v1, for consistency

# --- hazard source (locked, §3.1/§13.3) --------------------------------------
CIE_BASE = ("https://services1.arcgis.com/ze0XBzU1FXj94DJq/arcgis/rest/services/"
            "RU_NJ_CIE_Full/FeatureServer")
LEVELS_FT = list(range(0, 21))  # whole-foot, 0-20 ft above MHHW (locked, §2.1; 0 ft
                                 # -- the MHHW baseline itself -- added 2026-08-01,
                                 # owner-approved, reversing the original exclusion)
WHOLE_FOOT_NAME_RE = re.compile(
    r"^Rutgers NJ (\d+) ft\. Coastal Inundation Extent"
    r"(?: \(Mean Higher High Water\))?(, Low-Lying Areas)?\s*$"
    # The 0 ft layer (ids 82/83) is the only one with the "(Mean Higher High Water)"
    # suffix -- verified against all 84 layer names live, 2026-08-01, not just the
    # 0 ft pair, before adding this: no other level has a parenthetical suffix, so
    # this can't accidentally swallow anything else. Half-foot layers ("N ft., 6 in.")
    # still don't match -- there's a comma+inches between "ft." and "Coastal" there,
    # which this pattern still requires to be a single space.
)

UA = "floodops-v2/1.0 (portfolio project; ar.abdulkalam.mustaq@gmail.com)"
HEADERS = {"User-Agent": UA}

# --- town registry (LOCKED §3.2/§13.3 — single source of truth; 00_recon.py and every
# fetch script import this rather than each keeping their own copy of the town list) ---
TOWN_REGISTRY = [
    # (slug, town, mun, note)
    ("newark", "Newark", "NEWARK CITY",
     "Anchor: airport, port, rail hub; confirmed full coverage"),
    ("hoboken", "Hoboken", "HOBOKEN CITY",
     "Dense waterfront, famous Sandy flood history, small/compact"),
    ("jersey-city", "Jersey City", "JERSEY CITY",
     "Large waterfront city, PATH, Hudson + Newark Bay frontage"),
    ("atlantic-city", "Atlantic City", "ATLANTIC CITY",
     "Open-ocean-facing -- different flood geometry"),
    ("new-brunswick", "New Brunswick", "NEW BRUNSWICK CITY",
     "Raritan tidal limit; narrative link to FloodOps v1"),
    ("perth-amboy", "Perth Amboy", "PERTH AMBOY CITY",
     "Raritan Bay confluence, historic coastal flooding"),
    ("camden", "Camden", "CAMDEN CITY",
     "Delaware River waterfront -- different watershed, geographic diversity"),
    ("bayonne", "Bayonne", "BAYONNE CITY",
     "Kill Van Kull/Newark Bay, industrial critical infrastructure"),
]

STATE_FIPS = "34"  # New Jersey (§3, reused from v1's TIGERweb convention)


# --- Census TIGERweb boundary (reused pattern from v1's 02_fetch_boundary.py) -
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "Places_CouSub_ConCity_SubMCD/MapServer")


def arcgis_geojson(base_url: str, layer_id: int, where: str, out_fields: str = "*",
                   out_sr: int = WGS84, force: bool = False):
    """Query an ArcGIS REST layer -> GeoDataFrame. TIGERweb's outSR has been verified
    correct (v1 used it directly for Bound Brook with sane results) -- no CRS-detection
    workaround needed here, unlike the coordinate-magnitude check v1 needed for NWS_FIM."""
    import geopandas as gpd
    js = get_json(f"{base_url}/{layer_id}/query", params={
        "where": where, "outFields": out_fields, "returnGeometry": "true",
        "outSR": out_sr, "f": "geojson"}, force=force)
    feats = js.get("features", [])
    if not feats:
        raise ValueError(f"ArcGIS query returned 0 features [{base_url}/{layer_id}] {where}")
    return gpd.GeoDataFrame.from_features(feats, crs=out_sr)


def county_subdivision_layer(force: bool = False) -> int:
    svc = get_json(TIGERWEB, params={"f": "json"}, force=force)
    ids = [l["id"] for l in svc.get("layers", []) if l.get("name") == "County Subdivisions"]
    if not ids:
        raise RuntimeError("County Subdivisions layer not found in TIGERweb service.")
    return min(ids)  # most recent vintage, same choice v1 made


# Fixed 2026-07-31: a naive geometric 1 km buffer around a waterfront town's boundary can
# reach across a river/bay into another state (confirmed: Hoboken's buffer pulled in a
# Manhattan heliport 626 m across the Hudson; Camden's pulled in Philadelphia fire stations
# and even Philadelphia's own Packer Ave Marine Terminal tagged as a "port"). The state
# line (unlike a Euclidean buffer) already follows the legal river/bay boundary, so clipping
# every town's study area to NJ's TIGERweb state polygon removes cross-state contamination
# while preserving legitimate nearby-NJ-town assets (the buffer's actual intended purpose).
STATE_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
               "State_County/MapServer/0")
_nj_boundary_cache = None


def nj_boundary(force: bool = False):
    """New Jersey's state polygon (EPSG:4326), cached in-process. Used to clip every
    town's buffered study area so it never crosses a state line (§13.2 decision)."""
    global _nj_boundary_cache
    if _nj_boundary_cache is not None and not force:
        return _nj_boundary_cache
    import geopandas as gpd
    js = get_json(f"{STATE_LAYER}/query", params={
        "where": f"STATE='{STATE_FIPS}'", "outFields": "STATE",
        "returnGeometry": "true", "outSR": WGS84, "f": "geojson"}, force=force)
    gdf = gpd.GeoDataFrame.from_features(js["features"], crs=WGS84)
    _nj_boundary_cache = gdf.union_all()
    return _nj_boundary_cache


# --- Overpass (OSM) -----------------------------------------------------------
OVERPASS = "https://overpass-api.de/api/interpreter"


def overpass(query: str, force: bool = False) -> dict:
    """Run an Overpass QL query (cached). Retries/backoff via get_json's http layer."""
    return get_json(OVERPASS, params={"data": query}, force=force, timeout=180)


# --- elevation (informational only, §4.1 V5 -- NOT used in exposure math) ---
def elevation_ft(lon: float, lat: float, force: bool = False) -> tuple[float, str]:
    """Ground elevation in feet from USGS EPQS. No DEM fallback in V2 (no DEM fetched,
    §2.2/§4.1 -- unlike v1). Returns (nan, "unavailable") if EPQS fails for a point."""
    url = "https://epqs.nationalmap.gov/v1/json"
    try:
        js = get_json(url, params={"x": lon, "y": lat, "units": "Feet", "wkid": WGS84},
                      force=force, retries=2, timeout=30)
        val = float(js.get("value"))
        if val > -1e5:
            return round(val, 2), "epqs"
    except Exception:  # noqa: BLE001
        pass
    return float("nan"), "unavailable"


# --- http (cached + retried) -------------------------------------------------
def _cache_path(url: str, params: dict | None, suffix: str) -> Path:
    key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()[:16]
    return RAW / "http_cache" / f"{key}{suffix}"


def get_json(url: str, params: dict | None = None, force: bool = False,
             retries: int = 4, timeout: int = 90) -> dict:
    """Cached JSON GET with retry/backoff."""
    cache = _cache_path(url, params, ".json")
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET JSON failed after {retries}: {url} params={params}: {last}")


# --- CIE layer resolution (by NAME PATTERN, not hardcoded ids -- §3.1) -------
def resolve_whole_foot_layers(force: bool = False) -> dict[int, dict[str, int]]:
    """{level_ft: {"main": layer_id, "low_lying": layer_id}} for levels 1-20.

    Resolved by matching layer *names* against the service's live metadata, not
    by trusting a hardcoded id formula -- if Rutgers ever republishes the service
    with different layer ids, this still works; a hardcoded formula would not.
    """
    svc = get_json(CIE_BASE, params={"f": "json"}, force=force)
    out: dict[int, dict[str, int]] = {}
    for layer in svc.get("layers", []):
        m = WHOLE_FOOT_NAME_RE.match(layer["name"])
        if not m:
            continue
        level = int(m.group(1))
        kind = "low_lying" if m.group(2) else "main"
        out.setdefault(level, {})[kind] = layer["id"]
    return out


def cie_query_count(layer_id: int, mun: str, force: bool = False) -> int:
    r = get_json(f"{CIE_BASE}/{layer_id}/query",
                 params={"where": f"MUN='{mun}'", "returnCountOnly": "true", "f": "json"},
                 force=force)
    if "error" in r:
        raise RuntimeError(f"CIE query error for layer {layer_id}, MUN='{mun}': {r['error']}")
    return int(r.get("count", 0))


def cie_query_geojson(layer_id: int, mun: str, out_sr: int = WGS84, force: bool = False) -> dict:
    """Fetch a layer's features for one municipality as GeoJSON.

    Verified 2026-07-22: RU_NJ_CIE_Full honors `outSR` correctly (unlike v1's
    NWS_FIM service, which always returned Web Mercator regardless of outSR) --
    no coordinate-magnitude CRS-detection workaround is needed here.
    """
    return get_json(f"{CIE_BASE}/{layer_id}/query",
                     params={"where": f"MUN='{mun}'", "outFields": "MUN,COUNTY,MUN_CODE",
                             "returnGeometry": "true", "outSR": out_sr, "f": "geojson"},
                     force=force)


def count_vertices(geom: dict) -> int:
    def walk(c):
        if isinstance(c, (list, tuple)):
            if c and isinstance(c[0], (int, float)):
                return 1
            return sum(walk(x) for x in c)
        return 0
    return walk(geom.get("coordinates", []))


# --- manifest ----------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_add(name: str, source_url: str, path: Path | None,
                 license_note: str = "Rutgers NJAES / public research product",
                 extra: dict | None = None) -> None:
    try:
        man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        man = {"artifacts": []}
    arts = [a for a in man.get("artifacts", []) if a.get("source_url") != source_url]
    entry = {
        "name": name,
        "source_url": source_url,
        "retrieved_utc": utc_now(),
        "sha256": (sha256_file(path) if path and path.exists() else None),
        "local_path": (str(path.relative_to(REPO)) if path else None),
        "license_note": license_note,
    }
    if extra:
        entry.update(extra)
    arts.append(entry)
    man["artifacts"] = arts
    MANIFEST.write_text(json.dumps(man, indent=2), encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
