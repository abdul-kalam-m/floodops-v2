import type { TownEntry } from "../types";

interface Props {
  towns: TownEntry[];
  selectedSlug: string;
  onChange: (slug: string) => void;
}

export default function TownPicker({ towns, selectedSlug, onChange }: Props) {
  return (
    <select
      value={selectedSlug}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Select municipality"
      className="rounded-md border-gray-300 bg-white px-2 py-1 text-sm font-semibold text-gray-900 ring-1 ring-gray-300 hover:bg-gray-50"
    >
      {towns.map((t) => (
        <option key={t.slug} value={t.slug}>
          {t.name}
        </option>
      ))}
    </select>
  );
}
