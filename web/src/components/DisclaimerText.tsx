// §5.6 disclaimer text -- single source of truth (wording may be restyled, not
// reworded). Deliberately unstyled so it drops into both the dark dashboard footer
// and the light report/methods pages; each consumer supplies its own wrapper.
// NOTE: this is V2's own exposure-only wording, distinct from FloodOps v1's
// depth-model disclaimer -- do not copy v1's text here.
export default function DisclaimerText() {
  return (
    <p>
      <strong>Planning demonstration only — exposure screening, not a depth model.</strong>{" "}
      FloodOps V2 uses Rutgers University&rsquo;s NJ Coastal Inundation Explorer, a
      statewide static model referenced to Mean Higher High Water (MHHW), a local tidal
      datum. This dashboard shows whether an asset or road falls inside a modeled
      inundation footprint at a given water level — it does not compute flood depth, and
      levels are not directly comparable to NWS river-gauge flood stages or to elevations
      in NAVD88. It is not an operational forecasting tool and must not be used for
      real-time emergency decisions. Consult the National Weather Service, NJDEP, and
      local emergency management for actual flood response.
    </p>
  );
}
