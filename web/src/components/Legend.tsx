import {
  ASSET_COLORS, ASSET_STATUS_LABEL, BOUNDARY_COLOR, EXPOSURE_FILL_COLOR, ROAD_COLORS, ROAD_STATUS_LABEL,
} from "../lib/palette";
import type { AssetStatus, RoadStatus } from "../types";

const ASSET_ORDER: AssetStatus[] = ["operational", "isolated", "exposed"];
const ROAD_ORDER: RoadStatus[] = ["open", "closed"];

export default function Legend() {
  return (
    <div className="rounded-lg bg-white/95 p-3 text-xs shadow-lg ring-1 ring-black/5 backdrop-blur">
      <p className="mb-1.5 font-semibold text-gray-700">Legend</p>

      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-gray-400">
        Facilities
      </p>
      <div className="mb-2 space-y-1">
        {ASSET_ORDER.map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 shrink-0 rounded-full ring-1 ring-white"
              style={{ backgroundColor: ASSET_COLORS[s] }}
            />
            <span className="text-gray-600">{ASSET_STATUS_LABEL[s]}</span>
          </div>
        ))}
      </div>

      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-gray-400">Roads</p>
      <div className="mb-2 space-y-1">
        {ROAD_ORDER.map((s) => (
          <div key={s} className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-3 shrink-0" style={{ backgroundColor: ROAD_COLORS[s] }} />
            <span className="text-gray-600">{ROAD_STATUS_LABEL[s]}</span>
          </div>
        ))}
      </div>

      <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-gray-400">
        Inundation
      </p>
      <div className="mb-2 flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-3.5 shrink-0 rounded-sm"
          style={{ backgroundColor: EXPOSURE_FILL_COLOR, opacity: 0.45 }}
        />
        <span className="text-gray-600">Modeled extent</span>
      </div>

      <div className="flex items-center gap-1.5">
        <svg width="14" height="2" className="shrink-0" aria-hidden="true">
          <line x1="0" y1="1" x2="14" y2="1" stroke={BOUNDARY_COLOR} strokeWidth="2" strokeDasharray="3,2" />
        </svg>
        <span className="text-gray-600">Municipal boundary</span>
      </div>
    </div>
  );
}
