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


def test_split_line_respects_max_length():
    line = LineString([(0, 0), (500, 0)])
    segs = roads.split_line(line, max_len=200.0)
    assert len(segs) == 3
    assert all(s.length <= 200.0 + 1e-6 for s in segs)


def test_split_line_short_line_untouched():
    line = LineString([(0, 0), (150, 0)])
    segs = roads.split_line(line, max_len=200.0)
    assert len(segs) == 1
