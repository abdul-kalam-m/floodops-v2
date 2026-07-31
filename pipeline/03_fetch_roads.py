#!/usr/bin/env python3
"""03 — Fetch the drivable road network per town, clip to study area, segment to <=200 m.

Reuses v1's OSM/Overpass road-fetch and segmentation logic (§6.1) verbatim, looped
per town in floodops_v2_lib.TOWN_REGISTRY.

Outputs per town: data/processed/{slug}/roads.geojson (EPSG:4326).
Schema: {id, name, class, is_priority} (+ length_m) -- same as v1.
"""
from __future__ import annotations

import argparse
import sys

import floodops_v2_lib as fl  # imported first: PROJ env before geopandas/pyproj init

import geopandas as gpd
import pyproj
from shapely.geometry import LineString, Point
from shapely.ops import transform as shp_transform

MAX_SEG_M = 200.0
PRIORITY = {"motorway", "trunk", "primary"}
DRIVABLE = ("motorway|trunk|primary|secondary|tertiary|unclassified|residential|"
            "living_street|motorway_link|trunk_link|primary_link|secondary_link|"
            "tertiary_link")

_to_utm = pyproj.Transformer.from_crs(fl.WGS84, fl.UTM18N, always_xy=True).transform
_to_wgs = pyproj.Transformer.from_crs(fl.UTM18N, fl.WGS84, always_xy=True).transform


def split_line(line: LineString, max_len: float = MAX_SEG_M) -> list[LineString]:
    """Split a (UTM, meters) LineString into pieces <= max_len, preserving vertices."""
    coords = list(line.coords)
    if len(coords) < 2:
        return []
    segments, cur, acc = [], [coords[0]], 0.0
    for a, b in zip(coords, coords[1:]):
        start = a
        remaining = Point(a).distance(Point(b))
        while acc + remaining > max_len:
            need = max_len - acc
            t = need / remaining if remaining else 1.0
            cut = (start[0] + (b[0] - start[0]) * t, start[1] + (b[1] - start[1]) * t)
            cur.append(cut)
            segments.append(LineString(cur))
            cur, start, remaining, acc = [cut], cut, remaining - need, 0.0
        cur.append(b)
        acc += remaining
    if len(cur) >= 2:
        segments.append(LineString(cur))
    return segments


def line_parts(geom):
    if geom.is_empty:
        return
    gt = geom.geom_type
    if gt == "LineString":
        yield geom
    elif gt in ("MultiLineString", "GeometryCollection"):
        for g in geom.geoms:
            yield from line_parts(g)


def fetch_one_town(slug: str, town: str, force: bool) -> dict:
    study = gpd.read_file(fl.PROCESSED / slug / "study_area.geojson")
    study_utm = shp_transform(_to_utm, study.union_all())
    s, w, n, e = study.total_bounds[1], study.total_bounds[0], study.total_bounds[3], study.total_bounds[2]
    bbox = f"{s},{w},{n},{e}"

    query = (f'[out:json][timeout:180];\n'
             f'way["highway"~"^({DRIVABLE})$"]({bbox});\n'
             f'out geom tags;')
    data = fl.overpass(query, force=force)
    ways = [el for el in data.get("elements", []) if el.get("type") == "way"]

    rows = []
    for way in ways:
        geom = way.get("geometry") or []
        if len(geom) < 2:
            continue
        cls = way.get("tags", {}).get("highway")
        name = way.get("tags", {}).get("name", "")
        line_wgs = LineString([(p["lon"], p["lat"]) for p in geom])
        line_utm = shp_transform(_to_utm, line_wgs)
        clipped = line_utm.intersection(study_utm)
        for part in line_parts(clipped):
            for seg in split_line(part):
                # Some OSM ways have two adjacent nodes at (near-)identical coordinates
                # (a real data artifact, e.g. a duplicate node at a junction edit). A
                # strict `<= 0` check isn't enough: floating-point noise from the
                # UTM<->WGS84 round-trip can leave a segment technically >0 m (observed:
                # ~1e-8 degrees, effectively noise) but still collapse to a degenerate,
                # invalid LineString once 05_build_exposure.py's simplify(1 m) runs on
                # it. No real road segment is meaningfully shorter than half a meter, so
                # that's the threshold, not zero.
                MIN_SEG_LEN_M = 0.5
                if seg.length < MIN_SEG_LEN_M:
                    continue
                rows.append({
                    "id": f"{way['id']}-{len(rows)}",
                    "osm_way": way["id"],
                    "name": name,
                    "class": cls,
                    "is_priority": cls in PRIORITY,
                    "length_m": round(seg.length, 1),
                    "geometry": shp_transform(_to_wgs, seg),
                })

    if not rows:
        raise RuntimeError(f"{town}: no road segments produced.")

    gdf = gpd.GeoDataFrame(rows, crs=fl.WGS84)
    out_dir = fl.PROCESSED / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "roads.geojson"
    gdf[["id", "osm_way", "name", "class", "is_priority", "length_m", "geometry"]].to_file(
        out, driver="GeoJSON")
    fl.manifest_add(f"osm_roads_{slug}", fl.OVERPASS + f" (roads query, {town})", out,
                    "OpenStreetMap contributors, ODbL")

    total_km = gdf["length_m"].sum() / 1000
    prio_km = gdf.loc[gdf.is_priority, "length_m"].sum() / 1000
    return {"slug": slug, "town": town, "n_segments": len(gdf),
            "total_km": round(total_km, 1), "priority_km": round(prio_km, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated slugs to limit to (debugging)")
    args = ap.parse_args()

    towns = fl.TOWN_REGISTRY
    if args.only:
        wanted = set(args.only.split(","))
        towns = [t for t in towns if t[0] in wanted]

    results, failures = [], []
    for slug, town, mun, note in towns:
        print(f"\n--- {town} ({slug}) ---")
        try:
            r = fetch_one_town(slug, town, args.force)
            results.append(r)
            print(f"  {r['n_segments']} segments, {r['total_km']} km "
                  f"({r['priority_km']} km priority)")
        except Exception as e:  # noqa: BLE001
            failures.append((town, str(e)))
            print(f"  [FAIL] {e}")

    print(f"\n{'='*68}\n{len(results)}/{len(towns)} towns fetched.")
    if failures:
        print("Failures:")
        for town, err in failures:
            print(f"  {town}: {err}")
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
