// §5.7 disclaimer text (LOCKED wording, restyle-not-reword) -- single source of
// truth. Deliberately unstyled so it drops into both the dark dashboard footer and
// the light report/methods pages; each consumer supplies its own wrapper.
// NOTE: distinct from FloodOps v1's own disclaimer wording -- do not copy v1's text
// here; this is V2's own model characterization.
export default function DisclaimerText() {
  return (
    <p>
      <strong>Planning demonstration only — screening tool, not a survey and not a
      forecast.</strong>{" "}
      FloodOps uses Rutgers University&rsquo;s NJ Coastal Inundation Explorer, a
      statewide static model referenced to Mean Higher High Water (MHHW), a local tidal
      datum. <strong>The flood extents are Rutgers&rsquo;. Where facility depth is
      shown, it is not</strong> — it is computed by this project, by subtracting USGS
      ground elevation from a flat water surface, using a per-town MHHW-to-NAVD88
      offset verified against two independent public sources. Depth is reported to the
      nearest half-foot because its uncertainty is on the order of the one-foot level
      spacing itself, and it must not be read as a surveyed or measured depth. Not
      every town has computed depth — see the Methods page for per-town coverage.
      Water levels here are heights above a local tidal datum (MHHW), not flood stages
      from a river gauge. This is not an operational forecasting tool and must not be
      used for real-time emergency decisions. Consult the National Weather Service,
      NJDEP, and local emergency management for actual flood response.
    </p>
  );
}
