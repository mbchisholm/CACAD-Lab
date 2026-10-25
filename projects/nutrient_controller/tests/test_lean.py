"""L1 (lean): params validate; body and lid pass their print checks; every bought part is clear of both prints;
and each check fails on the defect it guards against (planted)."""
import pytest

from projects.nutrient_controller.lean_box import build_body, build_hardware, build_lid, check_assembly, check_body, check_lid
from projects.nutrient_controller.lean_params import derive, validate


@pytest.fixture(scope="module")
def d():
    return derive()


@pytest.fixture(scope="module")
def parts(d):
    return build_body(d), build_lid(d)


def test_validate():
    validate()


@pytest.mark.parametrize("override, match", [
    (dict(jst_gap=5.0), "plug needs"),                        # drivers' JST plugs jammed against the carrier
    (dict(cable_zone=12.0), "jack body"),                     # no room for the jack under the boards
    (dict(right_strip=6.0), "lid column"),                    # top driver into the corner column
    (dict(notches=(("I2C", -10.0, "carrier"), ("DS18B20", 8.0, "carrier"))), "bottom wall"),   # notch at a column
    (dict(driver_gap=1.0, cable_zone=30.0), "bosses/pads"),   # neighbouring drivers' bosses merge (box kept tall)
])
def test_validate_catches(override, match):
    with pytest.raises(AssertionError, match=match):
        validate(**override)


def test_prints(parts, d):
    body, lid = parts
    check_body(body, d)
    check_lid(lid, d)


def test_assembly(parts, d):
    assert check_assembly(*parts, build_hardware(d), d) == []


def test_assembly_catches_jack_on_a_board(parts, d):
    # a jack body long enough to reach the lowest boards
    hw = build_hardware(dict(d, jack=dict(d["jack"], body_l=d["cable_zone"] + 5.0)))
    assert any("jack vs boards" in f for f in check_assembly(*parts, hw, d))


def test_assembly_catches_misaligned_lid(d):
    body = build_body(d)
    shifted = dict(d, columns=[(x + 1.0, y) for x, y in d["columns"]])
    fails = check_assembly(body, build_lid(shifted), build_hardware(d), d)
    assert any("lid vs lid_screws" in f for f in fails), fails
