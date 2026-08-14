# FloodOps V2 — case-study staging notes

Staged per owner decision (2026-08-01): materials only, not integrated into the
portfolio website's own `OPERATING_GUIDE.md` §10 flagship list — that's a separate
positioning decision for the owner to make. Written in that guide's §10 format
(Hook / Facts / Source / Hero) so it drops in with minimal editing whenever that
decision is made. All numbers below are pulled directly from this repo's own
`PROGRESS.md`/`RECON.md`/validator output, not re-derived or estimated.

---

## Entry draft

### FloodOps V2 — `data-ai` (or `geospatial-intelligence`), candidate flagship

**Hook:** A multi-town coastal flood *exposure* explorer for New Jersey — honest about
what a statewide static model can and can't tell you, on purpose. Stands as its own
project (not part of a portfolio pair) — a registry-driven, multi-town dashboard on a
real statewide open-data product, with disclosed, quantified uncertainty in its
per-facility depth estimates (see `OPERATING_GUIDE.md` §16 for the positioning history).

**Refreshed 2026-08-14 against the live Phase 7 build** (real per-town numbers pulled
directly from `web/public/data/*/index.json` + `exposure_20.json`, and the validator's
own §5.6.5 output — not re-derived or estimated; see "Numbers verified" below for the
exact source of every figure).

**Facts:**
- 8 NJ coastal/tidal municipalities: Newark, Hoboken, Jersey City, Atlantic City, New
  Brunswick, Perth Amboy, Camden, Bayonne. 21 water levels per town (0–20 ft above
  Mean Higher High Water, whole-foot steps) against Rutgers University's NJ Coastal
  Inundation Explorer (`RU_NJ_CIE_Full`), a public ArcGIS FeatureServer.
- **Hybrid model, not extent-only:** the flood *extent* is always Rutgers' (2-tier road
  status, extent membership as the primary facility signal, in every town). On top of
  that, 7 of 8 towns additionally get a per-facility **computed depth** — this
  project's own estimate (USGS ground elevation subtracted from a flat water surface
  at a per-town MHHW→NAVD88 offset), never Rutgers'. Depth-available towns get 4-tier
  facility status (operational/access-threatened/isolated/exposed); Camden, the one
  town without a verified offset, keeps the original 3-tier model
  (operational/isolated/exposed) — a real finding, not a fallback engineered to always
  succeed (see the datum bullet below).
- **Real per-town exposure at the 20 ft scenario** (facilities ever non-operational /
  total mapped facilities):

  | Town | Affected / total | % | Depth model |
  |---|---|---|---|
  | Hoboken | 33 / 33 | 100% | 4-tier |
  | Atlantic City | 46 / 46 | 100% | 4-tier |
  | Camden | 62 / 90 | 69% | 3-tier (no depth) |
  | Bayonne | 23 / 35 | 66% | 4-tier |
  | Jersey City | 49 / 111 | 44% | 4-tier |
  | Perth Amboy | 10 / 32 | 31% | 4-tier |
  | Newark | 41 / 177 | 23% | 4-tier |
  | New Brunswick | 3 / 38 | 8% | 4-tier |

  Hoboken and Atlantic City stay at a genuine 100% — every single mapped critical
  facility in those towns is eventually affected. New Brunswick, at the Raritan's
  tidal limit, is the real outlier at the other end: **0 facilities are ever directly
  inside the flood extent**, but 3 show `access-threatened` purely from nearby road
  closures — the tool distinguishes "your building floods" from "your street floods
  and you can't get out," and reports the latter honestly instead of rounding it down
  to 0.
- **The model-disagreement rate (§5.6.5) is itself a finding, not swept under the rug:**
  for every depth-available town at every level, the validator checks how often a
  facility sits inside Rutgers' extent but this project's own elevation subtraction
  computes exactly 0 ft of depth — the visible seam between two independently-produced
  models. Real range across the 7 depth-available towns: **0–100% at individual
  levels, town means 0–27%**; **44 of 147 town-level combinations exceed the 25%
  named-limitation threshold** the guide sets. Not noise: the flagged levels cluster
  tightly at the *low* end of each town's range (Newark 4–15 ft, Atlantic City 0–6 ft),
  exactly where a facility has just entered the extent and its ground elevation sits
  closest to the water surface by construction — a real, physically-explainable
  pattern, not a bug. Surfaced on the live Methods page and in `RECON.md`, not tuned
  away to look cleaner.
- **A real technical problem solved during the depth-datum work, worth telling on its
  own:** resolving each town's MHHW→NAVD88 offset needed two independent public
  sources to agree within 0.25 ft. The obvious approach — NOAA's ~15 "major" tide
  stations — was a poor proxy inside a bay (differences up to 0.4+ ft); the fix was
  searching NOAA's full ~2,900-station historic/subordinate catalog for the *nearest*
  station with a real published NAVD88 tie-in (one turns out to sit literally inside
  Newark Bay). Two more real bugs found and fixed along the way: a MultiPolygon
  `.centroid` can land in the geometric gap between disconnected parts rather than on
  the geometry at all, and NOAA VDatum's own tidal grid has genuine internal coverage
  gaps — confirmed live via a real HTTP 200 with `{"errorCode":412}` in the body, not
  a timeout. Camden's missing depth is that exact gap, not a fallback dodge.
- **A real methodology fix mid-build, worth telling as part of the honesty narrative:**
  assets and roads were originally kept out to a 1 km buffer beyond each town's
  boundary, but the flood layer itself never extends past that same boundary (it's an
  independently-sourced attribute filter, not spatially clipped to anything in this
  project). That mismatch meant a road just outside the boundary always rendered "not
  flooded" — indistinguishable from a genuine no-flood finding when it was really just
  outside where hazard data exists at all. Fixed by clipping assets/roads to the same
  boundary the flood layer implicitly respects, verified with a real polygon-containment
  check (0 features outside the boundary, across all 8 towns) rather than eyeballed.
- Static-only architecture, zero backend: Python/GeoPandas pipeline precomputes every
  town × level combination into committed JSON/GeoJSON; Vite + React 18 + TypeScript +
  Tailwind v4 + MapLibre GL frontend reads it directly. Deployed on Cloudflare Workers
  (static assets).
- Accessibility: 0 axe-core violations (dashboard, report, methods pages) after a real
  scan-and-fix pass, not just an unverified claim — found and fixed 5 real issues,
  including a thin-margin color-contrast bug that only failed on the map's translucent
  overlay panels, not on solid-white backgrounds, caught by rescanning a second town.
- **Source:** `C:\Users\abdul\Documents\GitHub\floodops-v2` (`PROGRESS.md` is the full,
  dated build log — every fact above is traceable to a specific entry there).
- **Live URL:** https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/ (Cloudflare Workers).

**Hero:** interactive MapLibre view is the natural hero. Suggested
shot: Hoboken at the 20 ft scenario (`/#town=hoboken&level=20`) — every facility marker
shows exposed (orange), the modeled-extent fill visibly covers most of the town, dashed
boundary line legible against it. This single frame carries the "100% of Hoboken
eventually exposed" stat visually without needing a caption to explain it. Second
option for a depth-specific hero: Newark at 20 ft, clicking Newark Liberty Intl Airport
(15.5 ft computed depth) — shows the 4-tier legend and a real depth number in the same
frame.

---

## Screenshots not captured this session — exact repro steps instead

This session's Browser-pane automation environment has a known, previously-documented
rendering limitation (see `PROGRESS.md`'s Phase 3-5 entry): it intermittently fails to
composite MapLibre's WebGL canvas when the pane isn't actively displayed, and there is
no tool available in this session to save a Browser-pane screenshot as an image file on
disk (the screenshot tool returns an image for inline viewing, not a file). Rather than
fabricate placeholder images or claim screenshots exist when they don't, capturing the
following is left as a real 10-minute task for whoever builds the actual case-study page:

1. **Hero shot** — `https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/#town=hoboken&level=20`. Verified live this
   session (not guessed): every facility renders orange (exposed), blue modeled-extent
   fill covers most of the town, black dashed boundary line clearly legible against it,
   legend fully visible. This exact frame was seen and confirmed correct during this
   session's own verification pass — just not saved to a file.
2. **Second option, more dramatic scale** — `.../#town=newark&level=20` — 41 of 177
   facilities affected (24 exposed, 11 access-threatened, 6 isolated — Port Newark,
   Newark Liberty Intl among the exposed), visible amid a much larger built-up area
   than Hoboken. Click Newark Liberty Intl for a real computed-depth popup (15.5 ft).
3. **Methods-page limitations screenshot** (explicit portfolio-guide instruction, §14) —
   `https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/methods`, the "What this tool does *not* compute" section in
   particular — this is the direct visual evidence of the honesty discipline the guide
   asks for.
4. **Report page** — `https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/report?town=newark&level=20` — shows the
   operations-report format (summary counts, affected-facilities table, prepositioning
   watchlist) in a clean, static, always-renders-correctly view (no MapLibre dependency,
   verified repeatedly this session to render reliably).

---

## Numbers verified, not estimated

Every stat above traces to a specific source, re-checked 2026-08-14 against the live
Phase 7 build (not carried forward from the original 2026-08-01 draft without
re-verifying):
- **Per-town exposure counts/percentages (the table above):** computed fresh this pass
  directly from the committed `web/public/data/{slug}/index.json` +
  `levels/exposure_20.json` for all 8 towns — total facility count minus
  `by_asset_status.operational`. Cross-checked against the live production report
  pages for Newark and Camden (both matched exactly).
- **§5.6.5 disagreement-rate numbers (min/max/mean, 44/147 flagged):** direct output of
  `pipeline/09_validate.py`, re-run this pass; full per-town table and pattern analysis
  also in `RECON.md`'s "Phase 7.2/7.3" section.
- **Datum-recon facts** (the ~2,900-station catalog, the two point-selection bugs, the
  VDatum `errorCode:412` finding): `RECON.md`'s "Phase 7.0" section, and the
  "2026-08-14 — Phase 7: point depth (Tier 1)" `PROGRESS.md` entry.
- **Pre-Phase-7 facts unaffected by this refresh** (the 1 km buffer clip fix, the
  architecture/deploy facts, the accessibility pass): "2026-08-01 — Clip assets/roads
  to municipal boundary," "2026-08-01 — Phase 6: a11y (axe) checks," and the Cloudflare
  Workers-vs-Pages deploy-debugging entries in `PROGRESS.md` — re-checked that nothing
  in Phase 7 touched these, not just assumed.

If any of these numbers are re-quoted into the portfolio site later, reread the source
entry first rather than trusting this summary blindly — this file is a staging
convenience, not the system of record.
