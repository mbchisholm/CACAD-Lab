"""Parts and assembly: every printed part builds as one valid solid on its declared bed face, the assembly is clear
pairwise with its designed contacts touching, the camera sees the whole floor past the tray, and the floor has air
round it in the body."""
import pytest

from cacad import is_inside
from projects.birdhouse import params as P
from projects.birdhouse.assembly import build_printed, check_assembly
from projects.birdhouse.hardware import build_hardware


@pytest.fixture(scope="module")
def d():
    return P.validate()


@pytest.fixture(scope="module")
def printed():
    return build_printed()


@pytest.fixture(scope="module")
def hw():
    return build_hardware()


def test_assembly_checks_pass(printed, hw):
    report = check_assembly(printed=printed, hw=hw)
    assert any(line.startswith("pairwise clear") for line in report)
    assert any("sees" in line and "of the floor" in line for line in report)


def test_every_part_is_one_valid_solid(printed):
    assert set(printed) == set(P.PARTS)
    for name, p in printed.items():
        assert p.is_valid and len(p.solids()) == 1, name


def test_floor_has_air_round_it(d, printed):
    """Between the floor's edge and the wall: neither part. On the ledge under it: body."""
    z = sum(d["floor_z"]) / 2
    x_gap = d["floor_x"] + d["fit"] / 2
    assert not is_inside(printed["body"], (x_gap, 0.0, z)) and not is_inside(printed["floor"], (x_gap, 0.0, z))
    assert is_inside(printed["body"], (d["floor_x"] - 1.0, 0.0, d["ledge_t"] - 0.5))


def test_floor_foot_is_chamfered(d, printed):
    """Just inside the floor's edge at its bed face: air (the chamfer); a millimetre up: floor."""
    z0 = d["floor_z"][0]
    assert not is_inside(printed["floor"], (d["floor_x"] - 0.1, 0.0, z0 + 0.1))
    assert is_inside(printed["floor"], (d["floor_x"] - 0.1, 0.0, z0 + 1.0))


def test_entry_hole_is_open_and_the_perch_is_solid(d, printed):
    y = sum(d["panel_y"]) / 2
    assert not is_inside(printed["front"], (0.0, y, d["hole_z"]))
    assert is_inside(printed["front"], (0.0, d["panel_y"][0] - d["perch_len"] + 1.0, d["perch_z"]))


def test_lens_window_and_led_bores_are_through(d, printed):
    zt = sum(d["tray_z"]) / 2
    assert not is_inside(printed["tray"], (*d["lens_xy"], zt))
    for x, y in d["led_xy"]:
        assert not is_inside(printed["tray"], (x, y, zt))


def test_print_sizes_fit_the_bed(d):
    for name, s in P.part_sizes(d).items():
        assert all(v <= b for v, b in zip(sorted(s), sorted(d["bed"]))), name
