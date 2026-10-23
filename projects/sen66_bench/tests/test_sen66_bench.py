"""Three layers: geometry + function (check_part, which runs standoff_plate's check_plate on the plate under it),
manufacturability (walls, declared orientation, overhang only at the nut pockets' stepped bridges), and the
arithmetic of every size."""
import pytest

from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.checks.printability import check_walls_vs_nozzle
from projects.sen66_bench import params
from projects.sen66_bench.sen66_bench import check_part


def test_geometry_and_function(size, part):
    check_part(size, part)


def test_every_size_validates():
    for size in params.SIZES:
        params.validate(size)


def test_walls_vs_nozzle(d):
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))


def test_declared_orientation(d, part):
    check_declared_orientation(part, d["print_orientation"]["plate"])


def test_overhang_only_at_the_nut_pocket_bridges(d, part):
    """The lip and the groove add no overhang: the declared ceilings are the plate's, as many as standoff_plate
    counts for its bosses."""
    o = d["print_orientation"]["plate"]
    rep = check_overhang(part, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"],
                                    nozzle_d=d["nozzle_d"], exceptions=o["overhang_exceptions"]))
    p = d["p"]
    by_z = {z: sum(1 for *_, fz in rep["exceptions_found"] if abs(fz - z) < 0.01) for z in p["bridge_z"]}
    n = len(p["holes"])
    assert by_z == {p["bridge_z"][0]: 2 * n, p["bridge_z"][1]: 2 * n, p["bridge_z"][2]: n}, (by_z, rep)


def test_lip_clears_the_outlet_and_groove_takes_the_bend(d):
    e = d["e"]
    assert d["z_lip_top"] - d["z_floor"] < min(z for _, z in e["arch"])
    assert d["plug_bottom_z"] - d["z_groove"] >= e["bend_room"] - 1e-9


@pytest.mark.parametrize("override, message", [
    (dict(finger_room=20.0), "plug needs"),                  # the sensor crowds the breakout's GH plug
    (dict(floor_web=2.0), "groove leaves"),                 # no floor left under the groove
    (dict(arch_margin=-0.5), "outlet arch"),                # a lip tall enough to shade the exhaust
    (dict(metro_side_room=12.0), "from the Metro"),         # no finger room at the Metro's headers
])
def test_validate_refuses_planted_defects(override, message):
    with pytest.raises(AssertionError, match=message):
        params.validate("SEN66_BENCH", **override)
