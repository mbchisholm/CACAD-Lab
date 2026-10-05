"""Small solids the nutrient-controller part files share: axis-aligned boxes
by bounds, cylinders along an axis, truncated teardrops and teardrop slots
for holes that print horizontally, hex prisms for nut pockets. No numbers:
every size comes in as an argument from params.derive."""
from __future__ import annotations

import math

from build123d import Box, Circle, Cylinder, Part, Plane, Polygon, Pos, Rectangle, RegularPolygon, Rot, extrude

AXES = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1), "-x": (-1, 0, 0), "-y": (0, -1, 0), "-z": (0, 0, -1)}


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl(d, axis, centre, length) -> Part:
    """Cylinder of diameter d along axis 'x' | 'y' | 'z', centred at `centre`."""
    rot = {"x": Rot(0, 90, 0), "y": Rot(90, 0, 0), "z": Rot(0, 0, 0)}[axis]
    return Pos(*centre) * rot * Cylinder(d / 2, length)


def _plane(axis, apex, centre) -> Plane:
    return Plane(origin=centre, x_dir=AXES[apex], z_dir=AXES[axis])


def teardrop(d, axis, centre, length, apex="x", cap=None) -> Part:
    """Hole of diameter d along `axis`, with a 45 deg roof pointing to `apex` (the print's up), cut flat at
    r + cap above the centre when cap is given (a short bridge instead of a point)."""
    r = d / 2
    pl = _plane(axis, apex, centre)
    t = r / math.sqrt(2)
    prof = Circle(r) + Polygon((t, t), (r * math.sqrt(2), 0), (t, -t), (0, 0), align=None)
    if cap is not None:
        lo, hi = -r - 1.0, r + cap                      # keep -r-1 <= u <= r + cap along the apex direction
        prof = prof & Pos((lo + hi) / 2, 0) * Rectangle(hi - lo, 2 * r + 2)
    return extrude(pl * prof, amount=length / 2, both=True)


def slot_teardrop(w, half_len, axis, centre, length, apex="x") -> Part:
    """Slot of width w elongated +/- half_len along `apex` (the print's up), pointed roof at the top end."""
    r = w / 2
    pl = _plane(axis, apex, centre)
    t = r / math.sqrt(2)
    top = Pos(half_len, 0) * (Circle(r) + Polygon((t, t), (r * math.sqrt(2), 0), (t, -t), (0, 0), align=None))
    prof = top + Pos(-half_len, 0) * Circle(r) + Rectangle(2 * half_len, w)
    return extrude(pl * prof, amount=length / 2, both=True)


def hex_prism(s, axis, centre, length, flats_normal="y", apex=None) -> Part:
    """Hex of across-flats s along `axis`; one pair of flats faces `flats_normal`. With `apex` (the print's up,
    perpendicular to flats_normal) the vertex there gets a 45 deg roof, so a horizontal nut pocket prints."""
    pl = Plane(origin=centre, x_dir=AXES[flats_normal], z_dir=AXES[axis])
    prof = RegularPolygon(s / math.sqrt(3), 6, major_radius=True, rotation=30)
    if apex is not None:
        # local y is z_dir x x_dir; the roof goes on whichever side of local y points to `apex`
        ly = tuple(a * b for a, b in zip(tuple(pl.y_dir), AXES[apex]))
        sgn = 1 if sum(ly) > 0 else -1
        r = s / math.sqrt(3)
        prof = prof + Polygon((-s / 2, sgn * r / 2), (0, sgn * (r / 2 + s / 2)), (s / 2, sgn * r / 2), (0, 0), align=None)
    return extrude(pl * prof, amount=length / 2, both=True)
