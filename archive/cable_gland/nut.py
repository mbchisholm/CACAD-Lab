"""Dome nut: hex + dome outside; internal thread, relief bore, cone, insert
ledge and cable exit bore inside.

Local Z=0 is the nut's bottom (open) face. Bottom to top inside:
internal thread (nut_thread_len) -> unthreaded relief (the collet's straight
fingers live here) -> flat shoulder -> 15 deg cone (preloads the collet
fingers) -> flat ledge (pushes the insert) -> cable exit bore.
The part is a Compound: finished core solid + unfused internal thread solid.
Run:  python nut.py [M16] [--show]
"""
from __future__ import annotations

import sys

from build123d import Compound, Cone, Cylinder, Location, Part, RegularPolygon, Vector, extrude

import params
from cacad import (
    ALIGN_MIN_Z, assert_bbox, assert_material, assert_thread_present, circular_edges,
    cylindrical_faces, expect_solids, line_edges_at_z, maybe_show, planar_faces_with_normal,
    solid_thread, try_chamfer, with_threads,
)
from common import assert_walls, export

NUT_SOLIDS = 2   # core + internal thread


def build_nut_core(size: str, **overrides) -> Part:
    """overrides go to params.derive (e.g. thread_clearance for the clearance ladder)."""
    d = params.derive(size, **overrides)
    z_cone = d["nut_hex_h"]
    z_ledge = z_cone + d["cone_h"]

    hex_prism = extrude(RegularPolygon(d["nut_ac"] / 2, 6), d["nut_hex_h"])
    dome = Cone(d["nut_dome_base_d"] / 2, d["nut_top_od"] / 2, d["nut_dome_h"], align=ALIGN_MIN_Z).moved(
        Location((0, 0, z_cone))
    )
    nut = hex_prism + dome

    bore = Cylinder(d["nut_bore_r"], d["nut_hex_h"] + 1, align=ALIGN_MIN_Z).moved(Location((0, 0, -1)))
    cone = Cone(d["cone_base_d"] / 2, d["cone_top_d"] / 2, d["cone_h"], align=ALIGN_MIN_Z).moved(
        Location((0, 0, z_cone))
    )
    exit_bore = Cylinder(d["bore_d"] / 2, d["nut_exit_len"] + 2, align=ALIGN_MIN_Z).moved(
        Location((0, 0, z_ledge - 1))
    )
    nut = nut - bore - cone - exit_bore

    fb = d["chamfer_fallbacks"]
    nut = try_chamfer(nut, line_edges_at_z(nut, 0.0, min_r=d["nut_af"] / 2),
                      d["chamfer_hex"], fb, "hex bottom corners")
    nut = try_chamfer(nut, line_edges_at_z(nut, d["nut_hex_h"], min_r=d["nut_af"] / 2),
                      d["chamfer_hex"], fb, "hex top corners")
    nut = try_chamfer(nut, circular_edges(nut, d["bore_d"] / 2, d["nut_h"]),
                      d["chamfer_edge"], fb, "cable exit lead-in")
    nut = try_chamfer(nut, circular_edges(nut, d["nut_top_od"] / 2, d["nut_h"]),
                      d["chamfer_edge"], fb, "top outer edge")
    return nut


def nut_threads(size: str, **overrides) -> list:
    d = params.derive(size, **overrides)
    return [solid_thread(
        d["nut_thread_major"], d["pitch"], d["nut_thread_len"], external=False,
        end_finishes=d["nut_thread_finish"], interference=d["thread_interference"],
    )]


def build_nut(size: str, label: str | None = None, **overrides) -> Compound:
    """label: text embossed 0.4 mm proud on the +Y hex flat (clearance ladder)."""
    core = build_nut_core(size, **overrides)
    if label:
        core = emboss_label(core, size, label, **overrides)
    return with_threads(core, nut_threads(size, **overrides), f"nut_{size}" + (f"_{label}" if label else ""))


def emboss_label(core: Part, size: str, label: str, **overrides) -> Part:
    """Raised text on the +Y flat: adds material, so no wall gets thinner.
    Text height ~ a quarter of the hex height; reads correctly from outside."""
    from build123d import Align, Plane, Text, extrude
    d = params.derive(size, **overrides)
    pl = Plane(origin=(0, d["nut_af"] / 2, d["nut_hex_h"] / 2), x_dir=(-1, 0, 0), z_dir=(0, 1, 0))
    txt = extrude(pl * Text(label, font_size=d["nut_hex_h"] / 4, align=(Align.CENTER, Align.CENTER)), amount=d["nozzle_d"])
    out = core + txt
    assert out.is_valid and len(out.solids()) == 1, "label emboss failed"
    return out


def check_nut(nut: Compound, size: str, **overrides) -> None:
    d = params.derive(size, **overrides)
    tol = d["bbox_tol"]
    assert nut.is_valid, "nut is not a valid shape"
    expect_solids(nut, NUT_SOLIDS, "nut")
    assert_walls(d)

    assert_bbox(nut, (d["nut_ac"], d["nut_af"], d["nut_h"]), 0.0, tol, "nut")
    assert cylindrical_faces(nut, d["bore_d"] / 2), "exit bore face missing"
    assert cylindrical_faces(nut, d["nut_bore_r"]), "thread/relief bore face missing"
    assert planar_faces_with_normal(nut, Vector(0, 0, -1), d["nut_hex_h"]), "internal shoulder missing"
    assert planar_faces_with_normal(nut, Vector(0, 0, -1), d["nut_ledge_z_local"]), "insert ledge missing"
    assert planar_faces_with_normal(nut, Vector(0, 0, -1), 0.0), "bottom face missing"

    z_cone = d["nut_hex_h"]
    z_mid_cone = z_cone + d["cone_h"] / 2
    r_cone_mid = (d["cone_base_d"] / 2 + d["cone_top_d"] / 2) / 2
    z_relief = d["nut_thread_len"] + d["nut_relief_len"] / 2
    r_ledge = (d["bore_d"] + d["cone_top_d"]) / 4
    assert_material(nut, {
        "exit bore is empty": ((0, 0, d["nut_h"] - d["nut_exit_len"] / 2), False),
        "cone is empty just inside its wall": ((r_cone_mid - 0.15, 0, z_mid_cone), False),
        "cone wall is solid just outside": ((r_cone_mid + 0.3, 0, z_mid_cone), True),
        "ledge is clear below": ((r_ledge, 0, d["nut_ledge_z_local"] - 0.2), False),
        "ledge is solid above": ((r_ledge, 0, d["nut_ledge_z_local"] + 0.2), True),
        "relief bore is empty": ((d["nut_bore_r"] - 0.05, 0, z_relief), False),
        "relief wall is solid": ((d["nut_bore_r"] + d["thread_interference"] + 0.3, 0, z_relief), True),
        "hex flat is solid": ((0, d["nut_af"] / 2 - 0.1, d["nut_hex_h"] / 2), True),
        "top wall is solid": (((d["bore_d"] + d["nut_top_od"]) / 4, 0, d["nut_h"] - 0.3), True),
    })
    r_crest = params.iso_core_radius(d["nut_thread_major"], d["pitch"])  # internal thread apex
    assert_thread_present(nut, (r_crest + d["nut_bore_r"]) / 2,
                          d["nut_thread_len"] / 2, d["pitch"], "internal thread")


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    nut = build_nut(size)
    check_nut(nut, size)
    step, stl = export(nut, f"nut_{size}")
    print(f"nut {size}: OK -> {step.name}, {stl.name}")
    maybe_show(nut, names=[nut.label])
