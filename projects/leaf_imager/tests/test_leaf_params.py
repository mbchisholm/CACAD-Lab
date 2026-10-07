"""params: sourcing, the SPEC's validate() checks, and that each check refuses what it should."""
import math

import pytest

from projects.leaf_imager import params as P


@pytest.fixture(scope="module")
def d():
    return P.validate()


def test_validate_passes(d):
    """Every SPEC check green, nothing unsourced."""
    assert d["size"] in P.ACTIVE_SIZES


def test_every_value_is_tagged():
    for name, v, tag, src in P._tagged(P._tables()):
        assert tag in P.TAGS and src, name


def test_untagged_value_is_refused(monkeypatch):
    common = dict(P.COMMON)
    common["ring_r"] = (60.0, "", "")
    monkeypatch.setattr(P, "COMMON", common)
    with pytest.raises(AssertionError, match="ring_r: value/tag/source missing"):
        P.validate()


def test_placeholder_fails_by_name(monkeypatch):
    leds = dict(P.LEDS)
    leds["b450"] = dict(leds["b450"], vf=(2.9, "PLACEHOLDER", "datasheet not read"))
    monkeypatch.setattr(P, "LEDS", leds)
    with pytest.raises(AssertionError, match="b450.vf is PLACEHOLDER"):
        P.validate()


def test_field_matches_the_spec(d):
    """SPEC Geometry table: 121 x 91 mm at 100 mm, 74 um/px binned, 4.8 / 9.7 mm depth of field."""
    assert d["field"][0] == pytest.approx(120.6, abs=0.1) and d["field"][1] == pytest.approx(90.7, abs=0.1)
    assert d["um_px_binned"] == pytest.approx(73.5, abs=0.5)
    assert d["dof_full"] == pytest.approx(4.85, abs=0.05) and d["dof_binned"] == pytest.approx(9.7, abs=0.1)


def test_leds_see_the_centre_at_45(d):
    for b, pts in d["led_xyz"].items():
        for x, y, z in pts:
            assert math.degrees(math.atan2(z, math.hypot(x, y))) == pytest.approx(45.0, abs=d["angle_tol"]), b


def test_no_two_leds_share_a_position(d):
    pts = [p[:2] for b in P.BANDS for p in d["led_xyz"][b]]
    assert len(pts) == len(P.BANDS) * d["per_band"]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert math.dist(pts[i], pts[j]) > 10.0


def test_uniformity_model_reproduces_spec_table():
    """SPEC 'The LED ring' table: 4 flat LEDs at r 60, h 60, over 80 % of the 121 x 91 field."""
    leds = [(60 * math.cos(a), 60 * math.sin(a), 60.0) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    half = (0.8 * 60.3, 0.8 * 45.35)
    assert P.irradiance_ratio(120.0, leds, half) == pytest.approx(1.39, abs=0.05)
    assert P.irradiance_ratio(30.0, leds, half) > 100      # a +/-15 deg clear 5 mm LED fails the ring


def test_narrow_beam_fails(monkeypatch):
    leds = dict(P.LEDS)
    leds["fr730"] = dict(leds["fr730"], beam=(30.0, "VENDOR", "clear 5 mm 730 nm, +/-15 deg"))
    monkeypatch.setattr(P, "LEDS", leds)
    with pytest.raises(AssertionError, match="fr730: irradiance"):
        P.validate()


def test_overdriven_850_fails():
    with pytest.raises(AssertionError, match="nir850: .* over 0.7 x the 100 mA maximum"):
        P.validate(i_led=dict(b450=100.0, g525=100.0, r660=100.0, fr730=100.0, nir850=100.0))


def test_under_minimum_current_fails():
    with pytest.raises(AssertionError, match="r660: .* under the datasheet minimum"):
        P.validate(i_led=dict(b450=100.0, g525=100.0, r660=50.0, fr730=100.0, nir850=60.0))


def test_closer_than_focus_fails():
    with pytest.raises(AssertionError, match="inside the lens's closest focus"):
        P.validate(wd=90.0, min_leaf=(90.0, 60.0))   # 90 mm also shrinks the leaf area; isolate the focus check


def test_ring_in_view_cone_fails():
    with pytest.raises(AssertionError, match="view cone"):
        P.validate(ring_r=30.0, ring_h=30.0)


def test_chamber_governed_by_the_ring(d):
    assert d["inner_governed_by"] == "ring PCB on its ledge"
    assert d["pcb_outer_band"] >= d["pad_margin"] + d["ledge_w"] - 1e-9


def test_ribbon_fits(d):
    assert d["ribbon_path"] <= d["cam"]["ribbon_len"] - d["ribbon_slack"]
