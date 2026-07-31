#!/usr/bin/env python3
"""01 — Fetch municipal boundary + 1 km study area for every locked town.

Reuses v1's Census TIGERweb County Subdivision pattern (§6.1). Loops over
floodops_v2_lib.TOWN_REGISTRY, the single source of truth for the locked town set.

Outputs (EPSG:4326), one set per town:
  data/processed/{slug}/boundary.geojson    - municipal boundary
  data/processed/{slug}/study_area.geojson  - 1 km buffered study area
"""
from __future__ import annotations

import argparse
import sys

import floodops_v2_lib as fl  # imported first: sets PROJ env before geopandas/pyproj init

import geopandas as gpd

STUDY_BUFFER_M = 1000  # same convention as v1 §7.2


def fetch_one_town(slug: str, town: str, force: bool) -> dict:
    lid = fl.county_subdivision_layer(force)
    where = f"BASENAME='{town}' AND STATE='{fl.STATE_FIPS}'"
    gdf = fl.arcgis_geojson(fl.TIGERWEB, lid, where, out_fields="NAME,GEOID,BASENAME",
                            force=force)
    if len(gdf) != 1:
        raise RuntimeError(
            f"{town}: expected exactly 1 TIGERweb match, got {len(gdf)} "
            f"(where={where!r}) -- ambiguous town name, needs a COUNTY qualifier."
        )

    muni = gdf.dissolve()[["geometry"]].copy()
    muni["name"] = town
    muni["geoid"] = str(gdf.iloc[0].get("GEOID"))

    muni_utm = muni.to_crs(fl.UTM18N)
    area_km2 = float(muni_utm.area.iloc[0]) / 1e6

    # Clip to NJ's state polygon (§13.2 decision, 2026-07-31): a naive Euclidean buffer
    # can cross a river/bay into another state for waterfront towns; the state line
    # already follows the real legal river/bay boundary, so clipping to it removes
    # cross-state contamination (confirmed: Hoboken -> Manhattan, Camden -> Philadelphia,
    # Bayonne/Perth Amboy -> Staten Island) without shrinking legitimate NJ-side coverage.
    nj_utm = gpd.GeoSeries([fl.nj_boundary()], crs=fl.WGS84).to_crs(fl.UTM18N).iloc[0]
    study_geom = muni_utm.buffer(STUDY_BUFFER_M).union_all().intersection(nj_utm)
    study = gpd.GeoDataFrame(
        {"name": [f"{town} study area"], "buffer_m": [STUDY_BUFFER_M],
         "muni_area_km2": [round(area_km2, 3)], "clipped_to_nj": [True]},
        geometry=[study_geom], crs=fl.UTM18N).to_crs(fl.WGS84)

    out_dir = fl.PROCESSED / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    bpath = out_dir / "boundary.geojson"
    spath = out_dir / "study_area.geojson"
    muni.to_crs(fl.WGS84).to_file(bpath, driver="GeoJSON")
    study.to_file(spath, driver="GeoJSON")

    fl.manifest_add(f"census_tigerweb_boundary_{slug}", f"{fl.TIGERWEB}/{lid}/query?{where}",
                    bpath, "US Census TIGERweb, public domain")

    study_km2 = float(study.to_crs(fl.UTM18N).area.iloc[0]) / 1e6
    return {"slug": slug, "town": town, "geoid": muni["geoid"].iloc[0],
            "area_km2": round(area_km2, 3), "study_area_km2": round(study_km2, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated slugs to limit to (debugging)")
    args = ap.parse_args()

    towns = fl.TOWN_REGISTRY
    if args.only:
        wanted = set(args.only.split(","))
        towns = [t for t in towns if t[0] in wanted]

    results = []
    failures = []
    for slug, town, mun, note in towns:
        print(f"\n--- {town} ({slug}) ---")
        try:
            r = fetch_one_town(slug, town, args.force)
            results.append(r)
            print(f"  boundary: {r['area_km2']} km^2 (GEOID {r['geoid']})")
            print(f"  study area (1km buffer): {r['study_area_km2']} km^2")
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
