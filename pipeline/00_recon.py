#!/usr/bin/env python3
"""FloodOps V2 Phase 0 recon — verify candidate towns against RU_NJ_CIE_Full.

Implements OPERATING_GUIDE.md §3. For each ranked candidate municipality:
  1. Resolve the whole-foot layer ids (1-20 ft) by name pattern (§3.1 -- never
     hardcode the id formula, the service could be republished with new ids).
  2. Query coverage: which of the 20 levels return non-empty features for MUN=<town>.
  3. For the town's HIGHEST available level (worst-case payload, since extent
     area grows with level), fetch geometry and measure raw vertex count / size
     as a complexity proxy for the §7.4 per-town budget.
  4. Rank/lock the town set: keep candidates with usable coverage, drop and log
     the rest (mirrors v1's Denville precedent).

Outputs:
  - data/processed/recon_report.json  (machine-readable evidence)
  - RECON.md                          (human-readable table)

Design notes (matches v1's 00_recon.py):
  - stdlib-only entry point (--check-only) for CI; full run needs `requests`.
  - idempotent: cached under data/raw/http_cache/; --force refetches.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
REPO = PIPELINE_DIR.parent
PROCESSED = REPO / "data" / "processed"
RECON_MD = REPO / "RECON.md"
REPORT_JSON = PROCESSED / "recon_report.json"

# Coverage pass criteria (§3.2): a town needs a usable, contiguous exposure range.
MIN_LEVELS_COVERED = 3       # need at least this many of the 20 levels non-empty
MIN_TOP_LEVEL_FT = 5         # its highest covered level must reach at least this high
                             # (rules out towns with only a sliver of coverage at 1-2ft)

# Ranked candidates (guide §3.2). MUN values must match the service's exact
# uppercase + municipality-type-suffix convention (verified against the service
# in an earlier session; Phase 0 re-derives the *set* of valid MUN values live
# below as a cross-check, not just trusting this hardcoded string).
CANDIDATES = [
    ("Newark", "NEWARK CITY", "Anchor: airport, port, rail hub; confirmed full coverage"),
    ("Hoboken", "HOBOKEN CITY", "Dense waterfront, famous Sandy flood history, small/compact"),
    ("Jersey City", "JERSEY CITY", "Large waterfront city, PATH, Hudson + Newark Bay frontage"),
    ("Atlantic City", "ATLANTIC CITY", "Open-ocean-facing -- different flood geometry"),
    ("New Brunswick", "NEW BRUNSWICK CITY", "Raritan tidal limit; narrative link to FloodOps v1"),
    ("Perth Amboy", "PERTH AMBOY CITY", "Raritan Bay confluence, historic coastal flooding"),
    ("Camden", "CAMDEN CITY", "Delaware River waterfront -- different watershed, geographic diversity"),
    ("Bayonne", "BAYONNE CITY", "Kill Van Kull/Newark Bay, industrial critical infrastructure"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check-only", action="store_true",
                    help="verify imports/parse; no network (CI smoke)")
    args = ap.parse_args()

    if args.check_only:
        print("00_recon.py: --check-only OK (no network performed).")
        return 0

    import floodops_v2_lib as fl  # deferred: keeps --check-only stdlib-only

    print("Resolving whole-foot layer ids (1-20 ft) by name pattern ...")
    layers = fl.resolve_whole_foot_layers(force=args.force)
    missing_levels = [l for l in fl.LEVELS_FT if l not in layers
                      or "main" not in layers[l] or "low_lying" not in layers[l]]
    if missing_levels:
        print(f"[FATAL] whole-foot layer resolution incomplete, missing levels: {missing_levels}")
        return 2
    print(f"  resolved all {len(fl.LEVELS_FT)} levels (main + low-lying each).")

    # Cross-check: confirm every candidate's MUN value actually exists in the service
    # (catches typos/naming drift before wasting a full per-level sweep on a bad value).
    print("Fetching distinct MUN values for validation ...")
    any_layer_id = layers[1]["main"]
    distinct = fl.get_json(f"{fl.CIE_BASE}/{any_layer_id}/query",
                           params={"where": "1=1", "returnDistinctValues": "true",
                                   "outFields": "MUN", "f": "json", "orderByFields": "MUN"},
                           force=args.force)
    known_muns = {f["attributes"]["MUN"].strip() for f in distinct.get("features", [])}
    print(f"  {len(known_muns)} distinct municipalities in the service.")

    candidates_out = []
    for name, mun, note in CANDIDATES:
        print(f"\nAssessing {name} (MUN='{mun}') ...")
        if mun not in known_muns:
            print(f"  [FAIL] '{mun}' not found among service MUN values -- check spelling.")
            candidates_out.append({
                "town": name, "mun": mun, "note": note, "passes": False,
                "reason": "MUN value not found in service", "levels_covered": [],
            })
            continue

        covered = []
        for level in fl.LEVELS_FT:
            main_id = layers[level]["main"]
            ll_id = layers[level]["low_lying"]
            n_main = fl.cie_query_count(main_id, mun, force=args.force)
            n_ll = fl.cie_query_count(ll_id, mun, force=args.force)
            if n_main > 0 or n_ll > 0:
                covered.append(level)

        passes = (len(covered) >= MIN_LEVELS_COVERED
                  and covered and max(covered) >= MIN_TOP_LEVEL_FT)

        complexity = None
        if covered:
            top = max(covered)
            main_id = layers[top]["main"]
            gj = fl.cie_query_geojson(main_id, mun, force=args.force)
            n_feats = len(gj.get("features", []))
            n_verts = sum(fl.count_vertices(f["geometry"]) for f in gj.get("features", []))
            raw_kb = len(json.dumps(gj)) / 1024
            complexity = {"worst_level_ft": top, "n_features": n_feats,
                          "n_vertices": n_verts, "raw_geojson_kb": round(raw_kb, 1)}
            print(f"  levels covered: {len(covered)}/20 (range {min(covered)}-{max(covered)} ft)")
            print(f"  worst-case (level {top} ft): {n_feats} feature(s), "
                  f"{n_verts} vertices, {raw_kb:.1f} KB raw")
        else:
            print("  levels covered: 0/20 -- no coastal exposure in this dataset")

        print(f"  {'PASS' if passes else 'FAIL'} "
              f"(need >={MIN_LEVELS_COVERED} levels covered, top >={MIN_TOP_LEVEL_FT} ft)")

        candidates_out.append({
            "town": name, "mun": mun, "note": note, "passes": passes,
            "levels_covered": covered, "complexity": complexity,
        })

    fl.manifest_add("cie_service_metadata", fl.CIE_BASE, None,
                    "Rutgers NJAES / public research product")

    passing = [c for c in candidates_out if c["passes"]]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "hazard_source": fl.CIE_BASE,
        "levels_ft_in_scope": fl.LEVELS_FT,
        "min_levels_covered": MIN_LEVELS_COVERED,
        "min_top_level_ft": MIN_TOP_LEVEL_FT,
        "candidates": candidates_out,
        "locked_towns": [c["town"] for c in passing],
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    RECON_MD.write_text(render_recon_md(report), encoding="utf-8")

    print("\n" + "=" * 68)
    print(f"LOCKED TOWN SET ({len(passing)}): {', '.join(c['town'] for c in passing)}")
    print(f"Wrote {REPORT_JSON.relative_to(REPO)} and {RECON_MD.name}")
    print("=" * 68)
    return 0 if passing else 2


def render_recon_md(report: dict) -> str:
    lines = [
        "# FloodOps V2 — Town Recon (RECON.md)",
        "",
        f"Generated: {report['generated_utc']} · auto-written by `pipeline/00_recon.py` (§3).",
        "",
        f"Pass criteria: >= {report['min_levels_covered']} of the 20 whole-foot levels "
        f"(1-20 ft above MHHW) have non-empty features, AND the highest covered level "
        f"reaches >= {report['min_top_level_ft']} ft.",
        "",
        "## Candidate summary",
        "",
        "| Town | MUN | Passes | Levels covered | Range (ft) | Worst-case level | Features | Vertices | Raw KB |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in report["candidates"]:
        cx = c.get("complexity") or {}
        rng = f"{min(c['levels_covered'])}-{max(c['levels_covered'])}" if c["levels_covered"] else "—"
        lines.append(
            f"| {c['town']} | {c['mun']} | {'✅' if c['passes'] else '❌'} | "
            f"{len(c['levels_covered'])}/20 | {rng} | "
            f"{cx.get('worst_level_ft','—')} | {cx.get('n_features','—')} | "
            f"{cx.get('n_vertices','—')} | {cx.get('raw_geojson_kb','—')} |"
        )
    lines += [
        "",
        f"## Locked town set ({len(report['locked_towns'])})",
        "",
    ]
    for t in report["locked_towns"]:
        lines.append(f"- **{t}**")
    if not report["locked_towns"]:
        lines.append("- (none passed — review candidate list or pass thresholds)")
    lines += [
        "",
        "Dropped candidates and why:",
        "",
    ]
    for c in report["candidates"]:
        if not c["passes"]:
            reason = c.get("reason") or (
                f"only {len(c['levels_covered'])}/20 levels covered"
                if c["levels_covered"] else "zero coastal exposure in this dataset"
            )
            lines.append(f"- **{c['town']}**: {reason}")
    lines.append("")
    lines.append("Once Phase 1 completes, the town set is LOCKED (§13.3); "
                 "changing it needs owner approval.")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
