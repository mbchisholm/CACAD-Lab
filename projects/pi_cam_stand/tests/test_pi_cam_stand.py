"""Pi camera stand: params validate and every input is tagged, both printed parts build as one valid solid on their
declared bed faces, and the assembly is clear pairwise, over the tilt range, and in the camera's view down to 45 deg."""
import pytest

from cacad import is_inside
from projects.pi_cam_stand import params as P
from projects.pi_cam_stand.assembly import build_printed, check_assembly


@pytest.fixture(scope="module")
def d():
    return P.validate()


@pytest.fixture(scope="module")
def printed():
    return build_printed()


def test_every_input_is_tagged_and_sourced():
    for name, v, tag, src in P._tagged(P._tables()):
        assert tag in P.TAGS and src, name


def test_ribbon_needs_the_long_cable(d):
    """The stock 150 mm ribbon cannot reach; the bought 300 mm one does with slack."""
    assert d["ribbon_path"] > d["ribbon"]["stock_length"]
    assert d["ribbon_path"] <= d["ribbon"]["length"] - d["ribbon_slack"]


def test_lens_height(d):
    assert abs(d["lens_asm0"][2] - d["lens_h"]) < 1e-9


def test_parts_are_one_valid_solid(printed):
    assert set(printed) == set(P.PARTS)
    for name, p in printed.items():
        assert p.is_valid and len(p.solids()) == 1, name


def test_camera_screw_bores_and_pockets(d, printed):
    """Each M2 bore is open through boss and plate, its nut pocket is open at the back (hex flats face X, so it
    reaches 0.866 r along X), and boss wall surrounds it."""
    c = printed["carrier"]
    for x, y in d["cam_holes_c"]:
        assert not is_inside(c, (x, y, d["z_cam_back"] - 0.5))
        assert not is_inside(c, (x + 0.866 * d["cam_pocket"]["r"] - 0.3, y, 0.5)), "nut pocket missing"
        assert is_inside(c, (x + d["cam_boss_r"] - 0.3, y, d["z_cam_back"] - 0.5)), "boss wall missing"


def test_pi_bosses_and_nut_pockets(d, printed):
    s = printed["stand"]
    for x, y in d["pi_holes"]:
        assert is_inside(s, (x + d["pi_boss_r"] - 0.3, y, d["z_pi_bot"] - 0.5)), "boss wall missing"
        assert not is_inside(s, (x, y, d["z_pi_bot"] - 0.5)), "bore missing"
        assert not is_inside(s, (x + 0.866 * d["pi_pocket"]["r"] - 0.3, y, 0.5)), "nut pocket missing"


def test_ribbon_window_and_hinge_bore_open(d, printed):
    s = printed["stand"]
    zw = sum(d["window_z"]) / 2
    assert not is_inside(s, (0.0, (d["y_wb"] + d["y_wf"]) / 2, zw)), "ribbon window closed"
    for x in (-(d["side_x"][0] + 1), d["side_x"][0] + 1):
        assert not is_inside(s, (x, 0.0, d["hinge_z"])), "hinge bore closed"
        assert is_inside(s, (x, 0.0, d["hinge_z"] + d["hinge_bore"] / 2 + 1.5)), "cheek missing above the bore"


def test_assembly_checks_pass(printed):
    report = check_assembly(printed=printed)
    assert any(line.startswith("pairwise clear") for line in report)
    assert any(line.startswith("view clear") for line in report)
