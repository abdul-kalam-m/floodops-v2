#!/usr/bin/env python3
"""04 — Fetch the CIE inundation extent per town, per available whole-foot level.

Per town x level: fetch the main extent + "Low-Lying Areas" companion (both filtered
WHERE MUN=<TOWN>), union them (a hydrologically-disconnected low spot below the level
is still exposed, per Rutgers' own methodology note), buffer(0) to fix invalid rings,
reproject to the analysis CRS (§5.2). Levels come from data/processed/recon_report.json
(the live per-town coverage Phase 0 already established) -- not assumed to be 1-20 for
every town (§5.1).

Outputs (raw/intermediate, gitignored -- mirrors v1's data/raw/fim/ convention):
  data/raw/hazard/{slug}/extent_{level}.geojson   (EPSG:26918)
Phase 2's 05_build_exposure.py reads these, computes statuses, simplifies, and writes
the final committed web contracts.
"""
from __future__ import annotations

import argparse
import json
import sys

import floodops_v2_lib as fl  # imported first: PROJ env before geopandas/pyproj init

import geopandas as gpd
import pandas as pd

HAZARD_RAW = fl.RAW / "hazard"


def town_levels(slug: str) -> list[int]:
    report = json.loads((fl.PROCESSED / "recon_report.json").read_text(encoding="utf-8"))
    cand = next((c for c in report["candidates"] if c["slug"] == slug), None)
    if cand is None:
        raise RuntimeError(f"{slug}: not found in recon_report.json")
    return cand["levels_covered"]


def fetch_one_level(slug: str, town: str, mun: str, level: int,
                    layers: dict[int, dict[str, int]], force: bool) -> dict:
    main_id = layers[level]["main"]
    ll_id = layers[level]["low_lying"]

    main_gj = fl.cie_query_geojson(main_id, mun, out_sr=fl.WGS84, force=force)
    ll_gj = fl.cie_query_geojson(ll_id, mun, out_sr=fl.WGS84, force=force)

    parts = []
    for gj in (main_gj, ll_gj):
        feats = gj.get("features", [])
        if feats:
            parts.append(gpd.GeoDataFrame.from_features(feats, crs=fl.WGS84))
    if not parts:
        # Level had 0 features for this town at fetch time -- shouldn't happen given
        # recon already confirmed coverage, but don't silently fabricate an extent.
        raise RuntimeError(f"{town} level {level} ft: 0 features from CIE at fetch time "
                          f"(recon said this level was covered -- data may have changed).")

    gdf = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=fl.WGS84)
    geom_utm = gdf.to_crs(fl.UTM18N).union_all().buffer(0)

    out_dir = HAZARD_RAW / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"extent_{level}.geojson"
    gpd.GeoDataFrame({"level_ft": [level]}, geometry=[geom_utm], crs=fl.UTM18N).to_file(
        out, driver="GeoJSON")

    fl.manifest_add(f"cie_extent_{slug}_{level}ft",
                    f"{fl.CIE_BASE}/{main_id}(+{ll_id})/query?WHERE=MUN='{mun}'", out,
                    "Rutgers NJAES / public research product",
                    extra={"level_ft": level, "main_layer": main_id, "low_lying_layer": ll_id})

    return {"level": level, "area_km2": round(geom_utm.area / 1e6, 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated slugs to limit to (debugging)")
    args = ap.parse_args()

    towns = fl.TOWN_REGISTRY
    if args.only:
        wanted = set(args.only.split(","))
        towns = [t for t in towns if t[0] in wanted]

    print("Resolving whole-foot layer ids ...")
    layers = fl.resolve_whole_foot_layers(force=args.force)

    results, failures = [], []
    for slug, town, mun, note in towns:
        levels = town_levels(slug)
        print(f"\n--- {town} ({slug}): {len(levels)} level(s) to fetch ---")
        town_areas = []
        for level in levels:
            try:
                r = fetch_one_level(slug, town, mun, level, layers, args.force)
                town_areas.append(r)
            except Exception as e:  # noqa: BLE001
                failures.append((town, level, str(e)))
                print(f"  [FAIL] level {level} ft: {e}")
        if town_areas:
            areas = [r["area_km2"] for r in town_areas]
            mono_ok = all(areas[i + 1] >= areas[i] - 1e-6 for i in range(len(areas) - 1))
            print(f"  fetched {len(town_areas)}/{len(levels)} levels; "
                  f"area range {areas[0]:.3f}-{areas[-1]:.3f} km^2; "
                  f"monotonic={'OK' if mono_ok else 'FAILED'}")
            results.append({"slug": slug, "town": town, "n_levels": len(town_areas),
                           "monotonic": mono_ok})

    print(f"\n{'='*68}\n{len(results)}/{len(towns)} towns processed.")
    non_mono = [r for r in results if not r["monotonic"]]
    if non_mono:
        print(f"[WARN] non-monotonic area growth for: {[r['town'] for r in non_mono]} "
              f"(09_validate.py will assert this properly per-entity, not just per-town-area)")
    if failures:
        print("Failures:")
        for town, level, err in failures:
            print(f"  {town} @ {level}ft: {err}")
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())
