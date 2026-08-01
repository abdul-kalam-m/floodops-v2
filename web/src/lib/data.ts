// Data loading for the committed §7 contracts under public/data/. Everything is
// fetched from the site's own static files. Paths are already town-scoped (they
// include the slug), so one flat cache is safe -- no cross-town collision risk.
import type {
  ExposureJson, FirstExposedMap, GeoJson, TownEntry, TownIndexJson,
} from "../types";

const BASE = import.meta.env.BASE_URL;
const cache = new Map<string, unknown>();

async function loadJson<T>(path: string): Promise<T> {
  if (cache.has(path)) return cache.get(path) as T;
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Failed to load ${path}: ${res.status}`);
  const data = (await res.json()) as T;
  cache.set(path, data);
  return data;
}

export const loadTowns = () => loadJson<TownEntry[]>("data/towns.json");
export const loadTownIndex = (slug: string) =>
  loadJson<TownIndexJson>(`data/${slug}/index.json`);
export const loadTownAssets = (slug: string) => loadJson<GeoJson>(`data/${slug}/assets.geojson`);
export const loadTownRoads = (slug: string) => loadJson<GeoJson>(`data/${slug}/roads.geojson`);
export const loadTownBoundary = (slug: string) =>
  loadJson<GeoJson>(`data/${slug}/boundary.geojson`);
export const loadFirstExposed = (slug: string) =>
  loadJson<FirstExposedMap>(`data/${slug}/first_exposed.json`);
export const loadExposure = (slug: string, file: string) =>
  loadJson<ExposureJson>(`data/${slug}/${file}`);
export const loadExtent = (slug: string, file: string) => loadJson<GeoJson>(`data/${slug}/${file}`);

// Prefetch adjacent levels within the current town so slider moves feel instant (§8.5
// pattern reused from v1). Town-scoped: only ever prefetches within the active town.
export function prefetchNeighborLevels(slug: string, levels: TownIndexJson["levels"], idx: number) {
  [idx - 1, idx + 1].forEach((i) => {
    const lvl = levels[i];
    if (lvl) {
      void loadExposure(slug, lvl.files.exposure).catch(() => {});
      void loadExtent(slug, lvl.files.extent).catch(() => {});
    }
  });
}
