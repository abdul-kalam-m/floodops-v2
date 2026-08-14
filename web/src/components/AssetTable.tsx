import { useMemo, useState } from "react";
import type { AssetStatus, ExposureJson, FirstExposedMap, GeoJson, StatusModel } from "../types";
import { ASSET_COLORS, ASSET_STATUS_LABEL } from "../lib/palette";
import { ASSET_CATEGORY_LABEL } from "../lib/categoryLabels";

interface Row {
  id: string;
  name: string;
  category: string;
  ground_elev_ft: number;
  status: AssetStatus;
  depth_ft: number | null;
  first_exposed: number | null;
}

type SortKey = "name" | "category" | "ground_elev_ft" | "status" | "depth_ft" | "first_exposed";

// Worst-wins order (§5.3) -- unified across both status models. 3-tier towns never
// produce "access-threatened", so its rank slot doesn't affect their sort order.
const STATUS_RANK: Record<AssetStatus, number> = {
  exposed: 0,
  isolated: 1,
  "access-threatened": 2,
  operational: 3,
};

interface Props {
  assetsGeo: GeoJson;
  exposure: ExposureJson | null;
  firstExposed: FirstExposedMap;
  statusModel: StatusModel;
  selectedAssetId: string | null;
  onSelect: (id: string) => void;
}

export default function AssetTable({
  assetsGeo, exposure, firstExposed, statusModel, selectedAssetId, onSelect,
}: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("status");
  const [asc, setAsc] = useState(true);
  const [catFilter, setCatFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const showDepth = statusModel === "4-tier";

  const rows: Row[] = useMemo(() => {
    return assetsGeo.features.map((f) => {
      const p = f.properties as Record<string, unknown>;
      const id = String(p.id);
      const a = exposure?.assets[id];
      return {
        id,
        name: String(p.name),
        category: String(p.category),
        ground_elev_ft: Number(p.ground_elev_ft),
        status: a?.status ?? "operational",
        depth_ft: a?.depth_ft ?? null,
        first_exposed: firstExposed[id] ?? null,
      };
    });
  }, [assetsGeo, exposure, firstExposed]);

  const categories = useMemo(
    () => Array.from(new Set(rows.map((r) => r.category))).sort(),
    [rows],
  );

  const filtered = useMemo(() => {
    const f = rows.filter(
      (r) =>
        (catFilter === "all" || r.category === catFilter) &&
        (statusFilter === "all" || r.status === statusFilter),
    );
    const dir = asc ? 1 : -1;
    return f.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "status") cmp = STATUS_RANK[a.status] - STATUS_RANK[b.status];
      else if (sortKey === "first_exposed")
        cmp = (a.first_exposed ?? Infinity) - (b.first_exposed ?? Infinity);
      else if (sortKey === "depth_ft")
        cmp = (a.depth_ft ?? -Infinity) - (b.depth_ft ?? -Infinity);
      else if (typeof a[sortKey] === "number")
        cmp = (a[sortKey] as number) - (b[sortKey] as number);
      else cmp = String(a[sortKey]).localeCompare(String(b[sortKey]));
      return cmp * dir;
    });
  }, [rows, catFilter, statusFilter, sortKey, asc]);

  const toggleSort = (k: SortKey) => {
    if (k === sortKey) setAsc(!asc);
    else {
      setSortKey(k);
      setAsc(true);
    }
  };

  const Th = ({ k, children, className = "" }: { k: SortKey; children: React.ReactNode; className?: string }) => (
    <th
      className={`cursor-pointer select-none px-1 py-1 text-left font-medium hover:text-gray-900 ${className}`}
      onClick={() => toggleSort(k)}
      aria-sort={sortKey === k ? (asc ? "ascending" : "descending") : "none"}
    >
      {children}
      {sortKey === k ? (asc ? " ▲" : " ▼") : ""}
    </th>
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-2 flex items-center gap-2 text-xs">
        <select
          value={catFilter}
          onChange={(e) => setCatFilter(e.target.value)}
          className="rounded border-gray-300 bg-white px-1 py-0.5 ring-1 ring-gray-200"
          aria-label="Filter by category"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {ASSET_CATEGORY_LABEL[c] ?? c}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border-gray-300 bg-white px-1 py-0.5 ring-1 ring-gray-200"
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          {(Object.keys(ASSET_STATUS_LABEL) as AssetStatus[])
            .filter((s) => showDepth || s !== "access-threatened")
            .map((s) => (
              <option key={s} value={s}>
                {ASSET_STATUS_LABEL[s]}
              </option>
            ))}
        </select>
        <span className="ml-auto text-gray-500">{filtered.length}</span>
      </div>

      <div
        className="min-h-0 flex-1 overflow-auto"
        tabIndex={0}
        role="region"
        aria-label="Facilities table"
      >
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 bg-white text-gray-500 shadow-[0_1px_0_#e5e7eb]">
            <tr>
              <Th k="name">Facility</Th>
              <Th k="ground_elev_ft" className="text-right">Elev</Th>
              {showDepth && <Th k="depth_ft" className="text-right">Depth</Th>}
              <Th k="first_exposed" className="text-right">1st ft</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={showDepth ? 4 : 3} className="py-4 text-center text-gray-500">
                  No facilities match the filters.
                </td>
              </tr>
            )}
            {filtered.map((r) => (
              <tr
                key={r.id}
                onClick={() => onSelect(r.id)}
                className={`cursor-pointer border-b border-gray-100 hover:bg-blue-50 ${
                  selectedAssetId === r.id ? "bg-blue-100" : ""
                }`}
              >
                <td className="px-1 py-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-white"
                      style={{ backgroundColor: ASSET_COLORS[r.status] }}
                      title={ASSET_STATUS_LABEL[r.status]}
                    />
                    <span className="truncate" title={r.name}>{r.name}</span>
                  </div>
                </td>
                <td className="px-1 py-1 text-right tabular-nums">{r.ground_elev_ft.toFixed(0)}</td>
                {showDepth && (
                  <td className="px-1 py-1 text-right tabular-nums">
                    {r.depth_ft == null ? "—" : r.depth_ft.toFixed(1)}
                  </td>
                )}
                <td className="px-1 py-1 text-right tabular-nums">
                  {r.first_exposed == null ? "—" : r.first_exposed.toFixed(0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
