"""Small geometry helpers in the assembly frame (params.py): boxes and cylinders by extents, hex pockets, the
corbels under the ledge and corner bosses, and thin rods between two points (light rays)."""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Part, Plane, Pos, Rectangle, RegularPolygon, Solid, Vector, extrude, loft


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(x, y, r, z0, z1) -> Part:
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def hex_prism(x, y, r, z0, z1) -> Part:
    """Hex of circumradius r, flats perpendicular to X (standoff_plate's pockets)."""
    return Pos(x, y, z0) * extrude(RegularPolygon(r, 6, rotation=30), amount=z1 - z0)


def frustum(half_top: tuple, half_bot: tuple, z_top: float, z_bot: float, centre=(0.0, 0.0)) -> Part:
    """Loft between two centred rectangles (half sizes) at z_top and z_bot."""
    cx, cy = centre
    return loft([Plane.XY.offset(z_bot) * Pos(cx, cy) * Rectangle(2 * half_bot[0], 2 * half_bot[1]),
                 Plane.XY.offset(z_top) * Pos(cx, cy) * Rectangle(2 * half_top[0], 2 * half_top[1])])


def corner_corbel(sx: int, sy: int, inner_half: float, wall: float, c: float, z_top: float) -> Part:
    """45 deg corbel under a c x c corner block: a rectangle from the cavity corner's c-square (plus the wall) at
    z_top, shrinking toward the corner by 1 mm per mm down until it is inside the wall."""
    def rect(inset):
        x0, x1 = inner_half - inset, inner_half + wall
        return (x0 + x1) / 2, (x1 - x0) / 2
    (cxt, ht), (cxb, hb) = rect(c), rect(0.1)
    dz = c - 0.1
    return loft([Plane.XY.offset(z_top - dz) * Pos(sx * cxb, sy * cxb) * Rectangle(2 * hb, 2 * hb),
                 Plane.XY.offset(z_top) * Pos(sx * cxt, sy * cxt) * Rectangle(2 * ht, 2 * ht)])


def rod(p0, p1, r: float = 0.3) -> Solid:
    """A thin cylinder from p0 to p1: a light ray's envelope."""
    a, b = Vector(*p0), Vector(*p1)
    v = b - a
    return Solid.make_cylinder(r, v.length, Plane(origin=a, z_dir=v.normalized()))


def cone(wd: float, fov: tuple, z_bot: float = 0.0, z_top_gap: float = 0.5) -> Part:
    """The camera's view pyramid from just under the lens (wd - z_top_gap) to the plane z_bot."""
    tx, ty = (math.tan(math.radians(a / 2)) for a in fov)
    zt = wd - z_top_gap
    return frustum((z_top_gap * tx, z_top_gap * ty), ((wd - z_bot) * tx, (wd - z_bot) * ty), zt, z_bot)
