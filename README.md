# FloodOps V2

**Live demo:** [floodops-v2.ar-abdulkalam-mustaq.workers.dev](https://floodops-v2.ar-abdulkalam-mustaq.workers.dev/#town=newark&level=20)

Multi-municipality coastal flood **exposure** dashboard for New Jersey's tidal/coastal towns — uses Rutgers University's NJ Coastal Inundation Explorer (whole-foot levels, 0–20 ft above Mean Higher High Water). Deployed product name is just "FloodOps" — "V2" is this repo's own engineering-side name only (see `OPERATING_GUIDE.md` §16 changelog for why).

> **Planning demonstration only — screening tool, not a survey and not a forecast.** This dashboard shows whether an asset or road falls inside a modeled coastal-inundation footprint at a given water level above MHHW (a local tidal datum). The flood extent is Rutgers'; where a facility depth number is shown (7 of 8 towns), it is this project's own computed estimate, not Rutgers', rounded to the nearest 0.5 ft — see `/methods` on the live demo for the full honesty discipline. Not comparable to NAVD88 elevations or NWS river-gauge stages. It is not an operational forecasting tool.

## Repository layout

- `OPERATING_GUIDE.md` — the canonical build manual. **Read it before doing any work.**
- `PROGRESS.md` — session log (newest entry on top).
- `RECON.md` — Phase 0 town-coverage recon results.
- `pipeline/` — Python pipeline (recon → fetch → exposure engine → validate).
- `web/` — Vite + React multi-town dashboard (Phase 3+).
- `data/` — `raw/` (gitignored) and `processed/`; `MANIFEST.json` records data lineage.

## Status

Phases 0–7 complete for all 8 locked towns (Newark, Hoboken, Jersey City, Atlantic City, New Brunswick, Perth Amboy, Camden, Bayonne): pipeline, exposure engine, dashboard, simulator UX, reports (`/report`, `/methods`), and per-facility computed depth (7/8 towns — Camden ships extent-only, a real NOAA VDatum coverage gap, not a disagreement) are built, deployed, and verified live in production on Cloudflare Workers (static assets). See `PROGRESS.md` for full phase-by-phase detail and `RECON.md` for the per-town datum-verification results.
