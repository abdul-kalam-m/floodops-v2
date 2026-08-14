import type { AssetStatus, ExposureJson, StatusModel } from "../types";
import { ASSET_COLORS, ASSET_STATUS_LABEL } from "../lib/palette";

const STATUS_ORDER_3TIER: AssetStatus[] = ["exposed", "isolated", "operational"];
const STATUS_ORDER_4TIER: AssetStatus[] = ["exposed", "isolated", "access-threatened", "operational"];

export default function SummaryCards({
  exposure, statusModel,
}: { exposure: ExposureJson | null; statusModel: StatusModel }) {
  if (!exposure) return null;
  const s = exposure.summary;
  const statusOrder = statusModel === "4-tier" ? STATUS_ORDER_4TIER : STATUS_ORDER_3TIER;
  const total = statusOrder.reduce((a, k) => a + (s.by_asset_status[k] ?? 0), 0);
  const nonOperational = total - (s.by_asset_status.operational ?? 0);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <Stat value={nonOperational} label="Facilities affected" />
        <Stat value={s.road_closed_count} label="Roads closed" />
        <Stat value={s.road_closed_miles.toFixed(1)} label="Closed miles" />
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-gray-500">Facilities by status</p>
        <div className="space-y-1">
          {statusOrder.map((k) => {
            const n = s.by_asset_status[k] ?? 0;
            return (
              <div key={k} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block h-3 w-3 rounded-full ring-1 ring-white"
                  style={{ backgroundColor: ASSET_COLORS[k] }}
                />
                <span className="flex-1">{ASSET_STATUS_LABEL[k]}</span>
                <span className="font-semibold tabular-nums">{n}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="rounded-md bg-gray-50 p-2 text-center ring-1 ring-gray-200">
      <div className="text-lg font-semibold tabular-nums text-gray-900">{value}</div>
      <div className="text-[10px] leading-tight text-gray-500">{label}</div>
    </div>
  );
}
