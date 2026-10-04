"""Every active concept validates, builds, and passes its function checks; the checks catch a planted collision."""
import pytest

from projects.nutrient_controller import concepts as C
from projects.nutrient_controller.concept_params import ACTIVE_CONCEPTS, CONCEPTS, derive, validate


@pytest.mark.parametrize("concept", list(CONCEPTS))
def test_validate(concept):
    validate(concept)


@pytest.mark.parametrize("concept", ACTIVE_CONCEPTS)
def test_build_and_check(concept):
    m = C.BUILDERS[concept](derive(concept))
    for name, part in m["printed"].items():
        assert part.is_valid, f"{concept} {name} invalid"
        assert len(part.solids()) == 1, f"{concept} {name}: {len(part.solids())} solids"
    assert C.check(concept, m) == []


def test_check_catches_collision(monkeypatch):
    layout = dict(CONCEPTS["A_lid"]["floor_parts"], relay=(-40, 25, 0))      # onto the TDS board
    d = derive("A_lid", floor_parts=layout)
    monkeypatch.setattr(C, "derive", lambda c: d)
    fails = C.check("A_lid", C.build_A(d))
    assert any("relay x tds_board" in f for f in fails), fails
