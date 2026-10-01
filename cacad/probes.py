"""Geometric probes and assertions on built parts.

Assumes: parts may be compounds of several solids, so every probe works
solid-by-solid. `min_ring_wall` assumes a part built around the Z axis;
`min_section_wall` does not.
"""
from __future__ import annotations

import math
from typing import Iterable

from build123d import Face, Part, Plane, Shape, Vector, Vertex, section


def is_inside(part: Shape, pt) -> bool:
    """True if the point is inside any solid of the part."""
    return any(s.is_inside(pt) for s in part.solids())


def assert_material(part: Part, points: dict[str, tuple[tuple[float, float, float], bool]]):
    """points: name -> ((x, y, z), expect_solid). Probes with is_inside.
    Use pairs of probes (just inside / just outside a surface) to prove a
    feature exists at the right place; one point proves little."""
    for name, (pt, expect) in points.items():
        got = is_inside(part, pt)
        assert got == expect, f"probe {name} at {pt}: inside={got}, expected {expect}"


def single_solid(part: Shape):
    solids = part.solids()
    assert len(solids) == 1, f"expected one solid, got {len(solids)}"
    return solids[0]


def expect_solids(part: Shape, n: int, label: str):
    solids = part.solids()
    assert len(solids) == n, f"{label}: expected {n} solids, got {len(solids)}"
    for s in solids:
        assert s.is_valid, f"{label}: a solid is invalid"


def assert_bbox(part: Shape, size_xyz: tuple[float, float, float], zmin: float, tol: float, label: str):
    bb = part.bounding_box()
    got = (bb.size.X, bb.size.Y, bb.size.Z)
    for axis, g, want in zip("XYZ", got, size_xyz):
        assert abs(g - want) <= tol, f"{label}: bbox {axis} = {g:.3f}, expected {want:.3f} ±{tol}"
    assert abs(bb.min.Z - zmin) <= tol, f"{label}: bbox zmin = {bb.min.Z:.3f}, expected {zmin:.3f}"


def min_ring_wall(part: Part, z: float, n_samples: int = 24) -> float:
    """Thinnest radial wall of the XY cross-section at height z, measured on the
    geometry: per section face, (closest outer-boundary point to the Z axis)
    minus (farthest inner-boundary point from it). Overlapping solids' section
    faces are unioned first. A face with no inner wire (a finger between two
    slots) reports its own radial extent. Slots and thread roots are seen
    as-is, so this floors any analytic wall table.
    Assumes the part is arranged around the Z axis."""
    faces = list(section(part, Plane.XY.offset(z)).faces())
    assert faces, f"no material in section at z={z}"
    merged = faces[0].fuse(*faces[1:]) if len(faces) > 1 else faces[0]
    walls = []
    for f in merged.faces():
        def radii(wire):
            pts = [e.position_at(i / n_samples) for e in wire.edges() for i in range(n_samples + 1)]
            return [(p.X**2 + p.Y**2) ** 0.5 for p in pts]
        outer = radii(f.outer_wire())
        inner = [r for w in f.inner_wires() for r in radii(w)]
        walls.append(min(outer) - max(inner) if inner else max(outer) - min(outer))
    return min(walls)


def min_section_wall(part: Part, z: float, n_samples: int = 24) -> float:
    """Thinnest wall of the XY cross-section at height z, for parts that are not
    arranged around the Z axis (plates with off-axis bosses and pockets).
    Per section face: the smallest distance from a sample point on any inner
    wire to the outer wire or to another inner wire. A face with no inner wire
    (a plain slab, a solid boss) reports its own smallest bbox extent, so a
    thin rib is still seen. Floors any analytic wall table, like min_ring_wall,
    without the Z-axis assumption."""
    faces = list(section(part, Plane.XY.offset(z)).faces())
    assert faces, f"no material in section at z={z}"
    merged = faces[0].fuse(*faces[1:]) if len(faces) > 1 else faces[0]
    walls = []
    for f in merged.faces():
        inner = list(f.inner_wires())
        if not inner:
            bb = f.bounding_box()
            walls.append(min(bb.size.X, bb.size.Y))
            continue
        outer = f.outer_wire()
        for i, w in enumerate(inner):
            others = [outer] + inner[:i] + inner[i + 1:]
            for e in w.edges():
                for k in range(n_samples + 1):
                    v = Vertex(e.position_at(k / n_samples))
                    walls.append(min(o.distance_to(v) for o in others))
    return min(walls)


def max_overhang_deg(faces: Iterable[Face], up, n: int = 5) -> tuple[float, Face | None]:
    """Largest downward-facing angle from vertical over the sampled faces.
    0 = vertical wall, 90 = flat ceiling. Samples an n x n grid in (u, v) on
    each face (FINDINGS F14). Returns (angle, worst face)."""
    up = Vector(up).normalized()
    worst, worst_face = 0.0, None
    for f in faces:
        for i in range(n):
            for j in range(n):
                nrm = f.normal_at((i + 0.5) / n, (j + 0.5) / n)
                down = -nrm.dot(up)
                if down > 1e-6:
                    ang = math.degrees(math.asin(min(1.0, down)))
                    if ang > worst:
                        worst, worst_face = ang, f
    return worst, worst_face
