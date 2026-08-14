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

# Unified across both status models (§5.3): 3-tier towns never produce
# "access-threatened", so its slot in the ranking doesn't affect their monotonicity
# checks -- only relative order matters, not the literal numbers.
ASSET_SEVERITY = {"operational": 0, "access-threatened": 1, "isolated": 2, "exposed": 3}
DISAGREEMENT_RATE_FLAG = 0.25  # §5.6.5, LOCKED -- reported, never suppressed or tuned away


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


def validate_town(slug: str, town: str, R: Result, disagreement_report: list) -> None:
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

    # (§12.1, Phase 7) index.json depth-availability contract (§7.2)
    depth_available = index.get("depth_available")
    status_model = index.get("status_model")
    R.check(f"{town}: depth_available is a bool", isinstance(depth_available, bool))
    R.check(f"{town}: status_model matches depth_available",
            status_model == ("4-tier" if depth_available else "3-tier"),
            f"depth_available={depth_available} status_model={status_model}")
    if depth_available:
        R.check(f"{town}: mhhw_navd88_ft present when depth_available",
                isinstance(index.get("mhhw_navd88_ft"), (int, float)))
        R.check(f"{town}: datum_source present when depth_available",
                isinstance(index.get("datum_source"), dict))
    else:
        R.check(f"{town}: mhhw_navd88_ft is null when depth NOT available",
                index.get("mhhw_navd88_ft") is None)

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

    # (§12.1) status vocabulary, road sparseness, id membership -- plus, Phase 7:
    # depth_ft format/consistency and the §5.6.5 model-disagreement rate.
    valid_road_ids = set(roads["id"])
    valid_asset_ids = set(assets["id"])
    ffo_by_id = {row["id"]: float(row["ffo_ft"]) for _, row in assets.iterrows()}
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

        if depth_available:
            # depth_ft: present (never missing), always a non-negative multiple of 0.5
            depths = {aid: v.get("depth_ft") for aid, v in exp["assets"].items()}
            R.check(f"{town}: level {lvl['level_ft']}ft depth_ft never missing/null "
                    "(depth_available town)",
                    all(v is not None for v in depths.values()))
            R.check(f"{town}: level {lvl['level_ft']}ft depth_ft is a non-negative "
                    "multiple of 0.5",
                    all(v is not None and v >= 0 and abs(v * 2 - round(v * 2)) < 1e-9
                        for v in depths.values()))
            # exposed <=> d >= ffo (§5.3, 4-tier)
            mismatch = [aid for aid, v in exp["assets"].items()
                       if (v["status"] == "exposed") != (depths[aid] >= ffo_by_id.get(aid, 1.0))]
            R.check(f"{town}: level {lvl['level_ft']}ft exposed<=>depth>=ffo",
                    not mismatch, f"{len(mismatch)} mismatches" if mismatch else "")
            # §5.6.5 disagreement rate: inside the extent but depth computed as 0 --
            # the visible seam between Rutgers' extent and this project's own DEM
            # subtraction. Reported, never asserted pass/fail (a high rate is a real
            # finding, not a bug -- §5.6.5 explicitly forbids tuning it away).
            in_extent_ids = [aid for aid in exp["assets"] if aid in valid_asset_ids]
            # "inside the extent" isn't itself in the JSON contract -- reconstruct it
            # the same way status does: any asset with depth_ft>0 OR status=="exposed"
            # was inside the extent at some point in the cascade; assets never in
            # extent always have depth_ft==0 by construction (§5.6.1). The rate is
            # only meaningful over assets actually inside the extent, so approximate
            # "inside extent" as status != "operational and depth==0 with no access
            # closure" is unreliable -- instead, recompute directly against the raw
            # extent geometry.
            zero_inside = 0
            n_inside = 0
            extent_path = (d / lvl["files"]["extent"])
            if extent_path.exists():
                extent_gdf = gpd.read_file(extent_path).to_crs(fl.UTM18N)
                # buffer(0) fixes invalid rings before union -- the committed extent
                # is already simplified+coordinate-rounded (§7.4), which can produce
                # a self-intersection GEOS rejects outright (confirmed live: a real
                # TopologyException, not hypothetical). Same defensive pattern
                # 04_fetch_hazard.py already uses after its own CIE union.
                extent_geom = extent_gdf.geometry.buffer(0).union_all().buffer(20.0)
                assets_utm = assets.to_crs(fl.UTM18N)
                for _, row in assets_utm.iterrows():
                    if row.geometry.within(extent_geom):
                        n_inside += 1
                        if depths.get(row["id"], 0) == 0:
                            zero_inside += 1
            rate = (zero_inside / n_inside) if n_inside else 0.0
            disagreement_report.append({
                "town": town, "slug": slug, "level_ft": lvl["level_ft"],
                "n_inside_extent": n_inside, "n_zero_depth_inside": zero_inside,
                "rate": round(rate, 4),
            })
        else:
            R.check(f"{town}: level {lvl['level_ft']}ft depth_ft null "
                    "(depth NOT available)",
                    all(v.get("depth_ft") is None for v in exp["assets"].values()))
            R.check(f"{town}: level {lvl['level_ft']}ft no access-threatened status "
                    "(3-tier town)",
                    all(v["status"] != "access-threatened" for v in exp["assets"].values()))

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

        if depth_available:
            aids = list(assets["id"])
            mono_depth = True
            for aid in aids:
                dseq = [exp["assets"].get(aid, {}).get("depth_ft") for _, exp in level_data]
                if any((dseq[i + 1] or 0) < (dseq[i] or 0) for i in range(len(dseq) - 1)):
                    mono_depth = False
                    break
            R.check(f"{town}: depth_ft non-decreasing across levels", mono_depth)

            # §5.6.1: WSE rises exactly 1 ft per level step, so for any asset inside
            # the extent at BOTH consecutive levels, its depth must rise by exactly
            # 1.0 ft (within rounding to the nearest 0.5 ft) -- a direct, cheap check
            # that the MHHW offset was applied consistently level-to-level, not just
            # "some depth exists."
            step_ok = True
            step_mismatches = 0
            for i in range(len(level_data) - 1):
                lvl_a, exp_a = level_data[i]
                lvl_b, exp_b = level_data[i + 1]
                if lvl_b - lvl_a != 1:
                    continue  # only adjacent whole-foot levels are comparable this way
                for aid in aids:
                    da = exp_a["assets"].get(aid, {}).get("depth_ft")
                    db = exp_b["assets"].get(aid, {}).get("depth_ft")
                    if da is None or db is None or da == 0 or db == 0:
                        continue  # only meaningful when inside the extent at both levels
                    if abs((db - da) - 1.0) > 1e-6:
                        step_ok, step_mismatches = False, step_mismatches + 1
            R.check(f"{town}: depth rises exactly 1 ft per 1 ft level step "
                    "(inside extent at both levels)",
                    step_ok, f"{step_mismatches} mismatches" if not step_ok else "")

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


def validate() -> tuple[bool, list]:
    R = Result()
    R.check("towns.json exists", (WEB_DATA / "towns.json").exists())
    if (WEB_DATA / "towns.json").exists():
        reg = json.loads((WEB_DATA / "towns.json").read_text(encoding="utf-8"))
        reg_slugs = {t["slug"] for t in reg}
        registry_slugs = {t[0] for t in fl.TOWN_REGISTRY}
        R.check("towns.json slugs match TOWN_REGISTRY", reg_slugs == registry_slugs,
                f"diff={reg_slugs ^ registry_slugs}" if reg_slugs != registry_slugs else "")

    disagreement_report: list = []
    for slug, town, mun, note in fl.TOWN_REGISTRY:
        validate_town(slug, town, R, disagreement_report)

    ok = R.report()

    if disagreement_report:
        print(f"\n{'='*72}")
        print("§5.6.5 model-disagreement rate (assets inside the extent whose computed "
              "depth is still 0 -- Rutgers' extent vs. this project's own DEM subtraction):")
        flagged = [r for r in disagreement_report if r["rate"] > DISAGREEMENT_RATE_FLAG]
        by_town: dict[str, list] = {}
        for r in disagreement_report:
            by_town.setdefault(r["town"], []).append(r)
        for town, rows in by_town.items():
            rates = [r["rate"] for r in rows]
            print(f"  {town:15s} min={min(rates):.1%}  max={max(rates):.1%}  "
                  f"mean={sum(rates)/len(rates):.1%}  ({len(rows)} levels)")
        if flagged:
            print(f"\n  [NAMED LIMITATION -- not a failure, §5.6.5] {len(flagged)} town-level "
                  f"combination(s) exceed the {DISAGREEMENT_RATE_FLAG:.0%} threshold and must be "
                  f"surfaced on the Methods page:")
            for r in flagged:
                print(f"    {r['town']} @ {r['level_ft']} ft: {r['rate']:.1%} "
                      f"({r['n_zero_depth_inside']}/{r['n_inside_extent']} assets)")
        else:
            print(f"\n  No town/level exceeds the {DISAGREEMENT_RATE_FLAG:.0%} threshold.")

    return ok, disagreement_report


def main() -> int:
    ok, _ = validate()
    print("\nRESULT:", "ALL PASS ✅" if ok else "FAILURES ❌")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
