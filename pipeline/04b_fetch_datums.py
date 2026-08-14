#!/usr/bin/env python3
"""04b — Phase 7.0: resolve each town's MHHW->NAVD88 offset (§5.6.2, LOCKED).

Two independent sources, per town:
  - PRIMARY: NOAA VDatum point conversion (MHHW -> NAVD88) at a real water point
    inside the town's own extent_0.geojson (the MHHW baseline itself).
  - CROSS-CHECK: nearest NOAA CO-OPS station (from the full ~2,900-station
    waterlevels+historicwl catalog, not just the ~15 "major" stations) that has a
    published NAVD88 datum tie-in.
  - GATE: the two must agree within 0.25 ft, or the town ships without depth
    (§5.6.4). Do not average, do not widen the tolerance, do not pick the more
    convenient value -- verified against the guide's explicit instruction.

`mhhw_navd88_ft` in the output is always the VDatum (primary) value for towns that
pass the gate -- never an average of the two sources.

Outputs: data/processed/{slug}/datum.json (feeds 05_build_exposure.py's index.json,
§7.2) + MANIFEST entries. Also prints a summary table for RECON.md.
"""
from __future__ import annotations

import argparse
import json
import sys

import floodops_v2_lib as fl  # imported first: PROJ env before geopandas init

HAZARD_RAW = fl.RAW / "hazard"
GATE_FT = 0.25  # §5.6.2, LOCKED -- do not widen without owner reopening §13.3
N_STATIONS_TO_TRY = 30  # nearest-N CO-OPS candidates to try before giving up


def resolve_one_town(slug: str, town: str, stations: list[dict], force: bool) -> dict:
    extent_0 = HAZARD_RAW / slug / "extent_0.geojson"
    if not extent_0.exists():
        raise RuntimeError(f"{town}: no extent_0.geojson -- run 04_fetch_hazard.py first")

    candidates = fl.town_water_candidates(extent_0)

    # VDatum (primary): try every candidate point until one resolves.
    vdatum_ft, vdatum_pt, vdatum_raw = None, None, None
    for lon, lat in candidates:
        val, raw = fl.vdatum_mhhw_navd88_ft(lon, lat, force=force)
        vdatum_raw = raw
        if val is not None:
            vdatum_ft, vdatum_pt = val, (lon, lat)
            break

    town_lon, town_lat = vdatum_pt or candidates[0]

    # CO-OPS (cross-check): nearest stations by real distance, first one with a
    # published NAVD88 tie-in wins. Many nearby subordinate stations have no
    # accepted datums at all (`"datums": null`) -- normal, not an error; skip them.
    dists = []
    for s in stations:
        slat, slng = s.get("lat"), s.get("lng")
        if slat is None or slng is None:
            continue
        d = fl.haversine_km(town_lat, town_lon, slat, slng)
        dists.append((d, s))
    dists.sort(key=lambda x: x[0])

    coops_ft, coops_station, coops_raw = None, None, None
    for dist, s in dists[:N_STATIONS_TO_TRY]:
        val, raw = fl.coops_mhhw_navd88_ft(s["id"], force=force)
        if val is not None:
            coops_ft, coops_station, coops_raw = val, {**s, "dist_km": round(dist, 2)}, raw
            break

    diff_ft = (round(vdatum_ft - coops_ft, 3)
              if (vdatum_ft is not None and coops_ft is not None) else None)
    gate_pass = diff_ft is not None and abs(diff_ft) <= GATE_FT

    result = {
        "slug": slug, "town": town,
        "depth_available": gate_pass,
        "water_point": [round(town_lon, 5), round(town_lat, 5)],
        "mhhw_navd88_ft": round(vdatum_ft, 3) if gate_pass else None,
        "datum_source": {
            "vdatum_ft": round(vdatum_ft, 3) if vdatum_ft is not None else None,
            "vdatum_uncertainty_ft": (float(vdatum_raw.get("uncertainty"))
                                      if vdatum_raw and vdatum_raw.get("uncertainty") else None),
            "coops_station_id": coops_station["id"] if coops_station else None,
            "coops_station_name": coops_station["name"] if coops_station else None,
            "coops_dist_km": coops_station["dist_km"] if coops_station else None,
            "coops_ft": coops_ft,
            "coops_epoch": coops_raw.get("epoch") if coops_raw else None,
            "retrieved_utc": fl.utc_now(),
        } if gate_pass else None,
        # Diagnostic fields kept even when the gate fails, so RECON.md/PROGRESS.md can
        # explain *why* (disagreement vs. one source having zero coverage) rather than
        # just recording a bare failure.
        "diagnostic": {
            "vdatum_ft": round(vdatum_ft, 3) if vdatum_ft is not None else None,
            "coops_ft": coops_ft,
            "coops_station_id": coops_station["id"] if coops_station else None,
            "coops_station_name": coops_station["name"] if coops_station else None,
            "coops_dist_km": coops_station["dist_km"] if coops_station else None,
            "diff_ft": diff_ft,
            "reason": (
                "pass" if gate_pass else
                "no VDatum coverage at any candidate point in this town's MHHW extent"
                if vdatum_ft is None else
                f"no CO-OPS station within nearest {N_STATIONS_TO_TRY} has a published NAVD88 datum"
                if coops_ft is None else
                f"disagreement {abs(diff_ft):.3f} ft exceeds {GATE_FT} ft gate"
            ),
        },
    }

    out_dir = fl.PROCESSED / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "datum.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    if gate_pass:
        fl.manifest_add(
            f"mhhw_navd88_offset_{slug}",
            f"{fl.VDATUM_CONVERT} (primary) + {fl.COOPS_DATUMS.format(id=coops_station['id'])} (cross-check)",
            out_dir / "datum.json", "NOAA VDatum / NOAA CO-OPS, public domain",
            extra={"mhhw_navd88_ft": result["mhhw_navd88_ft"],
                   "coops_station_id": coops_station["id"],
                   "diff_ft": diff_ft})

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", help="comma-separated slugs to limit to (debugging)")
    args = ap.parse_args()

    towns = fl.TOWN_REGISTRY
    if args.only:
        wanted = set(args.only.split(","))
        towns = [t for t in towns if t[0] in wanted]

    print("Fetching CO-OPS station catalog (waterlevels + historicwl) ...")
    stations = fl.coops_all_stations(force=args.force)
    print(f"  {len(stations)} unique stations loaded.\n")

    results = []
    for slug, town, mun, note in towns:
        print(f"--- {town} ({slug}) ---")
        r = resolve_one_town(slug, town, stations, args.force)
        results.append(r)
        if r["depth_available"]:
            ds = r["datum_source"]
            print(f"  PASS: MHHW = {r['mhhw_navd88_ft']:.3f} ft NAVD88 "
                  f"(VDatum {ds['vdatum_ft']:.3f} vs CO-OPS {ds['coops_ft']:.3f} @ "
                  f"{ds['coops_station_name']}, {ds['coops_dist_km']:.1f} km, "
                  f"diff {r['diagnostic']['diff_ft']:+.3f} ft)")
        else:
            print(f"  NO DEPTH: {r['diagnostic']['reason']}")
        print()

    n_pass = sum(1 for r in results if r["depth_available"])
    print(f"{'='*72}")
    print(f"{n_pass}/{len(results)} towns pass the {GATE_FT} ft datum gate (§5.6.2).")
    print(f"\n{'town':15s} {'depth_available':>16s} {'mhhw_navd88_ft':>15s} {'diff_ft':>10s}  reason")
    for r in results:
        d = r["diagnostic"]
        print(f"{r['town']:15s} {str(r['depth_available']):>16s} "
              f"{r['mhhw_navd88_ft'] if r['mhhw_navd88_ft'] is not None else float('nan'):15.3f} "
              f"{d['diff_ft'] if d['diff_ft'] is not None else float('nan'):10.3f}  {d['reason']}")

    if n_pass == 0:
        print("\n[FATAL] 0 towns passed the datum gate -- per the guide's Phase 7.0 "
              "instruction, this is a hard stop, not something to route around.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
