"""Gland body: panel thread + gasket flange (recess + compression-stop foot)
+ hex + neck thread + collet seat.

Z=0 is the panel face = the foot face. The gasket recess is above it. Panel
thread runs to -Z, neck/nut to +Z. The part is a Compound: one finished core
solid plus two unfused thread solids (see params.COMMON["thread_interference"]).

Printed neck-down (params.PRINT_ORIENTATION): the flange is a frustum at
self_support_deg and the hex gets a 45 deg chamfer on its neck side, so the
only ceiling is the collet-seat floor.
Run:  python body.py [M16] [--show]
"""
from __future__ import annotations

import math
import sys

from build123d import Compound, Cone, Cylinder, GeomType, Location, Part, RegularPolygon, Vector, extrude

import params
from cacad import (
    ALIGN_MIN_Z, assert_bbox, assert_material, assert_thread_present, circular_edges,
    cylindrical_faces, expect_solids, line_edges_at_z, maybe_show, planar_faces_with_normal,
    solid_thread, try_chamfer, with_threads,
)
from common import assert_walls, export

BODY_SOLIDS = 3   # core + panel thread + neck thread


def build_body_core(size: str) -> Part:
    """Everything except the thread solids."""
    return _core(size, with_flange=True)


def _core(size: str, with_flange: bool) -> Part:
    """with_flange=False (coupon): the gasket recess and foot are left out and the
    flange is a plain collar of the frustum's top diameter. Every z level is
    the same as the production part."""
    d = params.derive(size)

    panel_core = Cylinder(d["panel_core_r"], d["panel_thread_len"] + d["flange_h"], align=ALIGN_MIN_Z).moved(
        Location((0, 0, -d["panel_thread_len"]))
    )
    if with_flange:
        # frustum: foot OD on the panel, inside the hex flats at the top -> self-supporting neck-down
        flange = Cone(d["foot_od"] / 2, d["flange_top_d"] / 2, d["flange_h"], align=ALIGN_MIN_Z)
    else:
        flange = Cylinder(d["flange_top_d"] / 2, d["flange_h"], align=ALIGN_MIN_Z)
    hex_prism = extrude(RegularPolygon(d["hex_ac"] / 2, 6), d["hex_h"]).moved(Location((0, 0, d["flange_h"])))
    neck_core = Cylinder(d["neck_core_r"], d["neck_len"], align=ALIGN_MIN_Z).moved(Location((0, 0, d["hex_top_z"])))
    core = panel_core + flange + hex_prism + neck_core

    through = Cylinder(d["bore_d"] / 2, d["body_len"] + 2, align=ALIGN_MIN_Z).moved(
        Location((0, 0, -d["panel_thread_len"] - 1))
    )
    seat = Cylinder(d["seat_d"] / 2, d["seat_depth"] + 1, align=ALIGN_MIN_Z).moved(Location((0, 0, d["seat_floor_z"])))
    core = core - through - seat
    if with_flange:
        # gasket recess: annulus from the thread OD out to recess_od, standoff deep; what is
        # left outside it on z=0 is the compression-stop foot ring
        recess = (Cylinder(d["recess_od"] / 2, d["standoff"] + 1, align=ALIGN_MIN_Z)
                  - Cylinder(d["recess_id"] / 2, d["standoff"] + 1, align=ALIGN_MIN_Z)).moved(Location((0, 0, -1)))
        core = core - recess

    # neck side of the hex: keep a flat stop ring out to hex_stop_r (the nut's hard
    # stop), cut everything outside a self_support_deg cone from there
    r0, h = d["hex_stop_r"], d["hex_cone_h"]
    keep = Cone(r0 + h * math.tan(math.radians(d["self_support_deg"])), r0, h, align=ALIGN_MIN_Z)
    cutter = (Cylinder(d["hex_ac"] / 2 + 1, h, align=ALIGN_MIN_Z) - keep).moved(Location((0, 0, d["hex_top_z"] - h)))
    core = core - cutter
    # cosmetic chamfers, individually, with fallback
    fb = d["chamfer_fallbacks"]
    core = try_chamfer(core, circular_edges(core, d["bore_d"] / 2, -d["panel_thread_len"]),
                       d["chamfer_edge"], fb, "bore lead-in (panel end)")
    core = try_chamfer(core, circular_edges(core, d["seat_d"] / 2, d["neck_top_z"]),
                       d["chamfer_edge"], fb, "seat lead-in")
    return core


def body_threads(size: str) -> list:
    d = params.derive(size)
    p = d["pitch"]
    panel_thread = solid_thread(
        d["thread_major"], p, d["panel_thread_len"], external=True,
        end_finishes=d["panel_thread_finish"], interference=d["thread_interference"],
    ).moved(Location((0, 0, -d["panel_thread_len"])))
    neck_thread = solid_thread(
        d["neck_major"], p, d["neck_len"], external=True,
        end_finishes=d["neck_thread_finish"], interference=d["thread_interference"],
    ).moved(Location((0, 0, d["hex_top_z"])))
    return [panel_thread, neck_thread]


def build_body(size: str) -> Compound:
    return with_threads(build_body_core(size), body_threads(size), f"body_{size}")


def check_body(body: Compound, size: str) -> None:
    d = params.derive(size)
    tol = d["bbox_tol"]
    assert body.is_valid, "body is not a valid shape"
    expect_solids(body, BODY_SOLIDS, "body")
    assert_walls(d)

    # bounding box: foot ring is the widest feature, panel-thread tip to neck top set Z
    assert_bbox(body, (max(d["hex_ac"], d["foot_od"]), max(d["hex_af"], d["foot_od"]), d["body_len"]),
                -d["panel_thread_len"], tol, "body")

    assert cylindrical_faces(body, d["seat_d"] / 2), "seat bore face missing"
    assert cylindrical_faces(body, d["bore_d"] / 2), "through bore face missing"
    assert cylindrical_faces(body, d["recess_od"] / 2), "gasket recess wall missing"
    assert planar_faces_with_normal(body, Vector(0, 0, 1), d["seat_floor_z"]), "seat floor missing"
    assert planar_faces_with_normal(body, Vector(0, 0, -1), 0.0), "foot (panel contact) face missing"
    assert planar_faces_with_normal(body, Vector(0, 0, -1), d["standoff"]), "gasket recess floor (sealing face) missing"
    # the flange is a self-supporting frustum, the hex neck side is chamfered to it
    cones = body.faces().filter_by(GeomType.CONE)
    assert any(abs(abs(f.normal_at(0.5, 0.5).Z) - math.sin(math.radians(d["flange_cone_deg"]))) < 0.02 for f in cones), \
        "flange frustum missing"
    r_foot_mid = (d["recess_od"] + d["foot_od"]) / 4
    r_recess_mid = (d["recess_id"] + d["recess_od"]) / 4

    r_wall = (d["panel_core_r"] + d["bore_d"] / 2) / 2
    r_seat_wall = (d["neck_core_r"] + d["seat_d"] / 2) / 2
    zs = -d["panel_thread_len"] / 2
    assert_material(body, {
        "bore is empty (panel end)": ((0, 0, zs), False),
        "bore is empty (hex)": ((0, 0, d["hex_top_z"] - 1), False),
        "panel core wall is solid": ((r_wall, 0, zs), True),
        "seat is empty": ((d["seat_d"] / 2 - 0.05, 0, d["neck_top_z"] - 0.5), False),
        "seat wall is solid": ((r_seat_wall, 0, d["neck_top_z"] - 0.5), True),
        "seat floor is solid": ((d["seat_d"] / 2 - 0.05, 0, d["seat_floor_z"] - 0.5), True),
        "hex flat is solid": ((0, d["hex_af"] / 2 - 0.1, d["shoulder_h"] + d["hex_h"] / 2), True),
        "outside hex flat is empty": ((0, d["hex_af"] / 2 + 0.1, d["shoulder_h"] + d["hex_h"] / 2), False),
        "foot ring is solid down to the panel face": ((r_foot_mid, 0, 0.1), True),
        "recess is empty above the panel face": ((r_recess_mid, 0, d["standoff"] / 2), False),
        "flange web above the recess is solid": ((r_recess_mid, 0, d["standoff"] + d["flange_web"] / 2), True),
        "outside the foot is empty": ((0, d["foot_od"] / 2 + 0.1, 0.1), False),
        "hex cone removed the flat near the neck": ((0, d["hex_af"] / 2 - 0.1, d["hex_top_z"] - 0.3), False),
        "hex flat below the cone is solid": ((0, d["hex_af"] / 2 - 0.1, d["hex_top_z"] - d["hex_cone_h_at_flats"] - 0.3), True),
        "stop ring is solid under the nut's bottom face": ((d["hex_stop_r"] - 0.3, 0, d["hex_top_z"] - 0.3), True),
        "cone surface: just inside is solid": ((d["hex_stop_r"] + 0.5 - 0.15, 0, d["hex_top_z"] - 0.5), True),
        "cone surface: just outside is empty": ((d["hex_stop_r"] + 0.5 + 0.15, 0, d["hex_top_z"] - 0.5), False),
    })
    assert_thread_present(body, (d["panel_core_r"] + d["thread_major"] / 2) / 2,
                          -d["panel_thread_len"] / 2, d["pitch"], "panel thread")
    assert_thread_present(body, (d["neck_core_r"] + d["neck_major"] / 2) / 2,
                          d["hex_top_z"] + d["neck_len"] / 2, d["pitch"], "neck thread")


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    body = build_body(size)
    check_body(body, size)
    step, stl = export(body, f"body_{size}")
    print(f"body {size}: OK -> {step.name}, {stl.name}")
    maybe_show(body, names=[body.label])
