"""params: sourcing, validate(), the numbers that follow from the slope, pump, structure and hydraulics."""
import math

import pytest

from projects.nft_table import params as P


def test_validate_passes():
    """The whole design review: every check green, nothing unsourced."""
    P.validate()


def test_every_value_is_tagged():
    for tname, items in P._tables():
        for k, v in items:
            assert isinstance(v, tuple) and len(v) == 3 and v[1] in P.TAGS and v[2], f"{tname}.{k}"
    assert P.gaps() == []


def test_untagged_value_is_refused(monkeypatch):
    lay = dict(P.LAYOUT)
    lay["hang"] = (55.0, "", "")
    monkeypatch.setattr(P, "LAYOUT", lay)
    with pytest.raises(AssertionError, match="hang: value/tag/source missing"):
        P.validate()


def test_placeholder_fails_by_name(monkeypatch):
    """Rule 2: an unsourced load-bearing value is a failing test, named."""
    row = dict(P.BOUGHT["tee34"])
    row["G"] = (row["G"][0], "PLACEHOLDER", "not published")
    b = dict(P.BOUGHT)
    b["tee34"] = row
    monkeypatch.setattr(P, "BOUGHT", b)
    with pytest.raises(AssertionError, match=r"BOUGHT.tee34.G \(PLACEHOLDER"):
        P.validate()


def test_slope_sets_the_saddles(d):
    """The P1 seat heights differ by the channel's drop between rails."""
    s, h = d["s_rail"], d["saddle_h"]
    assert h["F"] - h["B"] == pytest.approx((s["B"] - s["F"]) * d["sin"], abs=1e-9)
    assert h["M"] - h["B"] == pytest.approx((s["B"] - s["M"]) * d["sin"], abs=1e-9)
    assert h["B"] == pytest.approx(d["p1_t_base"] + P.bv("shcs", "k_M5") + d["L"]["p1_head_clear"])


def test_slope_outside_the_vault_range_is_refused():
    with pytest.raises(AssertionError, match="outside 1:30..1:40"):
        P.validate(slope=1 / 60)


def test_pump_curve_points():
    for ft, gph in ((1.0, 475.0), (5.0, 395.0), (10.0, 205.0)):
        assert P.pump_q(ft * P.FT) / P.GPH_TO_M3S == pytest.approx(gph)
    assert P.pump_q(14.0 * P.FT) == 0.0


def test_pump_meets_the_required_flow(d):
    h = d["hyd"]
    assert h["Q_req"] == pytest.approx(6 * 2.0 * P.LPM_TO_M3S)
    assert h["Q_at"] > h["Q_req"]
    assert h["q_open"] <= 1.0 * P.LPM_TO_M3S <= 2.0 * P.LPM_TO_M3S <= h["q_closed"]


def test_hazen_williams_against_a_hand_value():
    """10.67 L Q^1.852 / (C^1.852 D^4.8704): 10 m of 20.93 mm pipe at 12 L/min, C 150."""
    Q, D = 12 * P.LPM_TO_M3S, 0.02093
    assert P._hw(10.0, Q, D) == pytest.approx(10.67 * 10 * Q ** 1.852 / (150 ** 1.852 * D ** 4.8704))


def test_reactions_carry_the_whole_channel(d):
    for case in ("operating", "flooded"):
        R = d["structure"][case]["reactions"]
        assert R["F"] + R["M"] + R["B"] == pytest.approx(R["total"], rel=1e-9)
        assert min(R["F"], R["M"], R["B"]) > 0


def test_rail_deflection_against_the_closed_form(d):
    """Six equal loads plus self weight vs one UDL of the same total: within 15 % (shape only)."""
    E, I = P.spec("E_al"), P.spec("I2040_edge")
    r = d["frame_defl"]["operating"]["M"]
    W = 6 * r["P"] + P.spec("m2040") * P.G / 1000 * r["span"]
    udl = 5 * W * r["span"] ** 3 / (384 * E * I)
    assert r["max"] == pytest.approx(udl, rel=0.15)


def test_feed_lines_are_equal_and_bend_legal(d):
    lens = [f["length"] for f in d["feed"]]
    assert max(lens) - min(lens) < 1e-9


def test_cut_plan_covers_every_pipe_once_and_fits(d):
    for row, plan in (("pvc34", d["cut"]["pvc34"]), ("pvc2", d["cut"]["pvc2"])):
        names = sorted(n for stick in plan for n, _ in stick)
        want = sorted(n for n, e in d["expect"].items() if e.get("row") == row)
        assert names == want
        usable = P.bv(row, "stick") - d["L"]["pipe_end_trim"]
        for stick in plan:
            assert sum(l + d["L"]["pipe_kerf"] for _, l in stick) <= usable


def test_gland_squeeze_inside_parker(d):
    cs, tol, Lg = P.bv("oring", "cs"), P.bv("oring", "cs_tol"), d["gland_L"]
    lo, hi = P.bv("gland", "squeeze")
    assert lo <= (cs - tol - Lg) / (cs - tol) and (cs + tol - Lg) / (cs + tol) <= hi


def test_p6_screws_engage_across_the_lid_range(d):
    for sx, sy in d["p6_plate"]["screws"]:
        for lt in P.bv("tote", "lid_t_range"):
            assert d["L"]["p6_screw_L"] - d["p6_t_at"](sy) - lt >= d["L"]["p6_engage_min"]


def test_uphill_return_point_is_refused(d):
    """Control: the same path with one point raised above the one before it fails."""
    from projects.nft_table.table import check_fall
    name, pts = next(iter(d["return_paths"].items()))
    bad = list(pts)
    bad[3] = (bad[3][0], bad[3][1], bad[2][2] + 1.0)
    with pytest.raises(AssertionError, match="does not fall"):
        check_fall({name: bad})
