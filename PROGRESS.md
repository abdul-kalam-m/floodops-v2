# FloodOps V2 — Progress Log

Newest entry on top. Never delete entries. Format per OPERATING_GUIDE.md §13.5 (v1's convention, reused).

---

## 2026-08-01 — Phase 6: a11y (axe) checks (agent: sonnet-5)

**No existing axe/Playwright infrastructure to reuse.** Checked v1's repo first, per the
guide's "same CI shape as v1" instruction (§12.2) — v1 never actually built this either
(its own guide's Phase 7 was never executed; `web/package.json` and `.github/workflows/ci.yml`
both only run lint/typecheck/build, no axe/Lighthouse/Playwright anywhere). So this was a
real, ad-hoc scan against the live app, not a rerun of established tooling: injected real
axe-core 4.10.0 into the Browser pane against the production build and ran it against the
dashboard (two towns, several levels), `/report`, and `/methods`.

**Found and fixed 5 real issues, all now verified clean (0 violations) on every page checked:**
1. **Color contrast, `AssetTable`'s facility count + empty state** (serious violation):
   `text-gray-400` (2.60:1 against white) — computed precisely (WCAG relative-luminance
   formula, not eyeballed) that `gray-500` (4.84:1) clears the 4.5:1 AA threshold on true
   opaque white.
2. **Same `text-gray-400` pattern in `ReportPage`/`LevelSlider`/`Legend`** — same fix, but
   caught a real subtlety: `LevelSlider`/`Legend` sit on `bg-white/95` translucent panels
   *over the map*, not opaque white. `gray-500`'s 4.84:1 margin (already thin) actually
   **failed** there (4.36:1 against the composited `#f3f3f4` backdrop observed live) —
   caught by re-scanning a second town (Hoboken) where different content happened to be
   in-viewport at scan time, not by the first (Newark) scan. Fixed by going one step darker,
   `gray-600` (6.1–7.6:1 even against a much darker `#e5e7eb` worst case), for real margin
   on a background that isn't guaranteed to be pure white. `AssetTable`/`ReportPage` stay on
   `gray-500` since they're confirmed on true opaque white (`getComputedStyle` checked
   directly, not assumed).
3. **`scrollable-region-focusable`**: the facility table's scrolling container had no
   keyboard access. Added `tabIndex={0}` + `role="region"` + `aria-label="Facilities table"`.
4. **`landmark-one-main` + `region`, `/report` and `/methods`**: neither page had a `<main>`
   landmark — both were a bare `<div>` at the root. Changed both to `<main>`.
5. **`link-in-text-block`, `/methods`**: the inline "FloodOps v1" link in the Coverage
   section was distinguished from surrounding prose text by color alone (`hover:underline`
   only shows on hover) — fails WCAG 1.4.1. Made the underline permanent.

**Methodology note, since this environment has previously had rendering-verification
issues:** confirmed each fix against the actual rebuilt production bundle, not just the
source diff — checked the dist JS/CSS hash changed, and once hit a false "still failing"
result that turned out to be a stale in-page SPA state from a hash-only `navigate` call
(changing `#town=...` without a real page reload) rather than a real regression; resolved
by forcing an unambiguous fresh load (cache-busting query param) and confirmed clean
immediately after. Also cross-checked axe's "incomplete" color-contrast bucket (417 nodes,
mostly off-screen/scrolled facility-table rows axe couldn't fully verify) by reading
`getComputedStyle` directly on a sample — actual rendered color is near-black
(`rgb(17,24,39)`) on white, genuinely fine; not a hidden real issue, just an artifact of
axe being conservative about elements outside the scrollable viewport at scan time.

**Final state, verified across every page tested:** 0 violations. `tsc`/`eslint` clean,
JS bundle unchanged (276.58 KB gzip — class-name-only changes).

**⚠ Deviations / open items:** this was a manual, ad-hoc verification pass, not a
permanent CI gate — no `@axe-core/playwright` (or similar) was added to
`package.json`/`.github/workflows/ci.yml`, since that's a meaningfully larger addition
(new dependency, new CI job, ongoing maintenance surface) that wasn't explicitly asked
for. If a permanent, repeatable a11y gate is wanted later, that's a distinct follow-on
decision, not implied by this entry.

---

## 2026-08-01 — Clip assets/roads to municipal boundary, not the 1 km buffer (owner request, agent: sonnet-5)

**Owner's reasoning (correct, and a real honesty issue, not just a cosmetic one):** the flood
layer's own extent never exceeds the municipal boundary (it's an independent `MUN`-attribute
filter on Rutgers' service, not spatially clipped to anything in this repo). Assets/roads,
though, were being kept out to a 1 km buffer beyond that same boundary. A road or facility
sitting in that buffer zone would always show "not flooded," even at the 20 ft scenario —
visually indistinguishable from a genuine no-flood finding, when it's really just outside
where hazard data exists at all. Fixed by changing the final keep/drop check.

**Changed:**
- `02_fetch_assets.py`: the point-containment filter now uses `boundary.geojson`
  (`boundary_geom.contains(pt)`) instead of `study_area.geojson`. The 1 km buffer is kept
  *only* to size the Overpass query bbox (generous on purpose, so a real edge feature isn't
  dropped by too tight a box) — it no longer decides what's kept.
- `03_fetch_roads.py`: same change, `line_utm.intersection(boundary_utm)` instead of
  `study_utm`. Roads that cross the boundary are now trimmed exactly at the line, same as
  the flood layer's own edge behavior.
- Re-ran `02` → `03` → `05_build_exposure.py` → `09_validate.py` for all 8 towns. Overpass
  responses were already cached (same bbox, same categories — only the local filter logic
  changed), so re-fetching was fast. **1554/1554 validator checks pass**, 15/15 pytest.
- **Verified the clip rigorously, not just by inspection:** ran a true polygon-containment
  check (`geometry.within(boundary.buffer(tiny_epsilon))`, not a bounding-box proxy) across
  every road and asset in all 8 towns. **0 features outside the boundary anywhere** (7,020
  Newark road segments, 177 Newark assets, down to Hoboken's 521/33 — all towns, zero
  exceptions).
- Counts dropped meaningfully for compact towns where the 1 km buffer was proportionally
  large relative to the town itself: Newark 263→177 assets (11,142→7,020 road segments,
  continuing the trend from the earlier road-ordering fix's count), Hoboken 61→33 assets
  (521 segments, notably **0 km of priority-class road** inside Hoboken's strict boundary —
  its motorway/trunk/primary roads apparently all sit just outside the town line). Gzip
  budgets dropped too (Newark: 990.9 → 861.4 KB total), still comfortably under the 5 MB cap.
- **Notable finding, worth keeping for the eventual case study:** with the buffer gone,
  Hoboken (33/33) and Atlantic City (46/46) both now show **100% of their remaining assets**
  eventually exposed by the 20 ft scenario — every single facility inside the strict boundary
  becomes non-operational at some level. New Brunswick stays at 0/38 (upstream tidal-limit
  town, consistent with before — removing far-away buffer assets can only hold or shrink an
  already-zero count, never grow it).
- `OPERATING_GUIDE.md` updated (new paragraph after the §6.1 script list documenting the
  locked clip-target decision) and re-synced to the canonical portfolio copy.
- Web app rebuilt: `tsc`/`eslint` clean, JS bundle unchanged (276.58 KB gzip, data-only
  change). Spot-verified live: Newark's `/report?level=20` shows 32 affected facilities out
  of 177 total (unchanged from the pre-clip 32-exposed count — the removed buffer-zone
  assets were apparently all outside the flood-prone fringe anyway, so only the
  "operational" denominator shrank, not the exposed numerator).

**⚠ Deviations / open items:** none new.

---

## 2026-08-01 — Add 0 ft (MHHW baseline) level (owner request, agent: sonnet-5)

**Owner request:** add a 0 ft scenario. This reverses the 2026-07-22 exclusion of the
CIE service's 0 ft (MHHW baseline) layer (§2.1) — locked levels are now **0–20 ft, 21
levels**, not 1–20/20.

**Feasibility check before touching anything:** queried the live `RU_NJ_CIE_Full`
service metadata directly (all 84 layer names, not just the 0 ft pair) — confirmed the
0 ft layer (ids 82/83, main + low-lying) is the *only* layer with a differently-worded
suffix (`"... Coastal Inundation Extent (Mean Higher High Water)"` vs. every other
whole-foot level's plain `"... Coastal Inundation Extent"`), and confirmed all 8 towns
have real, non-empty 0 ft features (main count=1 everywhere; low-lying=1 for 6/8 towns,
0 for New Brunswick/Perth Amboy — same "not every companion layer is non-empty
everywhere" pattern already true at other levels, not a new problem class).

**Changed:**
- `floodops_v2_lib.py`: `LEVELS_FT` → `range(0, 21)`; `WHOLE_FOOT_NAME_RE` extended to
  accept the optional `" (Mean Higher High Water)"` suffix. `test_recon.py`'s negative
  test (`rejects_mhhw_baseline`) inverted to two positive tests (main + low-lying now
  match, level 0). 15/15 tests pass.
- Re-ran the full chain: `00_recon.py` (all 8 towns 21/21, range 0-20 ft, monotonic) →
  `04_fetch_hazard.py` (21/21 levels fetched, area monotonic incl. the new 0 ft floor) →
  `05_build_exposure.py` → `09_validate.py` (**1554/1554 checks pass**, up from 1490 at
  20 levels).
- Audited all of `web/src` for falsy-zero bugs before assuming the frontend "just
  works" with `level_ft: 0` / `first_exposed: 0` — every consumer already used `??` or
  `!= null` rather than truthy checks (no `if (level)`/`level || x` anywhere), so **no
  frontend code changes were needed.** Verified live against real data anyway: Bayonne
  has one facility (`Unnamed port`, ground elev **-5.3 ft** — physically sane, a
  dock/pier below the tidal datum) already `exposed` at the 0 ft baseline itself;
  confirmed `/report?town=bayonne&level=0` renders `1ST EXPOSED (FT): 0` correctly (not
  blank, not "—"), confirmed the level slider's leftmost tick shows "0" not a dot, and
  confirmed `prefetchNeighborLevels`'s `[idx-1, idx+1]` boundary logic at the new
  minimum (idx=0) correctly skips the nonexistent "level -1" neighbor without erroring
  (`levels[-1]` is `undefined` in JS, not a wraparound, so the existing `if (lvl)` guard
  was already correct).
- **Found + fixed a real, pre-existing pipeline bug while re-running `05_build_exposure.py`
  a second time (unrelated to 0 ft, just newly surfaced by being the first re-run since
  Phase 2):** every town's `roads.geojson`/`assets.geojson` were untouched, yet ~150
  already-existing `exposure_{1-20}.json` files showed as git-modified with byte-identical
  *content* (verified structurally) but fully different road-key **order**. Root cause:
  `closed_ids = set(roads_utm.loc[closed_mask, "id"])` iterated a Python `set` of road-id
  strings directly into the output dict — Python randomizes string-hash iteration order
  per process, so every re-run reshuffled every level's road key order for every town,
  pure diff noise with zero functional effect (assets were already safe: built via
  `enumerate()` over a DataFrame, which is order-stable). Fixed by capturing a
  DataFrame-ordered `list` first and building the sparse dict from that (keeping a real
  `set` alongside for the O(1) access-lost membership check, so no performance cost).
  **Proved the fix, didn't just assume it:** ran the full exposure build twice in a row
  and diffed every output file between the two runs — the *only* difference anywhere
  was each town's `index.json`'s `generated_utc` timestamp (expected); every
  `exposure_*.json`/`extent_*.geojson`/`first_exposed.json` was byte-identical. Small,
  unplanned bonus: naturally-ordered keys also gzip slightly smaller than hash-shuffled
  ones (Newark: 1058.5 → 990.9 KB gzip total, still comfortably under the 5 MB budget).
- Also fixed a cosmetic-only bug in `00_recon.py` found while re-running it: coverage
  was printed/written as "X/20" (a leftover hardcoded literal from when there really
  were only 20 levels) — now "21/21", computed from `len(fl.LEVELS_FT)` /
  `report['levels_ft_in_scope']` rather than hardcoded, so it can't go stale again if
  the level count ever changes once more.
- `OPERATING_GUIDE.md` updated (§1.1 one-liner + comparison table, §2.1 scope, §3.1
  verified facts incl. the 0 ft layer's naming exception, §5.1, §7.4) and re-synced to
  the canonical portfolio copy (`6. PORTFOLIO/10. FLOODOPS V2/OPERATING_GUIDE.md`) —
  confirmed identical before overwriting, not just assumed.
- `web/` rebuilt: `tsc`/`eslint` clean (same pre-existing fast-refresh warning as
  always), JS bundle unchanged at 276.58 KB gzip (data-only change, no code size
  impact).

**⚠ Deviations / open items:** none new. Same outstanding items as before this entry
(owner needs to push, then redeploy on Cloudflare so the live site picks up the new 0 ft
level — see the two entries below for the deploy-pipeline specifics already worked
through).

---

## 2026-08-01 — Deploy pipeline: Workers static assets, not classic Pages (owner + agent)

**Finding:** the Cloudflare project the owner created for V2 is on Cloudflare's newer
**Workers** git-integration pipeline (build command + explicit `wrangler deploy`/
`wrangler versions upload` steps), not the classic **Pages** pipeline v1 uses (build
command + output directory only, no deploy command, no wrangler config at all). This
repo has no `wrangler.toml`/`.jsonc`, same as v1, which is why the first deploy attempt
failed outright ("application detection... run in the root of a workspace instead of
targeting a specific project").

**Fixed:**
1. Added `wrangler.jsonc` (repo root, `assets.directory: "./web/dist"`, assets-only
   Worker, no script) — verified locally with `wrangler deploy --dry-run` (no Cloudflare
   auth needed for that check), which correctly read all files from `web/dist`.
2. Git integration itself was also disconnected (separate issue, likely the GitHub App's
   "selected repositories" scope never included this freshly-created repo) — owner
   fixed via Cloudflare's "Connect to a repository" flow.
3. **`web/public/_redirects` (the SPA-fallback file, same pattern as v1) had to be
   removed entirely.** Workers static assets has its own automatic `.html`/`/index`
   handling that collides with a catch-all `_redirects` rule (`/* /index.html 200`):
   Cloudflare's deploy-time linter rejects it outright as an infinite loop (`Line 5:
   Infinite loop detected... code: 100324`), a hard failure, not a warning. This is a
   genuine platform difference from classic Pages (v1's `_redirects` is fine there).
   `wrangler.jsonc`'s `assets.not_found_handling: "single-page-application"` is the
   correct, native replacement for this deploy target — already configured in step 1 —
   so no `_redirects` file is needed here at all. **If this project is ever migrated
   back to classic Pages, `_redirects` would need to be re-added; don't assume the two
   deploy targets are drop-in compatible.**

**Next:** owner retries the deploy; if `/report` or `/methods` 404 on a direct load
despite `not_found_handling`, that's the next thing to verify (untested in this
session — dry-run only validates the config parses, not runtime routing behavior).

---

## 2026-07-31 — Phases 3-5: Dashboard, simulator UX, reports (agent: sonnet-5)

**Done:**
- **Phase 3 (shell):** `TownPicker` (dropdown sourced from `towns.json`), `LevelSlider`
  (adapted from v1's `StageSlider` — sparse tick labels since up to 20 levels, no NWS
  category vocabulary, footer shows the hazard source), `MapView` (MapLibre GL, sources for
  exposure fill / boundary / roads / assets, single-color exposure fill per §8 — distinct
  from v1's 4-class depth ramp so a V2 screenshot is never mistaken for a depth map), `App`
  shell with hash routing (`#town=<slug>&level=<ft>`), town-switch and level-change effects,
  neighbor-level prefetching (`prefetchNeighborLevels`).
- **Phase 4 (simulator UX):** `SummaryCards` (3-tier facility counts + road-closure count/
  miles), `AssetTable` (sortable/filterable, no depth column — `STATUS_RANK` ordered
  exposed/isolated/operational), `Legend` (3-tier facility + 2-tier road + single exposure
  swatch), `LayerToggle`, asset popup + selection wired into `MapView`.
- **Phase 5 (reports):** `lib/csv.ts` (`buildExposedAssetsCsv` — V2 field list, no
  `depth_ft`/`category_label`, adds `town`/`hazard_source`; RFC-4180 escaping),
  `ReportButtons` (CSV download + `/report` link), `pages/ReportPage.tsx` (header, 3-tier
  summary, closed-priority-roads line, affected-facilities table sorted by
  first-exposed-level, **prepositioning watchlist at "next 1 ft of rise"** — an exact fit
  since levels are 1 ft apart, unlike v1's uneven NWS-category gaps), `pages/MethodsPage.tsx`
  (hazard source, **MHHW-vs-NAVD88 explanation**, what the model does *not* compute, 3-tier/
  2-tier status tables, access-loss rule, coverage note linking to v1 for a riverine
  example), `main.tsx` pathname routing (`/report`, `/methods`, else `App` — same
  no-router-library pattern as v1), `web/public/_redirects` (Cloudflare SPA fallback, same
  as v1).

**Verification:**
- `tsc --noEmit`: 0 errors. `eslint .`: 0 errors, 1 warning (`main.tsx` fast-refresh-only-
  works-with-exports on the inline `Root` component) — confirmed this is **not** a
  regression by running the same lint against v1's `main.tsx`, which has the identical
  warning from the identical pattern.
- `npm run build`: succeeds. JS bundle 276.5 KB gzip (v1's locked budget: ≤400 KB gzip,
  §8.7 — comfortable margin). Vite's generic >500 KB *raw*-chunk warning fires (988 KB raw)
  but raw size is not the governing metric per this project's own gzip-budget correction
  (Phase 2 finding) — not treated as a failure.
- **Real-data browser verification (`/report`, `/methods`, both fully static, no
  MapLibre):** loaded against the production build on Newark. `/report?town=newark`
  (defaults to level 20): 31 exposed + 1 isolated = 32-row table, monotonically sorted by
  first-exposed level (4→20), 24 closed priority roads listed, disclaimer present verbatim.
  Cross-checked `/report?town=newark&level=10` independently: 21 exposed + 0 isolated —
  matches counting first-exposed ≤ 10 from the level-20 table exactly (21 rows with
  `first_exposed ≤ 10`, and the one isolated facility's `first_exposed=18` correctly
  excluded). `/methods` rendered all sections with the real MHHW/NAVD88/tier-definition
  copy. Zero console errors on either page. CSV-download button click produced no errors
  (button/handler wiring confirmed; the resulting file's on-disk content was not opened and
  diff-checked byte-for-byte, since `buildExposedAssetsCsv` is a direct filter/map over the
  same already-verified `exposure`/`firstExposed` data with no new computation).

**⚠ Deviations / open items:**
- **The main dashboard (`App`/`MapView`, MapLibre-based) could not be visually/pixel
  verified in this session's Browser-pane environment.** Root cause (extensively
  diagnosed): the Browser pane's `requestAnimationFrame` is suspended whenever the pane
  isn't visually composited by the client, which stalls MapLibre's internal render loop
  (and therefore its `"load"` event) indefinitely; confirmed via explicit tool errors
  ("the Browser pane is currently hidden" / "is not displayed, so the page is not
  compositing frames") and reconfirmed just before this entry (a raw `requestAnimationFrame`
  poll ran 0 ticks in 3 s against the live dashboard). This is an environment/session
  limitation, not an application defect — ruled out StrictMode double-mount, the `bounds`-
  vs-`center` map-construction style, dev-vs-production build, and WebGL support (confirmed
  working, real GPU/ANGLE renderer) as causes; a bare MapLibre map built directly in the
  console, bypassing all app code, exhibited the identical stall; v1's live production
  deployment showed the same `blob:`-URL network pattern when checked in the same session.
  **What *is* verified for the dashboard:** all data loading, town switching, level
  changes, sparse road-closure state math, and category filtering were checked at the
  DOM/data level (not pixels) earlier in this phase and were correct; `MapView`'s
  popup/selection code was reviewed line-by-line against v1's proven, live, working
  pattern and is structurally faithful to it. **Recommend the owner do one real-browser
  smoke test of the dashboard (town switch, level slider, click an asset for a popup)
  before or shortly after deploying** — this is the one piece of Phase 3-5 that is
  "very likely correct" rather than "directly observed working," and that gap should be
  closed by a human, not silently assumed away.
- No GitHub remote yet for `floodops-v2` (mirrors Phases 0-2's situation) — committed
  locally only; same owner hand-off as before (`git remote add origin ...`, then push).
- Dev server (port 5183) and preview server (port 4174, serving this phase's `dist/`) were
  left running in the background for this session's verification; not stopped as part of
  this phase — harmless to leave running, safe to kill in a future session if unneeded.
- No dedicated Cloudflare Pages project created yet for V2 (§ Phase 3 exit criterion in the
  guide calls for "deployed preview on a new, separate Cloudflare Pages project") — deferred
  to the owner, same as v1's deploy step (an outward-facing action).

**Next:** Owner review + (1) create `floodops-v2` GitHub remote and push, (2) create a
Cloudflare Pages project and deploy (same manual flow as v1), (3) do the one real-browser
dashboard smoke test noted above. No further phases are defined in the guide beyond this —
V2's build is functionally complete pending that verification and deployment.

---

## 2026-07-31 — Phase 2: Hazard acquisition + exposure engine (agent: sonnet-5)

**Done — all 8 towns, all 20 levels each (160 town×level combinations):**
- `04_fetch_hazard.py`: per town × covered level, fetch CIE main + low-lying extent
  (filtered `MUN=`), union, `buffer(0)`, reproject to UTM. Wrote
  `data/raw/hazard/{slug}/extent_{level}.geojson` (gitignored, mirrors v1's
  `data/raw/fim/` convention). Validated on the two extremes first (Newark = worst-case
  size, Hoboken = smallest) before running all 8 — both monotonic, both physically
  plausible (Hoboken 0.14→3.23 km² of its 5.1 km² total; Newark 5.6→36.1 km² of 67.0 km²).
  All 8 towns: monotonic area growth confirmed.
- `05_build_exposure.py`: §5.3 (3-tier facility status) / §5.4 (2-tier road status) /
  §5.5 (120 m access-adjacency, same pattern as v1) exposure engine. Writes per-level
  `exposure_{level}.json` + `extent_{level}.geojson`, per-town `index.json` +
  `first_exposed.json` + rounded `assets/roads/boundary.geojson`, and the top-level
  `towns.json` registry.
- `09_validate.py`: §12.1 invariants generalized across all 8 towns (files exist/parse,
  gzip budgets, EPSG:4326 + valid geometries + unique ids, status-vocabulary validity,
  monotonic severity across levels for every asset AND every road, `first_exposed.json`
  consistency). **Final result: 1490/1490 checks pass, 0 failures.**
- `pipeline/tests/test_pipeline.py`: +1 regression test (degenerate zero-length line
  handling, see below). 14 tests total pass.

**Three real problems found and fixed during this phase — none were assumptions I let
slide, each verified before and after (§13.2 decisions):**

1. **Extent-polygon size.** Newark's raw single-level extent (Phase 0 flagged ~54.7k
   vertices at 20 ft) produced per-level files up to 826 KB raw — over the 800 KB/file
   budget as originally read. Tested simplification tolerance empirically (2/5/10/12/15/
   20/30/50 m on Newark's densest levels) rather than guessing: **locked `SIMPLIFY_M =
   15.0`** — every per-level file ≤ ~270 KB raw, area distortion < 1%, negligible next to
   the hazard model's own uncertainty.

2. **Budget methodology was measuring the wrong thing.** Even after tolerance-tuning,
   Newark's `roads.geojson` (11,142 segments, by far the densest network in the set) sat
   at 3.3 MB raw — still "over budget" by a literal reading of §7.4. Root cause: raw
   on-disk byte count was never the right metric — v1's own guide already measures its
   JS-bundle budget in **gzip-compressed** size (§8.7 there), and this project's §7.4
   should have matched that from the start. Measured real gzip transfer size directly:
   Newark's roads.geojson compresses 9.2× (3.3 MB → 360 KB gzip), comfortably under
   budget. **Corrected §7.4 in the guide to explicitly specify gzip-measured budgets**
   (owner-confirmed, 2026-07-31) rather than quietly redefining pass/fail without
   updating the source document. Also trimmed two client-unneeded properties
   (`osm_way`, `length_m`) from the web-facing `roads.geojson` as a free, correctness-
   preserving bonus. **Final, worst-case town (Newark): 1052.8 KB gzip total (budget 5
   MB), 306.3 KB max file gzip (budget 800 KB)** — genuine margin, not a near-miss.

3. **Degenerate road geometries — a real Phase 1 bug, caught by Phase 2's validator, in
   two rounds.** `09_validate.py`'s geometry-validity check failed for several towns'
   `roads.geojson`. Root cause round 1: some OSM ways have two adjacent nodes at
   identical coordinates (a real OSM editing artifact); `split_line()` (§6.1,
   `03_fetch_roads.py`) faithfully preserved that as a zero-length, degenerate
   `LineString([p, p])` instead of being filtered. Fixed with a `seg.length <= 0` guard
   — this cleared 7 of 8 affected towns, but **3 towns still failed** after re-running
   the full chain. Root cause round 2 (traced by direct inspection of the specific
   failing feature, not assumption): some segments were *technically* > 0 length in the
   source (~1×10⁻⁸ degrees — floating-point noise from the UTM↔WGS84 round-trip) but
   collapsed to a degenerate, invalid geometry once `05_build_exposure.py`'s
   `simplify(1 m)` ran on them. **Revised the guard to a real-world epsilon,
   `MIN_SEG_LEN_M = 0.5`** (no genuine road segment is meaningfully shorter than half a
   meter) instead of a strict zero comparison. Added a regression test
   (`test_split_line_degenerate_zero_length_input`) documenting both the raw
   `split_line()` behavior and the guard threshold. Re-ran `03_fetch_roads.py` →
   `05_build_exposure.py` → `09_validate.py` a final time: **0 invalid geometries
   anywhere, 0 validator failures.**

**Also fixed in passing:** tried `COORD_ROUND = 5` (vs. v1's 6) for a small extra size
cut — it collapsed 6 of Newark's shortest segments (plus one New Brunswick boundary
ring) into duplicate-point geometries. The saving was ~2%; reverted to 6 decimals
(v1's known-safe value) rather than keep chasing a marginal gain against real geometry
risk.

**Repository copy of the guide (`OPERATING_GUIDE.md` in this repo's root) re-synced from
the canonical portfolio copy after the §2.1/§3.1/§7.4 edits (1 ft steps, gzip budget).**

**⚠ Deviations / open items:** still no GitHub remote (mirrors Phase 0/1's situation) —
committed locally only.

**Next:** Phase 3 — dashboard shell (Vite + React + TS + Tailwind v4 + MapLibre,
multi-town): `TownPicker`, `MapView` adapted for single-class exposure fill (no depth
ramp), `LevelSlider` (replaces v1's `StageSlider`, ticks = that town's actual available
levels). Exit: switching towns fully reloads correct data with zero stale-town
artifacts; deployed preview on a **new**, separate Cloudflare Pages project.

---

## 2026-07-31 — Phase 1: Town + asset + road acquisition (agent: sonnet-5)

**Done — all 8 towns from the recon-locked registry (§13.3, `floodops_v2_lib.TOWN_REGISTRY`,
proceeding with the full 8 per owner instruction, not the guide's "aim for 4-5" suggestion):**
- `01_fetch_towns.py`: boundary + 1 km study area per town (Census TIGERweb County
  Subdivisions, `BASENAME=<town> AND STATE='34'`, exactly one match each — no ambiguous
  names in this set). Boundary areas cross-checked against known real-world figures:
  Newark 66.996 km² (actual ≈67.6), Hoboken 5.1 km² (actual ≈5.1), Jersey City 54.44 km²
  (actual ≈54.4), Perth Amboy 15.429 km² (actual ≈15.3) — all close matches, high confidence
  these are the correct municipal polygons.
- `02_fetch_assets.py`: OSM/Overpass critical-facility fetch, v1's 9 categories + **`airport`
  (`aeroway=aerodrome`) and `port` (`industrial=port`, `landuse=harbour` fallback)** — both
  tags verified live against Newark before writing the category list. **Newark exit
  criterion met: 1 airport (Newark Liberty Intl, IATA EWR) + 4 port facilities (Port Newark
  Container Terminal, Maher Terminals, APM Terminals, Port Newark-Elizabeth relation), all
  with EPQS elevations, all confirmed geographically inside Newark/Port Newark-Elizabeth
  (not a Brooklyn Red Hook mismatch — checked coordinates directly).**
- `03_fetch_roads.py`: OSM road network, segmented ≤200 m, `is_priority` flag — same logic
  as v1, parameterized per town.
- **Totals across all 8 towns: 790 assets, 32,308 road segments.** Per-town counts in
  `RECON.md`-adjacent script output; full breakdown available via `data/processed/{slug}/`.
- Added `pipeline/tests/test_pipeline.py` (6 tests: categorize() incl. new airport/port
  cases, town-registry slug uniqueness, split_line). 13 tests total pass.
- **Refactor:** moved the town list out of `00_recon.py` into
  `floodops_v2_lib.TOWN_REGISTRY` (single source of truth, now includes `slug`) before
  writing the fetch scripts, to avoid two copies of the same list drifting apart. Re-ran
  `00_recon.py` after the refactor — identical 8/8 result, confirms it wasn't a behavior
  change.

**Significant finding + fix (§13.2 decision) — cross-state contamination in the naive 1 km
buffer:**
- Initial asset fetch (before the fix) pulled in **53 of 843 assets (~6.3%) that were
  genuinely in a different state**, not New Jersey: 5 in Manhattan (Hoboken, incl. a
  heliport 626 m across the Hudson from Hoboken's shore), 11 in Manhattan (Jersey City), 1
  in Staten Island (Perth Amboy), 15 in Philadelphia (Camden — **including Philadelphia's
  own Packer Avenue Marine Terminal mis-tagged into Camden's "port" category**), and 21 in
  Staten Island (Bayonne, incl. multiple NYPD/FDNY units and NYC public schools). Newark,
  Atlantic City, and New Brunswick were unaffected (0 out of NJ each) — their buffers never
  reached another state.
- **Root cause:** the 1 km study-area buffer is a naive Euclidean buffer around the town
  polygon; it has no concept of a river or bay being in the way, so for a waterfront town
  close to another major urban core (Hoboken/Jersey City ↔ Manhattan; Camden ↔ Philadelphia;
  Bayonne/Perth Amboy ↔ Staten Island) it can geometrically reach across the water into a
  different state. v1's guide never had to confront this because Bound Brook has no
  immediately-adjacent out-of-state urban area within 1 km.
- **Fix:** added `floodops_v2_lib.nj_boundary()` (fetches + caches NJ's official TIGERweb
  state polygon) and clip every town's buffered study area to it in `01_fetch_towns.py`
  (`study_geom = buffer(...).intersection(nj_boundary)`), before it's written to
  `study_area.geojson` — every downstream script (assets, roads) inherits the fix
  automatically since they all read that one file. Deliberately **not** a blanket
  "exclude anything outside the town's own polygon" fix: legitimate nearby-**NJ**-town
  assets within the buffer are still included (matches v1's own intended use of the
  buffer — e.g. mutual-aid-relevant facilities just over a municipal line stay in scope);
  only cross-**state**-line contamination is removed, because the state line is the
  actual, legally-correct river/bay boundary, not a guess.
- **Re-verified end-to-end after the fix: 0 of 790 assets outside NJ, 0.0000% of road
  length outside NJ (checked directly, not assumed)** for all 8 towns, including the 3
  towns whose buffer had to shrink (Hoboken 17.6→13.2 km², Jersey City 89.6→79.8,
  Perth Amboy 34.5→28.0, Camden 55.2→46.1, Bayonne 57.6→44.9 km²; Newark/Atlantic
  City/New Brunswick unchanged, confirming they were never affected).

**⚠ Deviations / open items:**
- Still no GitHub remote (mirrors Phase 0's situation) — committed locally only.
- Re-fetching assets after the fix used `--force` (broader than the minimal necessary
  re-fetch — only the 5 affected towns' Overpass queries and EPQS lookups strictly needed
  to re-run, since their bbox changed; the other 3 towns' cached results were already
  correct). Cost extra time, not correctness — noted so a future session doesn't assume
  `--force` is the normal way to pick up a study-area change; `--only <affected-slugs>`
  without `--force` would have relied on the changed bbox naturally producing a new cache
  key for just those towns.

**Next:** Phase 2 — hazard acquisition + exposure engine (`04_fetch_hazard.py`,
`05_build_exposure.py`, `09_validate.py`): per town × per available whole-foot level,
fetch+union the main/low-lying CIE extent, compute §5.3/§5.4 exposure statuses, write the
§7 web data contracts. Newark's worst-case per-level geometry (54.7k vertices at 20 ft,
confirmed in Phase 0 recon) will need real simplification — verify empirically per town,
per the guide's explicit warning not to assume v1's Bound Brook tolerance transfers.

---

## 2026-07-31 — Phase 0: Bootstrap + recon (agent: sonnet-5)

**Done:**
- Scaffolded repo at `C:\Users\abdul\Documents\GitHub\floodops-v2`: git init on `main`
  (fully separate from FloodOps v1's `floodops` repo, per locked owner decision, §10.1/§13.3),
  dir tree (`data/{raw,processed}`, `pipeline/tests`, `web`, `.github/workflows`),
  `.gitignore`/`.gitattributes`, README, pnpm workspace, `pipeline/pyproject.toml` (uv, no
  rasterio/DEM deps — V2 is extent-only, no depth computation), CI skeleton, `data/MANIFEST.json`.
  Copied `OPERATING_GUIDE.md` from the portfolio guides folder.
- Wrote `pipeline/floodops_v2_lib.py` (cached HTTP, MANIFEST helper, CIE layer-resolution
  and query helpers) and `pipeline/00_recon.py` (§3), then ran it live against
  `RU_NJ_CIE_Full`.
- Added `pipeline/tests/test_recon.py` (7 offline tests, all pass) — including negative
  tests proving the whole-foot regex correctly rejects half-foot layers and the 0 ft
  MHHW-baseline layer.

**Two things verified live before writing the real recon logic (both directly informed
guide decisions and are now encoded in `floodops_v2_lib.py`):**
1. **Whole-foot layer resolution by name pattern works cleanly.** All 20 levels (1–20 ft)
   resolved with both `main` and `low_lying` layer ids present. Cross-checked against the
   `82 − 4×level` id formula noted in the guide — holds exactly, but the *code* resolves by
   name, not the formula, per §3.1's explicit instruction (don't hardcode a numbering
   convention a data provider could silently change).
2. **`RU_NJ_CIE_Full` correctly honors `outSR`** — requesting `outSR=4326` returns real
   WGS84 coordinates (confirmed against a known Newark point), `outSR=26918` and `outSR=6527`
   return plausible projected coordinates at different magnitudes. **Unlike v1's NWS_FIM
   service** (which always returned Web Mercator regardless of the requested `outSR`), this
   service needs no coordinate-magnitude CRS-detection workaround. `cie_query_geojson()`
   trusts `outSR` directly.

**Town recon (§3.2) — all 8 ranked candidates PASS, none dropped:**

| Town | Levels covered | Worst-case (highest) level | Vertices | Raw KB |
|---|---|---|---|---|
| Newark | 20/20 (1–20 ft) | 20 ft | 54,735 | 2,080.5 |
| Hoboken | 20/20 | 20 ft | 2,912 | 111.2 |
| Jersey City | 20/20 | 20 ft | 38,142 | 1,450.0 |
| Atlantic City | 20/20 | 20 ft | 4,628 | 176.0 |
| New Brunswick | 20/20 | 20 ft | 9,304 | 353.0 |
| Perth Amboy | 20/20 | 20 ft | 8,675 | 329.5 |
| Camden | 20/20 | 20 ft | 23,947 | 910.4 |
| Bayonne | 20/20 | 20 ft | 19,668 | 746.9 |

**Locked town set (§13.3 — locks fully once Phase 1 completes): Newark, Hoboken, Jersey
City, Atlantic City, New Brunswick, Perth Amboy, Camden, Bayonne** (all 8 ranked candidates
from the guide — none needed dropping, unlike v1's Denville).

**Decisions (§13.2):**
- All 8 candidates passed comfortably (every one has full 1–20 ft coverage), so no
  fallback/replacement candidates were needed. 8 towns for the initial release is more
  than the guide's "aim for 4–5" suggestion — flagging this for owner awareness: proceeding
  with all 8 keeps Phase 1 (asset/road acquisition × 8 towns) meaningfully larger than a
  4–5 town first release would have been. Not reducing the set unilaterally since dropping
  a passing, guide-ranked candidate is exactly the kind of scope change that should be a
  choice, not a default — flagged here rather than decided silently.
- Newark's raw worst-case single-level payload (2.08 MB, one 20 ft feature) is large before
  simplification. The §7.4 per-town budget (≤5 MB total, ≤800 KB per file) assumed this
  would need real simplification — confirmed necessary, not optional, exactly as flagged in
  the guide. Phase 2 (`05_build_exposure.py`) must empirically verify Newark fits the budget
  after simplification; do not assume v1's Bound Brook simplification tolerance transfers
  as-is to a coastline-following polygon at this vertex density.

**⚠ Deviations / open items:**
- **Repo not yet pushed to GitHub** — no remote created yet (mirrors v1's own Phase 0
  situation: creating a public repo is an outward-facing action, deferred to the owner).
  All work committed locally on `main`.

**Owner handoff needed before Phase 1 push/CI:**
1. Create the public GitHub repo (suggest `floodops-v2`, or a name of your choosing) and
   add it as `origin`, then `git push -u origin main`.
2. **Decide on the 8-town scope** (see decision note above) — proceed with all 8, or trim
   to a smaller initial set before Phase 1's asset/road acquisition (which scales roughly
   linearly with town count).
3. Confirm the locked town set (or override) — it fully locks at Phase 1 end (§13.3).

**Next:** Phase 1 — town + asset + road acquisition (`01_fetch_towns.py`,
`02_fetch_assets.py` with the widened category list incl. `airport`/`port`,
`03_fetch_roads.py`), run per locked town. Exit gate: every town has boundary/assets/roads;
Newark's airport + port present in `assets.geojson` (the concrete proof the category
widening worked, per §11).
