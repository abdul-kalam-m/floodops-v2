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
LEVELS_FT = list(range(1, 21))  # whole-foot only, 1-20 ft above MHHW (locked, §2.1)
WHOLE_FOOT_NAME_RE = re.compile(
    r"^Rutgers NJ (\d+) ft\. Coastal Inundation Extent(, Low-Lying Areas)?\s*$"
)

UA = "floodops-v2/1.0 (portfolio project; ar.abdulkalam.mustaq@gmail.com)"
HEADERS = {"User-Agent": UA}


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
