"""Geometry + function (check_bench: every board in place, nothing overlaps, the load path, the totes sit on both
rungs and touch nothing, every screw bites its member and nothing else), the params themselves (sources, inventory,
braces over the range on hand, bearing, work height) and the build sheet."""
import pytest

from projects.tote_bench import params
from projects.tote_bench.build_sheet import access_conflicts, render, screws_by_joint
from projects.tote_bench.params import DESIGN, IN, INVENTORY, SCREW, SPF, STORE_2X4, TOTE

TAGS = {"STANDARD", "VENDOR", "DESIGN", "UNVERIFIED", "INFERRED"}


def test_geometry_and_function(d, checked):
    n = len(d["boards"]) + len(d["prisms"]) + 1
    assert len(checked["assembly"].solids()) == n
    assert len(checked["totes"].solids()) == d["cols"] * d["levels"]
    assert len(checked["screws"].solids()) == len(d["screws"])


def test_validate_passes():
    params.validate()


@pytest.mark.parametrize("table", [DESIGN, TOTE, SCREW, SPF], ids=["DESIGN", "TOTE", "SCREW", "SPF"])
def test_every_number_has_tag_and_source(table):
    for k, row in table.items():
        assert isinstance(row, tuple) and len(row) == 3, f"{k}: (value, TAG, source)"
        _, tag, src = row
        assert tag in TAGS, f"{k}: tag {tag!r}"
        assert isinstance(src, str) and src.strip(), f"{k}: no source"


def test_cut_plan_fits_inventory(d):
    n_sticks, stick = INVENTORY["x2x2"][0], INVENTORY["x2x2"][1]
    assert len(d["plan_2x2"]) <= n_sticks
    for st in d["plan_2x2"]:
        assert sum(ln + d["kerf"] for _, ln in st) <= stick + 1e-9, st
    for st in d["plan_bought_2x4"]:
        assert sum(ln + d["kerf"] for _, ln in st) <= STORE_2X4[0] + 1e-9, st
    rails = d["plan_on_hand"]["31 in 2x4s, trimmed"]
    assert len(rails) <= INVENTORY["x2x4_31"][0]
    for nm in rails:
        assert max(d["boards"][nm][1]) <= INVENTORY["x2x4_31"][1] + 1e-9, nm
    legs = d["plan_on_hand"]["legs (on hand, 72 in, no cut)"]
    assert len(legs) <= INVENTORY["leg72"][0]
    assert all(d["boards"][nm][1][2] == INVENTORY["leg72"][1] for nm in legs)
    assert len(d["plan_on_hand"]["45 deg braces (on hand, no cut)"]) <= INVENTORY["brace45"][0]


def test_cut_plan_covers_every_piece_once(d):
    planned = [n for names in d["plan_on_hand"].values() for n in names]
    planned += [n for plan in ("plan_2x2", "plan_bought_2x4") for st in d[plan] for n, _ in st]
    planned += [n for n in d["plan_sheet"] if n != "TOP"]   # the top is not a board; it is built from d["top"]
    assert sorted(planned) == sorted(list(d["boards"]) + list(d["prisms"]))


@pytest.mark.parametrize("end", [0, 1], ids=["short", "long"])
def test_braces_at_both_ends_of_the_range(d, end):
    L = DESIGN["brace_range"][0][end]
    assert params._brace_checks(d, L) == []
    params.validate(brace_long_point=L)


def test_work_surface_in_range(d):
    lo, hi = d["work_height_range"]
    assert lo <= d["work_surface"] <= hi


def test_every_tote_bears_on_both_rungs(d):
    w, s, D = d["w"], d["s"], d["D"]
    for tn, (yb0, yb1) in d["tote_bottoms"].items():
        front = min(w + s, yb1) - max(w, yb0)
        back = min(D - w, yb1) - max(D - w - s, yb0)
        assert front >= d["bearing_min"] - 1e-9, f"{tn} front {front / IN:.2f} in"
        assert back >= d["bearing_min"] - 1e-9, f"{tn} back {back / IN:.2f} in"


def test_untrimmed_31s_fail_on_bearing():
    """Why the 31 in 2x4s are trimmed: at full length the tote, against the back panel, misses the front rung."""
    with pytest.raises(AssertionError, match="tote bottom on the front rung"):
        params.validate(D=INVENTORY["x2x4_31"][1])


def test_build_sheet_names_every_piece(d):
    md = render(d)
    for nm in list(d["boards"]) + list(d["prisms"]) + ["TOP"]:
        assert nm in md, nm


def test_build_sheet_accounts_for_every_screw(d):
    by_joint = screws_by_joint(d)
    assert sum(len(v) for v in by_joint.values()) == len(d["screws"])
    total = len(d["screws"]) + d["top_screws"] + d["toe_screws"]
    assert sum(d["screw_counts"].values()) == total


def test_every_screw_can_be_driven(d):
    """No two members need each other in place first: a screw whose head ends up buried against a member has to go
    in before it, so a pair where each buries the other's screws cannot be assembled in any order."""
    bad = access_conflicts(d)
    assert not bad, "head buried by the other member, no order drives both: " + "; ".join(f"{a} vs {b}" for a, b in bad)
