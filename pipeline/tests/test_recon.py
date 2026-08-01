"""Offline unit tests for 00_recon.py / floodops_v2_lib.py pure logic (no network)."""
import re

import floodops_v2_lib as fl


def test_levels_ft_is_0_to_20_whole_feet():
    assert fl.LEVELS_FT == list(range(0, 21))


def test_whole_foot_name_regex_matches_main():
    m = fl.WHOLE_FOOT_NAME_RE.match("Rutgers NJ 7 ft. Coastal Inundation Extent")
    assert m is not None
    assert m.group(1) == "7"
    assert m.group(2) is None  # main layer, no low-lying suffix


def test_whole_foot_name_regex_matches_low_lying():
    m = fl.WHOLE_FOOT_NAME_RE.match(
        "Rutgers NJ 20 ft. Coastal Inundation Extent, Low-Lying Areas"
    )
    assert m is not None
    assert m.group(1) == "20"
    assert m.group(2) == ", Low-Lying Areas"


def test_whole_foot_name_regex_rejects_half_foot():
    # Half-foot levels (out of scope, §2.1) must NOT match the whole-foot pattern.
    m = fl.WHOLE_FOOT_NAME_RE.match("Rutgers NJ 7 ft., 6 in. Coastal Inundation Extent")
    assert m is None


def test_whole_foot_name_regex_matches_mhhw_baseline_as_level_0():
    # The 0 ft layer has a differently-worded suffix; owner-approved 2026-08-01 to
    # bring it into scope as level 0 (reversing the original exclusion, §2.1).
    m = fl.WHOLE_FOOT_NAME_RE.match(
        "Rutgers NJ 0 ft. Coastal Inundation Extent (Mean Higher High Water)"
    )
    assert m is not None
    assert m.group(1) == "0"
    assert m.group(2) is None  # main layer, no low-lying suffix


def test_whole_foot_name_regex_matches_mhhw_baseline_low_lying_as_level_0():
    # Real layer name has a trailing space after "Areas" -- \s*$ must tolerate it.
    m = fl.WHOLE_FOOT_NAME_RE.match(
        "Rutgers NJ 0 ft. Coastal Inundation Extent (Mean Higher High Water), "
        "Low-Lying Areas "
    )
    assert m is not None
    assert m.group(1) == "0"
    assert m.group(2) == ", Low-Lying Areas"


def test_count_vertices_simple_polygon():
    geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
    assert fl.count_vertices(geom) == 4


def test_count_vertices_multipolygon():
    geom = {"type": "MultiPolygon", "coordinates": [
        [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        [[[5, 5], [6, 5], [6, 6], [5, 5]]],
    ]}
    assert fl.count_vertices(geom) == 8
