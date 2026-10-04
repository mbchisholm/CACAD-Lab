"""Declared print orientation with bed-face verification."""
from __future__ import annotations

from build123d import Axis, Location, Vector

from cacad.selectors import planar_faces_with_normal


def check_declared_orientation(part, orientation: dict) -> None:
    """orientation: up (unit vector in the part frame), bed_z (world z of the
    bed face in the part frame), bed_face (name, for the message),
    known_overhangs (list; may be empty but must exist so 'none declared' is a
    statement, not an omission). Verifies a planar face with normal -up
    exists at bed_z."""
    up = Vector(orientation["up"])
    assert abs(up.length - 1) < 1e-9, "up must be a unit vector"
    assert isinstance(orientation.get("known_overhangs"), list), "known_overhangs must be declared (a list)"
    bed = planar_faces_with_normal(part, -up, orientation["bed_z"])
    assert bed, f"declared bed face '{orientation.get('bed_face', '?')}' not found at z={orientation['bed_z']}"


def to_print_orientation(part, orientation: dict):
    """Return the part rotated/translated so the bed face lies on z=0 and `up`
    is +Z. Only +Z / -Z declarations are supported; anything else is a design
    choice this helper refuses to guess."""
    up = tuple(orientation["up"])
    if up == (0, 0, 1):
        return part.moved(Location((0, 0, -orientation["bed_z"])))
    if up == (0, 0, -1):
        return part.rotate(Axis.X, 180).moved(Location((0, 0, orientation["bed_z"])))
    raise ValueError(f"unsupported print orientation {up}")
