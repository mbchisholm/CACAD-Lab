"""Parts and assembly: every printed part builds as one valid solid on its declared bed face, the assembly is clear
pairwise with its designed contacts touching, the camera sees only the leaf plane and the hold-down frame, and every
LED reaches the field and the strip."""
import pytest

from cacad import interference_volume, is_inside
from projects.leaf_imager import params as P
from projects.leaf_imager.assembly import build_printed, check_assembly
from projects.leaf_imager.hardware import build_hardware, view_cone


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


def test_every_part_is_one_valid_solid(printed):
    assert set(printed) == set(P.PARTS)
    for name, p in printed.items():
        assert p.is_valid and len(p.solids()) == 1, name


def test_ledge_carries_the_pcb(d, printed):
    """Material just under the PCB seat at the ledge band and at each corner insert boss, air just above."""
    h = d["inner"] / 2
    ch = printed["chamber"]
    for x, y in ((0.0, h - d["ledge_w"] / 2), (h - d["ledge_w"] / 2, 0.0)):
        assert is_inside(ch, (x, y, d["z_pcb"] - 0.1)) and not is_inside(ch, (x, y, d["z_pcb"] + 0.1))
    for x, y in d["insert_xy"]:
        assert not is_inside(ch, (x, y, d["z_pcb"] - 1.0)), "insert bore missing"
        off = (d["boss_c"] / 2 - 0.2) * (1 if x < 0 else -1)
        assert is_inside(ch, (x + off, y, d["z_pcb"] - 1.0)), "insert boss wall missing"


def test_petiole_path_is_open(d, printed):
    """Air through the chamber's front wall and the base rim at the notch, just above the leaf plane."""
    y_wall = -(d["inner"] / 2 + d["wall"] / 2)
    y_rim = -(d["rim_in"] + d["rim_wall"] / 2)
    assert not is_inside(printed["chamber"], (0.0, y_wall, 2.0))
    assert not is_inside(printed["base"], (0.0, y_rim, 2.0))
    assert is_inside(printed["chamber"], (d["notch_x"][1] + 1.0, y_wall, 2.0))


def test_strip_face_in_the_leaf_plane(d, hw):
    bb = hw["ptfe_strip"].bounding_box()
    assert abs(bb.max.Z) < 1e-6 and abs(bb.min.Z - d["z_strip_floor"]) < 1e-6


def test_frame_is_the_only_thing_in_view(d, printed):
    cone = view_cone(d)
    assert interference_volume(cone, printed["hold_down"]) > 1.0, "frame should lie in the field, on the leaf's edges"
    for name in ("base", "chamber", "roof", "carrier"):
        assert interference_volume(cone, printed[name]) < 1e-3, name


def test_print_sizes_fit_the_bed(d):
    for name, s in P.part_sizes(d).items():
        assert all(v <= b for v, b in zip(sorted(s), sorted(d["bed"]))), name
