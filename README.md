# FloodOps V2

Multi-municipality coastal flood **exposure** dashboard for New Jersey's tidal/coastal towns — uses Rutgers University's NJ Coastal Inundation Explorer (whole-foot levels, 1–20 ft above Mean Higher High Water). A separate, independent product from [FloodOps v1](https://github.com/abdul-kalam-m/floodops) (Bound Brook, NWS river-gauge FIM, depth-based) — see `OPERATING_GUIDE.md` §1.1 for how and why they differ.

> **Planning demonstration only — exposure screening, not a depth model.** This dashboard shows whether an asset or road falls inside a modeled coastal-inundation footprint at a given water level above MHHW (a local tidal datum). It does not compute flood depth and is not comparable to NAVD88 elevations or NWS river-gauge stages. It is not an operational forecasting tool.

## Repository layout

- `OPERATING_GUIDE.md` — the canonical build manual. **Read it before doing any work.**
- `PROGRESS.md` — session log (newest entry on top).
- `RECON.md` — Phase 0 town-coverage recon results.
- `pipeline/` — Python pipeline (recon → fetch → exposure engine → validate).
- `web/` — Vite + React multi-town dashboard (Phase 3+).
- `data/` — `raw/` (gitignored) and `processed/`; `MANIFEST.json` records data lineage.

## Status

Phase 0 (bootstrap + recon). See `PROGRESS.md`.
