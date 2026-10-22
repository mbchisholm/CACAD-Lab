"""P1 rotor hub: joins the Pololu 8 mm hub on the gearbox shaft to the 2020 rotor arm.

Printed flat on its hub face, bores vertical. Torque path: Pololu hub -> four M3 (nuts captive on the arm side) -> P1
-> key in the arm's slot. Two M5 into T-nuts hold it on the arm; the key, not their friction, carries the torque.
Local frame: z = 0 the hub face, z = t the arm face, +X along the arm.

    .venv/bin/python projects/seedling_wheel/p1_hub.py     # -> out/p1_hub.step, .stl

A part file names no filesystem module (F23) and imports params by package path (F24).
"""
from __future__ import annotations

import math

from build123d import Box, BuildPart, Cylinder, Locations, Mode, Part, PolarLocations, RegularPolygon, extrude, \
    BuildSketch, Plane

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid
from projects.seedling_wheel.params import derive


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p, t = d["p1"], d["p1"]["t"]
    kw, kh = p["key"]
    with BuildPart() as bp:
        Cylinder(p["d"] / 2, t, align=ALIGN_MIN_Z)
        key_len = p["d"] / 2 - p["key_gap"]
        for sx in (-1, 1):
            with Locations((sx * (p["key_gap"] + key_len / 2), 0, t)):
                Box(key_len, kw, kh, align=ALIGN_MIN_Z)
        # trim the key ends to the disc
        Cylinder(p["d"] / 2 + 5, t + kh, align=ALIGN_MIN_Z, mode=Mode.INTERSECT)
        Cylinder(p["bore"] / 2, t + kh, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        # M5 into the arm: counterbore from the hub face, bore through the key
        for x in p["screws5"]:
            with Locations((x, 0, 0)):
                Cylinder(d["cb_d5"] / 2, d["cb_depth5"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
                Cylinder(d["bore5"] / 2, t + kh, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        # Pololu hub's M3: bores through, captive nut pockets open on the arm face (closed by the arm)
        with PolarLocations(p["hub_r"], p["n_hub"], start_angle=45):
            Cylinder(p["bore3"] / 2, t, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(t - p["nut3_depth"])):
            with PolarLocations(p["hub_r"], p["n_hub"], start_angle=45):
                RegularPolygon(p["nut3"] / 2, 6, major_radius=False)
        extrude(amount=p["nut3_depth"], mode=Mode.SUBTRACT)
    return bp.part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p1"]
    assert part.is_valid, f"{size}: P1 invalid"
    single_solid(part)
    assert_bbox(part, (p["d"], p["d"], p["t"] + p["key"][1]), 0.0, d["bbox_tol"], "P1")
    r45 = p["hub_r"] / math.sqrt(2)
    xk = p["key_gap"] + 3.0
    assert_material(part, {
        "shaft relief is air": ((0, 0, 1.0), False),
        "M5 counterbore is air": ((p["screws5"][1] + d["bore5"] / 2 + 1.0, 0, 1.0), False),
        "M5 bore through the key": ((p["screws5"][1], 0, p["t"] + 0.5), False),
        "M3 bore is air": ((r45, r45, 1.0), False),
        "M3 nut pocket is air": ((r45 + 2.2, r45, p["t"] - 0.5), False),
        "web around the hub": ((0, 15.0, p["t"] / 2), True),
        "key stands proud": ((xk, 0, p["t"] + 0.9), True),
        "key stops short of the nuts": ((p["key_gap"] - 2.0, 0, p["t"] + 0.9), False),
    })


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p1_hub", OUT)
    print(f"P1: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
