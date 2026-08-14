import { useEffect, useState } from "react";
import { loadTowns, loadTownIndex } from "../lib/data";
import DisclaimerText from "../components/DisclaimerText";
import type { TownEntry, TownIndexJson } from "../types";

export default function MethodsPage() {
  const [towns, setTowns] = useState<TownEntry[] | null>(null);
  const [indexes, setIndexes] = useState<Record<string, TownIndexJson>>({});

  useEffect(() => {
    document.title = "FloodOps — Methods";
    // Coverage table below is per-town (depth availability, MHHW offset, error
    // budget), so load every town's index.json once -- small (8 files, already
    // cached individually by the browser after a normal dashboard visit) and lets
    // this page state real, current numbers instead of hardcoded placeholder text
    // that would drift from the data the moment a town's datum status changes.
    loadTowns().then(async (list) => {
      setTowns(list);
      const entries = await Promise.all(
        list.map(async (t) => [t.slug, await loadTownIndex(t.slug)] as const),
      );
      setIndexes(Object.fromEntries(entries));
    });
  }, []);

  const depthTowns = towns?.filter((t) => indexes[t.slug]?.depth_available) ?? [];
  const noDepthTowns = towns?.filter((t) => towns && indexes[t.slug] && !indexes[t.slug].depth_available) ?? [];
  const anyDepth = depthTowns.length > 0;

  return (
    <main className="mx-auto max-w-2xl p-8 text-sm leading-relaxed text-gray-800">
      <a href="/" className="text-blue-700 hover:underline">
        ← FloodOps dashboard
      </a>

      <h1 className="mb-4 mt-4 text-2xl font-bold text-gray-900">Methods</h1>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Hazard data</h2>
        <p>
          Flood extents come from Rutgers University&rsquo;s{" "}
          <strong>NJ Coastal Inundation Explorer</strong> (<code>RU_NJ_CIE_Full</code>), a
          statewide static inundation model. Each town exposes whichever of the 21 locked
          whole-foot water levels (0&ndash;20 ft, where 0 ft is the MHHW baseline itself) the
          service returns non-empty features for — coverage varies by town. Every level is a
          static footprint, not a live forecast.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          MHHW vs. NAVD88 — why this matters
        </h2>
        <p>
          Levels are measured in feet above <strong>Mean Higher High Water (MHHW)</strong>, a
          local tidal datum defined as the average of the higher of the two daily high tides
          at a given station, averaged over a 19-year tidal epoch. MHHW is <em>not</em> the
          same reference surface as <strong>NAVD88</strong> (North American Vertical Datum of
          1988, a fixed geodetic datum), and the offset between the two varies by location
          along the coast. That means a FloodOps level is <strong>not directly comparable</strong>{" "}
          to an elevation given in NAVD88, nor to a National Weather Service river-gauge flood
          stage — those are measured against a different reference system entirely. The
          conversion described below is used internally to compute facility depth; it never
          changes what a level itself means or how it&rsquo;s labeled.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          What this tool does <em>not</em> compute
        </h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>No depth surface.</strong> There is no gridded or contoured depth field and
            no depth-class map ramp — the map fill is always a single exposure color. Depth (see
            below) exists only as a per-facility number, in towns where it&rsquo;s available.
          </li>
          <li>
            <strong>No road-segment depth.</strong> Road status is always closed/open only,
            based on whether the road intersects the flood extent — never depth-graded, in any
            town.
          </li>
          <li>
            <strong>No building-level survey.</strong> A facility&rsquo;s status is computed
            purely from whether its mapped point falls inside the extent polygon (plus, in
            depth-available towns, a computed depth) and whether its access roads are closed —
            not from any building-specific flood-proofing, elevation certificate, or site
            survey.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Facility status</h2>
        <p className="mb-2 text-gray-700">
          Two status models are used, depending on whether a town has a verified MHHW&rarr;NAVD88
          offset (see &ldquo;Facility depth&rdquo; below). Extent membership — whether the
          facility&rsquo;s point falls inside the level&rsquo;s modeled footprint, with a 20 m
          tolerance for alignment between OSM points and the independently produced hazard
          polygon — is always computed first and is always the primary signal in both models.
        </p>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Towns with computed depth (4-tier)
        </p>
        <table className="mb-3 w-full border-collapse text-sm">
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Exposed</td>
              <td className="py-1 text-gray-600">Computed depth &ge; the facility&rsquo;s first-floor offset (1.0 ft, uniform default).</td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Isolated</td>
              <td className="py-1 text-gray-600">Not exposed, but every access road is closed.</td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Access threatened</td>
              <td className="py-1 text-gray-600">Some depth but below the first-floor offset, or some (not all) access roads closed.</td>
            </tr>
            <tr>
              <td className="py-1 pr-3 font-medium">Operational</td>
              <td className="py-1 text-gray-600">None of the above.</td>
            </tr>
          </tbody>
        </table>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">
          Towns without computed depth (3-tier)
        </p>
        <table className="w-full border-collapse text-sm">
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Exposed</td>
              <td className="py-1 text-gray-600">Facility point falls inside the extent polygon.</td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Isolated</td>
              <td className="py-1 text-gray-600">Not exposed, but every access road is closed.</td>
            </tr>
            <tr>
              <td className="py-1 pr-3 font-medium">Operational</td>
              <td className="py-1 text-gray-600">Neither of the above.</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-gray-600">
          &ldquo;Exposed&rdquo; keeps the same label in both models rather than adopting a
          separate name for the depth-graded version — the label was already in the CSV/report
          vocabulary before facility depth existed, and its condition in the 4-tier model
          matches what a depth-graded &ldquo;flooded&rdquo; tier would mean anyway.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Road status</h2>
        <p>
          A road segment is <strong>closed</strong> if it intersects the level&rsquo;s extent
          polygon (same 20 m tolerance), otherwise <strong>open</strong>. There is no graded
          &ldquo;caution&rdquo; tier — that distinction would be depth-derived, and road segments
          never have a computed depth, in any town.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Access-loss rule</h2>
        <p>
          A facility loses access when every road segment within 120 m of it (nearest-segment
          fallback if none fall within that radius) is closed.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Facility depth</h2>
        <p className="mb-2">
          For towns where it&rsquo;s available, FloodOps computes an estimated depth at each
          facility&rsquo;s point, <strong>inside the level&rsquo;s flood extent only</strong>:
        </p>
        <pre className="mb-2 overflow-x-auto rounded bg-gray-50 p-2 text-xs">
          {"WSE (NAVD88 ft) = MHHW offset (NAVD88 ft) + level (ft above MHHW)\n" +
            "depth (ft) = max(0, WSE − ground elevation)"}
        </pre>
        <p className="mb-2">
          <strong>The flood extent is Rutgers&rsquo;. The depth is not</strong> — it is computed
          by this project, by subtracting USGS ground-elevation data (3DEP, via the Elevation
          Point Query Service) from a flat water surface, using a per-town MHHW-to-NAVD88 offset
          resolved from two independent public sources: NOAA VDatum (a point conversion at a
          real water location inside that town&rsquo;s own flood extent) and the nearest NOAA
          CO-OPS tide station with a published NAVD88 datum. The two must agree within 0.25 ft
          or the town does not get computed depth at all — no averaging, no picking the more
          convenient value. Depth is always rounded to the nearest 0.5 ft, because the combined
          uncertainty (ground-elevation accuracy, the MHHW-offset approximation, and Rutgers&rsquo;
          extent having been produced from a different elevation model than the one used here)
          is on the order of the 1 ft spacing between levels — reporting anything finer would
          claim a precision this method doesn&rsquo;t have. Outside a level&rsquo;s flood extent,
          depth is always exactly 0, never computed from the raw elevation difference — the
          extent stays the sole authority on whether a facility is exposed at all.
        </p>
        <p className="mb-2">
          A first-floor offset (1.0 ft, the same default for every facility, regardless of
          category) is used to decide the &ldquo;Exposed&rdquo; threshold above. This is an
          assumption, not a survey, and it is the single largest lever on the boundary between
          &ldquo;Exposed&rdquo; and &ldquo;Access threatened.&rdquo;
        </p>
        <p className="mb-2">
          At the 0 ft level, the water surface used is MHHW itself, so a computed depth there
          reads as &ldquo;depth below the mean higher high tide line&rdquo; — a real number, but
          easily misread as active flooding. It isn&rsquo;t: 0 ft is the baseline against which
          1&ndash;20 ft are the actual modeled rise scenarios.
        </p>
        <p>
          Sometimes a facility sits inside Rutgers&rsquo; flood extent but this project&rsquo;s
          own elevation subtraction computes a depth of exactly 0 — the two independently
          produced models disagreeing at the margin. This is <strong>reported, not hidden</strong>:
          the validator records how often it happens for every town and level, and any town/level
          where it happens for more than 25% of exposed facilities is treated as a named
          limitation, not smoothed over.
        </p>
      </section>

      {towns && Object.keys(indexes).length === towns.length && (
        <section className="mb-6">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">Depth coverage by town</h2>
          <p className="mb-2 text-gray-700">
            {anyDepth
              ? `${depthTowns.length} of ${towns.length} towns currently have a verified MHHW offset and computed facility depth; the rest use the extent-only (3-tier) model above until their offset can be verified.`
              : "No town currently has a verified MHHW offset — every town uses the extent-only (3-tier) model above."}
          </p>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b-2 border-gray-300 text-left text-xs uppercase text-gray-500">
                <th className="py-1 pr-2">Town</th>
                <th className="py-1 pr-2">Depth available</th>
                <th className="py-1 pr-2 text-right">MHHW offset (ft NAVD88)</th>
                <th className="py-1">Cross-check source</th>
              </tr>
            </thead>
            <tbody>
              {towns.map((t) => {
                const idx = indexes[t.slug];
                return (
                  <tr key={t.slug} className="border-b border-gray-100">
                    <td className="py-1 pr-2 font-medium">{t.name}</td>
                    <td className="py-1 pr-2">{idx?.depth_available ? "Yes" : "No"}</td>
                    <td className="py-1 pr-2 text-right tabular-nums">
                      {idx?.mhhw_navd88_ft != null ? idx.mhhw_navd88_ft.toFixed(2) : "—"}
                    </td>
                    <td className="py-1 text-gray-600">
                      {idx?.datum_source
                        ? `${idx.datum_source.coops_station_name} (${idx.datum_source.coops_dist_km?.toFixed(1)} km)`
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {noDepthTowns.length > 0 && (
            <p className="mt-2 text-xs text-gray-500">
              A town without depth isn&rsquo;t a lesser result — it means the two independent
              offset sources couldn&rsquo;t be reconciled within 0.25 ft (or one source had no
              usable coverage at that location) for this specific stretch of coastline. That
              town keeps the extent-only model rather than shipping a depth number that couldn&rsquo;t
              be verified.
            </p>
          )}
        </section>
      )}

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Coverage</h2>
        <p>
          FloodOps covers a fixed set of NJ coastal and tidal-influenced municipalities,
          one town at a time — it does not extend to non-tidal parts of New Jersey.
        </p>
      </section>

      <section className="border-t border-gray-300 pt-4 text-xs leading-relaxed text-gray-600">
        <DisclaimerText />
      </section>
    </main>
  );
}
