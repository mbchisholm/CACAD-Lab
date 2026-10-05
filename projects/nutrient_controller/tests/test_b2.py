"""B2 (rim clamp): params validate; hook, knob, pad and plate pass their print checks; the assembly is clear
across the container range, and the checks catch a too-thick container and misaligned hook bolts."""
import pytest

from projects.nutrient_controller import assembly as A
from projects.nutrient_controller.params import derive, validate
from projects.nutrient_controller.rim_hook import build_hook, build_knob, build_pad, check_rim_parts
from projects.nutrient_controller.wall_plate import build_plate, check_plates


@pytest.fixture(scope="module")
def printed():
    return A.build_printed("B2")


def test_validate():
    validate("B2")


def test_validate_rejects_a_wall_thicker_than_the_throat():
    with pytest.raises(AssertionError, match="throat"):
        validate("B2", rim_c=(2.0, 45.0))


def test_parts():
    check_rim_parts(build_hook("B2"), build_knob("B2"), build_pad("B2"), "B2")
    check_plates(build_plate("B2"), None, "B2")


def test_assembly(printed):
    assert A.check_assembly(printed, A.build_hardware("B2"), "B2") == []


def test_catches_container_too_thick(printed, monkeypatch):
    d = derive("B2", rim_c=(2.0, 45.0))
    monkeypatch.setattr(A, "derive", lambda s: d)
    fails = A.check_assembly(printed, A.build_hardware("B2"), "B2")
    assert any("container 45" in f for f in fails), fails


def test_catches_misaligned_hook_bolts(printed, monkeypatch):
    d = derive("B2", hook_bolts_y=(-46.0, -6.0))          # hardware moved, printed hook and plate not
    monkeypatch.setattr(A, "derive", lambda s: d)
    fails = A.check_assembly(printed, A.build_hardware("B2"), "B2")
    assert any("m5_" in f and ("hook" in f or "plate" in f) for f in fails), fails
