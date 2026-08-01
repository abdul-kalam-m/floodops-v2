import { buildExposedAssetsCsv, csvFilename, downloadCsv } from "../lib/csv";
import type { ExposureJson, FirstExposedMap, GeoJson, TownIndexJson } from "../types";

interface Props {
  index: TownIndexJson;
  levelFt: number;
  assetsGeo: GeoJson;
  exposure: ExposureJson | null;
  firstExposed: FirstExposedMap;
}

export default function ReportButtons({ index, levelFt, assetsGeo, exposure, firstExposed }: Props) {
  const onDownloadCsv = () => {
    if (!exposure) return;
    const csv = buildExposedAssetsCsv(
      assetsGeo, exposure, firstExposed, index.town, levelFt, index.hazard_source,
    );
    downloadCsv(csvFilename(index.slug, levelFt), csv);
  };

  return (
    <div className="flex gap-2">
      <button
        type="button"
        onClick={onDownloadCsv}
        disabled={!exposure}
        className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
      >
        Export CSV
      </button>
      <a
        href={`/report?town=${index.slug}&level=${levelFt}`}
        target="_blank"
        rel="noreferrer"
        className="flex-1 rounded bg-gray-900 px-2 py-1.5 text-center text-xs font-medium text-white hover:bg-gray-800"
      >
        View report ↗
      </a>
    </div>
  );
}
