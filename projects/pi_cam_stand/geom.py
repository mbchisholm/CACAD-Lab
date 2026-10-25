"""Small geometry helpers: boxes and cylinders by extents, hex pockets, teardrop bores along X (tip +Z, so a
horizontal hole prints without support), and the camera's view pyramid."""
from __future__ import annotations

import math

from build123d import (Box, Cylinder, Part, Plane, Polygon, Pos, Rectangle, RegularPolygon, Circle, extrude, loft)


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(x, y, r, z0, z1) -> Part:
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def cyl_x(y, z, r, x0, x1) -> Part:
    return extrude(Plane.YZ.offset(x0) * Pos(y, z) * Circle(r), amount=x1 - x0)


def hex_prism(x, y, r, z0, z1) -> Part:
    """Hex of circumradius r along Z, flats perpendicular to X (standoff_plate's pockets)."""
    return Pos(x, y, z0) * extrude(RegularPolygon(r, 6, rotation=30), amount=z1 - z0)


def hex_x(y, z, r, x0, x1) -> Part:
    """Hex of circumradius r along X with a vertex at +Z: its roof faces lean 30 deg off horizontal, no flat ceiling."""
    return extrude(Plane.YZ.offset(x0) * Pos(y, z) * RegularPolygon(r, 6, rotation=30), amount=x1 - x0)


def teardrop_x(y, z, r, x0, x1) -> Part:
    """Round bore along X with a 45 deg point at +Z."""
    s = r / math.sqrt(2)
    # counter-clockwise in (y, z), or the point extrudes toward -X and never fuses with the round part
    tip = Polygon((y + s, z + s), (y, z + r * math.sqrt(2)), (y - s, z + s), align=None)
    return cyl_x(y, z, r, x0, x1) + extrude(Plane.YZ.offset(x0) * tip, amount=x1 - x0)


def view_pyramid(apex, fov, length, gap=0.5) -> Part:
    """The camera's view from just ahead of the lens (apex + gap along +Z) to `length`, half-angles from fov
    (x, y degrees, full)."""
    ax, ay, az = apex
    tx, ty = (math.tan(math.radians(a / 2)) for a in fov)
    return loft([Plane.XY.offset(az + gap) * Pos(ax, ay) * Rectangle(2 * gap * tx, 2 * gap * ty),
                 Plane.XY.offset(az + length) * Pos(ax, ay) * Rectangle(2 * length * tx, 2 * length * ty)])
