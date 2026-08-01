import { useCallback, useEffect, useState } from "react";
import MapView, { type LayerVisibility } from "./components/MapView";
import LevelSlider from "./components/LevelSlider";
import TownPicker from "./components/TownPicker";
import Legend from "./components/Legend";
import SummaryCards from "./components/SummaryCards";
import AssetTable from "./components/AssetTable";
import LayerToggle from "./components/LayerToggle";
import ReportButtons from "./components/ReportButtons";
import DisclaimerFooter from "./components/DisclaimerFooter";
import {
  loadExposure,
  loadExtent,
  loadFirstExposed,
  loadTownAssets,
  loadTownBoundary,
  loadTownIndex,
  loadTownRoads,
  loadTowns,
  prefetchNeighborLevels,
} from "./lib/data";
import type { ExposureJson, FirstExposedMap, GeoJson, TownEntry, TownIndexJson } from "./types";

function parseHash(): { town: string | null; level: number | null } {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const town = params.get("town");
  const levelStr = params.get("level");
  return { town, level: levelStr ? Number(levelStr) : null };
}

function writeHash(town: string, levelFt: number) {
  window.history.replaceState(null, "", `#town=${town}&level=${levelFt}`);
}

const ALL_VISIBLE: LayerVisibility = { exposure: true, boundary: true, roads: true, assets: true };

export default function App() {
  const [towns, setTowns] = useState<TownEntry[] | null>(null);
  const [townSlug, setTownSlug] = useState<string | null>(null);
  const [index, setIndex] = useState<TownIndexJson | null>(null);
  const [assetsGeo, setAssetsGeo] = useState<GeoJson | null>(null);
  const [roadsGeo, setRoadsGeo] = useState<GeoJson | null>(null);
  const [boundaryGeo, setBoundaryGeo] = useState<GeoJson | null>(null);
  const [firstExposed, setFirstExposed] = useState<FirstExposedMap>({});
  const [levelIndex, setLevelIndex] = useState(0);
  const [exposure, setExposure] = useState<ExposureJson | null>(null);
  const [extentGeo, setExtentGeo] = useState<GeoJson | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [visibility, setVisibility] = useState<LayerVisibility>(ALL_VISIBLE);
  const [panelOpen, setPanelOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Load the town registry once, pick the initial town from the hash (or the first
  // registry entry).
  useEffect(() => {
    loadTowns()
      .then((list) => {
        setTowns(list);
        const { town } = parseHash();
        const initial = (town && list.some((t) => t.slug === town)) ? town : list[0].slug;
        setTownSlug(initial);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // 2. Whenever the selected town changes, load its index + static files. Default the
  // level to whatever the hash asked for (if valid for this town) else the highest
  // level (visible-impact-on-load, same convention v1 used), else try to preserve the
  // *value* of the previously-selected level across a town switch if it still exists.
  useEffect(() => {
    if (!townSlug) return;
    setSelectedAssetId(null); // an asset id from the previous town can't exist here
    Promise.all([
      loadTownIndex(townSlug), loadTownAssets(townSlug), loadTownRoads(townSlug),
      loadTownBoundary(townSlug), loadFirstExposed(townSlug),
    ])
      .then(([idx, assets, roads, boundary, fe]) => {
        setIndex(idx);
        setAssetsGeo(assets);
        setRoadsGeo(roads);
        setBoundaryGeo(boundary);
        setFirstExposed(fe);

        const { town: hashTown, level: hashLevel } = parseHash();
        let i = idx.levels.length - 1; // default: highest level
        if (hashTown === townSlug && hashLevel != null) {
          const found = idx.levels.findIndex((l) => l.level_ft === hashLevel);
          if (found >= 0) i = found;
        }
        setLevelIndex(i);
      })
      .catch((e) => setError(String(e)));
  }, [townSlug]);

  // 3. Whenever the level (or town) changes, load that level's exposure + extent and
  // persist the choice to the URL hash.
  useEffect(() => {
    if (!townSlug || !index) return;
    const lvl = index.levels[levelIndex];
    if (!lvl) return;
    writeHash(townSlug, lvl.level_ft);
    Promise.all([loadExposure(townSlug, lvl.files.exposure), loadExtent(townSlug, lvl.files.extent)])
      .then(([exp, ext]) => {
        setExposure(exp);
        setExtentGeo(ext);
      })
      .catch((e) => setError(String(e)));
    prefetchNeighborLevels(townSlug, index.levels, levelIndex);
  }, [townSlug, index, levelIndex]);

  // Keep browser back/forward and manual hash edits in sync.
  useEffect(() => {
    const onHash = () => {
      const { town, level } = parseHash();
      if (town && town !== townSlug && towns?.some((t) => t.slug === town)) {
        setTownSlug(town);
      } else if (level != null && index) {
        const found = index.levels.findIndex((l) => l.level_ft === level);
        if (found >= 0) setLevelIndex(found);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [townSlug, towns, index]);

  const onChangeLevel = useCallback((i: number) => setLevelIndex(i), []);
  const onSelectAsset = useCallback((id: string | null) => setSelectedAssetId(id), []);
  const onChangeTown = useCallback((slug: string) => setTownSlug(slug), []);

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center">
        <div>
          <p className="text-lg font-semibold text-red-700">Could not load dashboard data</p>
          <p className="mt-1 text-sm text-gray-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!towns || !townSlug || !index || !assetsGeo || !roadsGeo) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
        <p className="text-gray-500">Loading NJ coastal flood exposure data…</p>
      </div>
    );
  }

  const activeTown = towns.find((t) => t.slug === townSlug)!;

  return (
    <div className="flex h-full flex-col">
      <header className="z-10 flex items-center justify-between gap-4 bg-white px-4 py-2 shadow-sm">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-bold text-gray-900">FloodOps V2</h1>
            <p className="text-xs text-gray-500">
              NJ coastal flood exposure explorer · {index.hazard_source}
            </p>
          </div>
          <TownPicker towns={towns} selectedSlug={townSlug} onChange={onChangeTown} />
        </div>
        <button
          type="button"
          onClick={() => setPanelOpen((o) => !o)}
          className="rounded-md px-3 py-1 text-sm ring-1 ring-gray-300 md:hidden"
        >
          {panelOpen ? "Hide" : "Details"}
        </button>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside
          className={`${panelOpen ? "flex" : "hidden"} w-80 shrink-0 flex-col gap-3 border-r border-gray-200 bg-white p-3 md:flex`}
        >
          <LayerToggle visibility={visibility} onChange={setVisibility} />
          <div className="border-t border-gray-100 pt-3">
            <SummaryCards exposure={exposure} />
          </div>
          <div className="border-t border-gray-100 pt-3">
            <ReportButtons
              index={index}
              levelFt={index.levels[levelIndex].level_ft}
              assetsGeo={assetsGeo}
              exposure={exposure}
              firstExposed={firstExposed}
            />
          </div>
          <div className="flex min-h-0 flex-1 flex-col border-t border-gray-100 pt-3">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Facilities
            </h2>
            <AssetTable
              assetsGeo={assetsGeo}
              exposure={exposure}
              firstExposed={firstExposed}
              selectedAssetId={selectedAssetId}
              onSelect={onSelectAsset}
            />
          </div>
        </aside>

        <main className="relative flex-1">
          <MapView
            townSlug={townSlug}
            townBbox={activeTown.bbox}
            assetsGeo={assetsGeo}
            roadsGeo={roadsGeo}
            boundaryGeo={boundaryGeo}
            extentGeo={extentGeo}
            exposure={exposure}
            firstExposed={firstExposed}
            selectedAssetId={selectedAssetId}
            visibility={visibility}
            onSelectAsset={onSelectAsset}
          />
          <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-3">
            <div className="flex justify-end">
              <div className="pointer-events-auto w-44">
                <Legend />
              </div>
            </div>
            <div className="pointer-events-auto mx-auto w-full max-w-xl">
              <LevelSlider index={index} levelIndex={levelIndex} onChange={onChangeLevel} />
            </div>
          </div>
        </main>
      </div>

      <DisclaimerFooter />
    </div>
  );
}
