"""Offline unit tests for Phase 1 pure logic (no network)."""
import importlib.util
from pathlib import Path

from shapely.geometry import LineString

PIPE = Path(__file__).resolve().parents[1]


def _load(mod_file, name):
    spec = importlib.util.spec_from_file_location(name, PIPE / mod_file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


assets = _load("02_fetch_assets.py", "assets")
roads = _load("03_fetch_roads.py", "roads")
exposure = _load("05_build_exposure.py", "exposure")


def test_categorize_v1_categories_still_work():
    assert assets.categorize({"amenity": "fire_station"}) == "fire"
    assert assets.categorize({"amenity": "school"}) == "school"
    assert assets.categorize({"amenity": "restaurant"}) is None


def test_categorize_airport():
    assert assets.categorize({"aeroway": "aerodrome"}) == "airport"
    assert assets.categorize({"aeroway": "terminal"}) is None  # only aerodrome, not terminal


def test_categorize_port():
    assert assets.categorize({"industrial": "port"}) == "port"
    assert assets.categorize({"landuse": "harbour"}) == "port"


def test_town_registry_slugs_are_unique():
    import floodops_v2_lib as fl
    slugs = [t[0] for t in fl.TOWN_REGISTRY]
    assert len(slugs) == len(set(slugs))
    assert len(fl.TOWN_REGISTRY) == 8


def test_split_line_degenerate_zero_length_input():
    # Regression test (2026-07-31): some OSM ways have two adjacent nodes at identical
    # coordinates (a real data artifact). split_line() faithfully preserves that as a
    # zero-length LineString rather than raising -- the fix lives in the CALLER
    # (03_fetch_roads.py skips any seg.length < MIN_SEG_LEN_M = 0.5 m), so this documents
    # split_line's actual behavior and pins the guard condition it must be filtered with.
    # A strict `== 0` check isn't enough on its own: floating-point noise from the
    # UTM<->WGS84 round-trip can leave a segment technically >0 (observed: ~1e-8 degrees)
    # but still collapse once simplify(1 m) runs on it downstream -- hence 0.5 m, not 0.
    degenerate = LineString([(5.0, 5.0), (5.0, 5.0)])
    segs = roads.split_line(degenerate, max_len=200.0)
    assert len(segs) == 1
    assert segs[0].length == 0
    assert not segs[0].is_valid  # a real LineString needs 2 distinct points
    assert segs[0].length < 0.5  # confirms the MIN_SEG_LEN_M guard catches this case


def test_split_line_respects_max_length():
    line = LineString([(0, 0), (500, 0)])
    segs = roads.split_line(line, max_len=200.0)
    assert len(segs) == 3
    assert all(s.length <= 200.0 + 1e-6 for s in segs)


def test_split_line_short_line_untouched():
    line = LineString([(0, 0), (150, 0)])
    segs = roads.split_line(line, max_len=200.0)
    assert len(segs) == 1


# --- Phase 7 (§5.6): point depth -- pure-function tests -----------------------

def test_round_half_ft_rounds_to_nearest_half():
    assert exposure.round_half_ft(0.24) == 0.0
    assert exposure.round_half_ft(0.26) == 0.5
    assert exposure.round_half_ft(0.74) == 0.5
    assert exposure.round_half_ft(0.76) == 1.0
    assert exposure.round_half_ft(0.0) == 0.0
    assert exposure.round_half_ft(2.0) == 2.0


def test_classify_4tier_exposed_when_depth_meets_ffo():
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=1.0, ffo=1.0, all_closed=False, any_closed=False)
    assert status == "exposed"
    assert access_lost is False  # real fact, not hardcoded True (unlike 3-tier)


def test_classify_4tier_exposed_reports_real_access_lost_even_when_flooded():
    # A facility can be genuinely flooded (d>=ffo) while its own access roads are
    # still open -- the 4-tier model must report that fact, not flatten it to "lost"
    # the way the pre-Phase-7 3-tier model did.
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=5.0, ffo=1.0, all_closed=True, any_closed=True)
    assert status == "exposed"
    assert access_lost is True


def test_classify_4tier_isolated_beats_access_threatened_worst_wins():
    # Depth is between 0 and ffo (would be access-threatened on its own), but every
    # access road is closed too -- isolated must win per the guide's ordered table
    # (exposed > isolated > access-threatened > operational).
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=0.5, ffo=1.0, all_closed=True, any_closed=True)
    assert status == "isolated"
    assert access_lost is True


def test_classify_4tier_access_threatened_from_partial_depth():
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=0.5, ffo=1.0, all_closed=False, any_closed=False)
    assert status == "access-threatened"
    assert access_lost is False


def test_classify_4tier_access_threatened_from_any_closed_with_zero_depth():
    # 0 depth (outside the extent, or inside with ground==WSE) but SOME (not all)
    # access roads closed -- the "or any access segment is closed" clause of §5.3.
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=0.0, ffo=1.0, all_closed=False, any_closed=True)
    assert status == "access-threatened"
    assert access_lost is False


def test_classify_4tier_operational_when_nothing_triggers():
    status, access_lost = exposure.classify_asset_4tier(
        depth_ft=0.0, ffo=1.0, all_closed=False, any_closed=False)
    assert status == "operational"
    assert access_lost is False


def test_classify_3tier_unchanged_pre_phase7_behavior():
    # Locked precedent: exposed hardcodes access_lost=True regardless of actual road
    # status (unlike the 4-tier model) -- this must never change for 3-tier towns.
    assert exposure.classify_asset_3tier(in_extent=True, all_closed=False) == ("exposed", True)
    assert exposure.classify_asset_3tier(in_extent=False, all_closed=True) == ("isolated", True)
    assert exposure.classify_asset_3tier(in_extent=False, all_closed=False) == ("operational", False)
