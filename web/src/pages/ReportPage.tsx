import { useEffect, useMemo, useState } from "react";
import {
  loadExposure, loadFirstExposed, loadTownAssets, loadTownIndex, loadTownRoads, loadTowns,
} from "../lib/data";
import { buildExposedAssetsCsv, csvFilename, downloadCsv } from "../lib/csv";
import { ASSET_CATEGORY_LABEL } from "../lib/categoryLabels";
import { ASSET_STATUS_LABEL } from "../lib/palette";
import DisclaimerText from "../components/DisclaimerText";
import type {
  AssetStatus, ExposureJson, FirstExposedMap, GeoJson, TownEntry, TownIndexJson,
} from "../types";

function paramsFromQuery(): { town: string | null; level: number | null } {
  const params = new URLSearchParams(window.location.search);
  const town = params.get("town");
  const levelStr = params.get("level");
  return { town, level: levelStr ? Number(levelStr) : null };
}

interface AssetRow {
  id: string;
  name: string;
  category: string;
  address: string;
  ground_elev_ft: number;
  status: AssetStatus;
  access_lost: boolean;
  first_exposed: number | null;
}

export default function ReportPage() {
  const [towns, setTowns] = useState<TownEntry[] | null>(null);
  const [index, setIndex] = useState<TownIndexJson | null>(null);
  const [assetsGeo, setAssetsGeo] = useState<GeoJson | null>(null);
  const [roadsGeo, setRoadsGeo] = useState<GeoJson | null>(null);
  const [firstExposed, setFirstExposed] = useState<FirstExposedMap>({});
  const [exposure, setExposure] = useState<ExposureJson | null>(null);
  const [levelFt, setLevelFt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "FloodOps V2 — Exposure Report";
    const { town: qTown } = paramsFromQuery();
    loadTowns()
      .then(async (list) => {
        setTowns(list);
        const slug = qTown && list.some((t) => t.slug === qTown) ? qTown : list[0].slug;
        const [idx, assets, roads, fe] = await Promise.all([
          loadTownIndex(slug), loadTownAssets(slug), loadTownRoads(slug), loadFirstExposed(slug),
        ]);
        setIndex(idx);
        setAssetsGeo(assets);
        setRoadsGeo(roads);
        setFirstExposed(fe);
        const { level } = paramsFromQuery();
        const found = level != null ? idx.levels.find((l) => l.level_ft === level) : undefined;
        const chosen = found ?? idx.levels[idx.levels.length - 1];
        setLevelFt(chosen.level_ft);
        setExposure(await loadExposure(slug, chosen.files.exposure));
      })
      .catch((e) => setError(String(e)));
  }, []);

  const exposedRows: AssetRow[] = useMemo(() => {
    if (!assetsGeo || !exposure) return [];
    return assetsGeo.features
      .map((f) => {
        const p = f.properties as Record<string, unknown>;
        const id = String(p.id);
        const a = exposure.assets[id];
        return {
          id,
          name: String(p.name),
          category: String(p.category),
          address: String(p.address ?? ""),
          ground_elev_ft: Number(p.ground_elev_ft),
          status: a?.status ?? "operational",
          access_lost: a?.access_lost ?? false,
          first_exposed: firstExposed[id] ?? null,
        };
      })
      .filter((r) => r.status !== "operational")
      .sort((a, b) => {
        const fe = (a.first_exposed ?? Infinity) - (b.first_exposed ?? Infinity);
        return fe !== 0 ? fe : a.category.localeCompare(b.category);
      });
  }, [assetsGeo, exposure, firstExposed]);

  // Prepositioning watchlist: operational now, but exposed within the next 1 ft of rise
  // (levels are exactly 1 ft apart, so this maps to "the next level up" precisely).
  const watchlist = useMemo(() => {
    if (!assetsGeo || !exposure || levelFt == null) return [];
    return assetsGeo.features
      .map((f) => {
        const p = f.properties as Record<string, unknown>;
        const id = String(p.id);
        return {
          id, name: String(p.name), category: String(p.category),
          status: exposure.assets[id]?.status ?? "operational",
          first_exposed: firstExposed[id] ?? null,
        };
      })
      .filter(
        (r) => r.status === "operational" && r.first_exposed != null && r.first_exposed <= levelFt + 1,
      )
      .sort((a, b) => (a.first_exposed ?? 0) - (b.first_exposed ?? 0));
  }, [assetsGeo, exposure, firstExposed, levelFt]);

  const closedPriorityRoads = useMemo(() => {
    if (!roadsGeo || !exposure) return [];
    const names = new Set<string>();
    for (const f of roadsGeo.features) {
      const p = f.properties as Record<string, unknown>;
      const id = String(p.id);
      if (exposure.roads[id]?.status === "closed" && p.is_priority && p.name) {
        names.add(String(p.name));
      }
    }
    return [...names].sort();
  }, [roadsGeo, exposure]);

  if (error) return <Message title="Could not load report" detail={error} />;
  if (!towns || !index || !assetsGeo || !exposure || levelFt == null) {
    return <Message title="Loading report…" />;
  }

  const onDownloadCsv = () => {
    const csv = buildExposedAssetsCsv(
      assetsGeo, exposure, firstExposed, index.town, levelFt, index.hazard_source,
    );
    downloadCsv(csvFilename(index.slug, levelFt), csv);
  };

  return (
    <div className="mx-auto max-w-3xl p-8 print:max-w-none print:p-0">
      <div className="no-print mb-6 flex flex-wrap items-center justify-between gap-2 text-sm">
        <a href="/" className="text-blue-700 hover:underline">
          ← FloodOps V2 dashboard
        </a>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onDownloadCsv}
            className="rounded border border-gray-300 px-3 py-1 font-medium hover:bg-gray-50"
          >
            Download CSV
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded bg-gray-900 px-3 py-1 font-medium text-white hover:bg-gray-800"
          >
            Print / Save as PDF
          </button>
        </div>
      </div>
      <p className="no-print mb-4 text-[11px] text-gray-400">
        Tip: enable “Headers and footers” in your browser’s print dialog for page numbers
        and the date on every sheet.
      </p>

      {/* (1) Header */}
      <header className="mb-6 border-b border-gray-300 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">
          FloodOps V2 Exposure Report — {index.town}, {index.state}
        </h1>
        <p className="mt-1 text-gray-600">
          {levelFt} ft above MHHW · {index.hazard_source}
        </p>
        <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-sm text-gray-700 sm:grid-cols-3">
          <Field label="County" value={index.county} />
          <Field label="Data generated" value={new Date(index.generated_utc).toLocaleString()} />
          <Field label="Model" value="Extent-only exposure (no depth)" />
        </dl>
      </header>

      {/* (2) Summary */}
      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Summary</h2>
        <div className="grid grid-cols-3 gap-3">
          {(["exposed", "isolated", "operational"] as AssetStatus[]).map((s) => (
            <div key={s} className="rounded border border-gray-200 p-2 text-center">
              <div className="text-xl font-semibold tabular-nums">
                {exposure.summary.by_asset_status[s] ?? 0}
              </div>
              <div className="text-xs text-gray-500">{ASSET_STATUS_LABEL[s]}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-sm text-gray-700">
          <strong>{exposure.summary.road_closed_count}</strong> road segment(s) closed (
          <strong>{exposure.summary.road_closed_miles.toFixed(1)} mi</strong>).{" "}
          {closedPriorityRoads.length > 0 ? (
            <>
              Closed priority roads: <strong>{closedPriorityRoads.join(", ")}</strong>.
            </>
          ) : (
            "No priority roads closed at this level."
          )}
        </p>
      </section>

      {/* (3) Exposed / isolated assets */}
      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          Affected facilities ({exposedRows.length})
        </h2>
        {exposedRows.length === 0 ? (
          <p className="text-sm text-gray-500">No facilities are exposed or isolated at this level.</p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b-2 border-gray-300 text-left text-xs uppercase text-gray-500">
                <th className="py-1 pr-2">Facility</th>
                <th className="py-1 pr-2">Category</th>
                <th className="py-1 pr-2">Address</th>
                <th className="py-1 pr-2 text-right">Elev (ft)</th>
                <th className="py-1 pr-2">Status</th>
                <th className="py-1 pr-2">Access</th>
                <th className="py-1 text-right">1st exposed (ft)</th>
              </tr>
            </thead>
            <tbody>
              {exposedRows.map((r) => (
                <tr key={r.id} className="border-b border-gray-100">
                  <td className="py-1 pr-2 font-medium">{r.name}</td>
                  <td className="py-1 pr-2">{ASSET_CATEGORY_LABEL[r.category] ?? r.category}</td>
                  <td className="py-1 pr-2 text-gray-600">{r.address || "—"}</td>
                  <td className="py-1 pr-2 text-right tabular-nums">{r.ground_elev_ft.toFixed(1)}</td>
                  <td className="py-1 pr-2">{ASSET_STATUS_LABEL[r.status]}</td>
                  <td className="py-1 pr-2">{r.access_lost ? "Lost" : "—"}</td>
                  <td className="py-1 text-right tabular-nums">
                    {r.first_exposed != null ? r.first_exposed : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* (4) Prepositioning watchlist */}
      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          Prepositioning watchlist — at risk within next 1 ft of rise
        </h2>
        {watchlist.length === 0 ? (
          <p className="text-sm text-gray-500">
            No currently-operational facilities become exposed within 1 ft of this level.
          </p>
        ) : (
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b-2 border-gray-300 text-left text-xs uppercase text-gray-500">
                <th className="py-1 pr-2">Facility</th>
                <th className="py-1 pr-2">Category</th>
                <th className="py-1 text-right">Becomes exposed at (ft)</th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((r) => (
                <tr key={r.id} className="border-b border-gray-100">
                  <td className="py-1 pr-2 font-medium">{r.name}</td>
                  <td className="py-1 pr-2">{ASSET_CATEGORY_LABEL[r.category] ?? r.category}</td>
                  <td className="py-1 text-right tabular-nums">{r.first_exposed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* (5) Limitations & disclaimer */}
      <section className="border-t border-gray-300 pt-4 text-xs leading-relaxed text-gray-600">
        <DisclaimerText />
      </section>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-gray-400">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function Message({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex h-screen items-center justify-center p-6 text-center">
      <div>
        <p className="text-lg font-semibold text-gray-800">{title}</p>
        {detail && <p className="mt-1 text-sm text-gray-500">{detail}</p>}
      </div>
    </div>
  );
}
