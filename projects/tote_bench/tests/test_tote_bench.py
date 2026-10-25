"""Geometry + function (check_bench: nothing overlaps the garage or itself, back frame on the lip against the
drywall, front legs on the slab, open fronts and knee space, each tote stopped by the lip or the ledger, every
screw through its board into the next and nothing else), buildability (crosscuts, stock, screws, wall screws vs
lap screws at any stud position), the build sheet is current and covers every board in one stage, and controls
that show the checks can fail."""
import pytest

from cacad.lumber import frac_in
from projects.tote_bench import params
from projects.tote_bench.bench import check_bench
from projects.tote_bench.build_sheet import STAGES, path, sheet, stage_of
from projects.tote_bench.params import IN


def test_geometry_and_function(version, parts):
    check_bench(version, parts)


def test_every_version_validates():
    for v in params.VERSIONS:
        params.validate(v)


def test_ladders_are_identical(d):
    """Every ladder is the same six boards in the same relative places."""
    shapes = []
    for lad in d["ladders"]:
        x0 = lad["rail_L"]
        mine = sorted((nm.split("-", 1)[1], kind, tuple(round(v, 6) for v in size), tuple(round(v, 6) for v in (lo[0] - x0, lo[1], lo[2])))
                      for nm, (kind, size, lo) in d["boards"].items() if nm.startswith(f"L{lad['i']}-"))
        assert len(mine) == 6
        shapes.append(mine)
    assert all(s == shapes[0] for s in shapes)


def test_whole_boards_and_two_screws(d):
    for nm in ("SILL", "LEDGER", *[n for n in d["boards"] if n.startswith("PLANK")]):
        assert max(d["boards"][nm][1]) == pytest.approx(120 * IN), nm
    assert {s[5] for s in d["screws"]} == {2.5 * IN}
    assert d["wall_screw"]["length"] == pytest.approx(3.5 * IN)


def test_back_frame_uses_the_lip_and_the_wall(d):
    """Sill and back legs stand on the lip top; sill and ledger touch the drywall; front legs stand on the slab."""
    b = d["boards"]
    for nm in ("SILL", "LEDGER"):
        assert b[nm][2][1] == 0.0
    assert b["SILL"][2][2] == d["lip_h"] and b["L0-LEG-BACK"][2][2] == d["lip_h"]
    assert b["L0-LEG-FRONT"][2][2] == 0.0
    assert d["upper_tote_y"] - d["tote_stop_gap"] == pytest.approx(b["LEDGER"][1][1])


def test_every_board_has_one_stage_in_build_order(d):
    for nm in d["boards"]:
        assert sum(any(p in nm for p in frag) for _, _, frag in STAGES) == 1, nm
    # anything a board rests on is in the same or an earlier stage
    assert stage_of("SILL") < stage_of("L0-RAIL-TOP-L") < stage_of("L0-LEG-FRONT") < stage_of("C0-SLAT-0") < stage_of("PLANK-0")


def test_build_sheet_is_current(version):
    with open(path(version)) as f:
        assert f.read() == sheet(version), f"build/{version}.md is stale: run build_sheet.py"


def test_build_sheet_reads_in_tape_fractions(version):
    s = sheet(version)
    for want in ("30-1/4 in", "28-1/2 in", "23-5/8 in", "Stage 1: Back frame on the wall"):
        assert want in s, want
    assert "." not in "".join(ln.split("|")[1] for ln in s.splitlines() if ln.startswith("| ") and "stop" not in ln.split("|")[1])


@pytest.mark.parametrize("override, match", [
    (dict(knee_min=30.0 * IN), "knee space"),
    (dict(rail_rows=(0.875 * IN, 2.625 * IN)), "plank screws"),
    (dict(stud_rows=(1.375 * IN, 2.125 * IN)), "meets lap row"),
    (dict(lip_edge_min=1.5 * IN), "does not fit the lip"),
    (dict(slat_gap_max=0.5 * IN), "slat gap"),
    (dict(tote_gap_over=3.25 * IN), "ledger catches"),
])
def test_control_validate_refuses(override, match):
    with pytest.raises(AssertionError, match=match):
        params.validate("long", **override)


def test_frac_in():
    assert [frac_in(x * IN) for x in (33.3125, 0.875, 32.0, 2.625, 0.5)] == ["33-5/16", "7/8", "32", "2-5/8", "1/2"]
