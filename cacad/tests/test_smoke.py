"""Smoke tests on trivial shapes; the package must stand without the project."""
import math
import pytest
from build123d import Align, Axis, Box, Compound, Cone, Cylinder, Location, Vector

import cacad

A = (Align.CENTER, Align.CENTER, Align.MIN)


def ring(r_out=10.0, r_in=6.0, h=8.0):
    return Cylinder(r_out, h, align=A) - Cylinder(r_in, h, align=A)


def test_selectors():
    p = ring()
    assert len(cacad.circular_edges(p, 6.0, 0.0)) == 1
    assert len(cacad.circular_edges(p, 10.0, 8.0)) == 1
    assert len(cacad.cylindrical_faces(p, 6.0)) == 1
    assert len(cacad.planar_faces_with_normal(p, Vector(0, 0, -1), 0.0)) == 1
    hexp = Box(10, 10, 5, align=A)
    assert len(cacad.line_edges_at_z(hexp, 5.0)) == 4
    assert len(cacad.line_edges_at_z(hexp, 5.0, min_r=100)) == 0


def test_try_chamfer_and_fallback():
    p = ring()
    q = cacad.try_chamfer(p, cacad.circular_edges(p, 6.0, 0.0), 0.5, (0.3,), "bore")
    assert q.is_valid and len(q.faces()) == len(p.faces()) + 1
    # impossible size falls back, then gives up with a warning, not an exception
    with pytest.warns(UserWarning, match="left sharp"):
        r = cacad.try_chamfer(p, cacad.circular_edges(p, 10.0, 8.0), 50.0, (40.0,), "rim")
    assert r.is_valid
    with pytest.raises(AssertionError):
        cacad.try_chamfer(p, [], 0.5, (), "nothing", required=True)


def test_probes_and_walls():
    p = ring()
    cacad.assert_material(p, {"wall": ((8, 0, 4), True), "bore": ((0, 0, 4), False), "outside": ((11, 0, 4), False)})
    cacad.assert_bbox(p, (20, 20, 8), 0.0, 1e-6, "ring")
    assert abs(cacad.min_ring_wall(p, 4.0) - 4.0) < 1e-3
    # a slot through the wall: the wall between slots is still 4, the finger reports its own extent
    slotted = p - Box(12, 1, 10, align=(Align.MIN, Align.CENTER, Align.MIN))
    assert abs(cacad.min_ring_wall(slotted, 4.0) - 4.0) < 1e-3
    cacad.single_solid(p)
    # off-axis: a 30 x 20 x 4 slab with a bore at (10, 5): thinnest wall is 20/2 - 5 - 1.5 = 3.5 to the +Y edge
    slab = Box(30, 20, 4, align=A) - Cylinder(1.5, 4, align=A).moved(Location((10, 5, 0)))
    assert abs(cacad.min_section_wall(slab, 2.0) - 3.5) < 1e-2
    assert abs(cacad.min_section_wall(Box(30, 20, 4, align=A), 2.0) - 20.0) < 1e-6
    assert abs(cacad.min_section_wall(p, 4.0) - 4.0) < 1e-2          # agrees with min_ring_wall on a ring
    cacad.expect_solids(Compound(children=[p, p.moved(Location((30, 0, 0)))]), 2, "two")


def test_max_overhang():
    cone = Cone(5, 3, 4, align=A)                       # narrows upward: side faces outward-up -> no overhang
    ang, _ = cacad.max_overhang_deg(cone.faces(), (0, 0, 1))
    assert ang == 90.0                                  # only the flat bottom faces down
    side = [f for f in cone.faces() if f.geom_type.name == "CONE"]
    assert cacad.max_overhang_deg(side, (0, 0, 1))[0] == 0.0
    assert abs(cacad.max_overhang_deg(side, (0, 0, -1))[0] - math.degrees(math.atan2(2, 4))) < 0.5


def test_booleans_pairwise(tmp_path):
    a = Compound(children=[Cylinder(5, 10, align=A), Cylinder(5.2, 10, align=A)])
    far = Cylinder(3, 10, align=A).moved(Location((30, 0, 0)))
    near = Cylinder(3, 10, align=A).moved(Location((6, 0, 0)))
    assert cacad.interference_volume(a, far) == 0.0
    assert cacad.interference_volume(a, near) > 1.0
    assert cacad.interference_pieces(a, near)
    assert cacad.volume_of(None) == 0.0
    step, stl = cacad.export(a, "compound", tmp_path)
    assert step.exists() and stl.exists()
