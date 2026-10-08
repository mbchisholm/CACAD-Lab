"""Geometry + function per version (check_bench: nothing overlaps the garage or itself, load path to lip and slab,
open fronts and knee space, each tote stopped, every screw through its board into the next and nothing else),
buildability (crosscuts only, one screw, stock lengths), the committed build sheets are current, and controls
that show the checks can fail."""
import pytest

from cacad.lumber import frac_in
from projects.tote_bench import params
from projects.tote_bench.bench import check_bench
from projects.tote_bench.build_sheet import path, sheet
from projects.tote_bench.params import IN


def test_geometry_and_function(version, parts):
    check_bench(version, parts)


def test_every_version_validates():
    for v in params.VERSIONS:
        params.validate(v)


def test_ladders_are_identical(d):
    """Every ladder is the same six boards in the same relative places: build one, repeat."""
    shapes = []
    for lad in d["ladders"]:
        x0 = lad["rail_L"]
        mine = sorted((nm.split("-", 1)[1], kind, tuple(round(v, 6) for v in size), tuple(round(v, 6) for v in (lo[0] - x0, lo[1], lo[2])))
                      for nm, (kind, size, lo) in d["boards"].items() if nm.startswith(f"L{lad['i']}-"))
        assert len(mine) == 6
        shapes.append(mine)
    assert all(s == shapes[0] for s in shapes)


def test_one_screw_two_lumber_sizes(d):
    assert {s[5] for s in d["screws"]} == {2.5 * IN}
    assert {k for k, _, _ in d["boards"].values()} <= {"x2x4", "x2x6"}


def test_chair_versions_use_uncut_planks(d):
    if d["fit_planks"]:
        assert not d["plank_cut"] and d["W"] == pytest.approx(d["plank_stock"], abs=IN / 16)


def test_build_sheet_is_current(version):
    with open(path(version)) as f:
        assert f.read() == sheet(version), f"build/{version}.md is stale: run build_sheet.py"


def test_build_sheet_reads_in_tape_fractions(version):
    s = sheet(version)
    assert "33-1/4 in" in s and "31-1/2 in" in s and "17-3/4 in" in s
    assert "." not in "".join(ln.split("|")[1] for ln in s.splitlines() if ln.startswith("| ") and "stop" not in ln.split("|")[1])


@pytest.mark.parametrize("override, match", [
    (dict(knee_min=30.0 * IN), "knee space"),
    (dict(screw_rows=(0.875 * IN, 2.625 * IN)), "apart"),
    (dict(wall_gap=1.0 * IN), "not on the lip"),
    (dict(slat_gap_max=0.5 * IN), "slat gap"),
])
def test_control_validate_refuses(override, match):
    with pytest.raises(AssertionError, match=match):
        params.validate("desk", **override)


def test_frac_in():
    assert [frac_in(x * IN) for x in (33.3125, 0.875, 32.0, 2.625, 0.5)] == ["33-5/16", "7/8", "32", "2-5/8", "1/2"]
