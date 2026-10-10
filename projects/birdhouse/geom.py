"""Small geometry helpers in the assembly frame (params.py): boxes and cylinders by extents, rounded-corner prisms,
the cap's sloped plane, L-shaped cradle corners, and the print pose of a part."""
from __future__ import annotations

import math

from build123d import (Axis, Box, Cylinder, Location, Part, Plane, Pos, Rectangle, RectangleRounded, Solid, Vector,
                       extrude)


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(x, y, r, z0, z1) -> Part:
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def cyl_y(x, z, r, y0, y1) -> Solid:
    """Cylinder along Y from y0 to y1, axis at (x, z)."""
    return Solid.make_cylinder(r, y1 - y0, Plane(origin=(x, y0, z), z_dir=(0, 1, 0)))


def cone_y(x, z, r0, r1, y0, y1) -> Solid:
    """Cone along Y: radius r0 at y0, r1 at y1."""
    return Solid.make_cone(r0, r1, y1 - y0, Plane(origin=(x, y0, z), z_dir=(0, 1, 0)))


def rbox(x0, x1, y0, y1, z0, z1, r) -> Part:
    """Box with its four vertical edges rounded to r."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * extrude(RectangleRounded(x1 - x0, y1 - y0, r), amount=z1 - z0)


def slope_plane(z_at_y0: float, y0: float, deg: float) -> Plane:
    """The plane z = z_at_y0 + (y - y0) tan(deg), normal pointing up and toward -Y."""
    s, c = math.sin(math.radians(deg)), math.cos(math.radians(deg))
    return Plane(origin=(0, y0, z_at_y0), x_dir=(1, 0, 0), z_dir=(0, -s, c))


def below(plane: Plane, size: float = 1000.0) -> Part:
    """A large block on the -normal side of the plane: intersect with it to cut a part off at the plane."""
    return plane * Pos(0, 0, -size / 2) * Box(size, size, size)


def on_plane(plane: Plane, sx: float, sy: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Part:
    """A sx x sy x h block standing on the plane (local X across, local Y up the slope), centred at (cx, cy)."""
    return plane * Pos(cx, cy, h / 2) * Box(sx, sy, h)


def cradle_corners(x0, x1, y0, y1, fit, wall, leg, z0, z1) -> Part:
    """Four L-shaped corner walls round a board outline, `fit` outside it."""
    a0, a1, b0, b1 = x0 - fit - wall, x1 + fit + wall, y0 - fit - wall, y1 + fit + wall
    parts = []
    for xa, xs in ((a0, 1), (a1, -1)):
        for yb, ys in ((b0, 1), (b1, -1)):
            parts.append(box(*sorted((xa, xa + xs * leg)), *sorted((yb, yb + ys * wall)), z0, z1))
            parts.append(box(*sorted((xa, xa + xs * wall)), *sorted((yb, yb + ys * leg)), z0, z1))
    out = parts[0]
    for p in parts[1:]:
        out += p
    return out


def print_pose(part, rot_x: float):
    """The part as it sits on the bed: rotated about X by rot_x, then dropped to z = 0. Returns (part, bed_z)."""
    p = part.rotate(Axis.X, rot_x) if rot_x else part
    if rot_x:
        p = p.moved(Location((0, 0, -p.bounding_box().min.Z)))
    return p, p.bounding_box().min.Z


def unit(v) -> Vector:
    return Vector(*v).normalized()
