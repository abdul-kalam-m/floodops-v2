#!/usr/bin/env python3
"""09 — Validate all §7 web contracts and §12.1 invariants, generalized across every
locked town (v1's 09_validate.py checked one town; this checks all 8).

Exits 0 if all pass, non-zero otherwise. Also invoked by pytest (see tests/).
"""
from __future__ import annotations

import gzip
import json
import sys

import floodops_v2_lib as fl  # imported first: PROJ env

import geopandas as gpd

WEB_DATA = fl.REPO / "web" / "public" / "data"
FILE_GZIP_BUDGET = 800 * 1024
TOWN_GZIP_BUDGET = 5 * 1024 * 1024

ASSET_SEVERITY = {"operational": 0, "isolated": 1, "exposed": 2}


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        self.rows.append((name, cond, detail))

    def report(self) -> bool:
        for name, ok, det in self.rows:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}  ({det})" if det
                  else f"  [{'PASS' if ok else 'FAIL'}] {name}")
        return all(ok for _, ok, _ in self.rows)


def gzip_size(path) -> int:
    return len(gzip.compress(path.read_bytes(), compresslevel=9))


def validate_town(slug: str, town: str, R: Result) -> None:
    d = WEB_DATA / slug
    for name in ("index.json", "assets.geojson", "roads.geojson", "boundary.geojson",
                "first_exposed.json"):
        R.check(f"{town}: {name} exists", (d / name).exists())
    if not (d / "index.json").exists():
        return

    index = json.loads((d / "index.json").read_text(encoding="utf-8"))
    levels = index["levels"]
    R.check(f"{town}: levels sorted ascending",
            [l["level_ft"] for l in levels] == sorted(l["level_ft"] for l in levels))
    R.check(f"{town}: fim_mode is extent-only", index.get("fim_mode") == "extent-only")
    R.check(f"{town}: roads_encoding documented",
            index.get("roads_encoding") == "sparse-closed-only")

    # (§7.4) gzip-measured budgets
    files = [p for p in d.rglob("*") if p.is_file()]
    total_gzip = sum(gzip_size(p) for p in files)
    R.check(f"{town}: town total ≤5MB gzip", total_gzip <= TOWN_GZIP_BUDGET,
            f"{total_gzip/1024:.1f} KB")
    for p in files:
        sz = gzip_size(p)
        R.check(f"{town}: {p.relative_to(d)} ≤800KB gzip", sz <= FILE_GZIP_BUDGET,
                f"{sz/1024:.1f} KB")

    # scenario files exist
    for lvl in levels:
        for k, subpath in lvl["files"].items():
            R.check(f"{town}: level {lvl['level_ft']}ft {k} file exists",
                    (d / subpath).exists(), str(subpath))

    # (§12.1) EPSG:4326 + valid geoms + unique ids
    assets = gpd.read_file(d / "assets.geojson")
    roads = gpd.read_file(d / "roads.geojson")
    boundary = gpd.read_file(d / "boundary.geojson")
    for name, gdf in (("assets", assets), ("roads", roads), ("boundary", boundary)):
        R.check(f"{town}: {name} CRS=4326", gdf.crs and gdf.crs.to_epsg() == 4326)
        R.check(f"{town}: {name} geoms valid", bool(gdf.geometry.is_valid.all()))
    R.check(f"{town}: asset ids unique", len(assets["id"].unique()) == len(assets))
    R.check(f"{town}: road ids unique", len(roads["id"].unique()) == len(roads))

    # (§12.1) depths -- N/A for V2 (extent-only); instead validate status vocabulary
    valid_road_ids = set(roads["id"])
    valid_asset_ids = set(assets["id"])
    level_data = []
    for lvl in levels:
        exp = json.loads((d / lvl["files"]["exposure"]).read_text(encoding="utf-8"))
        level_data.append((lvl["level_ft"], exp))
        R.check(f"{town}: level {lvl['level_ft']}ft asset statuses valid",
                all(v["status"] in ASSET_SEVERITY for v in exp["assets"].values()))
        R.check(f"{town}: level {lvl['level_ft']}ft road statuses valid (closed-only)",
                all(v["status"] == "closed" for v in exp["roads"].values()),
                "sparse dict must contain only 'closed' entries, never 'open'")
        R.check(f"{town}: level {lvl['level_ft']}ft asset ids known",
                set(exp["assets"]) <= valid_asset_ids)
        R.check(f"{town}: level {lvl['level_ft']}ft road ids known",
                set(exp["roads"]) <= valid_road_ids)

    # (§12.1) monotonic severity across levels, per asset and per road
    if len(level_data) >= 2:
        aids = list(assets["id"])
        mono_asset = True
        for aid in aids:
            sevs = [ASSET_SEVERITY[exp["assets"].get(aid, {"status": "operational"})["status"]]
                    for _, exp in level_data]
            if any(sevs[i + 1] < sevs[i] for i in range(len(sevs) - 1)):
                mono_asset = False
                break
        R.check(f"{town}: asset severity non-decreasing across levels", mono_asset)

        rids = list(roads["id"])
        mono_road = True
        for rid in rids:
            # sparse: absent = open(0), present = closed(1) -- severity can only go 0->1, never 1->0
            was_closed = False
            for _, exp in level_data:
                is_closed = rid in exp["roads"]
                if was_closed and not is_closed:
                    mono_road = False
                    break
                was_closed = was_closed or is_closed
            if not mono_road:
                break
        R.check(f"{town}: road closure non-decreasing across levels (once closed, stays closed)",
                mono_road)

        counts = [sum(1 for v in exp["assets"].values() if v["status"] != "operational")
                  for _, exp in level_data]
        R.check(f"{town}: non-operational asset count non-decreasing",
                all(counts[i + 1] >= counts[i] for i in range(len(counts) - 1)), f"{counts}")

    # (§12.1) first_exposed.json consistency
    fe = json.loads((d / "first_exposed.json").read_text(encoding="utf-8"))
    ok, bad = True, 0
    for aid in fe:
        expected = None
        for lvl_ft, exp in level_data:
            st = exp["assets"].get(aid, {"status": "operational"})["status"]
            if st != "operational":
                expected = float(lvl_ft)
                break
        if fe[aid] != expected:
            ok, bad = False, bad + 1
    R.check(f"{town}: first_exposed matches per-level statuses", ok,
            f"{bad} mismatches" if not ok else f"{len(fe)} assets")


def validate() -> bool:
    R = Result()
    R.check("towns.json exists", (WEB_DATA / "towns.json").exists())
    if (WEB_DATA / "towns.json").exists():
        reg = json.loads((WEB_DATA / "towns.json").read_text(encoding="utf-8"))
        reg_slugs = {t["slug"] for t in reg}
        registry_slugs = {t[0] for t in fl.TOWN_REGISTRY}
        R.check("towns.json slugs match TOWN_REGISTRY", reg_slugs == registry_slugs,
                f"diff={reg_slugs ^ registry_slugs}" if reg_slugs != registry_slugs else "")

    for slug, town, mun, note in fl.TOWN_REGISTRY:
        validate_town(slug, town, R)

    return R.report()


def main() -> int:
    ok = validate()
    print("\nRESULT:", "ALL PASS ✅" if ok else "FAILURES ❌")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
