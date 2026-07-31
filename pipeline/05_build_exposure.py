#!/usr/bin/env python3
"""05 — Build the §5 exposure model into the §7 web data contracts, per town.

For each town, for each level it has raw hazard data for (04_fetch_hazard.py's output):
  - road status (2-tier, §5.4): closed if the segment intersects the level's extent
    (with the same 20 m source-alignment tolerance v1 used, §13.2), else open.
  - facility status (3-tier, §5.3): exposed if the point falls inside the (tolerant)
    extent; isolated if not exposed but every access road (120 m proximity, §5.5,
    same rule as v1) is closed; operational otherwise.
  - summary counts + road-closed miles.
Then first_exposed.json (first level, ascending, at which each asset's status != operational)
and the per-town index.json + a top-level towns.json registry.

Outputs (EPSG:4326, committed): web/public/data/{towns.json, {slug}/*}
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

import floodops_v2_lib as fl  # imported first: PROJ env before geopandas/pyproj init

import geopandas as gpd
from shapely.geometry import mapping, shape

EXTENT_TOLERANCE_M = 20.0  # same constant + rationale as v1 (OSM<->independent-polygon alignment)
ACCESS_RADIUS_M = 120.0    # same proximity rule as v1 §5.5A
# §13.2 decision (2026-07-31), empirically derived, NOT assumed from v1's 1 m tolerance
# (the guide explicitly warned against that): tested 2/5/10/12/15/20/30/50 m on Newark's
# worst-case (densest) extents. 2 m left several per-level files at 550-830 KB, over the
# §7.4 800 KB/file budget, and a ~15.7 MB town total, over the 5 MB/town budget. 15 m gives
# every Newark file <= 267 KB and a ~4.82 MB town total (the real worst case across all 8
# towns) -- a genuine ~4% margin under budget, not a razor's edge -- while distorting
# extent area by < 1%, negligible next to the hazard model's own inherent uncertainty.
SIMPLIFY_M = 15.0
# 6 decimals (~11 cm), not 5: tried 5 first for a small extra size cut, but it collapsed
# 6/11,142 of Newark's shortest road segments (and one New Brunswick boundary ring) into
# degenerate duplicate-point geometries (~1.1 m precision isn't safe against real segments
# that short). The size difference was ~2% -- not worth trading away geometry validity for.
COORD_ROUND = 6

WEB_DATA = fl.REPO / "web" / "public" / "data"
HAZARD_RAW = fl.RAW / "hazard"

# Road status dict is SPARSE (§13.2 decision, see PROGRESS.md): only CLOSED segments are
# listed; any segment id absent from a level's `roads` dict is "open". This is a deliberate
# deviation from listing every entity (as v1 always did) -- Newark alone has 11,142 road
# segments, and a full per-segment listing at every level would blow the §7.4 800 KB/file
# budget. Assets stay fully listed (far fewer of them, and the dashboard wants every
# asset's status without inferring a default).


def gzip_size(path: Path) -> int:
    """Real-world transfer size: Cloudflare Pages (and v1's own §8.7 JS-bundle budget)
    both measure web performance budgets in gzip-compressed bytes, not raw disk bytes --
    §7.4's budget is corrected to match (2026-07-31 decision; see PROGRESS.md). GeoJSON's
    repeated key names and similar-magnitude coordinates compress 8-9x in practice."""
    return len(gzip.compress(path.read_bytes(), compresslevel=9))


def round_coords(geom, ndigits: int = COORD_ROUND):
    def _r(v):
        if isinstance(v, (list, tuple)):
            return [_r(x) for x in v]
        if isinstance(v, float):
            return round(v, ndigits)
        return v
    m = mapping(geom)
    m["coordinates"] = _r(m["coordinates"])
    return shape(m)


def town_levels(slug: str) -> list[int]:
    report = json.loads((fl.PROCESSED / "recon_report.json").read_text(encoding="utf-8"))
    cand = next((c for c in report["candidates"] if c["slug"] == slug), None)
    return cand["levels_covered"]


def county_for(mun: str, force: bool) -> str:
    # Cheap, cached lookup straight from the CIE service (already-verified source of MUN/
    # COUNTY pairs) -- avoids depending on TIGERweb exposing the same field under a
    # different name.
    layers = fl.resolve_whole_foot_layers(force=force)
    any_id = layers[1]["main"]
    r = fl.get_json(f"{fl.CIE_BASE}/{any_id}/query",
                    params={"where": f"MUN='{mun}'", "outFields": "COUNTY",
                            "returnGeometry": "false", "resultRecordCount": 1, "f": "json"},
                    force=force)
    feats = r.get("features", [])
    return feats[0]["attributes"]["COUNTY"].strip() if feats else "unknown"


def build_access_adjacency(assets_utm: gpd.GeoDataFrame,
                           roads_utm: gpd.GeoDataFrame) -> dict[str, list[str]]:
    """Same pattern as v1 §5.5A: roads within 120 m of each asset, nearest-segment fallback."""
    seg_idx = roads_utm.sindex
    out: dict[str, list[str]] = {}
    for _, a in assets_utm.iterrows():
        buf = a.geometry.buffer(ACCESS_RADIUS_M)
        hits = list(seg_idx.query(buf, predicate="intersects"))
        seg_ids = [roads_utm.iloc[i]["id"] for i in hits] if hits else []
        if not seg_ids:
            nearest = list(seg_idx.nearest(a.geometry, return_all=False))
            if nearest:
                seg_ids = [roads_utm.iloc[nearest[1][0]]["id"]]
        out[a["id"]] = seg_ids
    return out


def build_one_town(slug: str, town: str, mun: str, force: bool) -> dict:
    levels = town_levels(slug)
    assets = gpd.read_file(fl.PROCESSED / slug / "assets.geojson")
    roads = gpd.read_file(fl.PROCESSED / slug / "roads.geojson")
    boundary = gpd.read_file(fl.PROCESSED / slug / "boundary.geojson")

    assets_utm = assets.to_crs(fl.UTM18N)
    roads_utm = roads.to_crs(fl.UTM18N)
    access_by_asset = build_access_adjacency(assets_utm, roads_utm)

    out_dir = WEB_DATA / slug
    (out_dir / "levels").mkdir(parents=True, exist_ok=True)

    first_exposed: dict[str, float | None] = {aid: None for aid in assets["id"]}
    level_entries = []

    for level in levels:
        raw_path = HAZARD_RAW / slug / f"extent_{level}.geojson"
        if not raw_path.exists():
            print(f"  [SKIP] level {level} ft: no raw extent (run 04_fetch_hazard.py first)")
            continue
        extent_utm = gpd.read_file(raw_path).to_crs(fl.UTM18N).union_all()
        extent_tolerant = extent_utm.buffer(EXTENT_TOLERANCE_M)

        # --- roads (2-tier) ---
        closed_mask = roads_utm.geometry.intersects(extent_tolerant)
        closed_ids = set(roads_utm.loc[closed_mask, "id"])
        roads_sparse = {rid: {"status": "closed"} for rid in closed_ids}

        # --- assets (3-tier) ---
        exposed_mask = assets_utm.geometry.within(extent_tolerant)
        assets_out: dict[str, dict] = {}
        for i, aid in enumerate(assets_utm["id"]):
            if exposed_mask.iloc[i]:
                status, access_lost = "exposed", True
            else:
                access_segs = access_by_asset.get(aid, [])
                access_lost = bool(access_segs) and all(s in closed_ids for s in access_segs)
                status = "isolated" if access_lost else "operational"
            assets_out[aid] = {"status": status, "access_lost": access_lost}
            if status != "operational" and first_exposed[aid] is None:
                first_exposed[aid] = float(level)

        by_status: dict[str, int] = defaultdict(int)
        for v in assets_out.values():
            by_status[v["status"]] += 1
        closed_len_m = roads_utm.loc[closed_mask, "length_m"].sum()
        summary = {
            "by_asset_status": dict(by_status),
            "road_closed_count": len(closed_ids),
            "road_closed_miles": round(float(closed_len_m) / 1609.344, 2),
        }

        exposure_json = {
            "level_ft": level, "town": town,
            "assets": assets_out, "roads": roads_sparse, "summary": summary,
        }
        (out_dir / "levels" / f"exposure_{level}.json").write_text(
            json.dumps(exposure_json, separators=(",", ":")), encoding="utf-8")

        # single-class exposure polygon, STRICT extent (no tolerance -- rendered footprint
        # should show the true modeled hazard, not the point/line-matching allowance)
        simplified = extent_utm.simplify(SIMPLIFY_M, preserve_topology=True)
        simplified_wgs = gpd.GeoSeries([simplified], crs=fl.UTM18N).to_crs(fl.WGS84).iloc[0]
        simplified_wgs = round_coords(simplified_wgs)
        ext_gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "properties": {"level_ft": level},
             "geometry": mapping(simplified_wgs)},
        ]}
        (out_dir / "levels" / f"extent_{level}.geojson").write_text(
            json.dumps(ext_gj, separators=(",", ":")), encoding="utf-8")

        level_entries.append({
            "level_ft": level,
            "files": {"exposure": f"levels/exposure_{level}.json",
                      "extent": f"levels/extent_{level}.geojson"},
        })

    # --- per-town static files ---
    web_assets = assets.copy()
    web_assets["geometry"] = web_assets.geometry.apply(round_coords)
    web_assets.to_file(out_dir / "assets.geojson", driver="GeoJSON")

    web_roads_utm = roads.to_crs(fl.UTM18N).copy()
    web_roads_utm["geometry"] = web_roads_utm.geometry.simplify(1.0, preserve_topology=True)
    web_roads = web_roads_utm.to_crs(fl.WGS84)
    web_roads["geometry"] = web_roads.geometry.apply(round_coords)
    # Drop fields the dashboard never needs client-side (osm_way is pipeline-internal
    # traceability; length_m is only needed server-side, already aggregated into each
    # level's road_closed_miles summary) -- free size reduction, no functional loss.
    web_roads = web_roads[["id", "name", "class", "is_priority", "geometry"]]
    web_roads.to_file(out_dir / "roads.geojson", driver="GeoJSON")

    web_boundary = boundary[["geometry"]].copy()
    web_boundary["geometry"] = web_boundary.geometry.apply(round_coords)
    web_boundary.to_file(out_dir / "boundary.geojson", driver="GeoJSON")

    (out_dir / "first_exposed.json").write_text(
        json.dumps(first_exposed, indent=2), encoding="utf-8")

    county = county_for(mun, force)
    index_json = {
        "town": town, "slug": slug, "county": county, "state": "NJ",
        "levels": level_entries,
        "hazard_source": "Rutgers NJ Coastal Inundation Explorer (RU_NJ_CIE_Full)",
        "fim_mode": "extent-only",
        "roads_encoding": "sparse-closed-only",  # absence from a level's `roads` = open
        "generated_utc": fl.utc_now(),
    }
    (out_dir / "index.json").write_text(json.dumps(index_json, indent=2), encoding="utf-8")

    n_exposed_ever = sum(1 for v in first_exposed.values() if v is not None)
    files = [p for p in out_dir.rglob("*") if p.is_file()]
    total_raw = sum(p.stat().st_size for p in files)
    total_gzip = sum(gzip_size(p) for p in files)
    max_raw = max((p.stat().st_size for p in files), default=0)
    max_gzip = max((gzip_size(p) for p in files), default=0)
    return {
        "slug": slug, "town": town, "n_levels": len(level_entries),
        "n_assets_ever_exposed": n_exposed_ever, "n_assets_total": len(assets),
        "total_kb": round(total_raw / 1024, 1), "total_gzip_kb": round(total_gzip / 1024, 1),
        "max_file_kb": round(max_raw / 1024, 1), "max_gzip_kb": round(max_gzip / 1024, 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated slugs to limit to (debugging)")
    args = ap.parse_args()

    towns = fl.TOWN_REGISTRY
    if args.only:
        wanted = set(args.only.split(","))
        towns = [t for t in towns if t[0] in wanted]

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    results = []
    for slug, town, mun, note in towns:
        print(f"\n--- {town} ({slug}) ---")
        r = build_one_town(slug, town, mun, args.force)
        results.append(r)
        print(f"  {r['n_levels']} levels; {r['n_assets_ever_exposed']}/{r['n_assets_total']} "
              f"assets ever non-operational; {r['total_kb']} KB raw ({r['total_gzip_kb']} KB "
              f"gzip), largest file {r['max_file_kb']} KB raw ({r['max_gzip_kb']} KB gzip)")

    # towns.json registry (built last, once, from every town's boundary)
    reg = []
    for slug, town, mun, note in fl.TOWN_REGISTRY:
        b = gpd.read_file(fl.PROCESSED / slug / "boundary.geojson")
        c = b.to_crs(fl.UTM18N).union_all().centroid
        c_wgs = gpd.GeoSeries([c], crs=fl.UTM18N).to_crs(fl.WGS84).iloc[0]
        w, s, e, n = b.total_bounds
        reg.append({"slug": slug, "name": town, "mun": mun,
                   "center": [round(c_wgs.y, 5), round(c_wgs.x, 5)],
                   "bbox": [round(w, 5), round(s, 5), round(e, 5), round(n, 5)]})
    (WEB_DATA / "towns.json").write_text(json.dumps(reg, indent=2), encoding="utf-8")

    # §7.4 budget is measured in gzip-compressed size (matches v1's own JS-bundle
    # convention, §8.7 there) -- raw size is reported for transparency only.
    print(f"\n{'='*68}")
    over_budget = [r for r in results if r["total_gzip_kb"] > 5120 or r["max_gzip_kb"] > 800]
    for r in results:
        flag = " OVER BUDGET" if r in over_budget else ""
        print(f"  {r['town']:15s} {r['total_kb']:8.1f} KB raw / {r['total_gzip_kb']:7.1f} KB gzip"
              f"   max {r['max_gzip_kb']:6.1f} KB gzip{flag}")
    if over_budget:
        print(f"\n[WARN] {len(over_budget)} town(s) over the §7.4 budget "
              f"(5 MB total / 800 KB per file, gzip-compressed) -- increase SIMPLIFY_M "
              f"or investigate.")
    else:
        print("\nAll towns within the §7.4 gzip budget.")
    print(f"Wrote {WEB_DATA.relative_to(fl.REPO)}/towns.json + {len(results)} town dirs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
