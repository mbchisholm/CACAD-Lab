"""Select faces/edges by geometric predicate, never by index.

Assumes: nothing about the part, except that "at height z" means the
world Z coordinate of the feature's centre (rotate the part first if its
axis is not Z).
"""
from __future__ import annotations

from build123d import Edge, Face, GeomType, Shape, ShapeList, Vector


def circular_edges(shape: Shape, radius: float, z: float, tol: float = 1e-3) -> ShapeList[Edge]:
    """Circle/arc edges with the given radius whose centre lies at height z.
    Arcs left by slots or chamfers keep their full-circle radius and centre,
    so a ring of arcs is returned as one list."""
    return shape.edges().filter_by(GeomType.CIRCLE).filter_by(
        lambda e: abs(e.radius - radius) < tol and abs(e.center().Z - z) < tol
    )


def line_edges_at_z(shape: Shape, z: float, min_r: float = 0.0, tol: float = 1e-3) -> ShapeList[Edge]:
    """Straight edges whose centre lies in the plane z, optionally only those at
    least min_r from the Z axis (e.g. the outline of a hex, not its bore)."""
    def ok(e: Edge) -> bool:
        c = e.center()
        return abs(c.Z - z) < tol and (c.X**2 + c.Y**2) ** 0.5 >= min_r
    return shape.edges().filter_by(GeomType.LINE).filter_by(ok)


def planar_faces_with_normal(shape: Shape, normal, z: float | None = None, tol: float = 1e-3) -> ShapeList[Face]:
    """Planar faces whose outward normal equals `normal` (same sense), optionally
    with their centre at height z."""
    n = Vector(normal).normalized()

    def ok(f: Face) -> bool:
        if f.geom_type != GeomType.PLANE:
            return False
        if (f.normal_at() - n).length > tol:
            return False
        return z is None or abs(f.center().Z - z) < tol

    return shape.faces().filter_by(ok)


def cylindrical_faces(shape: Shape, radius: float, tol: float = 1e-3) -> ShapeList[Face]:
    """Cylindrical faces of the given radius whose axis is parallel to Z."""
    def ok(f: Face) -> bool:
        if f.geom_type != GeomType.CYLINDER:
            return False
        if abs(f.radius - radius) > tol:
            return False
        ax = f.axis_of_rotation
        return ax is not None and abs(abs(ax.direction.Z) - 1) < tol

    return shape.faces().filter_by(ok)
