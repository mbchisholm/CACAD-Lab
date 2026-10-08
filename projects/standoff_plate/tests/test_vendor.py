"""Vendor STEP models on the NUTRIENT_ANALOG plates: outline, thickness and holes against the registry, and no
interference with the plate, screws, nuts or each other. The STEPs live in ref/ (gitignored): on a machine without
them these tests skip and say so. Each check has a planted defect that must fail it."""
import pytest
from build123d import Location

from cacad import interference_volume
from projects.standoff_plate import params, vendor
from projects.standoff_plate.plate import build_plate

WITH_STEP = [p for p in params.NUTRIENT_ANALOG if any(pl[0] in params.VENDOR_STEPS for pl in params.PLATES[p]["placements"])]


def _need(name):
    if vendor.load_model(name) is None:
        pytest.skip(f"{name}: vendor STEP not in ref/ on this machine ({params.VENDOR_STEPS[name]['source']})")


@pytest.mark.parametrize("plate", WITH_STEP)
def test_vendor_models_match_registry_and_fit(plate):
    for pl in params.PLATES[plate]["placements"]:
        _need(pl[0])
    rep = vendor.check_vendor(plate)
    assert all(b["vendor"] for b in rep["boards"]), rep["boards"]


def test_planted_sunk_board_hits_the_plate():
    """The fit check is not vacuous: the same model 0.5 mm lower sits in its bosses and rest pads."""
    _need("MOSFET_5648")
    placed = vendor.place_models("MOSFET_5648x3")["boards"][0]["placed"]
    part = build_plate("MOSFET_5648x3")
    assert interference_volume(placed, part) < 1e-6
    assert interference_volume(placed.moved(Location((0, 0, -0.5))), part) > 1.0


def test_planted_wrong_rotation_fails_the_holes(monkeypatch):
    """The MOSFET's holes are on one end: the STEP turned 180 degrees puts them on the other, and the check says so."""
    _need("MOSFET_5648")
    rows = dict(params.VENDOR_STEPS)
    rows["MOSFET_5648"] = dict(rows["MOSFET_5648"], rot=180)
    monkeypatch.setattr(vendor, "VENDOR_STEPS", rows)
    with pytest.raises(AssertionError, match="not in the STEP"):
        vendor.check_vendor("MOSFET_5648x3")
