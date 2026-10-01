import math
import pytest
from build123d import Align, Box, Cone, Cylinder, Vector

from cacad.checks import orientation, overhang, printability

A = (Align.CENTER, Align.CENTER, Align.MIN)


def test_printability():
    printability.check_walls_vs_nozzle({"a": 0.8, "b": 1.2}, {"nozzle_d": 0.4})
    with pytest.raises(AssertionError):
        printability.check_walls_vs_nozzle({"thin": 0.6}, {"nozzle_d": 0.4})
    printability.check_slots_vs_nozzle({"s": 0.4}, {"nozzle_d": 0.4})
    ring = Cylinder(10, 8, align=A) - Cylinder(6, 8, align=A)
    got = printability.check_measured_walls(ring, {"nozzle_d": 0.4, "probes": {"mid": 4.0}})
    assert abs(got["mid"] - 4.0) < 1e-3


def test_orientation():
    box = Box(10, 10, 5, align=A)
    orientation.check_declared_orientation(box, {"up": (0, 0, 1), "bed_z": 0.0, "bed_face": "bottom", "known_overhangs": []})
    orientation.check_declared_orientation(box, {"up": (0, 0, -1), "bed_z": 5.0, "bed_face": "top", "known_overhangs": []})
    with pytest.raises(AssertionError):
        orientation.check_declared_orientation(box, {"up": (0, 0, 1), "bed_z": 2.0, "bed_face": "?", "known_overhangs": []})
    flipped = orientation.to_print_orientation(box, {"up": (0, 0, -1), "bed_z": 5.0})
    assert abs(flipped.bounding_box().min.Z) < 1e-9


def test_overhang():
    # a T: wide plate on a narrow post -> the plate's underside is an undeclared ceiling
    t = Cylinder(3, 5, align=A) + Cylinder(8, 2, align=A).moved(__import__("build123d").Location((0, 0, 5)))
    p = {"up": (0, 0, 1), "bed_z": 0.0, "max_deg": 45.0, "nozzle_d": 0.4}
    with pytest.raises(AssertionError):
        overhang.check_overhang(t, p)
    rep = overhang.check_overhang(t, dict(p, exceptions=[("plate underside", 5.0)]))
    assert rep["exceptions_found"] and not rep["offenders"]
    # a 45-degree frustum widening upward is fine at 45, not at 40
    fr = Cone(3, 6, 3, align=A)
    overhang.check_overhang(fr, dict(p, max_deg=45.5))
    with pytest.raises(AssertionError):
        overhang.check_overhang(fr, dict(p, max_deg=40.0))
    # stale exception list is itself a failure
    with pytest.raises(AssertionError):
        overhang.check_overhang(Box(4, 4, 4, align=A), dict(p, exceptions=[("ghost", 2.0)]))

def test_rederive_compare_logic():
    from cacad.freecad import rederive
    assert rederive.compare({"a&b": 0.0, "a&c": 64.6}, {"a&b": 0.0, "a&c": 64.59}) == []
    assert rederive.compare({"a&b": 0.0}, {"a&b": 0.0})            # zeros only: flagged
    assert rederive.compare({"a&b": 0.0, "a&c": 64.6}, {"a&b": 1.5, "a&c": 64.6})
