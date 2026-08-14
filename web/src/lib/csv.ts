// §9 CSV export. Phase 7 (§5.6) added depth_ft/ffo_ft back into the export -- empty
// (not "0") for depth_available:false towns, so a consumer can tell "not computed"
// from a real zero-depth result. category_label (v1's flood-category label) stays
// dropped -- there's no per-scenario category vocabulary here; `town` and
// `hazard_source` are the export-context fields worth knowing instead.
import type { ExposureJson, FirstExposedMap, GeoJson } from "../types";

const CSV_COLUMNS = [
  "asset_id",
  "name",
  "category",
  "address",
  "ground_elev_ft",
  "depth_ft",
  "ffo_ft",
  "status",
  "access_lost",
  "first_exposed_level_ft",
  "town",
  "level_ft",
  "hazard_source",
  "generated_utc",
] as const;

function csvField(v: unknown): string {
  const s = v === null || v === undefined ? "" : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/**
 * One row per non-operational asset at `levelFt`, matching what the dashboard shows --
 * no recomputation. Numbers come straight from the already-computed exposure JSON and
 * first_exposed map, exactly as the map/table already display them.
 */
export function buildExposedAssetsCsv(
  assetsGeo: GeoJson,
  exposure: ExposureJson,
  firstExposed: FirstExposedMap,
  town: string,
  levelFt: number,
  hazardSource: string,
): string {
  const generatedUtc = new Date().toISOString();
  const lines = [CSV_COLUMNS.join(",")];
  for (const f of assetsGeo.features) {
    const p = f.properties as Record<string, unknown>;
    const id = String(p.id);
    const a = exposure.assets[id];
    if (!a || a.status === "operational") continue;
    const fe = firstExposed[id];
    const row = [
      id,
      p.name,
      p.category,
      p.address ?? "",
      p.ground_elev_ft,
      a.depth_ft != null ? a.depth_ft : "",
      a.depth_ft != null ? (p.ffo_ft ?? "") : "",
      a.status,
      a.access_lost,
      fe != null ? fe : "",
      town,
      levelFt,
      hazardSource,
      generatedUtc,
    ];
    lines.push(row.map(csvField).join(","));
  }
  return lines.join("\r\n") + "\r\n";
}

export function csvFilename(townSlug: string, levelFt: number): string {
  const d = new Date();
  const ymd =
    `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}` +
    `${String(d.getDate()).padStart(2, "0")}`;
  return `floodops_${townSlug}_level${levelFt}ft_${ymd}.csv`;
}

export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
