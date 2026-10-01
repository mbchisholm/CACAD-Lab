"""Collet: rigid seat for the TPU insert. Slotted ring with a stepped bore.

Local Z=0 is the collet's bottom face (sits on the body's seat floor).
Bottom to top: base ring (in the body seat, bore = body bore) -> straight
fingers (bore = insert OD + clearance; the step between the two bores is the
ledge the insert sits on) -> short 15 deg taper the nut cone rides on.
Slots run from the top down to the base ring.
Run:  python collet.py [M16] [--show]
"""
from __future__ import annotations

import math
import sys

from build123d import Axis, Box, Cone, Cylinder, Location, Part, Vector

import params
from cacad import (
    ALIGN_MIN_Z, assert_bbox, assert_material, circular_edges, cylindrical_faces, maybe_show,
    planar_faces_with_normal, single_solid, try_chamfer,
)
from common import assert_walls, export


def build_collet(size: str) -> Part:
    d = params.derive(size)
    r_base = d["collet_base_od"] / 2
    r_tip = d["collet_tip_od"] / 2
    z_taper = d["seat_depth"] + d["collet_cyl_len"]

    straight = Cylinder(r_base, z_taper, align=ALIGN_MIN_Z)
    taper = Cone(r_base, r_tip, d["collet_taper_len"], align=ALIGN_MIN_Z).moved(Location((0, 0, z_taper)))
    collet = straight + taper

    # stepped bore: body bore through the base ring, insert bore above it
    through = Cylinder(d["bore_d"] / 2, d["collet_h"] + 2, align=ALIGN_MIN_Z).moved(Location((0, 0, -1)))
    finger_bore = Cylinder(d["collet_finger_bore_d"] / 2, d["collet_h"], align=ALIGN_MIN_Z).moved(
        Location((0, 0, d["collet_base_ring_h"]))
    )
    collet = collet - through - finger_bore

    # slots: radial, through the wall, from the top down to the base ring
    slot_len = d["collet_h"] - d["collet_base_ring_h"] + 1  # +1 overshoots the top
    slot = Box(r_base + 1, d["slot_width"], slot_len).moved(
        Location(((r_base + 1) / 2, 0, d["collet_base_ring_h"] + slot_len / 2))
    )
    for i in range(d["slot_count"]):
        collet = collet - slot.rotate(Axis.Z, 360 * i / d["slot_count"])

    # chamfers last, individually, with fallback
    fb = d["chamfer_fallbacks"]
    collet = try_chamfer(collet, circular_edges(collet, d["collet_finger_bore_d"] / 2, d["collet_h"]),
                         d["chamfer_edge"] / 2, fb[1:], "insert bore lead-in (top)")
    collet = try_chamfer(collet, circular_edges(collet, d["bore_d"] / 2, 0.0),
                         d["chamfer_edge"], fb, "cable bore lead-in (bottom)")
    collet = try_chamfer(collet, circular_edges(collet, r_tip, d["collet_h"]),
                         d["chamfer_edge"] / 2, fb[1:], "tip outer edge")
    collet.label = f"collet_{size}"
    return collet


def check_collet(collet: Part, size: str) -> None:
    d = params.derive(size)
    tol = d["bbox_tol"]
    assert collet.is_valid, "collet is not a valid shape"
    single_solid(collet)
    assert_walls(d)
    assert d["collet_bore_d"] >= d["cable_od_min"], "collet bore smaller than min cable OD"
    assert d["bore_d"] > d["cable_od_max"], "base ring bore does not admit max cable"

    assert_bbox(collet, (d["collet_base_od"], d["collet_base_od"], d["collet_h"]), 0.0, tol, "collet")
    assert cylindrical_faces(collet, d["collet_finger_bore_d"] / 2), "insert bore face missing"
    assert cylindrical_faces(collet, d["bore_d"] / 2), "cable bore face missing"
    assert cylindrical_faces(collet, d["collet_base_od"] / 2), "base OD face missing"
    assert planar_faces_with_normal(collet, Vector(0, 0, -1), 0.0), "seating face missing"
    # the insert ledge and the slot floors are coplanar and merge into one face
    assert planar_faces_with_normal(collet, Vector(0, 0, 1), d["collet_base_ring_h"]), "insert ledge missing"
    assert planar_faces_with_normal(collet, Vector(0, 1, 0)), "no slot walls found"

    z_mid_taper = d["seat_depth"] + d["collet_cyl_len"] + d["collet_taper_len"] / 2
    r_mid_taper = (d["collet_base_od"] / 2 + d["collet_tip_od"] / 2) / 2
    r_wall_mid = (r_mid_taper + d["collet_finger_bore_d"] / 2) / 2
    slot_angle = math.radians(180 / d["slot_count"])  # halfway between slots 0 and 1
    between = lambda r, z: (r * math.cos(slot_angle), r * math.sin(slot_angle), z)
    r_ledge = (d["bore_d"] + d["collet_finger_bore_d"]) / 4
    assert_material(collet, {
        "cable bore is empty": ((0, 0, d["collet_h"] / 2), False),
        "base ring wall is solid (on slot azimuth)": (((d["collet_base_od"] + d["bore_d"]) / 4, 0, d["collet_base_ring_h"] / 2), True),
        "slot is empty above base ring": (((d["collet_base_od"] + d["collet_finger_bore_d"]) / 4, 0, d["collet_base_ring_h"] + 0.5), False),
        "ledge is solid below the step": (between(r_ledge, d["collet_base_ring_h"] - 0.3), True),
        "ledge is clear above the step": (between(r_ledge, d["collet_base_ring_h"] + 0.3), False),
        "finger is solid between slots": (between(r_wall_mid, z_mid_taper), True),
        "outside taper is empty": ((r_mid_taper + 0.2, 0.0, z_mid_taper), False),
    })


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    collet = build_collet(size)
    check_collet(collet, size)
    step, stl = export(collet, f"collet_{size}")
    print(f"collet {size}: OK -> {step.name}, {stl.name}")
    maybe_show(collet, names=[collet.label])
