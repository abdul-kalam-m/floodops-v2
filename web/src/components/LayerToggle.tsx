import type { LayerVisibility } from "./MapView";

const LAYERS: { key: keyof LayerVisibility; label: string }[] = [
  { key: "exposure", label: "Flood exposure" },
  { key: "boundary", label: "Municipal boundary" },
  { key: "roads", label: "Roads" },
  { key: "assets", label: "Facilities" },
];

interface Props {
  visibility: LayerVisibility;
  onChange: (v: LayerVisibility) => void;
}

export default function LayerToggle({ visibility, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {LAYERS.map(({ key, label }) => (
        <label key={key} className="flex items-center gap-1.5 text-xs text-gray-700">
          <input
            type="checkbox"
            checked={visibility[key]}
            onChange={(e) => onChange({ ...visibility, [key]: e.target.checked })}
            className="h-3.5 w-3.5 rounded accent-blue-700"
          />
          {label}
        </label>
      ))}
    </div>
  );
}
