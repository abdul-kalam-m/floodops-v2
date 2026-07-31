#!/usr/bin/env python3
"""02 — Fetch critical facilities/community assets per town, with ground elevation.

Reuses v1's OSM/Overpass category set (§4.1 V3) plus two additions this project
needs and v1 never did: `airport` (aeroway=aerodrome) and `port` (industrial=port,
with landuse=harbour as a fallback tag) -- Newark's two anchor assets. Elevation
is informational only (§4.1 V5) -- EPQS, no DEM fallback (V2 has no DEM, §2.2).

Outputs per town: data/processed/{slug}/assets.geojson (EPSG:4326).
"""
from __future__ import annotations

import argparse
import sys

import floodops_v2_lib as fl  # imported first: PROJ env before geopandas init

import geopandas as gpd
from shapely.geometry import Point

DEDUPE_M = 50.0
FFO_DEFAULT_FT = 1.0  # kept for schema parity with v1; NOT used in V2 status math (§5.3)

# Overpass selectors. Same v1 categories, plus airport + port (verified live
# against Newark 2026-07-31: aeroway=aerodrome -> Newark Liberty Intl (EWR);
# industrial=port -> Port Newark Container Terminal, Maher, APM, Port Newark-Elizabeth).
CATEGORY_SELECTORS = [
    'nwr["amenity"="fire_station"]',
    'nwr["emergency"="fire_station"]',
    'nwr["amenity"="police"]',
    'nwr["amenity"="ambulance_station"]',
    'nwr["emergency"="ambulance_station"]',
    'nwr["amenity"="hospital"]',
    'nwr["amenity"="school"]',
    'nwr["amenity"="community_centre"]',
    'nwr["amenity"="library"]',
    'nwr["amenity"="townhall"]',
    'nwr["office"="government"]',
    'nwr["amenity"="social_facility"]["social_facility"="shelter"]',
    'nwr["aeroway"="aerodrome"]',
    'nwr["industrial"="port"]',
    'nwr["landuse"="harbour"]',
]


def categorize(tags: dict) -> str | None:
    a, em = tags.get("amenity"), tags.get("emergency")
    sf, office = tags.get("social_facility"), tags.get("office")
    aeroway, industrial, landuse = tags.get("aeroway"), tags.get("industrial"), tags.get("landuse")
    if a == "fire_station" or em == "fire_station":
        return "fire"
    if a == "police":
        return "police"
    if a == "ambulance_station" or em == "ambulance_station":
        return "ems"
    if a == "hospital":
        return "hospital"
    if a == "school":
        return "school"
    if a == "community_centre":
        return "community"
    if a == "library":
        return "library"
    if a == "townhall":
        return "municipal"
    if a == "social_facility" and sf == "shelter":
        return "shelter"
    if office == "government":
        return "municipal"
    if aeroway == "aerodrome":
        return "airport"
    if industrial == "port" or landuse == "harbour":
        return "port"
    return None


def address(tags: dict) -> str:
    hn, st = tags.get("addr:housenumber"), tags.get("addr:street")
    city = tags.get("addr:city")
    parts = [p for p in [" ".join(x for x in [hn, st] if x), city] if p]
    return ", ".join(parts)


def fetch_one_town(slug: str, town: str, force: bool) -> dict:
    study = gpd.read_file(fl.PROCESSED / slug / "study_area.geojson")
    study_geom = study.union_all()
    s, w, n, e = study.total_bounds[1], study.total_bounds[0], study.total_bounds[3], study.total_bounds[2]
    bbox = f"{s},{w},{n},{e}"

    parts = "\n".join(f"  {sel}({bbox});" for sel in CATEGORY_SELECTORS)
    query = f"[out:json][timeout:180];\n(\n{parts}\n);\nout center tags;"
    data = fl.overpass(query, force=force)
    elements = data.get("elements", [])

    rows = []
    for el in elements:
        tags = el.get("tags", {}) or {}
        cat = categorize(tags)
        if cat is None:
            continue
        if el["type"] == "node":
            lon, lat = el.get("lon"), el.get("lat")
        else:
            c = el.get("center") or {}
            lon, lat = c.get("lon"), c.get("lat")
        if lon is None or lat is None:
            continue
        pt = Point(lon, lat)
        if not study_geom.contains(pt):
            continue
        rows.append({
            "osm_id": f"{el['type'][0]}{el['id']}",
            "name": tags.get("name") or f"Unnamed {cat}",
            "category": cat,
            "address": address(tags),
            "geometry": pt,
        })

    if not rows:
        raise RuntimeError(f"{town}: no assets found in study area.")

    gdf = gpd.GeoDataFrame(rows, crs=fl.WGS84)

    # Dedupe: same category within 50 m (prefer named features over "Unnamed").
    gdf_utm = gdf.to_crs(fl.UTM18N)
    gdf["_x"], gdf["_y"] = gdf_utm.geometry.x, gdf_utm.geometry.y
    gdf = gdf.sort_values(by=["name"], key=lambda s: s.str.startswith("Unnamed"))
    keep = []
    for cat, grp in gdf.groupby("category"):
        kept_pts: list[tuple[float, float]] = []
        for idx, r in grp.iterrows():
            if any(((r["_x"] - kx) ** 2 + (r["_y"] - ky) ** 2) ** 0.5 < DEDUPE_M
                   for kx, ky in kept_pts):
                continue
            kept_pts.append((r["_x"], r["_y"]))
            keep.append(idx)
    gdf = gdf.loc[keep].drop(columns=["_x", "_y"]).reset_index(drop=True)

    elevs, srcs = [], []
    for _, r in gdf.iterrows():
        ev, src = fl.elevation_ft(r.geometry.x, r.geometry.y, force=force)
        elevs.append(ev)
        srcs.append(src)
    gdf["ground_elev_ft"] = elevs
    gdf["elev_source"] = srcs
    gdf["ffo_ft"] = FFO_DEFAULT_FT
    gdf["source"] = "OpenStreetMap"
    gdf["id"] = gdf["osm_id"]

    out_dir = fl.PROCESSED / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "assets.geojson"
    cols = ["id", "name", "category", "address", "ground_elev_ft",
            "elev_source", "ffo_ft", "source", "geometry"]
    gdf[cols].to_file(out, driver="GeoJSON")
    fl.manifest_add(f"osm_assets_{slug}", fl.OVERPASS + f" (assets query, {town})", out,
                    "OpenStreetMap contributors, ODbL")

    by_cat = gdf["category"].value_counts().to_dict()
    return {"slug": slug, "town": town, "n_assets": len(gdf), "by_category": by_cat}


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
            print(f"  {r['n_assets']} assets: {r['by_category']}")
        except Exception as e:  # noqa: BLE001
            failures.append((town, str(e)))
            print(f"  [FAIL] {e}")

    print(f"\n{'='*68}\n{len(results)}/{len(towns)} towns fetched.")
    newark = next((r for r in results if r["slug"] == "newark"), None)
    if newark:
        has_airport = "airport" in newark["by_category"]
        has_port = "port" in newark["by_category"]
        print(f"Newark category-widening check: airport={has_airport} port={has_port}")
        if not (has_airport and has_port):
            print("[FATAL] Newark exit criterion not met (§11): airport+port must both be present.")
            return 2
    if failures:
        print("Failures:")
        for town, err in failures:
            print(f"  {town}: {err}")
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
