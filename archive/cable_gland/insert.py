"""Seal insert: TPU 95A sleeve, one per cable sub-range.

Local Z=0 is the bottom face (sits on the collet's base-ring ledge). The
nut's flat ledge presses the top face; the collet fingers hold the OD. Axial
squeeze bulges the bore onto the cable. IDs come from params.derive()
["insert_ids"]; each seals from its ID down to insert_coverage[i]
["seals_down_to"].
Run:  python insert.py [M16] [--show]
"""
from __future__ import annotations

import sys

from build123d import Cylinder, Location, Part, Vector

import params
from cacad import (
    ALIGN_MIN_Z, assert_bbox, assert_material, circular_edges, cylindrical_faces, maybe_show,
    planar_faces_with_normal, single_solid, try_chamfer,
)
from common import export


def insert_name(size: str, insert_id: float) -> str:
    return f"insert_{size}_ID{insert_id:.1f}"


def build_insert(size: str, insert_id: float) -> Part:
    d = params.derive(size)
    assert insert_id in d["insert_ids"], f"{insert_id} is not in the derived insert set {d['insert_ids']}"
    sleeve = Cylinder(d["insert_od"] / 2, d["insert_len"], align=ALIGN_MIN_Z)
    bore = Cylinder(insert_id / 2, d["insert_len"] + 2, align=ALIGN_MIN_Z).moved(Location((0, 0, -1)))
    ins = sleeve - bore
    fb = d["chamfer_fallbacks"]
    wall = (d["insert_od"] - insert_id) / 2
    lead = min(d["chamfer_edge"], wall / 2)
    ins = try_chamfer(ins, circular_edges(ins, insert_id / 2, d["insert_len"]), lead, fb[1:], "cable lead-in (top)")
    ins = try_chamfer(ins, circular_edges(ins, insert_id / 2, 0.0), lead, fb[1:], "cable lead-in (bottom)")
    ins.label = insert_name(size, insert_id)
    return ins


def check_insert(ins: Part, size: str, insert_id: float) -> None:
    d = params.derive(size)
    tol = d["bbox_tol"]
    assert ins.is_valid, "insert is not a valid shape"
    single_solid(ins)
    wall = (d["insert_od"] - insert_id) / 2
    assert wall >= d["min_printable_wall"], f"insert wall {wall:.2f} < 2 x nozzle"
    assert d["insert_od"] < d["collet_finger_bore_d"], "insert does not fit the collet bore"
    assert d["insert_od"] > d["bore_d"], "insert would fall through the collet ledge"
    assert_bbox(ins, (d["insert_od"], d["insert_od"], d["insert_len"]), 0.0, tol, "insert")
    assert cylindrical_faces(ins, d["insert_od"] / 2), "OD face missing"
    assert cylindrical_faces(ins, insert_id / 2), "bore face missing"
    assert planar_faces_with_normal(ins, Vector(0, 0, -1), 0.0), "bottom (ledge) face missing"
    assert planar_faces_with_normal(ins, Vector(0, 0, 1), d["insert_len"]), "top (nut ledge) face missing"
    assert_material(ins, {
        "bore is empty": ((0, 0, d["insert_len"] / 2), False),
        "wall is solid": (((d["insert_od"] + insert_id) / 4, 0, d["insert_len"] / 2), True),
    })


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    d = params.derive(size)
    for insert_id in d["insert_ids"]:
        ins = build_insert(size, insert_id)
        check_insert(ins, size, insert_id)
        step, stl = export(ins, insert_name(size, insert_id))
        print(f"{ins.label}: OK -> {step.name}, {stl.name}")
    maybe_show(ins, names=[ins.label])
