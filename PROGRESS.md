# FloodOps V2 — Progress Log

Newest entry on top. Never delete entries. Format per OPERATING_GUIDE.md §13.5 (v1's convention, reused).

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
