# FloodOps V2 — Operating Guide

**Project:** FloodOps V2 — Multi-Municipality Coastal Flood Exposure Explorer (New Jersey)
**Owner:** Abdul Kalam Azad Mustaq (ar.abdulkalam.mustaq@gmail.com)
**Guide version:** 1.0 — written 2026-07-22
**Status:** Not started (no repository exists yet)
**Guide location (canonical):** `C:\Users\abdul\Desktop\Temporary Files\RUTGERS\6. PORTFOLIO\10. FLOODOPS V2\OPERATING_GUIDE.md`
**Sibling project:** FloodOps v1 (`4. FLOODOPS\`, repo `C:\Users\abdul\Documents\GitHub\floodops`, live at floodops.pages.dev) — **stays exactly as-is.** V2 is a **separate, independent deployment**, not a migration or replacement. Read v1's guide for shared conventions (design tokens, testing philosophy, agent protocol); this guide only specifies what's **new or different** in V2.

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

**One-liner:** A multi-town dashboard covering New Jersey's tidally-influenced municipalities, showing which critical facilities and roads fall inside Rutgers University's modeled coastal-inundation footprint at each of 21 water levels (0 to 20 ft above Mean Higher High Water, in 1 ft steps) — with a town picker, the same operations-report/CSV workflow as v1, and full honesty that this is an **exposure** (in/out) product, not a depth model.

| | FloodOps v1 | FloodOps V2 |
|---|---|---|
| Hazard | NWS river-gauge FIM (riverine, one gauge) | Rutgers NJ Coastal Inundation Explorer — CIE (coastal/tidal, statewide product) |
| Scenario dimension | 5 NWS flood categories, gauge-relative stage (ft) | 21 fixed elevations (0–20 ft, whole-foot steps), ft **above MHHW** (a tidal datum) |
| Depth | Computed: `max(0, WSE − DEM)` inside extent | **Not computed.** Extent-only: a point/segment is inside the level's footprint or it isn't. (§5.6 — a deliberate, documented simplification; owner-approved, no MHHW→NAVD88 conversion attempted.) |
| Facility status | 4-tier, depth-graded | 3-tier, exposure-graded (§5.3) |
| Road status | 4-tier, depth-graded | 2-tier, exposure-graded (§5.4) |
| Geography | One municipality (Bound Brook), locked | **Multiple municipalities**, town picker, registry-driven |
| Repo / deploy | `floodops` / floodops.pages.dev | **New, separate** repo and Pages project (§10) |

### 1.2 Why it exists (portfolio narrative)

v1 proved the single-town static-precompute pattern end to end. V2 proves the *harder* engineering problem the same pattern raises once you scale geography and swap hazard models: a registry-driven multi-town architecture, ingesting a real statewide open-data product (not a hand-picked gauge), and — critically — **being honest in the UI and Methods page about a coarser hazard representation** (extent-only vs. v1's computed depths) rather than papering over the difference. Presented as a pair with v1: "one deep, gauge-anchored simulation" vs. "one broad, state-open-data-anchored exposure screen." Flagship candidate, alongside v1, for the portfolio's Geospatial Intelligence section.

### 1.3 Audiences

Same as v1 (§1.3 there): hiring managers/reviewers primarily; NJ coastal-resilience professionals as the credibility audience; the owner.

### 1.4 Success criteria (measurable)

- [ ] Phase 0 recon verifies actual per-level, per-town coverage for **≥ 4 candidate towns** (§3) against the live service; town set locked from towns that pass.
- [ ] Town picker loads a new town's data in one interaction; all UI (map, level slider, table, report) updates to that town, no stale-town data visible at any point.
- [ ] Level slider covers every level that town actually has data for (varies by town — do not assume all 21 for every town); moving it swaps the exposure layer and re-colors assets/roads in < 500 ms after cache warm.
- [ ] Every asset shows: category, address, ground elevation (informational only, EPQS — not used in status math), exposure status at the current level, and first level at which it becomes exposed.
- [ ] CSV export and printable report work per-town, per-level, and match on-screen numbers exactly (same contract as v1 §9, adapted per §9 below).
- [ ] Methods page explicitly states the extent-only limitation and the MHHW datum caveat in plain language — this is a hard gate, not optional polish.
- [ ] `data/MANIFEST.json` records lineage for every fetched artifact, including the exact ArcGIS layer IDs used per town/level.
- [ ] Deployed to a **new** Cloudflare Pages project, independent of v1's.

---

## 2. Scope contract

### 2.1 In scope (v1 of this project — confusingly "V2" is the *product* version, not this build's phase-1 scope; be careful not to over-read)

- A curated set of NJ coastal/tidal municipalities (§3), not all 235 the service covers — Phase 0 recon picks the workable subset.
- The **whole-foot** inundation levels (0–20 ft above MHHW) the CIE service has data for, **per town** (varies; do not pad to 21 where a town has fewer). The 0 ft level is the MHHW baseline itself — **in scope** as of 2026-08-01 (owner decision, reversing the original 2026-07-22 exclusion below): it reads naturally as "current conditions, no added flood" against which 1–20 ft are the actual flood scenarios. Every half-foot level (0.5, 1.5, 2.5 … 20.5 ft) remains **explicitly out of scope for V2** (owner decision, 2026-07-22): whole-foot steps only, for a cleaner scenario set. Do not fetch or expose half-foot layers anywhere in this project.
- Extent-only exposure (§5) — no depth values, no MHHW→NAVD88 conversion work.
- Asset categories: same set as v1 (§7.3 of v1's guide), **plus** two additions that matter for coastal cities and are common in OSM: `airport` and `port` (Newark's anchor assets — Newark Liberty and Port Newark‑Elizabeth — must not be silently excluded by v1's category list).
- Town picker, per-town CSV/report, per-town Methods content where the numbers are town-specific.

### 2.2 Out of scope (hard — do not build)

- No depth computation, no MHHW surface acquisition, no NAVD88 conversion (§13.3 — locked by owner decision, not a technical judgment call; do not "improve" this later without asking).
- No river/fluvial hazard modeling for any town in this project (that is v1's and FloodScope's domain). If a candidate town also has a relevant NWS gauge, ignore it here — V2 is coastal-only, on purpose, to keep the hazard model honest and singular.
- No backend, database, or server-side rendering — static-only, same as v1.
- No editing, migrating, or redeploying v1's `floodops` repo. It is not touched by this project.
- No claim of operational readiness (same disclaimer discipline as v1, reworded for exposure-only semantics, §5.7).

### 2.3 Stretch (only after Phase 6)

MHHW→NAVD88 depth upgrade (explicitly deferred, not cancelled — if the owner later wants true depths, that's a new phase built on top of this one, requiring the Rutgers MHHW surface or an equivalent tidal-datum grid); additional towns beyond the initial set; combining with v1/FloodScope's riverine model for towns that have both hazards.

---

## 3. Geography — town registry & candidates

### 3.1 Verified facts (already confirmed live against the service, 2026-07-22 — do not re-verify these, but do re-verify anything below marked "Phase 0 confirms")

- Service: `RU_NJ_CIE_Full` FeatureServer, `https://services1.arcgis.com/ze0XBzU1FXj94DJq/arcgis/rest/services/RU_NJ_CIE_Full/FeatureServer`. The **full** service has 84 layers = 42 elevation levels (0 to 20.5 ft above MHHW, 0.5 ft steps) × 2 (main extent + "Low-Lying Areas" companion, per level). **V2 uses only the whole-foot subset: 0 ft through 20 ft — 21 levels, 42 of the 84 layers** (owner decision, 2026-07-22, revised 2026-08-01 to include 0 ft, §2.1). Confirmed layer-naming pattern: whole-foot layers are named `"Rutgers NJ {N} ft. Coastal Inundation Extent"` (no `", 6 in."` substring) plus a `"..., Low-Lying Areas"` companion immediately after; half-foot layers are named `"Rutgers NJ {N} ft., 6 in. ..."`. **Exception: the 0 ft layer pair (ids 82/83) has an extra `" (Mean Higher High Water)"` suffix** not present on any other whole-foot level (verified against all 84 layer names live, 2026-08-01) — `WHOLE_FOOT_NAME_RE` must accept this suffix as optional (it never appears on levels 1–20). Confirmed layer-id pattern at time of writing: main-layer id = `82 − 4×level_ft` for whole-foot levels 0–20 (e.g. level 7 ft → id 54; level 0 ft → id 82), low-lying id = main id + 1 — **treat this as a convenience cross-check, not a stable contract**; the fetch script must resolve layer IDs by matching the name pattern above at runtime (exactly as v1's recon resolved gauges by querying, not by hardcoding NWPS lids), so a future service republish that renumbers layers doesn't silently break V2.
- Every feature carries `MUN`, `COUNTY`, `MUN_CODE` (plus `FID`, `Shape__Area`, `Shape__Length`) — **filterable server-side by municipality**, no spatial clip needed: `WHERE MUN='NEWARK CITY'`. `MUN` values are upper-case with the municipality-type suffix (`'NEWARK CITY'`, `'BOUND BROOK BORO'`), not the plain name — Phase 0 must fetch the distinct `MUN` list and match exactly.
- CRS: `wkid 103106` / `latestWkid 6527` (NAD83(2011) / New Jersey, US feet), `vcsWkid 105703` / `6360`. Reproject to EPSG:4326 for web output, same as v1.
- **Bound Brook has zero features at every level** (confirmed 2ft through the 20.5ft maximum) — it is above the tidal limit; this dataset cannot represent it. This is exactly why v1 and V2 are separate products.
- **Newark City has features at every level checked** (2/3/5/7 ft, both main and low-lying) — confirmed full-range coastal exposure, and it is the anchor town.
- New Brunswick City (a few miles downstream of Bound Brook on the Raritan, near the tidal limit) has features at both 2 ft and 7 ft — confirms the dataset's tidal reach extends that far up the Raritan, and gives V2 a nice narrative bridge to v1 (same river, different reach, different hazard type) if picked as a candidate.
- Only ~235 of NJ's 564 municipalities appear in the dataset at all (coastal + tidal-reach towns only) — "statewide" for this hazard model means "the tidal third of the state," not literally every town.
- Geometry is dense: Newark's single 2 ft main-extent feature alone has ~9,400 vertices (~356 KB raw GeoJSON). Simplification (same `shapely.simplify` approach as v1 §7.3) is mandatory, not optional, and budgets (§7.4) must account for this being heavier per-town than v1's single-gauge FIM extents.

### 3.2 Candidate towns (ranked; Phase 0 verifies actual per-level coverage + post-simplification size for each — this list is a proposal, not a lock)

1. **Newark City** — anchor, confirmed full coverage; airport, port, rail, highways — the richest asset story.
2. **Hoboken City** — small, dense, famous Sandy flood history; good complexity/size contrast to Newark.
3. **Jersey City** — large waterfront city, PATH, both Hudson and Newark Bay frontage.
4. **Atlantic City** — open-ocean-facing (different flood geometry than back-bay/harbor towns) — geographic diversity.
5. **New Brunswick City** — confirmed partial coverage; Raritan tidal limit; narrative link to v1.
6. **Perth Amboy City** — Raritan Bay confluence, historically significant coastal flooding, likely moderate complexity.
7. **Camden City** — Delaware River waterfront; different watershed than the NY-metro towns above (geographic diversity within the candidate set).
8. **Bayonne City** — small, Kill Van Kull/Newark Bay, industrial critical-infrastructure story.

**Initial target: Newark + 3–4 more that pass Phase 0 verification** (aim for 4–5 towns total in the first release; more can be added later without an architecture change, since the pipeline is registry-driven, §6). Do not add a town whose simplified per-town payload would blow the per-town budget (§7.4) — drop it and note why in `RECON.md`, exactly as v1's Phase 0 dropped Denville.

---

## 4. Data sources

### 4.1 Table

| # | Dataset | Access | Notes |
|---|---|---|---|
| V1 | Coastal inundation extents (all levels) | `RU_NJ_CIE_Full` FeatureServer, `WHERE MUN='<TOWN>'` per level layer, main + low-lying unioned | §3.1 — the only hazard source in this project |
| V2 | Municipal boundary | Census TIGERweb County Subdivisions (same service v1 used, §2 of v1's guide) | reused verbatim |
| V3 | Critical facilities & community assets | OSM via Overpass, v1's category list **+ `airport`, `port`** | widen `CATEGORY_QUERIES` in the ported `04_fetch_assets.py` |
| V4 | Roads | OSM via Overpass (same as v1) | reused verbatim |
| V5 | Ground elevation (informational only — not used in exposure math) | USGS EPQS (same as v1) | kept for asset-popup display parity with v1; **must not** feed into status computation (§2.2) |

No DEM fetch is required for V2 (no depth computation) — a real simplification vs. v1's pipeline; skip v1's `03_fetch_dem.py` equivalent entirely unless a future MHHW-depth stretch phase needs it.

### 4.2 Handling rules

Same as v1 §4.2 (raw gitignored, processed/committed budgeted, MANIFEST entry per artifact, idempotent + `--force`). One addition: MANIFEST entries for hazard data must record the **exact layer ID and town filter** used (e.g. `layer=54 (7ft main), WHERE MUN='NEWARK CITY'`), since a single ArcGIS service query is now the join key across town × level, and that mapping must be auditable.

---

## 5. Exposure model (LOCKED — changes require owner approval, §13.3)

This section replaces v1's §5 risk model. It is **not** a depth model — read it as what it is, not as a lesser version of v1's math.

### 5.1 Levels

Per town, the available levels are whichever of the 21 locked whole-foot levels (0–20 ft, §2.1/§3.1) the service returns non-empty features for (varies by town; Phase 0/1 discovers this per town, does not assume all 21). Each level's label is its elevation **in feet above MHHW** — display it as such, never imply NAVD88 or a gauge stage. No WSE, no zero-datum, no category labels like "Minor/Major" (those are v1's NWS vocabulary and do not apply here — do not reuse v1's `FLOOD_CATEGORY_LABEL` map or its concepts).

### 5.2 Extent construction

Per town × level: fetch the **main** extent layer and the **low-lying areas** companion layer (both filtered `WHERE MUN='<TOWN>'`), union them (a hydrologically-disconnected low spot below the level is still exposed, per Rutgers' own methodology note in the service description), `buffer(0)` to fix invalid rings, reproject to the analysis CRS. This mirrors v1's `06_fetch_fim.py` cumulative-union pattern structurally, but here each level is independently fetched (not built by cumulating lower levels) since the service already provides each level's full extent directly — **do not** assume monotonic nesting is something you need to construct; it should already hold level-to-level since these are cumulative bathtub fills by construction, but §12.1 must still test it, exactly as v1 did, because "should hold" is not "verified to hold."

### 5.3 Facility status (3-tier — simpler than v1's 4-tier by necessity)

| Status | Condition |
|---|---|
| `exposed` | facility point falls inside the level's extent (§5.2), with the same 20 m source-alignment tolerance v1 used (§13.2 of v1's PROGRESS.md) — carry that constant forward, same rationale (OSM points vs. an independently-produced polygon product) |
| `isolated` | not exposed, but every access road (§5.5, same 120 m proximity rule as v1) is `closed` per §5.4 |
| `operational` | otherwise |

There is no `access-threatened` tier — that tier in v1 existed to represent shallow/partial water, which requires a depth value V2 deliberately does not compute. Do not invent a proxy for it.

### 5.4 Road status (2-tier)

| Status | Condition |
|---|---|
| `closed` | segment intersects the level's extent (with the same 20 m tolerance) |
| `open` | otherwise |

No `caution`/`closed-all` distinction — that graded scale was depth-derived in v1 (§5.4 there) and has no extent-only equivalent. Do not invent one.

### 5.5 Access-loss rule

Identical to v1 §5.5A (proximity, 120 m, nearest-segment fallback) — reuse the code, only the road-status vocabulary feeding into it changes (§5.4 above).

### 5.6 Honesty rules & standing disclaimer (verbatim; restyle, don't reword)

Every level, every asset popup, every report must make the extent-only nature legible — never show a number that looks like a depth. Footer/report disclaimer:

> **Planning demonstration only — exposure screening, not a depth model.** FloodOps V2 uses Rutgers University's NJ Coastal Inundation Explorer, a statewide static model referenced to Mean Higher High Water (MHHW), a local tidal datum. This dashboard shows whether an asset or road falls inside a modeled inundation footprint at a given water level — it does **not** compute flood depth, and levels are not directly comparable to NWS river-gauge flood stages (see FloodOps v1) or to elevations in NAVD88. It is not an operational forecasting tool and must not be used for real-time emergency decisions. Consult the National Weather Service, NJDEP, and local emergency management for actual flood response.

Methods page must additionally explain, in plain language: what MHHW is and why it isn't NAVD88; that "isolated" facilities are computed from road exposure, not building-level surveys; that first-floor height is not modeled at all here (unlike v1) because there is no depth to compare it against; and that coverage is per-town and does not extend to non-tidal parts of NJ (link to v1 for a riverine example).

---

## 6. Architecture

### 6.1 Shape

Same two-part shape as v1 (Python pipeline → committed static JSON/GeoJSON → Vite/React/MapLibre static site), **generalized for multiple towns via a registry**, and simplified by dropping the DEM/depth stage entirely.

```
pipeline/
  00_recon.py            # verify candidate towns (§3.2) against the live service
  01_fetch_towns.py       # boundary + study area per town in the locked registry
  02_fetch_assets.py      # OSM assets per town (widened category list, §4.1 V3)
  03_fetch_roads.py       # OSM roads per town
  04_fetch_hazard.py      # per town x per available level: main+low-lying union -> extent
  05_build_exposure.py    # §5 exposure engine -> web data contracts (§7)
  09_validate.py          # §12.1 invariants, generalized across towns
```

Numbering intentionally does not match v1's 01–07 one-for-one (no gauge, no DEM stage) — do not try to preserve v1's script numbers for their own sake; preserve the *pattern* (idempotent, cached, `--force`, one script per concern).

**Assets/roads clip target (owner decision, 2026-08-01):** `01_fetch_towns.py`'s 1 km `study_area.geojson` buffer now only sizes the Overpass query envelope (generous on purpose, so real features right at the edge aren't dropped by too tight a bbox) — it is **not** the final keep/drop boundary. `02_fetch_assets.py`/`03_fetch_roads.py` clip their final output to `boundary.geojson` (the strict municipal polygon) instead. Reason: the flood layer's own extent (§5.2) never exceeds the municipal boundary either — it's an independent `MUN`-attribute filter on Rutgers' service, not spatially clipped to anything in this repo — so a road or asset left sitting in the old 1 km buffer zone would always render as "not flooded," even at the 20 ft scenario, which is indistinguishable on the map from a genuine no-flood finding when it's really just outside where hazard data exists at all. Do not revert to clipping against `study_area.geojson` for the final output without reopening this question.

### 6.2 Stack (LOCKED — same as v1, no changes)

Vite + React 18 + TypeScript strict + Tailwind v4 + MapLibre GL; pnpm; Cloudflare Pages. Python 3.11+ / uv for the pipeline. Reuse v1's `floodops_lib.py` patterns (cached HTTP, MANIFEST helper, ArcGIS-GeoJSON CRS-detection helper — **that CRS-autodetect fix from v1 is directly relevant here too**: verify whether `RU_NJ_CIE_Full` respects `outSR` or has the same Web-Mercator-mislabeling behavior v1's NWS_FIM service had, before trusting any `outSR` parameter — Phase 0 must check this explicitly, it is a known failure mode in this exact class of service).

### 6.3 Multi-town data layout (the core new contract)

```
web/public/data/
  towns.json                      # registry: [{slug, name, county, center, bbox}]
  {town-slug}/
    index.json                    # per-town metadata + level list (mirrors v1's index.json shape,
                                   #   minus "gauge", plus "levels: [{level_ft, files}]")
    assets.geojson
    roads.geojson
    boundary.geojson
    first_exposed.json            # per-asset first level at which status != operational
    levels/
      exposure_{level}.json       # per-level asset/road statuses + summary (renamed from v1's
                                   #   "impacts_" to avoid implying a depth-impact model)
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

`{town, county, state, levels: [{level_ft, wse_note: "ft above MHHW", files: {exposure, extent}}], hazard_source: "Rutgers NJ Coastal Inundation Explorer (2024)", generated_utc}`. No `gauge` object, no `access_rule` (always proximity, no need to state it varies), no `fim_mode` (always "extent-only" — may include the field set to that literal string for schema parity with v1 if useful, but do not invent a fake "mode A/B" value).

### 7.3 Per-level files

`exposure_{level}.json`: `{level_ft, town, assets: {[id]: {status, access_lost}}, roads: {[id]: {status}}, summary: {by_asset_status, road_closed_count, road_closed_miles}}` — note: **no `depth_ft` field anywhere in this contract.** Its absence is the point; do not add a placeholder/zero depth field that could be mistaken for real data.

`extent_{level}.geojson`: the unioned, simplified exposure polygon (single class — there is no depth-class breakdown since there's no depth; style it as a single fill color in the UI, not v1's 4-class blue ramp).

### 7.4 Budgets

Per-town budget: same per-file cap as v1 (≤ 800 KB) but a **larger per-town total cap, ≤ 5 MB**, reflecting denser coastal-city geometry (§3.1 — Newark's raw single-level extent alone is 356 KB before simplification; budget for that, don't assume v1's Bound Brook numbers transfer) across up to 21 levels. Total site budget: **≤ 5 MB × (number of locked towns) + towns.json**, loaded lazily per §6.3 — this is a *ceiling if every town's data were downloaded at once*, not the real user experience, which only ever loads one town at a time.

**Both numbers are measured in gzip-compressed size**, not raw/on-disk bytes (owner-confirmed correction, 2026-07-31, made consistent with v1's own §8.7 JS-bundle budget, which was already specified in gzip terms). Rationale, confirmed empirically on Newark's road network (11,142 segments, the densest in the locked town set): raw `roads.geojson` was 3.3 MB, comfortably over an 800 KB *raw* reading — but GeoJSON's repeated property keys and similar-magnitude coordinates compress 8–9× in practice, so the real transfer size (what Cloudflare Pages actually serves, and what governs load time) was 360 KB, comfortably under budget. Raw size may still be reported for transparency in build output, but it is **not** the pass/fail criterion — do not "fix" a raw-size overage by mangling the data model (dropping needed segments, over-aggressive dissolving) before checking the gzip number first.

Extent-polygon simplification tolerance is locked at **15 m** (`SIMPLIFY_M` in `05_build_exposure.py`) — empirically derived by testing 2/5/10/12/15/20/30/50 m on Newark's densest levels (Phase 0 flagged its raw 20 ft extent at ~54,700 vertices): 15 m keeps every per-level file's raw size ≤ ~270 KB (well under 800 KB even before gzip) while distorting extent area by < 1%, negligible next to the hazard model's own inherent uncertainty.

---

## 8. Web application spec (deltas from v1 — everything else reuses v1's §7–§8 verbatim)

- **New: `TownPicker` component** — dropdown or searchable list sourced from `towns.json`; changes the hash, triggers a full data reload for the new town (map re-fits bounds, level slider resets to that town's first available level).
- **`LevelSlider`** replaces v1's `StageSlider` — same interaction model, but ticks are that town's actual available levels (not a fixed 5), labeled `"X.X ft above MHHW"`, no category pill (there is no NWS category here).
- **Map fill**: single exposure color (pick one, e.g. a mid-blue, distinct from v1's 4-class ramp so a viewer can never confuse a V2 screenshot for a v1 depth map), `AssetPopup`/`AssetTable`/`ReportPage` all drop any depth column, add nothing in its place (don't backfill with "N/A" columns — just omit the column, per v1's own precedent, §9.2 note, of only showing fields with real content).
- **Disclaimer**: §5.6 text, on every page, plus the Methods page content specified there.

---

## 9. Report generator spec (deltas from v1 §9)

Same shape (CSV + printable `/report`), adapted:
- CSV columns: `asset_id, name, category, address, ground_elev_ft, status, access_lost, first_exposed_level_ft, town, level_ft, hazard_source, generated_utc` — `depth_ft` and `category_label` (which was v1's flood-category label) are dropped; `hazard_source` replaces them as the export-context field worth knowing.
- Report header states the town, the level (as "X.X ft above MHHW"), and the hazard-source name — no WSE, no gauge, no access-rule line beyond "proximity, 120 m" if you want to keep it for transparency.
- Prepositioning watchlist: "at risk within the next 1 ft of rise" (not v1's 2 ft) — with whole-foot levels exactly 1 ft apart, this maps precisely to "becomes exposed at the next level up," the cleanest possible near-term window and a direct match to the level granularity, unlike v1's uneven NWS-category gaps. This is a deliberate parameter choice — record it as such if changed again later.

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

---

## 12. Testing & verification

### 12.1 Pipeline assertions (generalized across towns — run per town, not just once)

Per town: extent monotonicity across that town's available levels (area non-decreasing — test it, don't assume it, §5.2); asset/road status severity non-decreasing across levels; `first_exposed.json` consistent with per-level statuses; every geometry EPSG:4326 and valid; per-town payload within §7.4 budget; MANIFEST has a layer-ID-and-`MUN`-filter entry for every hazard fetch. Cross-town: `towns.json` slugs match directory names exactly; no town's data references another town's files.

### 12.2 Web checks

Same CI shape as v1 (lint, typecheck, build, Playwright smoke, axe) — smoke test must include a **town switch** (load Newark, switch to a second town, assert the map/table/slider all reflect the new town and nothing from Newark lingers in state).

---

## 13. Instructions for coding agents

### 13.1 Session protocol

This guide → v1's guide (for shared conventions only) → `PROGRESS.md` → one phase → phase tests → PROGRESS entry → commit, push.

### 13.2 Decision rules (apply without asking)

A candidate town fails Phase 0 coverage/size checks → drop it, try the next ranked candidate, log why (mirrors v1's Denville precedent). `RU_NJ_CIE_Full` CRS-mislabels like v1's NWS_FIM did → apply the same coordinate-magnitude-detection fix from v1's `floodops_lib.arcgis_geojson`, don't re-derive a new approach. A town's simplified geometry still exceeds budget after standard simplification → increase simplification tolerance for that town specifically (record the tolerance used per town in MANIFEST), don't silently drop assets/roads to hit budget.

### 13.3 Never change without explicit owner approval

Project name and separateness from v1 (§1.1, §10.1 — do not merge into the `floodops` repo); the extent-only decision (§5, §2.2 — do not add depth computation or attempt MHHW→NAVD88 conversion without the owner explicitly reopening that question); the 3-tier/2-tier status model (§5.3/§5.4); disclaimer wording (§5.6); the multi-town registry architecture (§6.3) — don't collapse it back to a single hardcoded town; repo/deploy independence from v1.

### 13.4 Prohibited at all times

Everything in v1's §13.4, plus: presenting any V2 number as a depth or implying NAVD88 comparability; touching the `floodops` (v1) repo or its Cloudflare Pages project; padding a town's level list to look like it has more coverage than the service actually returned.

---

## 14. Portfolio integration

Presented as a **pair with v1**, not a replacement: "FloodOps (one gauge, deep simulation) and FloodOps V2 (many towns, broad exposure screening) — two honest takes on the same problem, using two different classes of public flood data." Case-study assets should explicitly screenshot the Methods-page limitations section as evidence of the honesty discipline carried across both projects.

---

## 15. Glossary (supplements v1's §15 — read that one too)

- **CIE** — Rutgers' Coastal Inundation Explorer, the source of all V2 hazard data.
- **MHHW** — Mean Higher High Water: the average of the higher of the two daily high tides, computed per tidal station over a standard epoch. A **local** datum — it is not NAVD88, and the offset between them varies along the coast. V2 deliberately does not convert between them (§5).
- **Extent-only / exposure model** — this project's hazard representation: in-or-out of a modeled footprint, no depth. Distinct from v1's bathtub-depth model.
- **Low-lying areas (companion layer)** — Rutgers' term for hydrologically-disconnected low spots below a level's elevation that would also flood even though not contiguous with the main extent; unioned into V2's exposure footprint per level (§5.2).
- **Town registry** — `towns.json`, the multi-town equivalent of v1's single locked study area.

---

*End of guide. When in doubt: §13.2. When tempted to compute a depth: don't — that's §13.3.*
