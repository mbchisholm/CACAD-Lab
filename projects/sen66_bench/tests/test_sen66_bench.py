"""Three layers per size: geometry + function (check_part; the screw plate also runs standoff_plate's check_plate),
manufacturability (walls, declared orientation, overhang: the screw plate only at its nut pockets' stepped bridges,
the peg plate nowhere), and the arithmetic of every size, with planted defects."""
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


def test_overhang_only_where_declared(d, part):
    """The lip, the groove and the pegs add no overhang. The screw plate's declared ceilings are standoff_plate's
    stepped bridges, as many as it counts for its bosses; the peg plate has none."""
    o = d["print_orientation"]["plate"]
    rep = check_overhang(part, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"],
                                    nozzle_d=d["nozzle_d"], exceptions=o["overhang_exceptions"]))
    if d["fixing"] == "peg":
        assert not rep["exceptions_found"], rep
        return
    p = d["p"]
    by_z = {z: sum(1 for *_, fz in rep["exceptions_found"] if abs(fz - z) < 0.01) for z in p["bridge_z"]}
    n = len(p["holes"])
    assert by_z == {p["bridge_z"][0]: 2 * n, p["bridge_z"][1]: 2 * n, p["bridge_z"][2]: n}, (by_z, rep)


def test_lip_clears_the_outlet_and_groove_takes_the_bend(d):
    e = d["e"]
    assert d["z_lip_top"] - d["z_floor"] < min(z for _, z in e["arch"])
    assert d["plug_bottom_z"] - d["z_groove"] >= e["bend_room"] - 1e-9


@pytest.mark.parametrize("variant, override, message", [
    ("SEN66_BENCH", dict(floor_web=2.0), "groove leaves"),               # no floor left under the groove
    ("SEN66_BENCH", dict(arch_margin=-0.5), "outlet arch"),              # a lip tall enough to shade the exhaust
    ("SEN66_BENCH", dict(end_room=20.0), "battery/microSD end"),         # no room to pull the Metro's microSD card
    ("SEN66_BENCH", dict(header_room=10.0), "POWER/AD header side"),     # the sensor crowds the Metro's rear headers
    ("SEN66_BENCH", dict(cable_edge="+Y"), "cable edge"),                # the STEMMA QT pair no longer faces the edge
    ("SEN66_BENCH_PEG", dict(peg_clear=1.0), "peg"),                     # a breakout peg too thin to print
])
def test_validate_refuses_planted_defects(variant, override, message):
    with pytest.raises(AssertionError, match=message):
        params.validate(variant, **override)


def test_both_versions_share_the_layout():
    a, b = params.derive("SEN66_BENCH"), params.derive("SEN66_BENCH_PEG")
    assert a["p"]["plate_size"] == b["p"]["plate_size"] and a["sensor_xy"] == b["sensor_xy"]
    assert [pg["xy"] for pg in b["pegs"]] == list(a["p"]["holes"])
