"""Three layers per rack: geometry + function (check_rack: load path probes, totes touch nothing, every screw
bites its target), buildability (cut plan against stock, screws against the stocked ladder), the arithmetic of
every inactive rack, and the spec's own bounding-box table (S7) reproduced from derive()."""
import pytest

from projects.tote_rack import params
from projects.tote_rack.params import IN
from projects.tote_rack.rack import check_rack

# Spec S7, worked example: ID -> (min corner, size), inches. Typed from the spec, not derived.
SPEC_S7 = {
    "LEG-FL": ((0.00, 0.00, 0.00), (1.5, 3.5, 72.0)), "LEG-FR": ((22.00, 0.00, 0.00), (1.5, 3.5, 72.0)),
    "LEG-BL": ((0.00, 27.50, 0.00), (1.5, 3.5, 72.0)), "LEG-BR": ((22.00, 27.50, 0.00), (1.5, 3.5, 72.0)),
    "STR-L1": ((1.50, 0.00, 14.75), (0.75, 31.0, 1.5)), "STR-L2": ((1.50, 0.00, 31.75), (0.75, 31.0, 1.5)),
    "STR-L3": ((1.50, 0.00, 48.75), (0.75, 31.0, 1.5)), "STR-L4": ((1.50, 0.00, 65.75), (0.75, 31.0, 1.5)),
    "STR-R1": ((21.25, 0.00, 14.75), (0.75, 31.0, 1.5)), "STR-R2": ((21.25, 0.00, 31.75), (0.75, 31.0, 1.5)),
    "STR-R3": ((21.25, 0.00, 48.75), (0.75, 31.0, 1.5)), "STR-R4": ((21.25, 0.00, 65.75), (0.75, 31.0, 1.5)),
    "RUN-L1": ((1.50, 0.00, 16.25), (0.75, 31.0, 0.75)), "RUN-L2": ((1.50, 0.00, 33.25), (0.75, 31.0, 0.75)),
    "RUN-L3": ((1.50, 0.00, 50.25), (0.75, 31.0, 0.75)), "RUN-L4": ((1.50, 0.00, 67.25), (0.75, 31.0, 0.75)),
    "RUN-R1": ((21.25, 0.00, 16.25), (0.75, 31.0, 0.75)), "RUN-R2": ((21.25, 0.00, 33.25), (0.75, 31.0, 0.75)),
    "RUN-R3": ((21.25, 0.00, 50.25), (0.75, 31.0, 0.75)), "RUN-R4": ((21.25, 0.00, 67.25), (0.75, 31.0, 0.75)),
    "TIE-FRONT-TOP": ((1.50, 0.00, 70.5), (20.5, 0.75, 1.5)),
    "TIE-BACK-TOP": ((1.50, 30.25, 70.5), (20.5, 0.75, 1.5)),
    "TIE-BACK-BOT": ((1.50, 27.50, 0.00), (20.5, 3.5, 1.5)),
}


def test_geometry_and_function(rack_name, parts):
    check_rack(rack_name, parts)


def test_every_rack_validates_or_names_the_unknown_tote():
    """A rack whose tote is not calipered fails validate() by name (never silently), every other rack passes."""
    for name, r in params.RACKS.items():
        if any(r[k] is None for k in ("TWr", "TWb", "T_rim")):
            with pytest.raises(AssertionError, match="not known"):
                params.validate(name)
        else:
            params.validate(name)


def test_hdx_bin_is_recorded_from_its_label():
    t = params.TOTES["HDX_207585"]
    assert (t["lid_l"] / params.IN, t["lid_w"] / params.IN, t["h_with_lid"] / params.IN) == pytest.approx((28.6, 19.6, 15.2))
    r = params.RACKS["hdx_207585"]
    assert r["TL"] == t["lid_l"] and r["TWr"] is None


def test_sheets_cover_every_screw_head(d):
    """Every screw's head lands on exactly one member sheet, at that member's face."""
    from projects.tote_rack.build_sheet import holes_on, sheet_groups
    n = sum(len(holes_on(d, m)[3]) for ms in sheet_groups(d).values() for m in ms)
    assert n == len(d["screws"])
    for nm in d["boards"]:
        axis, long_ax, across, holes = holes_on(d, nm)
        _, size, _ = d["boards"][nm]
        for along, acr, _ in holes:
            assert -1e-6 <= along <= size[long_ax] + 1e-6 and -1e-6 <= acr <= size[across] + 1e-6, (nm, along, acr)


def test_derive_reproduces_spec_table():
    d = params.derive("4x27gal")
    assert set(d["boards"]) == set(SPEC_S7)
    for name, (lo, size) in SPEC_S7.items():
        _, got_size, got_lo = d["boards"][name]
        assert tuple(x / IN for x in got_lo) == pytest.approx(lo, abs=1e-9), name
        assert tuple(x / IN for x in got_size) == pytest.approx(size, abs=1e-9), name
    assert (d["W"] / IN, d["D"] / IN, d["H"] / IN) == (23.5, 31.0, 72.0)
    assert [z / IN for z in d["railtops"]] == [17, 34, 51, 68]


def test_spec_interference_checks(d):
    """Spec S7's three clearance checks, with the rim lip counted (T_rim), which the spec's own arithmetic implies."""
    assert d["tote_base"][0] / IN == pytest.approx(2.75)          # > back bottom tie top 1.5
    assert d["gap_under_tote"][-1] / IN == pytest.approx(2.75)    # top tote base to the runner below
    assert d["gap_over_top_tote"] > 0                             # spec says 2.5; with the rim lip it is 1.75


def test_cut_plan_covers_every_board_once(d):
    planned = sorted(n for plan in d["cut_plans"].values() for st in plan for n, _ in st)
    assert planned == sorted(d["boards"])


def test_cut_plan_fits_stock(d):
    for kind, plan in d["cut_plans"].items():
        stock = params.LUMBER[kind]["stock"][0]
        for st in plan:
            assert sum(l + d["kerf"] for _, l in st) <= stock + 1e-9, (kind, st)


def test_screws_are_stocked_and_bite(d):
    sc = d["screw_spec"]
    for jn, (through, into, ln) in d["joints"].items():
        assert ln in sc["lengths"], jn
        assert ln - through >= sc["min_penetration_d"] * sc["d"] - 1e-9, jn
        assert ln < through + into, f"{jn}: screw exits the member"


def test_spec_shopping_list_screw_lengths_checked(d):
    """Spec S9 buys 2.5 in for frame joints: through a 0.75 stringer into a 1.5 leg that exits by 0.25 in.
    derive() must not pick it for that joint."""
    assert d["joints"]["stringer->leg"][2] / IN < 0.75 + 1.5
    assert d["joints"]["tie->leg"][2] / IN == 2.5


def test_front_is_open(d, parts):
    """No member crosses the front plane between the legs below the top tie."""
    for n, p in parts.items():
        bb = p.bounding_box()
        if n.startswith("LEG") or n == "TIE-FRONT-TOP":
            continue
        crosses_front = bb.min.Y < 1e-6 and bb.min.X < d["W"] - d["leg_t"] - d["str_t"] - 1e-6 and bb.max.X > d["leg_t"] + d["str_t"] + 1e-6
        assert not crosses_front, n
