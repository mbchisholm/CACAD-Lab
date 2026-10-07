"""Small geometry helpers in the ASM frame (params.py): boxes by extents,
rectangles across the optical axis (Y), lofts and cylinders along it."""
from __future__ import annotations

from build123d import Box, Circle, Cylinder, Part, Plane, Polygon, Pos, Rectangle, Rot, extrude, loft


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def rect_y(y, cx, cz, w, h):
    """A w (X) x h (Z) rectangle in the plane Y = y, centred on (cx, cz)."""
    return Plane(origin=(cx, y, cz), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * Rectangle(w, h)


def prism_y(y0, y1, cx, cz, w, h) -> Part:
    return box(cx - w / 2, cx + w / 2, y0, y1, cz - h / 2, cz + h / 2)


def loft_y(y0, r0, y1, r1) -> Part:
    """Loft between two (cx, cz, w, h) rectangles at Y = y0 and Y = y1."""
    return loft([rect_y(y0, *r0), rect_y(y1, *r1)])


def cyl_y(d, cx, cz, y0, y1) -> Part:
    return Pos(cx, (y0 + y1) / 2, cz) * Rot(90, 0, 0) * Cylinder(d / 2, y1 - y0)


def teardrop_y(d, cx, cz, y0, y1) -> Part:
    """A hole along Y that prints with +Z up: the circle plus a 45 deg roof to an apex at r*sqrt(2). The plane's
    y_dir is -Z (rect_y), so the roof points to -v in sketch coordinates."""
    r = d / 2
    k = r / 2 ** 0.5
    prof = Circle(r) + Polygon((-k, -k), (0, -r * 2 ** 0.5), (k, -k), (0, 0), align=None)
    return extrude(Plane(origin=(cx, y0, cz), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * prof, amount=y1 - y0)
