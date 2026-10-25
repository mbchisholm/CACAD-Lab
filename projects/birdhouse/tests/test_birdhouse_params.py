"""params: sourcing, the fit and power checks, and that each check refuses what it should."""
import re

import pytest

from cacad.registries.materials import FIT_CLEAR
from projects.birdhouse import params as P


@pytest.fixture(scope="module")
def d():
    return P.validate()


def test_validate_passes(d):
    assert d["size"] in P.ACTIVE_SIZES


def test_every_value_is_tagged():
    for name, v, tag, src in P._tagged(P._tables()):
        assert tag in P.TAGS and src, name


def test_untagged_value_is_refused(monkeypatch):
    common = dict(P.COMMON)
    common["perch_d"] = (10.0, "", "")
    monkeypatch.setattr(P, "COMMON", common)
    with pytest.raises(AssertionError, match="perch_d: value/tag/source missing"):
        P.validate()


def test_placeholder_fails_by_name(monkeypatch):
    tpl = dict(P.TPL5110)
    tpl["iq_ua"] = (20.0, "PLACEHOLDER", "not read")
    monkeypatch.setattr(P, "TPL5110", tpl)
    with pytest.raises(AssertionError, match="TPL5110.iq_ua is PLACEHOLDER"):
        P.validate()


def test_floor_fit_is_the_registry_clearance(d):
    """The floor clears the walls, jambs and panel by FIT_CLEAR, and its bed edge is chamfered past the foot."""
    assert d["fit"] == FIT_CLEAR
    assert abs((d["in_x"] - d["floor_x"]) - FIT_CLEAR) < 1e-9
    assert abs((d["floor_y"][0] - d["panel_y"][1]) - FIT_CLEAR) < 1e-9
    assert d["foot_chamfer"] >= 0.4


def test_perch_is_larger_and_below_the_hole(d):
    assert d["perch_d"] >= 10.0 and d["perch_len"] >= 50.0
    assert d["perch_z"] + d["perch_d"] / 2 <= d["hole_z"] - d["hole_d"] / 2


def test_every_header_pin_has_a_job():
    pins = {p for row in P.ESP32CAM["pins"][0] for p in row}
    tokens = {t for p, _, _ in P.WIRING for t in re.split(r"[ ,/]+", p)}
    missing = {x for x in pins if not set(x.split("/")) & tokens}
    assert not missing, f"pins with no wiring row: {missing}"


def test_power_budget_closes(d):
    assert d["autonomy_days"] >= d["autonomy_min"]
    assert d["wh_harvest_dec"] >= d["harvest_margin"] * d["wh_day"]


def test_a_four_minute_interval_fails_the_harvest():
    """Still a week on the cell, but December sun no longer refills it."""
    with pytest.raises(AssertionError, match="December harvest"):
        P.validate(interval_s=240.0)


def test_a_too_bright_ir_string_is_refused():
    with pytest.raises(AssertionError, match="IR current"):
        P.validate(ir_ma=90.0)


def test_cradle_on_the_rim_is_refused():
    with pytest.raises(AssertionError, match="tpl cradle"):
        P.validate(tpl_xy=(42.0, -30.0))
