"""P8 nacelle: the cone over each tower's gearmotor, the shape you see at the ends of the wheel.

A closed cone shell from the spokes' outboard faces over the gearmotor. Three ears at the rim, one on each spoke,
take an M5 into the spoke's outboard slot with the head outside, where a key reaches it. A notch at the rim between
the legs lets the motor cable out and down a leg. Printed on its end cap: the wall leans out 18 deg as it rises, the
ears stand on 45 deg gussets. The ear head seats are pocketed from below (small bridged circles, declared).
Local frame: z = 0 the end cap, z = L the rim, +y up (assembly +Z), origin on the axis.

    .venv/bin/python projects/seedling_wheel/p8_nacelle.py     # -> out/p8_nacelle.step, .stl
"""
from __future__ import annotations

import math

from build123d import Axis, BuildPart, BuildSketch, Cone, Cylinder, Locations, Mode, Part, Plane, Polygon, Box, \
    extrude, Pos, Rot

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid
from projects.seedling_wheel.params import derive


def _cone(r0: float, r1: float, z0: float, z1: float) -> Part:
    return Pos(0, 0, (z0 + z1) / 2) * Cone(r0, r1, z1 - z0)


def _r_at(p: dict, z: float) -> float:
    """Outer radius of the shell at height z (end cap z = 0, rim z = L)."""
    return p["r_end"] + (p["r_rim"] - p["r_end"]) * z / p["L"]


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p8"]
    L, w = p["L"], p["wall"]
    er, eo, ew, et = p["ear"]
    shell = _cone(p["r_end"], p["r_rim"], 0, L)
    # cavity: the wall measured square to the axis is w; the slant adds < 2 %
    cavity = _cone(p["r_end"] - w + (p["r_rim"] - p["r_end"]) * w / L, p["r_rim"] - w, w, L + 0.01)
    part = shell
    for u, v in d["p5"]["spokes"].values():
        ang = math.degrees(math.atan2(v, u))
        # ear profile in the (radial, z) plane: plate at the rim on a 45 deg gusset down to the shell
        r_in = er - 25.0                       # deep enough that the gusset's foot is buried in the wall
        assert _r_at(p, L - et - (eo - r_in)) > r_in + w, "P8 gusset foot outside the wall"
        prof = [(r_in, L), (eo, L), (eo, L - et), (r_in, L - et - (eo - r_in))]
        ear = extrude(Plane.XZ * Polygon(*prof, align=None), amount=ew / 2, both=True)
        part = part + Rot(0, 0, ang) * ear
    part = part - cavity
    for u, v in d["p5"]["spokes"].values():
        x, y = u * er, v * er
        part = part - Pos(x, y, 0) * Cylinder(d["bore5"] / 2, L + 1, align=ALIGN_MIN_Z)
        part = part - Pos(x, y, 0) * Cylinder(p["seat_d"] / 2, L - et, align=ALIGN_MIN_Z)
    nw, nh = p["notch"]
    part = part - Pos(0, -p["r_rim"], L - nh / 2) * Box(nw, 2 * p["wall"] + 10, nh + 0.01)
    return part.solids()[0] if len(part.solids()) == 1 else part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p8"]
    L, w = p["L"], p["wall"]
    er, eo, ew, et = p["ear"]
    assert part.is_valid, f"{size}: P8 invalid"
    single_solid(part)
    bb = part.bounding_box()
    assert abs(bb.size.Z - L) < 0.05 and abs(bb.max.Y - eo) < 0.5, f"P8 bbox {bb.size}"
    mid = L / 2
    assert_material(part, {
        "end cap": ((0, 0, w / 2), True),
        "hollow for the gearmotor": ((0, 0, mid), False),
        "wall at mid height": ((0, _r_at(p, mid) - w / 2, mid), True),
        "mast ear around its M5": ((0, er + d["bore5"] / 2 + 1.0, L - et / 2), True),
        "mast ear M5 is air": ((0, er, L - et / 2), False),
        "seat under the ear is air": ((0, er + d["bore5"] / 2 + 1.0, L - et - 1.0), False),
        "cable notch is air": ((0, -p["r_rim"] + w / 2, L - 1.0), False),
    })
    hd = d["motor_half_diag"]
    assert _r_at(p, L - w) - w > hd and p["r_end"] - w > hd, "P8 crowds the gearmotor"


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p8_nacelle", OUT)
    print(f"P8: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
