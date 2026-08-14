# FloodOps V2 — Operating Guide

**Project:** FloodOps V2 — Multi-Municipality Coastal Flood Exposure Explorer (New Jersey)
**Owner:** Abdul Kalam Azad Mustaq (ar.abdulkalam.mustaq@gmail.com)
**Guide version:** 1.1 — written 2026-07-22, amended 2026-08-08 (Amendment A1 — see §16 Changelog)
**Status:** Phases 0–7 complete and verified live in production. 7/8 towns have computed facility depth (Camden ships extent-only, §5.6.4 — a real VDatum coverage gap, not a disagreement). **Live:** https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/ (Cloudflare Workers). Repo: `github.com/abdul-kalam-m/floodops-v2`.
**Guide location (canonical):** `C:\Users\abdul\Desktop\Temporary Files\RUTGERS\6. PORTFOLIO\10. FLOODOPS V2\OPERATING_GUIDE.md`
**Prior project (internal reference only):** FloodOps v1 (`4. FLOODOPS\`, repo `C:\Users\abdul\Documents\GitHub\floodops`) established the design tokens, testing philosophy, and agent protocol this guide reuses — read its guide for those conventions; this guide only specifies what's **new or different**. **V1 and V2 are independent products with independent shipping decisions. No instruction in this guide assumes v1 is published, live, or presented alongside V2** — that assumption was retired 2026-08-08 (§16).

---

## 0. How to use this document

Written so a coding agent (Opus/Sonnet) can build the project across sessions with **no conversation history**.

1. Read this guide, then FloodOps v1's guide (`4. FLOODOPS\OPERATING_GUIDE.md`) for shared conventions, then `PROGRESS.md` in this repo's root once it exists.
2. One phase (§11) per session; meet all exit criteria before advancing.
3. This guide wins over v1's guide wherever they conflict — V2 is a deliberately different product (different hazard model, different exposure semantics, multi-town), not a v1 patch.
4. §13.3 items are hard-locked.

---

## 1. Project identity

### 1.1 What V2 is, and how it differs from v1

**One-liner:** A multi-town dashboard covering New Jersey's tidally-influenced municipalities, showing which critical facilities and roads fall inside Rutgers University's modeled coastal-inundation footprint at each of 21 water levels (0 to 20 ft above Mean Higher High Water, in 1 ft steps) — with a town picker, the same operations-report/CSV workflow as v1, and full honesty about how the hazard model and this project's own inference on top of it differ.

| | FloodOps v1 | FloodOps V2 |
|---|---|---|
| Hazard | NWS river-gauge FIM (riverine, one gauge) | Rutgers NJ Coastal Inundation Explorer — CIE (coastal/tidal, statewide product) |
| Scenario dimension | 5 NWS flood categories, gauge-relative stage (ft) | 21 fixed elevations (0–20 ft, whole-foot steps), ft **above MHHW** (a tidal datum) |
| Depth | Computed: `max(0, WSE − DEM)` inside extent | **Point depth at facilities only** (§5.6): same bathtub-within-extent method as v1, computed inside Rutgers' extents using a per-town MHHW→NAVD88 offset. Optional per town (§5.6.4) — degrades cleanly where the datum can't be verified. No depth surface, no road-segment depth, no map depth ramp — the map fill stays single-class (§8, §7.4). |
| Facility status | 4-tier, depth-graded | 4-tier where depth is available, 3-tier fallback otherwise (§5.3) |
| Road status | 4-tier, depth-graded | 2-tier, exposure-graded (§5.4) |
| Geography | One municipality (Bound Brook), locked | **Multiple municipalities**, town picker, registry-driven |
| Repo / deploy | `floodops` / floodops.pages.dev | **New, separate** repo and Pages project (§10) |

### 1.2 Why it exists (portfolio narrative)

v1 proved the single-town static-precompute pattern end to end. V2 proves the *harder* engineering problem the same pattern raises once you scale geography and swap hazard models: a registry-driven multi-town architecture, ingesting a real statewide open-data product (not a hand-picked gauge), and — critically — **being explicit about the seam between an authoritative published product and this project's own inference on top of it.** Rutgers' extents are the hazard model; the facility depths (§5.6) are FloodOps V2's own bathtub computation layered inside those extents, carrying their own error budget, labelled as such everywhere they appear, and reported at a precision that matches their real uncertainty rather than their floating-point one. The Methods page quantifies that error budget and reports how often the two models disagree (§5.6.5) instead of hiding the disagreement. V2 stands as its own project — not one half of a pair with v1. With this architecture and this honesty discipline, it is a strong standalone flagship candidate for the portfolio's Geospatial Intelligence section, independent of whether v1 ships.

### 1.3 Audiences

Same as v1 (§1.3 there): hiring managers/reviewers primarily; NJ coastal-resilience professionals as the credibility audience; the owner.

### 1.4 Success criteria (measurable)

- [ ] Phase 0 recon verifies actual per-level, per-town coverage for **≥ 4 candidate towns** (§3) against the live service; town set locked from towns that pass.
- [ ] Town picker loads a new town's data in one interaction; all UI (map, level slider, table, report) updates to that town, no stale-town data visible at any point.
- [ ] Level slider covers every level that town actually has data for (varies by town — do not assume all 21 for every town); moving it swaps the exposure layer and re-colors assets/roads in < 500 ms after cache warm.
- [ ] Every asset shows: category, address, ground elevation (EPQS — feeds point depth for towns with `depth_available: true`, §5.6; informational only otherwise), exposure status at the current level, and first level at which it becomes exposed.
- [ ] CSV export and printable report work per-town, per-level, and match on-screen numbers exactly (same contract as v1 §9, adapted per §9 below).
- [ ] Methods page explicitly states the extent hazard-model limitation, the MHHW datum caveat, and — for towns with computed facility depth — the depth error budget and model-disagreement rate (§5.6) in plain language. This is a hard gate, not optional polish.
- [ ] `data/MANIFEST.json` records lineage for every fetched artifact, including the exact ArcGIS layer IDs used per town/level, and the MHHW datum sources per town (§4.1 V6).
- [ ] Deployed to a **new** Cloudflare Pages project, independent of v1's.

---

## 2. Scope contract

### 2.1 In scope (v1 of this project — confusingly "V2" is the *product* version, not this build's phase-1 scope; be careful not to over-read)

- A curated set of NJ coastal/tidal municipalities (§3), not all 235 the service covers — Phase 0 recon picks the workable subset.
- The **whole-foot** inundation levels (0–20 ft above MHHW) the CIE service has data for, **per town** (varies; do not pad to 21 where a town has fewer). The 0 ft level is the MHHW baseline itself — **in scope** as of 2026-08-01 (owner decision, reversing the original 2026-07-22 exclusion below): it reads naturally as "current conditions, no added flood" against which 1–20 ft are the actual flood scenarios. Every half-foot level (0.5, 1.5, 2.5 … 20.5 ft) remains **explicitly out of scope for V2** (owner decision, 2026-07-22): whole-foot steps only, for a cleaner scenario set. Do not fetch or expose half-foot layers anywhere in this project.
- Extent-based exposure (§5) as the primary hazard signal for every town — facility/road status is always determined first by extent membership (§5.2), for every town, regardless of depth availability.
- **Per-asset point depth (§5.6)** as a secondary, optional refinement: computed only at facility points, only inside the level's extent, only for towns that pass the datum gate (§5.6.2); reported to the nearest 0.5 ft. Never a replacement for the extent test, never applied to roads, never a depth surface.
- Asset categories: same set as v1 (§7.3 of v1's guide), **plus** two additions that matter for coastal cities and are common in OSM: `airport` and `port` (Newark's anchor assets — Newark Liberty and Port Newark‑Elizabeth — must not be silently excluded by v1's category list).
- Town picker, per-town CSV/report, per-town Methods content where the numbers are town-specific.

### 2.2 Out of scope (hard — do not build)

- **No depth *surface*** — no DEM raster fetch, no gridded/contoured depth field, no depth-class polygons, no 4-class map ramp. The single-color exposure fill is locked (§8), for payload reasons (§7.4) — see §16. Point depth at facility locations is in scope per §5.6 and is the *only* depth permitted in this project.
- **No road-segment depth.** Road status stays 2-tier (§5.4). Do not sample elevations along road geometry; do not reintroduce v1's `caution`/`closed-all` scale or its 6 ft cap / `bridge_suspected` machinery.
- **No spatially-varying MHHW surface.** A single scalar MHHW→NAVD88 offset per town (§5.6.2) is the locked approximation. Do not interpolate a tidal-datum grid.
- No river/fluvial hazard modeling for any town in this project (that is v1's and FloodScope's domain). If a candidate town also has a relevant NWS gauge, ignore it here — V2 is coastal-only, on purpose, to keep the hazard model honest and singular.
- No backend, database, or server-side rendering — static-only, same as v1.
- No editing, migrating, or redeploying v1's `floodops` repo. It is not touched by this project.
- No claim of operational readiness (same disclaimer discipline as v1, reworded for exposure-only semantics, §5.7).

### 2.3 Stretch (only after Phase 7)

Depth **surface** upgrade (DEM raster per town → gridded depth → classed map ramp; requires solving the per-level payload problem, likely by moving extents from GeoJSON to raster tiles or PMTiles — do not attempt inside the current GeoJSON contract); road-segment depth and a 4-tier road scale; a spatially-varying MHHW grid replacing §5.6.2's per-town scalar; additional towns beyond the locked set; combining with v1/FloodScope's riverine model for towns that have both hazards.

---

## 3. Geography — town registry & candidates

### 3.1 Verified facts (already confirmed live against the service, 2026-07-22 — do not re-verify these, but do re-verify anything below marked "Phase 0 confirms")

- Service: `RU_NJ_CIE_Full` FeatureServer, `https://services1.arcgis.com/ze0XBzU1FXj94DJq/arcgis/rest/services/RU_NJ_CIE_Full/FeatureServer`. The **full** service has 84 layers = 42 elevation levels (0 to 20.5 ft above MHHW, 0.5 ft steps) × 2 (main extent + "Low-Lying Areas" companion, per level). **V2 uses only the whole-foot subset: 0 ft through 20 ft — 21 levels, 42 of the 84 layers** (owner decision, 2026-07-22, revised 2026-08-01 to include 0 ft, §2.1). Confirmed layer-naming pattern: whole-foot layers are named `"Rutgers NJ {N} ft. Coastal Inundation Extent"` (no `", 6 in."` substring) plus a `"..., Low-Lying Areas"` companion immediately after; half-foot layers are named `"Rutgers NJ {N} ft., 6 in. ..."`. **Exception: the 0 ft layer pair (ids 82/83) has an extra `" (Mean Higher High Water)"` suffix** not present on any other whole-foot level (verified against all 84 layer names live, 2026-08-01) — `WHOLE_FOOT_NAME_RE` must accept this suffix as optional (it never appears on levels 1–20). Confirmed layer-id pattern at time of writing: main-layer id = `82 − 4×level_ft` for whole-foot levels 0–20 (e.g. level 7 ft → id 54; level 0 ft → id 82), low-lying id = main id + 1 — **treat this as a convenience cross-check, not a stable contract**; the fetch script must resolve layer IDs by matching the name pattern above at runtime (exactly as v1's recon resolved gauges by querying, not by hardcoding NWPS lids), so a future service republish that renumbers layers doesn't silently break V2.
- Every feature carries `MUN`, `COUNTY`, `MUN_CODE` (plus `FID`, `Shape__Area`, `Shape__Length`) — **filterable server-side by municipality**, no spatial clip needed: `WHERE MUN='NEWARK CITY'`. `MUN` values are upper-case with the municipality-type suffix (`'NEWARK CITY'`, `'BOUND BROOK BORO'`), not the plain name — Phase 0 must fetch the distinct `MUN` list and match exactly.
- CRS: `wkid 103106` / `latestWkid 6527` (NAD83(2011) / New Jersey, US feet), `vcsWkid 105703` / `6360`. Reproject to EPSG:4326 for web output, same as v1.
- **Bound Brook has zero features at every level** (confirmed 2ft through the 20.5ft maximum) — it is above the tidal limit; this dataset cannot represent it. This is exactly why v1 and V2 are separate products.
- **Newark City has features at every level checked** (2/3/5/7 ft, both main and low-lying) — confirmed full-range coastal exposure, and it is the anchor town.
- New Brunswick City (a few miles downstream of Bound Brook on the Raritan, near the tidal limit) has features at both 2 ft and 7 ft — confirms the dataset's tidal reach extends that far up the Raritan.
- Only ~235 of NJ's 564 municipalities appear in the dataset at all (coastal + tidal-reach towns only) — "statewide" for this hazard model means "the tidal third of the state," not literally every town.
- Geometry is dense: Newark's single 2 ft main-extent feature alone has ~9,400 vertices (~356 KB raw GeoJSON). Simplification (same `shapely.simplify` approach as v1 §7.3) is mandatory, not optional, and budgets (§7.4) must account for this being heavier per-town than v1's single-gauge FIM extents.

### 3.2 Candidate towns (ranked; Phase 0 verifies actual per-level coverage + post-simplification size for each — this list is a proposal, not a lock)

1. **Newark City** — anchor, confirmed full coverage; airport, port, rail, highways — the richest asset story.
2. **Hoboken City** — small, dense, famous Sandy flood history; good complexity/size contrast to Newark.
3. **Jersey City** — large waterfront city, PATH, both Hudson and Newark Bay frontage.
4. **Atlantic City** — open-ocean-facing (different flood geometry than back-bay/harbor towns) — geographic diversity.
5. **New Brunswick City** — confirmed partial coverage; Raritan tidal limit.
6. **Perth Amboy City** — Raritan Bay confluence, historically significant coastal flooding, likely moderate complexity.
7. **Camden City** — Delaware River waterfront; different watershed than the NY-metro towns above (geographic diversity within the candidate set).
8. **Bayonne City** — small, Kill Van Kull/Newark Bay, industrial critical-infrastructure story.

**Initial target: Newark + 3–4 more that pass Phase 0 verification** (aim for 4–5 towns total in the first release; more can be added later without an architecture change, since the pipeline is registry-driven, §6). Do not add a town whose simplified per-town payload would blow the per-town budget (§7.4) — drop it and note why in `RECON.md`, exactly as v1's Phase 0 dropped Denville.

---

## 4. Data sources

### 4.1 Table

| # | Dataset | Access | Notes |
|---|---|---|---|
| V1 | Coastal inundation extents (all levels) | `RU_NJ_CIE_Full` FeatureServer, `WHERE MUN='<TOWN>'` per level layer, main + low-lying unioned | §3.1 — the only hazard-extent source in this project |
| V2 | Municipal boundary | Census TIGERweb County Subdivisions (same service v1 used, §2 of v1's guide) | reused verbatim |
| V3 | Critical facilities & community assets | OSM via Overpass, v1's category list **+ `airport`, `port`** | widen `CATEGORY_QUERIES` in the ported `04_fetch_assets.py` |
| V4 | Roads | OSM via Overpass (same as v1) | reused verbatim |
| V5 | Ground elevation at facility points | USGS EPQS (same as v1) | **Now a status input** (was "informational only" in guide v1.0) — feeds §5.6 depth math for towns that pass the datum gate. Phase 7.0 must verify **units and vertical datum explicitly** against the live service and record both in MANIFEST — do not assume feet, and do not assume NAVD88 without confirming. Roads are **not** elevation-sampled (§2.2). |
| V6 | MHHW→NAVD88 offset, per town | NOAA VDatum point transform (primary) + NOAA CO-OPS published station datums (cross-check) | One scalar per town (§5.6.2). Both sources recorded in MANIFEST with the tidal epoch. Fetched by `04b_fetch_datums.py`. |

No DEM **raster** fetch is required for V2 — point elevations come from EPQS at asset locations only. v1's `03_fetch_dem.py` equivalent stays unbuilt; a raster DEM is only needed by the deferred depth-*surface* work in §2.3.

### 4.2 Handling rules

Same as v1 §4.2 (raw gitignored, processed/committed budgeted, MANIFEST entry per artifact, idempotent + `--force`). One addition: MANIFEST entries for hazard data must record the **exact layer ID and town filter** used (e.g. `layer=54 (7ft main), WHERE MUN='NEWARK CITY'`), since a single ArcGIS service query is now the join key across town × level, and that mapping must be auditable.

---

## 5. Exposure model (LOCKED — changes require owner approval, §13.3)

This section replaces v1's §5 risk model. V2's hazard signal (§5.1–§5.2) is not a depth model — it stays extent in/out. On top of that, §5.6 adds a narrow, optional, quantified point-depth layer at facility locations only. Read the whole section as what it is: a hybrid of an authoritative extent product and this project's own bounded inference, not a lesser or full copy of v1's math.

### 5.1 Levels

Per town, the available levels are whichever of the 21 locked whole-foot levels (0–20 ft, §2.1/§3.1) the service returns non-empty features for (varies by town; Phase 0/1 discovers this per town, does not assume all 21). Each level's label is its elevation **in feet above MHHW** — display it as such, never imply NAVD88 or a gauge stage. No WSE, no zero-datum, no category labels like "Minor/Major" (those are v1's NWS vocabulary and do not apply here — do not reuse v1's `FLOOD_CATEGORY_LABEL` map or its concepts). The NAVD88 conversion used internally for §5.6's point depth is strictly internal to the pipeline and **must not** surface in this level vocabulary.

### 5.2 Extent construction

Per town × level: fetch the **main** extent layer and the **low-lying areas** companion layer (both filtered `WHERE MUN='<TOWN>'`), union them (a hydrologically-disconnected low spot below the level is still exposed, per Rutgers' own methodology note in the service description), `buffer(0)` to fix invalid rings, reproject to the analysis CRS. This mirrors v1's `06_fetch_fim.py` cumulative-union pattern structurally, but here each level is independently fetched (not built by cumulating lower levels) since the service already provides each level's full extent directly — **do not** assume monotonic nesting is something you need to construct; it should already hold level-to-level since these are cumulative bathtub fills by construction, but §12.1 must still test it, exactly as v1 did, because "should hold" is not "verified to hold."

### 5.3 Facility status

Two status models coexist, selected per town via `index.json`'s `status_model` field (§7.2), depending on whether that town passed the depth-availability gate (§5.6.4). Extent membership (§5.2) is always computed first and is always the primary signal in both models.

**4-tier (`status_model: "4-tier"`, towns with `depth_available: true`)** — `d` = point depth (§5.6.1). `ffo` = first-floor offset above ground, **default 1.0 ft** for all categories (no per-category table in this phase; the field exists per-asset in the schema for future override):

| Status (ordered, worst wins) | Condition |
|---|---|
| `exposed` | `d ≥ ffo` |
| `isolated` | not `exposed`, but every access road (§5.5, 120 m proximity rule) is `closed` per §5.4 |
| `access-threatened` | `0 < d < ffo`, or any access segment is `closed` |
| `operational` | otherwise |

**3-tier fallback (`status_model: "3-tier"`, towns with `depth_available: false`)**:

| Status | Condition |
|---|---|
| `exposed` | facility point falls inside the level's extent (§5.2), with the same 20 m source-alignment tolerance v1 used (§13.2 of v1's PROGRESS.md) — same rationale (OSM points vs. an independently-produced polygon product) |
| `isolated` | not exposed, but every access road (§5.5) is `closed` per §5.4 |
| `operational` | otherwise |

There is no `access-threatened` tier for these towns — it requires the point depth §5.6 does not compute for them. Do not invent a proxy for it.

**Naming decision:** the worst tier is labelled `exposed` in both models, not v1's `facility-flooded` — `exposed` was already shipped in the CSV contract, URL state, and report vocabulary before this amendment, and in the 4-tier model its condition now matches v1's `facility-flooded` exactly. The Methods page notes the label difference for towns with computed depth. Overridable by the owner, but do not "fix" it unasked.

### 5.4 Road status (2-tier)

| Status | Condition |
|---|---|
| `closed` | segment intersects the level's extent (with the same 20 m tolerance) |
| `open` | otherwise |

No `caution`/`closed-all` distinction — that graded scale was depth-derived in v1 (§5.4 there) and has no equivalent here, since road-segment depth is out of scope (§2.2). Do not invent one.

### 5.5 Access-loss rule

Identical to v1 §5.5A (proximity, 120 m, nearest-segment fallback) — reuse the code, only the road-status vocabulary feeding into it changes (§5.4 above).

### 5.6 Point depth at facilities (LOCKED — §13.3)

#### 5.6.1 Definition

Identical in form to v1 §5.2 Mode B, with the water surface derived from a datum conversion instead of a gauge reading:

```
WSE_navd88_ft(town, level) = MHHW_navd88_ft(town) + level_ft
d_ft(asset, level)         = max(0, WSE_navd88_ft − ground_elev_navd88_ft(asset))
```

`d_ft` is computed **only for assets whose point falls inside that level's extent** (§5.2, same 20 m tolerance). Outside the extent, `d_ft = 0` — never `null`, never negative. The extent remains the authority on *whether* a facility is exposed; the DEM point sample only ever answers *how deep*, and only inside a footprint Rutgers already drew.

Do not invert this. An asset outside the extent whose ground elevation happens to sit below WSE is **not** exposed — Rutgers' model has already accounted for hydrologic connectivity (and the low-lying companion layer, §5.2, already covers disconnected low spots). Trusting our elevation sample over their extent would be substituting a cruder model for a better one.

#### 5.6.2 The MHHW offset (the one new input)

One scalar per town, in feet, resolved in Phase 7.0:

1. **Primary:** NOAA VDatum point transform (MHHW → NAVD88) at the town centroid.
2. **Cross-check:** nearest NOAA CO-OPS tide station's published MHHW-on-NAVD88 datum.
3. **Gate:** the two must agree within **0.25 ft**. If they do not, that town **ships without depth** (§5.6.4) and the disagreement is recorded in `RECON.md`. Do not average them, do not pick the more convenient one, do not widen the tolerance to make a town pass.

Record per town in MANIFEST and in `index.json`: the offset, both source values, the CO-OPS station id, the tidal epoch, and the retrieval timestamp.

**A per-town scalar is a deliberate approximation.** MHHW varies little within one municipal footprint but varies materially between Newark Bay, Atlantic City, and the tidal Delaware at Camden. A single statewide constant is **prohibited** (§13.4).

#### 5.6.3 Reported precision

Depth is reported **rounded to the nearest 0.5 ft**, everywhere it appears — popup, table, CSV, report. Never more precisely.

Rationale, to be stated on the Methods page: the error budget stacks EPQS/3DEP vertical error, the per-town MHHW scalar approximation, and the fact that Rutgers' extents were produced from a different elevation model than the one being subtracted here. The combined uncertainty is on the order of the 1 ft level spacing itself. Reporting `4.3 ft` would assert a precision this method does not have. Phase 7.0 computes the itemized budget with real figures; the Methods page carries them.

#### 5.6.4 Per-town degradation (required — this is what makes the phase safe)

Depth is **optional per town**. A town failing §5.6.2's gate, or lacking verifiable EPQS datum/units, ships exactly as it did before this amendment: 3-tier status, no depth column, no regression.

- `index.json` gains `depth_available: bool`, `mhhw_navd88_ft: number|null`, `datum_source: object|null`.
- `depth_ft` is `null` (not `0`) for every asset in a town where `depth_available` is false.
- The UI **omits** the depth column entirely for such towns rather than rendering "N/A" — same precedent as §8's existing rule and v1 §9.2.
- `index.json` states which status model produced a town's data via `status_model: "3-tier" | "4-tier"` (§5.3).

#### 5.6.5 Model-disagreement reporting (required)

For each town × level, the validator computes and records:

```
depth_disagreement_rate = (# assets inside extent with d_ft == 0) / (# assets inside extent)
```

These are facilities Rutgers' model places inside the flood footprint but whose 3DEP ground elevation sits at or above our computed water surface — the visible seam between two independently-produced models. This number is **reported, never suppressed**:

- written per town × level into the validator output and `RECON.md`;
- if it exceeds **25%** at any level in any town, it becomes a **named limitation on the Methods page**, stated in plain language, and flagged in `PROGRESS.md`.

A high rate is a legitimate finding about model disagreement, not a bug to tune away. Do not adjust the MHHW offset, the tolerance, or the rounding to suppress it.

#### 5.6.6 Level 0 (MHHW baseline)

At level 0, WSE is MHHW itself, so `d_ft` reads as "depth below the mean higher high tide line" — real, but easily misread as flooding. The Methods page must state this explicitly, and the 0 ft level's report header must say **"MHHW baseline — no added flood"** wherever depth is shown at that level.

### 5.7 Honesty rules & standing disclaimer (verbatim; restyle, don't reword)

Every level, every asset popup, every report must make the hazard model's real character legible — never show a number that looks more precise or more authoritative than it is. Footer/report disclaimer:

> **Planning demonstration only — screening tool, not a survey and not a forecast.** FloodOps uses Rutgers University's NJ Coastal Inundation Explorer, a statewide static model referenced to Mean Higher High Water (MHHW), a local tidal datum. **The flood extents are Rutgers'. The depths shown at individual facilities are not** — they are computed by this project, by subtracting USGS 3DEP ground elevation from a flat water surface, using a single MHHW-to-NAVD88 offset per municipality. They are reported to the nearest half-foot because their uncertainty is on the order of the one-foot level spacing itself, and they must not be read as surveyed or measured depths. Water levels here are heights above a local tidal datum (MHHW), not flood stages from a river gauge. This is not an operational forecasting tool and must not be used for real-time emergency decisions. Consult the National Weather Service, NJDEP, and local emergency management for actual flood response.

Methods page must additionally explain, in plain language:
- what MHHW is and why it isn't NAVD88;
- that "isolated" facilities are computed from road exposure, not building-level surveys;
- that coverage is per-town and limited to NJ's tidal/coastal municipalities;
- the §5.6.1 depth formula, and an explicit statement of which layer came from Rutgers and which is this project's own computation;
- the itemized error budget from Phase 7.0, with real figures;
- the per-town MHHW offset table, with CO-OPS station, epoch, and both source values;
- the §5.6.5 disagreement rates, and what a high rate means;
- the §5.6.6 level-0 caveat;
- that a uniform 1.0 ft first-floor offset is assumed for all categories (towns with computed depth only) — an assumption, not a survey, and the single largest lever on the `exposed` / `access-threatened` boundary.

---

## 6. Architecture

### 6.1 Shape

Same two-part shape as v1 (Python pipeline → committed static JSON/GeoJSON → Vite/React/MapLibre static site), **generalized for multiple towns via a registry**, and simplified by dropping the DEM-raster/depth-surface stage entirely.

```
pipeline/
  00_recon.py            # verify candidate towns (§3.2) against the live service
  01_fetch_towns.py       # boundary + study area per town in the locked registry
  02_fetch_assets.py      # OSM assets per town (widened category list, §4.1 V3)
  03_fetch_roads.py       # OSM roads per town
  04_fetch_hazard.py      # per town x per available level: main+low-lying union -> extent
  04b_fetch_datums.py     # per-town MHHW->NAVD88 offset (VDatum + CO-OPS cross-check, §5.6.2)
  05_build_exposure.py    # §5 exposure engine (extent status + optional point depth) -> web data contracts (§7)
  09_validate.py          # §12.1 invariants, generalized across towns
```

Numbering intentionally does not match v1's 01–07 one-for-one (no gauge, no DEM **raster** stage — `04b`'s per-town datum scalar is not a DEM fetch) — do not try to preserve v1's script numbers for their own sake; preserve the *pattern* (idempotent, cached, `--force`, one script per concern). `04b`'s `b` suffix is deliberate: it preserves the already-committed numbering of `05`/`09` (referenced throughout `PROGRESS.md` and MANIFEST) while keeping the run order unambiguous: `00 → 01 → 02 → 03 → 04 → 04b → 05 → 09`. Do not renumber existing scripts.

**Assets/roads clip target (owner decision, 2026-08-01):** `01_fetch_towns.py`'s 1 km `study_area.geojson` buffer now only sizes the Overpass query envelope (generous on purpose, so real features right at the edge aren't dropped by too tight a bbox) — it is **not** the final keep/drop boundary. `02_fetch_assets.py`/`03_fetch_roads.py` clip their final output to `boundary.geojson` (the strict municipal polygon) instead. Reason: the flood layer's own extent (§5.2) never exceeds the municipal boundary either — it's an independent `MUN`-attribute filter on Rutgers' service, not spatially clipped to anything in this repo — so a road or asset left sitting in the old 1 km buffer zone would always render as "not flooded," even at the 20 ft scenario, which is indistinguishable on the map from a genuine no-flood finding when it's really just outside where hazard data exists at all. Do not revert to clipping against `study_area.geojson` for the final output without reopening this question.

### 6.2 Stack (LOCKED — same as v1, no changes)

Vite + React 18 + TypeScript strict + Tailwind v4 + MapLibre GL; pnpm; Cloudflare Pages. Python 3.11+ / uv for the pipeline. Reuse v1's `floodops_lib.py` patterns (cached HTTP, MANIFEST helper, ArcGIS-GeoJSON CRS-detection helper — **that CRS-autodetect fix from v1 is directly relevant here too**: verify whether `RU_NJ_CIE_Full` respects `outSR` or has the same Web-Mercator-mislabeling behavior v1's NWS_FIM service had, before trusting any `outSR` parameter — Phase 0 must check this explicitly, it is a known failure mode in this exact class of service). Phase 7 (§5.6) adds no new stack dependency — VDatum/CO-OPS lookups are plain HTTP calls via the existing `requests` dependency.

### 6.3 Multi-town data layout (the core new contract)

```
web/public/data/
  towns.json                      # registry: [{slug, name, county, center, bbox}]
  {town-slug}/
    index.json                    # per-town metadata + level list + depth availability (§5.6.4, §7.2)
    assets.geojson
    roads.geojson
    boundary.geojson
    first_exposed.json            # per-asset first level at which status != operational
    levels/
      exposure_{level}.json       # per-level asset/road statuses + summary + optional depth_ft (§7.3)
      extent_{level}.geojson      # per-level exposure polygon (renamed from v1's "inundation_")
```

`{level}` slug: same `.` → `_` convention as v1 (e.g. `exposure_3_0.json` for 3.0 ft). The web app fetches `towns.json` once, then lazily fetches only the selected town's `index.json` and the current level's files — **never eagerly fetch every town's data**, that's the whole point of the registry.

### 6.4 URL scheme

Hash-based, extending v1's pattern (no router library, §8.1 of v1's guide, unchanged): `#town=newark&level=3.0`. `/report` and `/methods` (real paths, same `_redirects` SPA-fallback requirement v1 established) take `?town=` and `?level=` query params — e.g. `/report?town=newark&level=3.0`.

---

## 7. Web data contracts

### 7.1 `towns.json`

`[{slug, name, county, muni_query_value ("NEWARK CITY"), center: [lat,lon], bbox: [w,s,e,n]}]` — drives the town picker without needing to fetch every town's full index.

### 7.2 Per-town `index.json`

`{town, county, state, levels: [{level_ft, wse_note: "ft above MHHW", files: {exposure, extent}}], hazard_source: "Rutgers NJ Coastal Inundation Explorer (2024)", depth_available: bool, status_model: "3-tier"|"4-tier", mhhw_navd88_ft: number|null, datum_source: {vdatum_ft, coops_station_id, coops_ft, epoch, retrieved_utc}|null, ffo_default_ft: 1.0, generated_utc}`. No `gauge` object, no `access_rule` (always proximity, no need to state it varies), no `fim_mode` (always "extent-only" — may include the field set to that literal string for schema parity with v1 if useful, but do not invent a fake "mode A/B" value).

### 7.3 Per-level files

`exposure_{level}.json`: `{level_ft, town, assets: {[id]: {status, access_lost, depth_ft}}, roads: {[id]: {status}}, summary: {by_asset_status, road_closed_count, road_closed_miles}}`.

`depth_ft` is present, rounded per §5.6.3, and is `null` (never `0`) for every asset in a town with `depth_available: false`. `0` means "computed, and the water surface does not reach this facility's ground elevation" — a real result, distinct from "not computed." Consumers must distinguish the two.

`extent_{level}.geojson`: the unioned, simplified exposure polygon (single class — there is no depth-class breakdown at the extent level; style it as a single fill color in the UI, not v1's 4-class blue ramp — locked for payload reasons, §7.4).

### 7.4 Budgets

Per-town budget: same per-file cap as v1 (≤ 800 KB) but a **larger per-town total cap, ≤ 5 MB**, reflecting denser coastal-city geometry (§3.1 — Newark's raw single-level extent alone is 356 KB before simplification; budget for that, don't assume v1's Bound Brook numbers transfer) across up to 21 levels. Total site budget: **≤ 5 MB × (number of locked towns) + towns.json**, loaded lazily per §6.3 — this is a *ceiling if every town's data were downloaded at once*, not the real user experience, which only ever loads one town at a time.

**Both numbers are measured in gzip-compressed size**, not raw/on-disk bytes (owner-confirmed correction, 2026-07-31, made consistent with v1's own §8.7 JS-bundle budget, which was already specified in gzip terms). Rationale, confirmed empirically on Newark's road network (11,142 segments, the densest in the locked town set): raw `roads.geojson` was 3.3 MB, comfortably over an 800 KB *raw* reading — but GeoJSON's repeated property keys and similar-magnitude coordinates compress 8–9× in practice, so the real transfer size (what Cloudflare Pages actually serves, and what governs load time) was 360 KB, comfortably under budget. Raw size may still be reported for transparency in build output, but it is **not** the pass/fail criterion — do not "fix" a raw-size overage by mangling the data model (dropping needed segments, over-aggressive dissolving) before checking the gzip number first.

Extent-polygon simplification tolerance is locked at **15 m** (`SIMPLIFY_M` in `05_build_exposure.py`) — empirically derived by testing 2/5/10/12/15/20/30/50 m on Newark's densest levels (Phase 0 flagged its raw 20 ft extent at ~54,700 vertices): 15 m keeps every per-level file's raw size ≤ ~270 KB (well under 800 KB even before gzip) while distorting extent area by < 1%, negligible next to the hazard model's own inherent uncertainty. Newark's single-class 20 ft extent already runs ~1.05 MB gzip against the 5 MB per-town budget — this is the concrete number behind §2.2's ban on a multi-class map ramp: a 4-class breakdown would multiply per-level vertex count 2.5–4× and would very likely break the GeoJSON contract, forcing a move to raster tiles or PMTiles (§2.3, deferred), which this phase does not take on.

Adding `depth_ft` to §7.3's per-asset object is negligible against this budget — one rounded float per asset per level, against a scale of roughly 100 assets per town. Re-measure at Phase 7 anyway; do not assume.

---

## 8. Web application spec (deltas from v1 — everything else reuses v1's §7–§8 verbatim)

- **New: `TownPicker` component** — dropdown or searchable list sourced from `towns.json`; changes the hash, triggers a full data reload for the new town (map re-fits bounds, level slider resets to that town's first available level).
- **`LevelSlider`** replaces v1's `StageSlider` — same interaction model, but ticks are that town's actual available levels (not a fixed 5), labeled `"X.X ft above MHHW"`, no category pill (there is no NWS category here).
- **Map fill**: single exposure color (pick one, e.g. a mid-blue). Locked for payload reasons (§7.4), not for portfolio-distinguishability — explicitly not a depth ramp.
- **`AssetPopup` / `AssetTable` / `ReportPage`**: for towns with `depth_available: true`, add a depth column rendered at half-foot precision, with a short inline note or tooltip attributing it to this project's own computation rather than Rutgers'. For towns with `depth_available: false`, **omit the column entirely** — do not render "N/A" (per v1's own precedent, §9.2 note, of only showing fields with real content).
- **Asset symbology**: the status scale goes from 3 colors to 4 for towns with depth. Reuse v1's existing four status color tokens (implementation convenience — same design-token source already shared per §6.2). Update `Legend` accordingly.
- **Disclaimer**: §5.7 text, on every page, plus the Methods page content specified there.
- **Display name (owner decision, 2026-08-11):** the deployed product presents itself as **"FloodOps"**, not "FloodOps V2" — window/tab titles (`index.html`, and every page's `document.title`), the dashboard header `<h1>`, the "← FloodOps dashboard" back-links on `/report`/`/methods`, the disclaimer, all Methods-page and report-header copy, and the downloaded CSV filename (`floodops_{town}_level{N}ft_{date}.csv`, no `-v2`) all drop the "V2" suffix. This is a **display-only** change — the project remains "FloodOps V2" in this guide, `PROGRESS.md`, the repo name (`floodops-v2`), `package.json`, and `wrangler.jsonc`'s Worker name; none of those are user-visible and none were touched. Do not let the two drift back into sync — the whole point is that the public product reads as a clean, single "FloodOps," while the engineering-side name stays disambiguated from v1.

---

## 9. Report generator spec (deltas from v1 §9)

Same shape (CSV + printable `/report`), adapted:
- CSV columns: `asset_id, name, category, address, ground_elev_ft, depth_ft, ffo_ft, status, access_lost, first_exposed_level_ft, town, level_ft, hazard_source, generated_utc` — `category_label` (v1's flood-category label) is dropped; `hazard_source` is the export-context field worth knowing. `depth_ft`/`ffo_ft` are empty (not `0`) for towns without computed depth.
- Report header states the town, the level (as "X.X ft above MHHW"), the hazard-source name, and — for towns with computed depth — the town's MHHW offset and its source, so any exported artifact is self-describing about the datum assumption. No WSE, no gauge, no access-rule line beyond "proximity, 120 m" if you want to keep it for transparency.
- Prepositioning watchlist: "at risk within the next 1 ft of rise" (not v1's 2 ft) — with whole-foot levels exactly 1 ft apart, this maps precisely to "becomes exposed at the next level up," the cleanest possible near-term window and a direct match to the level granularity, unlike v1's uneven NWS-category gaps. This is a deliberate parameter choice — record it as such if changed again later. Watchlist membership will shift for towns gaining the 4-tier model, since `access-threatened` now triggers earlier than the old `isolated`-only signal — expected, not a regression.

---

## 10. Repository

### 10.1 Location (LOCKED) — separate from v1, per owner decision

`C:\Users\abdul\Documents\GitHub\floodops-v2` (or an equivalently clear name the owner confirms at Phase 0 — do not reuse or branch off the `floodops` repo). New public GitHub repo. New Cloudflare Pages project (new project name, e.g. `floodops-v2` → `floodops-v2.pages.dev`), independent build/deploy from v1's.

### 10.2 Structure

```
floodops-v2/
├── OPERATING_GUIDE.md  PROGRESS.md  RECON.md  README.md
├── pipeline/            # per §6.1
├── web/                 # Vite app; public/data/ per §6.3
└── .github/workflows/
```

---

## 11. Phased build plan

| Phase | Work | Exit criteria |
|---|---|---|
| **0. Bootstrap + recon** | New repo/env; `00_recon.py`: verify §3.2 candidates' actual per-level coverage + post-simplification size against the live service; **also verify whether `RU_NJ_CIE_Full` mislabels its CRS the way v1's NWS_FIM service did** (§6.2) | `RECON.md` with per-candidate level-coverage table; town set locked (Newark + ≥3 more); CRS behavior documented |
| **1. Town + asset + road acquisition** | `01_fetch_towns.py`, `02_fetch_assets.py` (widened categories), `03_fetch_roads.py`, run per locked town | Every locked town has boundary/assets/roads; Newark's airport + port present in assets.geojson (the concrete proof the category widening worked) |
| **2. Hazard acquisition + exposure engine** | `04_fetch_hazard.py`, `05_build_exposure.py`, `09_validate.py` | All §7 contracts written per town per available level; monotonicity + budget invariants (§12.1) pass for every town |
| **3. Dashboard shell + town picker** | Vite app skeleton, `TownPicker`, `MapView` adapted for single-class exposure fill, `LevelSlider` | Switching towns fully reloads correct data with no stale-town artifacts; level slider reflects that town's real level set |
| **4. Simulator UX** | SummaryCards/AssetTable/AssetPopup adapted (3-tier/2-tier statuses, no depth columns), first-exposed display, URL scheme (§6.4) | §1.4 boxes for slider/table/popup met |
| **5. Reports** | CSV + `/report` + `/methods` per §9, disclaimer placement | Numbers match UI exactly per town/level; Methods page passes the honesty gate (§1.4) |
| **6. Hardening + launch** | a11y + perf checks, README, portfolio assets, new Cloudflare Pages deploy | All §1.4 boxes checked; production URL live, independent of v1's |
| **7. Point depth (Tier 1)** | **7.0** datum recon: verify EPQS units + vertical datum live; resolve MHHW per town via VDatum + CO-OPS; apply §5.6.2 gate; compute the §5.6.3 error budget; write findings to `RECON.md`. **7.1** `04b_fetch_datums.py`. **7.2** `05_build_exposure.py` → depth + 4-tier status + per-town degradation (§5.6.4). **7.3** `09_validate.py` → §12.1 additions. **7.4** web: depth column, 4th status color, legend, CSV, report. **7.5** Methods + disclaimer per §5.7. | Every locked town either has a gated, MANIFEST-recorded MHHW offset **or** is explicitly and visibly running in no-depth mode; §12.1 additions pass for every town; disagreement rates recorded per town × level; depth never displayed at finer than 0.5 ft anywhere; map fill still single-class; Methods page carries the real error budget, not placeholder text. |

---

## 12. Testing & verification

### 12.1 Pipeline assertions (generalized across towns — run per town, not just once)

Per town: extent monotonicity across that town's available levels (area non-decreasing — test it, don't assume it, §5.2); asset/road status severity non-decreasing across levels; `first_exposed.json` consistent with per-level statuses; every geometry EPSG:4326 and valid; per-town payload within §7.4 budget; MANIFEST has a layer-ID-and-`MUN`-filter entry for every hazard fetch. Cross-town: `towns.json` slugs match directory names exactly; no town's data references another town's files.

**Point-depth assertions (Phase 7, per town):**

- Every `depth_ft` is `null`, or a non-negative multiple of 0.5.
- `depth_ft > 0` implies the asset is inside that level's extent. (The converse does **not** hold — that gap is §5.6.5's disagreement rate, which is measured, not asserted away.)
- Depth is non-decreasing across ascending levels for every asset — same monotonicity discipline §5.2 already applies to extents.
- `d_ft(asset, level+1) − d_ft(asset, level)` equals 1.0 ft (within rounding) for any asset inside the extent at both levels — a direct consequence of a flat water surface rising in 1 ft steps, and a cheap check that the datum offset was applied consistently.
- Status/`depth_ft` agreement: `exposed` ⟺ `d ≥ ffo` for 4-tier towns.
- `depth_available: false` towns: every `depth_ft` is `null`, `status_model == "3-tier"`, no status is `access-threatened`.

**Regression assertion against the pre-Phase-7 data** (run once, at Phase 7, before overwriting): for every asset, `first_exposed_level_ft_new ≤ first_exposed_level_ft_old`. This should hold because `access-threatened` triggers on *any* closed access segment while the old `isolated` required *all* of them — a strictly weaker condition — and the `exposed` tier only ever narrows. If it fails for any asset, stop and investigate; do not accept the new value. Note in `PROGRESS.md` that `first_exposed` values are expected to shift downward for some assets and that this is Phase 7 working, not drift.

### 12.2 Web checks

Same CI shape as v1 (lint, typecheck, build, Playwright smoke, axe) — smoke test must include a **town switch** (load Newark, switch to a second town, assert the map/table/slider all reflect the new town and nothing from Newark lingers in state).

---

## 13. Instructions for coding agents

### 13.1 Session protocol

This guide → v1's guide (for shared conventions only) → `PROGRESS.md` → one phase → phase tests → PROGRESS entry → commit, push.

### 13.2 Decision rules (apply without asking)

A candidate town fails Phase 0 coverage/size checks → drop it, try the next ranked candidate, log why (mirrors v1's Denville precedent). `RU_NJ_CIE_Full` CRS-mislabels like v1's NWS_FIM did → apply the same coordinate-magnitude-detection fix from v1's `floodops_lib.arcgis_geojson`, don't re-derive a new approach. A town's simplified geometry still exceeds budget after standard simplification → increase simplification tolerance for that town specifically (record the tolerance used per town in MANIFEST), don't silently drop assets/roads to hit budget.

### 13.3 Never change without explicit owner approval

Project name and separateness from v1 (§1.1, §10.1 — do not merge into the `floodops` repo); the **depth boundary** (§2.2, §5.6): point depth at facility locations is permitted and specified; a depth *surface*, road-segment depth, a classed map ramp, and a spatially-varying MHHW grid are **not**, and adding any of them requires reopening §2.3 the way Amendment A1 reopened this section (§16). The single-color map fill (§8) is locked independently of this, for the payload/architecture reasons in §7.4 — not to distinguish V2 from v1. The 0.5 ft reporting precision (§5.6.3), the 0.25 ft datum gate (§5.6.2), and the 1.0 ft `ffo` default (§5.3) are owner-set parameters: changeable by the owner, never by an agent mid-build. Also locked: the status models (§5.3: 4-tier where depth is available, 3-tier fallback otherwise) and the 2-tier road model (§5.4); disclaimer wording (§5.7); the multi-town registry architecture (§6.3) — don't collapse it back to a single hardcoded town; repo/deploy independence from v1.

### 13.4 Prohibited at all times

Everything in v1's §13.4, plus: presenting V2's computed point depth as a **measured or surveyed** depth, or as part of Rutgers' published product; relabelling the level slider, level list, or any user-facing level value in NAVD88 (the NAVD88 conversion is strictly internal to §5.6 — levels stay MHHW-relative everywhere a user can see them); using a single MHHW offset across multiple towns; displaying depth at finer than 0.5 ft; suppressing or tuning away a §5.6.5 disagreement rate; introducing any depth value for road segments; touching the `floodops` (v1) repo or its Cloudflare Pages project; padding a town's level list to look like it has more coverage than the service actually returned; **naming or linking FloodOps v1 in any public-facing copy** (disclaimer, Methods page, README, case-study, site nav, report output).

---

## 14. Portfolio integration

FloodOps V2 is presented as its own project in the portfolio's Geospatial Intelligence section, independent of FloodOps v1's shipping status. Its case for inclusion stands on its own: a registry-driven, multi-town coastal-exposure dashboard built on a real statewide open-data product, with disclosed and quantified uncertainty in its facility-level depth estimates (§5.6). Case-study assets should screenshot the Methods-page limitations/error-budget section as evidence of the honesty discipline, on its own merits. **No public-facing copy — site nav, README, case-study text, disclaimer, Methods page, report output — may name or link FloodOps v1.**

---

## 15. Glossary (supplements v1's §15 — read that one too)

- **CIE** — Rutgers' Coastal Inundation Explorer, the source of all V2 hazard-extent data.
- **MHHW** — Mean Higher High Water: the average of the higher of the two daily high tides, computed per tidal station over a standard epoch. A **local** datum — it is not NAVD88, and the offset between them varies along the coast. V2 does not build a spatially-varying conversion between them; it uses one scalar offset per town (§5.6.2).
- **Extent / exposure model** — V2's hazard-extent representation: in-or-out of a modeled footprint, no depth. This part of the model is always extent-only, for every town. Distinct from v1's bathtub-depth model, and distinct from V2's own facility-level point depth (§5.6), which is not extent-only.
- **Point depth** — V2's only depth: `max(0, WSE − ground elevation)` at a facility point, inside a Rutgers extent (§5.6). Not a surface, not measured, not part of Rutgers' product.
- **MHHW offset** — the per-town scalar converting a level's height above MHHW into NAVD88 so it can be differenced against a ground-elevation sample (§5.6.2). One number per municipality; a deliberate approximation of a spatially-varying quantity.
- **Disagreement rate** — the share of assets inside a level's extent whose computed depth is 0 (§5.6.5); the measured seam between Rutgers' model and this project's elevation subtraction. Reported, never suppressed.
- **`ffo`** — first-floor offset above ground, default 1.0 ft, uniform across categories (§5.3). Inherited from v1 §5.3. An assumption, not a survey.
- **Low-lying areas (companion layer)** — Rutgers' term for hydrologically-disconnected low spots below a level's elevation that would also flood even though not contiguous with the main extent; unioned into V2's exposure footprint per level (§5.2).
- **Town registry** — `towns.json`, the multi-town equivalent of v1's single locked study area.

---

## 16. Changelog

**v1.0 (2026-07-22):** initial guide. Extent-only exposure, no depth anywhere; 3-tier facility / 2-tier road status for all towns; presented as a portfolio pair with v1.

**v1.1 — Amendment A1 (2026-08-08):** two independent changes, applied together because both arose in the same session.
- **Part 1 (Tier 1 point depth):** reopened §13.3's extent-only lock, narrowly. Added per-asset point depth at facilities (§5.6), using v2's already-fetched EPQS ground elevation plus one new input — a per-town MHHW→NAVD88 offset (§5.6.2), gated at 0.25 ft agreement between NOAA VDatum and CO-OPS. Restores the 4-tier facility status (§5.3) for towns that pass the gate; depth-optional degradation (§5.6.4) means a failing town ships exactly as v1.0 specified, no regression. Reported at 0.5 ft precision only (§5.6.3). Explicitly still out of scope: a depth surface/DEM raster, road-segment depth, and the 4-class map ramp (§2.2, §2.3) — the map fill stays single-class for payload reasons (§7.4: Newark's single-class 20 ft extent is already ~1.05 MB gzip of a 5 MB budget). New §5.6.5 requires reporting (never suppressing) the rate at which Rutgers' extent and this project's elevation subtraction disagree.
- **Part 2 (standalone portfolio framing):** retired the v1/v2 "pair" narrative (owner directive — v1's shipping status is undecided, V2 is the likelier flagship). Removed every public-facing reference to FloodOps v1 (disclaimer, Methods page, §1.1/§1.2 framing, §14 Portfolio integration); added a standing prohibition (§13.4) against naming or linking v1 in any public-facing copy. Internal engineering references to v1 (shared code/design-token conventions, §6.2) are unaffected.

**Phase 7 executed (2026-08-14, no guide version bump — this amendment's spec, above, did not change):** built and verified per §11's Phase 7 row. 7/8 towns pass the §5.6.2 datum gate; Camden ships extent-only (a genuine VDatum coverage gap, not a disagreement — see `RECON.md`). All §12.1 assertions and the regression check pass; disagreement rates (§5.6.5) are real and reported on `/methods`. Full details in `PROGRESS.md`, 2026-08-14 entry.

---

*End of guide. When in doubt: §13.2. When tempted to build anything beyond a Tier-1 point depth: don't — that's §13.3/§2.3.*
