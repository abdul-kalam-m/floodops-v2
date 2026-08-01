import { useEffect } from "react";
import DisclaimerText from "../components/DisclaimerText";

export default function MethodsPage() {
  useEffect(() => {
    document.title = "FloodOps V2 — Methods";
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-8 text-sm leading-relaxed text-gray-800">
      <a href="/" className="text-blue-700 hover:underline">
        ← FloodOps V2 dashboard
      </a>

      <h1 className="mb-4 mt-4 text-2xl font-bold text-gray-900">Methods</h1>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Hazard data</h2>
        <p>
          Flood extents come from Rutgers University&rsquo;s{" "}
          <strong>NJ Coastal Inundation Explorer</strong> (<code>RU_NJ_CIE_Full</code>), a
          statewide static inundation model. Each town exposes whichever of the 20 locked
          whole-foot water levels (1&ndash;20 ft) the service returns non-empty features for —
          coverage varies by town. Every level is a static footprint, not a live forecast.
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
          along the coast. That means a FloodOps V2 level is <strong>not directly comparable</strong>{" "}
          to an elevation given in NAVD88, nor to a National Weather Service river-gauge flood
          stage. FloodOps v1 (Bound Brook, on the Raritan River) uses NWS gauge stages in
          NAVD88-referenced terms — a genuinely different measurement system from this tool,
          even though both are called &ldquo;FloodOps.&rdquo;
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          What this tool does <em>not</em> compute
        </h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>No flood depth.</strong> A level tells you whether a location falls inside
            or outside a modeled inundation footprint — never how deep the water is there.
          </li>
          <li>
            <strong>No first-floor height comparison.</strong> Unlike FloodOps v1, ground
            elevation is not compared against a water-surface elevation, because there is no
            depth value to compare it against. First-floor height is not modeled at all here.
          </li>
          <li>
            <strong>No building-level survey.</strong> A facility&rsquo;s status is computed
            purely from whether its mapped point falls inside the extent polygon and whether
            its access roads are closed — not from any building-specific flood-proofing,
            elevation certificate, or site survey.
          </li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Facility status</h2>
        <table className="w-full border-collapse text-sm">
          <tbody>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Exposed</td>
              <td className="py-1 text-gray-600">
                The facility&rsquo;s point falls inside the level&rsquo;s extent polygon
                (with a 20 m tolerance for alignment between OSM points and the independently
                produced hazard polygon).
              </td>
            </tr>
            <tr className="border-b border-gray-200">
              <td className="py-1 pr-3 font-medium">Isolated</td>
              <td className="py-1 text-gray-600">
                Not exposed, but every road within 120 m of the facility is closed (see
                &ldquo;Road status&rdquo; and &ldquo;Access-loss rule&rdquo; below) —{" "}
                <strong>computed from road exposure, not a building-level survey</strong>.
              </td>
            </tr>
            <tr>
              <td className="py-1 pr-3 font-medium">Operational</td>
              <td className="py-1 text-gray-600">Neither of the above.</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-2 text-gray-600">
          There is no fourth &ldquo;access-threatened&rdquo; tier. FloodOps v1 used that tier
          to represent shallow or partial water at a facility, which requires a depth value
          this model deliberately does not compute.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Road status</h2>
        <p>
          A road segment is <strong>closed</strong> if it intersects the level&rsquo;s extent
          polygon (same 20 m tolerance), otherwise <strong>open</strong>. There is no graded
          &ldquo;caution&rdquo; tier — that distinction in v1 was depth-derived and has no
          extent-only equivalent.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Access-loss rule</h2>
        <p>
          A facility loses access when every road segment within 120 m of it (nearest-segment
          fallback if none fall within that radius) is closed — the same proximity rule used
          in FloodOps v1.
        </p>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Coverage</h2>
        <p>
          FloodOps V2 covers a fixed set of NJ coastal and tidal-influenced municipalities,
          one town at a time — it does not extend to non-tidal parts of New Jersey. For a
          riverine (non-tidal, gauge-based) flood example, see{" "}
          <a
            href="https://floodops.pages.dev"
            target="_blank"
            rel="noreferrer"
            className="text-blue-700 hover:underline"
          >
            FloodOps v1
          </a>{" "}
          (Bound Brook, on the Raritan River).
        </p>
      </section>

      <section className="border-t border-gray-300 pt-4 text-xs leading-relaxed text-gray-600">
        <DisclaimerText />
      </section>
    </div>
  );
}
