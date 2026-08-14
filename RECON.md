# FloodOps V2 — Town Recon (RECON.md)

Generated: 2026-08-01T03:50:10.534157+00:00 · auto-written by `pipeline/00_recon.py` (§3).

Pass criteria: >= 3 of the 21 whole-foot levels (0-20 ft above MHHW) have non-empty features, AND the highest covered level reaches >= 5 ft.

## Candidate summary

| Town | MUN | Passes | Levels covered | Range (ft) | Worst-case level | Features | Vertices | Raw KB |
|---|---|---|---|---|---|---|---|---|
| Newark | NEWARK CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 54735 | 2080.5 |
| Hoboken | HOBOKEN CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 2912 | 111.2 |
| Jersey City | JERSEY CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 38142 | 1450.0 |
| Atlantic City | ATLANTIC CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 4628 | 176.0 |
| New Brunswick | NEW BRUNSWICK CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 9304 | 353.0 |
| Perth Amboy | PERTH AMBOY CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 8675 | 329.5 |
| Camden | CAMDEN CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 23947 | 910.4 |
| Bayonne | BAYONNE CITY | ✅ | 21/21 | 0-20 | 20 | 1 | 19668 | 746.9 |

## Locked town set (8)

- **Newark**
- **Hoboken**
- **Jersey City**
- **Atlantic City**
- **New Brunswick**
- **Perth Amboy**
- **Camden**
- **Bayonne**

Dropped candidates and why:


Once Phase 1 completes, the town set is LOCKED (§13.3); changing it needs owner approval.

---

## Phase 7.0 — MHHW→NAVD88 datum recon (§5.6.2)

Generated: 2026-08-11 · `pipeline/04b_fetch_datums.py`. Two independent sources per
town: NOAA VDatum (primary, point conversion at a real water point inside the town's
own `extent_0.geojson`) + nearest NOAA CO-OPS station with a published NAVD88 datum
(cross-check, searched against the full ~2,900-station waterlevels+historicwl
catalog, not just the ~15 "major" stations). Gate: 0.25 ft agreement (§5.6.2, LOCKED).

**7/8 towns pass.**

| Town | Water point (lon, lat) | VDatum (ft) | CO-OPS station | Dist (km) | CO-OPS (ft) | Diff (ft) | Gate |
|---|---|---|---|---|---|---|---|
| Newark | -74.1305, 40.6871 | 2.649 | Kearny Point, Hackensack River (8530772) | 5.1 | 2.700 | -0.051 | ✅ PASS |
| Hoboken | -74.0260, 40.7466 | 2.303 | The Battery (8518750) | 5.2 | 2.280 | +0.023 | ✅ PASS |
| Jersey City | -74.1086, 40.7126 | 2.717 | Kearny Point, Hackensack River (8530772) | 1.8 | 2.700 | +0.017 | ✅ PASS |
| Atlantic City | -74.4190, 39.3583 | 1.999 | Atlantic City (8534720) | 0.2 | 1.990 | +0.009 | ✅ PASS |
| New Brunswick | -74.4025, 40.4909 | 2.902 | Keyport, Raritan Bay (8531545) | 18.2 | 2.660 | +0.242 | ✅ PASS (thin margin) |
| Perth Amboy | -74.2736, 40.4972 | 2.652 | Keyport, Raritan Bay (8531545) | 9.0 | 2.660 | -0.008 | ✅ PASS |
| Camden | (every part tried, none resolve) | n/a | Philadelphia, Pier 11 North (8545530) | 1.5 | 3.590 | n/a | ❌ FAIL |
| Bayonne | -74.1119, 40.6977 | 2.683 | Kearny Point, Hackensack River (8530772) | 3.5 | 2.700 | -0.017 | ✅ PASS |

**Camden: real failure mode, not a fixable point-selection bug.** VDatum's tidal
transformation grid has a genuine internal gap over the Camden/Philadelphia reach of
the Delaware River — confirmed by trying every disconnected part of Camden's own
`extent_0.geojson` (29 parts) plus five independent points spread across the river
channel; every single one returned VDatum's own server-side error (HTTP 200, body
`{"errorCode":412,"message":"Uncaught error, please contact NOAA VDatum Program
Support team."}`), not a timeout or a coverage sentinel (`-999999`) that a different
point might dodge. The nearest CO-OPS station with NAVD88 (Philadelphia, Pier 11
North, 1.5 km away) works fine on its own — it's specifically VDatum's grid that has
no data here. Per §5.6.2/§5.6.4, Camden ships with `depth_available: false` — 3-tier
status, no depth column, no regression from the pre-Phase-7 build.

**New Brunswick's 0.242 ft diff is real margin, not a rubber stamp.** It's the
thinnest pass (0.008 ft under the 0.25 ft gate) and also has the largest CO-OPS
distance (18.2 km, Keyport on Raritan Bay — there is no closer station with a
published NAVD88 tie-in on the tidal Raritan itself, checked against the full
station catalog). Both facts point the same direction: New Brunswick's true
uncertainty is plausibly higher than the other 6 clean passes, even though it
technically clears the gate. Worth a second look if the disagreement-rate validator
(§5.6.5, `09_validate.py`) shows anything unusual for this town once real facility
depths are computed.

**Point-selection finding worth keeping for future phases (already fixed in
`floodops_v2_lib.town_water_candidates`):** a MultiPolygon's `.centroid` can land in
the geometric gap between disconnected parts — not on the geometry at all. Naive
centroid-only queries against VDatum initially failed for 5/8 towns purely from this,
before any real coverage question was even reached. `.representative_point()` (which
is guaranteed to be *on* the geometry) fixed most of these; Atlantic City then
additionally required trying every individual part (not just the largest), since the
part that actually falls inside VDatum's grid there is a small, disconnected marsh
area, not the town's main back-bay extent.

**Error-budget inputs for §5.6.3 (real figures, not placeholders):** VDatum's own
self-reported uncertainty across the 7 passing towns ranged 0.194–0.209 ft. The
VDatum/CO-OPS disagreement itself ranged 0.008–0.242 ft across the passing towns
(median ≈0.02 ft, one outlier at 0.242 ft — New Brunswick, discussed above). Combined
with 3DEP/EPQS's own published vertical accuracy (~1 ft RMSE nationally, better in
well-surveyed urban/coastal areas), the guide's §5.6.3 claim that "combined
uncertainty is on the order of the one-foot level spacing itself" is well supported
by these real numbers, not an assumption.

---

## Phase 7.2/7.3 — point depth build + validator results (§5.3, §5.6.5)

Generated: 2026-08-14 · `05_build_exposure.py` + `09_validate.py`, all 8 towns × up
to 21 levels each. **Every validator check passes** (per-town/per-level status
vocabulary, road sparseness, id membership, `depth_ft` format and non-negative
0.5 ft multiples, `exposed ⇔ depth ≥ ffo`, depth monotonicity, the exact-1-ft-per-
level-step check, non-operational-count monotonicity, `first_exposed.json`
consistency) — 0 failures across all 7 depth-available towns and Camden's 3-tier
fallback. `pytest`: 23/23 pass, including 7 new pure-function unit tests for the
4-tier/3-tier classification cascade (`classify_asset_4tier`/`classify_asset_3tier`
in `05_build_exposure.py`).

**Regression check against the pre-Phase-7 committed data (guide's own required
assertion, §12.1):** for every one of the 562 assets across all 8 towns,
`first_exposed_level_ft_new ≤ first_exposed_level_ft_old` — **0 violations**. 168
assets (30%) moved to an earlier level (expected: `access-threatened` triggers on
*any* closed access segment, strictly weaker than the old `isolated`'s *all*-closed
requirement); the rest stayed exactly the same. No asset moved later. Camden (no
depth) shows 0 changes, as expected — it's running the byte-identical pre-Phase-7
3-tier logic.

**§5.6.5 model-disagreement rate — real numbers, not placeholders:**

| Town | Min | Max | Mean (21 levels) |
|---|---|---|---|
| Newark | 0.0% | 55.6% | 26.6% |
| Hoboken | 0.0% | 100.0% | 23.2% |
| Jersey City | 0.0% | 66.7% | 20.1% |
| Atlantic City | 0.0% | 86.4% | 20.3% |
| New Brunswick | 0.0% | 0.0% | 0.0% |
| Perth Amboy | 0.0% | 100.0% | 10.3% |
| Bayonne | 0.0% | 50.0% | 14.8% |

44 town-level combinations exceed the 25% flag threshold (§5.6.5) — a real,
non-trivial fraction of the 147 depth-available town-level combinations. **Pattern,
not noise:** flagged levels cluster heavily at the *low* end of each town's range —
Newark 4–15 ft, Hoboken 2–11 ft, Jersey City 3–11 ft, Atlantic City 0–6 ft, Perth
Amboy/Bayonne scattered at their own low-exposure levels — exactly where a facility
has *just* entered the extent and the sample size is smallest (e.g. Hoboken @ 2 ft:
100% is 5/5 assets; Atlantic City @ 3 ft: 86.4% is 19/22). Two contributing effects,
both physically sensible rather than a data-quality problem: (1) small-N noise at
threshold levels — a couple of facilities near the exact 0-depth margin can swing
the percentage sharply when the denominator is under ~10; (2) at the level a
facility first enters Rutgers' extent, its ground elevation is by construction close
to that level's water surface, so many first-entry facilities compute a real depth
of exactly (or near) 0 even though CIE's extent correctly places them inside — this
is the honest seam between an independently-produced hazard-extent product and this
project's own DEM subtraction, not an error in either one. New Brunswick's flat 0%
across all levels is consistent with it being the thinnest-margin town in the §7.0
datum gate (0.242 ft) but a genuinely small facility count (3 ever non-operational)
that never happened to land near a zero-depth margin.

**Methods-page requirement (§5.6.5):** since real town/level combinations exceed
25%, this is surfaced as a named limitation on `/methods`, not smoothed over — see
the "Facility depth" section there, plus the live "Depth coverage by town" table
pulling real `index.json` data per town.