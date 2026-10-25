"""Geometry + function (check_bench: nothing overlaps the garage or itself, load path to the lip and slab, open
front, each tote stopped by the lip or the stretcher), buildability (stock, screws), and controls that show the
checks can fail."""
import pytest

from projects.workbench import params
from projects.workbench.bench import _box, _no_overlap, build_garage, build_totes, check_bench
from projects.workbench.params import IN


def test_geometry_and_function(bench_name, parts):
    check_bench(bench_name, parts)


def test_every_bench_validates():
    for name in params.BENCHES:
        params.validate(name)


def test_back_legs_stand_on_the_lip_and_front_legs_on_the_slab(d):
    for nm, (base, r, h) in d["feet"].items():
        want = d["lip_h"] if nm.endswith("BACK") else 0.0
        assert base[2] == pytest.approx(want), nm
    assert d["back_leg_z"][0] - d["front_leg_z"][0] == pytest.approx(d["lip_h"])


def test_tote_is_the_registry_hdx(d):
    assert (d["tote_x"] / IN, d["tote_y"] / IN, d["tote_h"] / IN) == pytest.approx((28.6, 19.6, 15.2))


def test_buy_list(d):
    assert len(d["sheet_plan"]) == 2 and len(d["cut_plan_2x4"]) == 5


def test_control_a_tote_in_the_lip_is_caught(bench_name):
    """Shift a lower tote 1 in toward the wall: it must overlap the lip, or the overlap check proves nothing."""
    d = params.derive(bench_name)
    tn = "TOTE-B0-LOWER"
    size, lo = d["totes"][tn]
    moved = {tn: _box(size, (lo[0], lo[1] - 1 * IN, lo[2]), tn)}
    with pytest.raises(AssertionError, match="LIP"):
        _no_overlap([moved, build_garage(bench_name)], "control")
    _no_overlap([build_totes(bench_name), build_garage(bench_name)], "as built")


@pytest.mark.parametrize("override, match", [
    (dict(wall_gap=1.0 * IN), "not on the lip"),
    (dict(stop_engage_min=2.0 * IN), "stretcher hangs"),
    (dict(top_depth=20.0 * IN), "past the top's front edge"),
])
def test_control_validate_refuses(bench_name, override, match):
    with pytest.raises(AssertionError, match=match):
        params.validate(bench_name, **override)


def test_height_rises_when_the_totes_need_it(bench_name):
    d = params.derive(bench_name, tote_gap_over=2.0 * IN)
    assert d["top_h_governed_by"] == "two totes stacked" and d["top_h"] > d["top_h_target"]
