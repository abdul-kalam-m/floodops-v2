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

**⚠ Stats below predate Phase 7 (point depth, added 2026-08-11/14) — re-verify against
current `PROGRESS.md`/`RECON.md` before quoting anywhere.** Phase 7 added a 4th facility
status (`access-threatened`) for 7 of 8 towns, which changes the "ever non-operational"
counts below (e.g. Newark's affected-facility count is now 41, not 32 — the old figure
undercounts because it predates the tier that catches partial road closures). The
"extent-only, no depth model" framing in the next bullet is also no longer accurate
for those 7 towns. Left as-is here rather than silently rewritten, since refreshing
every number below is a bigger job than this pass covers.

**Facts (pre-Phase-7 snapshot — see warning above):**
- 8 NJ coastal/tidal municipalities: Newark, Hoboken, Jersey City, Atlantic City, New
  Brunswick, Perth Amboy, Camden, Bayonne. 21 water levels per town (0–20 ft above
  Mean Higher High Water, whole-foot steps) against Rutgers University's NJ Coastal
  Inundation Explorer (`RU_NJ_CIE_Full`), a public ArcGIS FeatureServer.
- Extent-only exposure model, deliberately not a depth model — no MHHW→NAVD88
  conversion attempted, stated as a limitation rather than glossed over. 3-tier
  facility status (operational/isolated/exposed), 2-tier road status (open/closed).
- **Striking, real finding, not a cherry-picked demo number:** at the 20 ft scenario,
  100% of Hoboken's 33 facilities and 100% of Atlantic City's 46 facilities are
  eventually exposed — every single mapped critical facility in those towns. Newark
  (the largest town in the set) shows 32 of 177 facilities exposed at the same level.
  New Brunswick, sitting at the Raritan's tidal limit, shows 0 — a genuine negative
  result the tool reports plainly rather than hides.
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
eventually exposed" stat visually without needing a caption to explain it.

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
2. **Second option, more dramatic scale** — `.../#town=newark&level=20` — 32 of 177
   facilities exposed (Port Newark, Newark Liberty Intl among them), visible amid a much
   larger built-up area than Hoboken.
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

Every stat above traces to a specific `PROGRESS.md` entry in this repo:
- Town/level counts, exposure percentages: "2026-08-01 — Clip assets/roads to municipal
  boundary" and "2026-08-01 — Add 0 ft (MHHW baseline) level" entries.
- Validator pass count (1554/1554): same entries.
- Accessibility fixes (5 issues, 0 violations after): "2026-08-01 — Phase 6: a11y (axe)
  checks" entry.
- Architecture/deploy facts: `OPERATING_GUIDE.md` §6, and the Cloudflare
  Workers-vs-Pages deploy-debugging entries earlier in `PROGRESS.md`.

If any of these numbers are re-quoted into the portfolio site later, reread the source
`PROGRESS.md` entry first rather than trusting this summary blindly — this file is a
staging convenience, not the system of record.
