"""Geometry + function (check_bench: every board in place, nothing overlaps, the load path, the totes clear
everything and sit against their stops, every screw bites its member and nothing else), the params themselves
(sources, inventory, fit, structure, negative controls that must fail) and the build sheet (every piece named, every
screw driven before anything covers its head, nothing blocks a piece on its way in)."""
import pytest

from projects.tote_bench import params
from projects.tote_bench.build_sheet import (access_conflicts, counted_screws, open_issues, render, schedule,
                                             screws_by_joint, steps)
from projects.tote_bench.params import DESIGN, IN, INVENTORY, LBF, SCREW, SPF, STORE_2X4, TOTE

TAGS = {"STANDARD", "VENDOR", "DESIGN", "UNVERIFIED", "INFERRED"}


def test_geometry_and_function(d, checked):
    n = len(d["boards"]) + len(d["prisms"]) + 1                      # + the notched top
    assert len(checked["assembly"].solids()) == n
    assert len(checked["totes"].solids()) == len(d["totes"]) == 4
    assert len(checked["screws"].solids()) == len(d["screws"])
    bb, tol = checked["bbox"], d["bbox_tol"]
    for got, want in zip((bb.X, bb.Y, bb.Z), (d["W"], d["D"], d["H"] + d["ply"])):
        assert abs(got - want) < tol, (got, want)


def test_validate_passes():
    params.validate()


@pytest.mark.parametrize("table", [DESIGN, TOTE, SCREW, SPF], ids=["DESIGN", "TOTE", "SCREW", "SPF"])
def test_every_number_has_tag_and_source(table):
    for k, row in table.items():
        assert isinstance(row, tuple) and len(row) == 3, f"{k}: (value, TAG, source)"
        _, tag, src = row
        assert tag in TAGS, f"{k}: tag {tag!r}"
        assert isinstance(src, str) and src.strip(), f"{k}: no source"


def test_cuts_fit_the_inventory(d):
    n_sticks, stick = INVENTORY["x2x2"][0], INVENTORY["x2x2"][1]
    assert len(d["plan_2x2"]) <= n_sticks
    for st in d["plan_2x2"]:
        assert d["end_trim"] + sum(ln + d["kerf"] for _, ln in st) <= stick + 1e-9, st
    for st in d["plan_bought_2x4"]:
        assert d["end_trim"] + sum(ln + d["kerf"] for _, ln in st) <= STORE_2X4[0] + 1e-9, st
    con = d["cut_on_hand"]
    assert len(con["72 in 2x4"]) <= INVENTORY["leg72"][0]
    assert all(ln <= INVENTORY["leg72"][1] + 1e-9 for _, ln in con["72 in 2x4"])
    assert len(con["31 in 2x4"]) <= INVENTORY["x2x4_31"][0]
    assert all(ln <= INVENTORY["x2x4_31"][1] + 1e-9 for _, ln in con["31 in 2x4"])
    # the floor side rails come from the two front legs' offcuts
    n_front = sum(1 for _, ln in con["72 in 2x4"] if ln < INVENTORY["leg72"][1])
    assert len(con["72 in offcuts"]) <= n_front
    assert all(ln <= d["leg_offcut"] + 1e-9 for _, ln in con["72 in offcuts"])
    assert d["leg_offcut"] >= d["D"] - 1e-9
    lo, _ = INVENTORY["brace45"][1]
    assert len(con["45 deg braces"]) <= INVENTORY["brace45"][0]
    assert d["brace_long_point"] <= lo - d["brace_recut_min"] + 1e-9


def test_every_piece_is_cut_exactly_once(d):
    assert "TOP" not in d["boards"]                                  # the top is built from d["top"]
    planned = [n for pieces in d["cut_on_hand"].values() for n, _ in pieces]
    planned += [n for plan in ("plan_2x2", "plan_bought_2x4") for st in d[plan] for n, _ in st]
    planned += [n for n, _, _ in d["plan_sheet"]]
    planned += ["PEGBOARD"]                                          # cut from the bought panel (validate checks its size)
    assert sorted(planned) == sorted(list(d["boards"]) + list(d["prisms"]) + ["TOP"])


def test_work_surface_in_range(d):
    lo, hi = d["work_height_range"]
    assert lo <= d["work_surface"] <= hi


def test_lid_gaps_and_front_reveal(d):
    assert len(d["lid_gap"]) == 2
    for g in d["lid_gap"]:
        assert g >= d["clear_lid"] - 1e-9
    assert d["front_reveal"] >= d["front_reveal_min"] - 1e-9


def test_structure(d):
    assert d["shelf_rail_stress"] <= d["shelf_rail_Fb"]
    assert d["shelf_rail_defl"] <= d["bay"] / d["defl_limit_shelf"]
    assert d["apron_stress"] <= d["apron_Fb"]
    assert d["apron_defl"] <= d["bay"] / d["defl_limit_top"]


@pytest.mark.parametrize("over, match", [
    (dict(hutch_shelf_d=30 * IN), "cannot be recut"),                # brace longer than the shortest on hand
    (dict(clear_mid=3 * IN), "wider than the sheet"),                # bay grows past the 4 ft plywood
    (dict(D=32 * IN), "longer than the 31 in on hand"),
    (dict(clear_lid=2 * IN), "outside the window"),                  # two levels push the work surface too high
    (dict(tote_L=TOTE["L"][0] + 1 * IN), "behind the bench front"),  # tote sticks out the front
    (dict(point_load=500 * LBF), "under the point load"),            # apron overstressed
], ids=["long hutch", "wide bay", "deep bench", "tall lid gap", "long tote", "heavy lean"])
def test_negative_controls_fail(over, match):
    with pytest.raises(AssertionError, match=match):
        params.validate(**over)


def test_every_screw_can_be_driven(d):
    """No two members need each other in place first, and the build sheet's order drives every modelled screw before
    anything covers its head and brings every piece in along a clear path."""
    bad = access_conflicts(d)
    assert not bad, "head buried by the other member, no order drives both: " + "; ".join(f"{a} vs {b}" for a, b in bad)
    sch = schedule(d)
    assert not sch["late"], sch["late"]
    assert not sch["blocked"], sch["blocked"]
    assert not sch["undriven"], sch["undriven"]
    assert not sch["loose"], sch["loose"]
    assert open_issues(d) == []


def _moved(keys, key, after):
    keys = [k for k in keys if k != key]
    keys.insert(keys.index(after) + 1, key)
    return keys


def test_wrong_orders_are_caught(d):
    """The order check has teeth: the lip screwed up through the shelf once it is on its frame buries the heads on the
    back shelf rail; the shelf or the top added late cannot get past what is above it; the top frame's end screws
    are under the legs."""
    keys = [st["key"] for st in steps(d)]
    late = schedule(d, _moved(keys, "shelf panel", "shelf on"))["late"]
    assert late and {m for _, m in late} == {"SHELF-RAIL-B"}
    blocked = schedule(d, _moved(keys, "shelf on", "right legs"))["blocked"]
    assert {(b, a) for _, b, a in blocked} >= {("SHELF", "APRON-F"), ("SHELF", "JOIST-TOP")}
    blocked = schedule(d, _moved(keys, "top", "arms"))["blocked"]
    assert {(b, a) for _, b, a in blocked} == {("TOP", "ARM-L"), ("TOP", "ARM-R")}
    late = schedule(d, _moved(keys, "top frame", "right legs"))["late"]
    assert {m for _, m in late} == {"LEG-FL", "LEG-FR", "LEG-BL", "LEG-BR"}


def test_build_sheet_names_every_piece(d):
    md = render(d)
    for nm in list(d["boards"]) + list(d["prisms"]) + ["TOP"] + list(d["totes"]):
        assert nm in md, nm


def test_build_sheet_accounts_for_every_screw(d):
    by_joint = screws_by_joint(d)
    assert sum(len(v) for v in by_joint.values()) == len(d["screws"])
    assert counted_screws(d) == d["screw_counts"]
