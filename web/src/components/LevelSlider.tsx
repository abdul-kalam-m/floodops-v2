import type { TownIndexJson } from "../types";
import { EXPOSURE_FILL_COLOR } from "../lib/palette";

interface Props {
  index: TownIndexJson;
  levelIndex: number;
  onChange: (i: number) => void;
}

// Adapted from v1's StageSlider: no NWS category vocabulary here (§5.1 -- V2 has no
// category system), and up to 20 levels instead of v1's 5, so ticks are rendered as
// light marks + sparse labels (every 5th) rather than one full button per tick --
// 20 individually-labeled buttons would be cramped and redundant with the native
// range input, which already gives full keyboard operability across every step.
export default function LevelSlider({ index, levelIndex, onChange }: Props) {
  const levels = index.levels;
  const current = levels[levelIndex];
  const min = levels[0].level_ft;
  const max = levels[levels.length - 1].level_ft;

  return (
    <div className="rounded-lg bg-white/95 p-3 shadow-lg ring-1 ring-black/5 backdrop-blur">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <div>
          <span className="text-2xl font-semibold tabular-nums">{current.level_ft} ft</span>
          <span className="ml-2 text-sm text-gray-500">above MHHW</span>
        </div>
        <span className="text-xs text-gray-400">{index.town}</span>
      </div>

      <input
        type="range"
        min={0}
        max={levels.length - 1}
        step={1}
        value={levelIndex}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Coastal inundation level"
        aria-valuetext={`${current.level_ft} feet above mean higher high water`}
        className="w-full"
        style={{ accentColor: EXPOSURE_FILL_COLOR }}
      />

      <div className="relative mt-0.5 h-3">
        {levels.map((lvl, i) => {
          const pct = levels.length > 1 ? (i / (levels.length - 1)) * 100 : 0;
          const showLabel = i === 0 || i === levels.length - 1 || lvl.level_ft % 5 === 0;
          return (
            <div
              key={lvl.level_ft}
              className="absolute -translate-x-1/2 text-[10px] tabular-nums text-gray-400"
              style={{ left: `${pct}%` }}
            >
              {showLabel ? lvl.level_ft : "·"}
            </div>
          );
        })}
      </div>

      <p className="mt-1.5 text-[11px] text-gray-400">
        {min}–{max} ft range · {index.hazard_source}
      </p>
    </div>
  );
}
