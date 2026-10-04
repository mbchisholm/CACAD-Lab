"""B1: params validate; each printed part builds and passes its print checks; the assembly has no unplanned
contact, hangs, and its checks catch planted defects."""
import pytest

from projects.nutrient_controller import assembly as A
from projects.nutrient_controller.body import build_body, check_body
from projects.nutrient_controller.cover import build_cover, check_cover
from projects.nutrient_controller.params import SIZES, derive, validate
from projects.nutrient_controller.wall_plate import build_backing, build_plate, check_plates


@pytest.fixture(scope="module")
def printed():
    return dict(body=build_body(), cover=build_cover(), plate=build_plate(), backing=build_backing())


@pytest.mark.parametrize("size", list(SIZES))
def test_validate(size):
    validate(size)


def test_parts(printed):
    check_body(printed["body"])
    check_cover(printed["cover"])
    check_plates(printed["plate"], printed["backing"])


def test_assembly(printed):
    assert A.check_assembly(printed, A.build_hardware()) == []


def test_catches_board_collision(printed, monkeypatch):
    boards = dict(SIZES["B1"]["back_boards"], ads=("ADS1115", (-30.0, 50.0), 0, "M2"))   # onto the TDS board
    d = derive("B1", back_boards=boards)
    monkeypatch.setattr(A, "derive", lambda s: d)
    fails = A.check_assembly(printed, A.build_hardware())
    assert any("ads" in f and "tds" in f for f in fails), fails


def test_catches_keyhole_too_short(printed, monkeypatch):
    d = derive("B1", slide=4.0)          # posts would rest where the big hole is not
    monkeypatch.setattr(A, "derive", lambda s: d)
    fails = A.check_assembly(printed, A.build_hardware())
    assert any("keyholes" in f for f in fails), fails


def test_validate_catches_low_hole():
    import projects.nutrient_controller.params as P
    d = P.derive("B1", cable_hole=(-20.0, 40.0))
    assert d["lowest_hole_over_water"] < d["hole_over_water"]
