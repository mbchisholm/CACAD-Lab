"""Three layers per bed: geometry + function (check_bed), buildability (cut plan
against stock, screws against the stocked ladder), and the arithmetic of every
inactive bed."""
import pytest

from projects.raised_bed import params
from projects.raised_bed.bed import check_bed


def test_geometry_and_function(bed_name, parts):
    check_bed(bed_name, parts)


def test_every_bed_validates():
    for name in params.BEDS:
        params.validate(name)


def test_cut_plan_covers_every_picket_once(d):
    planned = sorted(n for st in d["picket_plan"] for n, _ in st)
    assert planned == sorted(n for n, (k, _, _) in d["boards"].items() if k == "picket")


def test_cut_plan_fits_stock(d):
    stock = params.LUMBER["picket"]["stock"][0]
    for st in d["picket_plan"]:
        assert sum(l + d["kerf"] for _, l in st) + d["picket_end_trim"] <= stock + 1e-9, st
    stock = params.LUMBER["post"]["stock"][0]
    for st in d["post_plan"]:
        assert sum(l + d["kerf"] for _, l in st) <= stock + 1e-9, st


def test_screw_is_stocked_and_bites(d):
    sc = d["screw_spec"]
    assert d["screw_len"] in sc["lengths"]
    assert d["screw_penetration"] >= sc["min_penetration_d"] * sc["d"] - 1e-9
    assert d["screw_penetration"] < d["p"]


def test_posts_hidden_from_outside(d, parts):
    """The post never reaches the outer faces: it sits inside the pickets on both axes."""
    for n, (k, _, _) in d["boards"].items():
        if k != "post":
            continue
        bb = parts[n].bounding_box()
        assert abs(bb.min.X) <= d["outer_l"] / 2 - d["t"] + 1e-6 and abs(bb.max.X) <= d["outer_l"] / 2 - d["t"] + 1e-6
        assert abs(bb.min.Y) <= d["outer_w"] / 2 - d["t"] + 1e-6 and abs(bb.max.Y) <= d["outer_w"] / 2 - d["t"] + 1e-6
        assert bb.max.Z == pytest.approx(d["height"])
