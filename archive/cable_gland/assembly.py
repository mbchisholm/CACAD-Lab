"""Place body, collet, insert and nut in the shared frame (Z=0 = gasket face).

Nominal assembled position = nut seated at first contact: the cone touches
the collet taper (slide clearance) and the nut ledge touches the insert top,
with `nut_travel` of tightening left. Tightening from there compresses the
insert axially by nut_travel and deflects the collet fingers by
nut_travel * tan(taper_deg); the hard stop is the nut's bottom face on the
hex top.
"""
from __future__ import annotations

from build123d import Axis, Compound, Location, Part

import params
from body import build_body
from collet import build_collet
from insert import build_insert
from nut import build_nut


def place_collet(collet: Part, d: dict) -> Part:
    return collet.moved(Location((0, 0, d["collet_z"])))


def place_insert(ins: Part, d: dict) -> Part:
    return ins.moved(Location((0, 0, d["insert_z"])))


def place_nut(nut: Part, d: dict, extra_travel: float = 0.0) -> Part:
    """Nut at the seated position minus `extra_travel` (tightening), with the
    thread phase that mates it onto the neck thread."""
    dz = d["nut_z"] - extra_travel - d["hex_top_z"]
    phase = (dz / d["pitch"]) * 360 + d["thread_phase_offset_deg"]
    return nut.rotate(Axis.Z, phase).moved(Location((0, 0, d["hex_top_z"] + dz)))


def assemble(size: str, parts: dict | None = None, insert_id: float | None = None) -> Compound:
    d = params.derive(size)
    insert_id = d["insert_ids"][0] if insert_id is None else insert_id
    parts = parts or dict(body=build_body(size), collet=build_collet(size), nut=build_nut(size),
                          insert=build_insert(size, insert_id))
    body = parts["body"]
    collet = place_collet(parts["collet"], d)
    ins = place_insert(parts["insert"], d)
    nut = place_nut(parts["nut"], d)
    body.label, collet.label, ins.label, nut.label = (
        f"body_{size}", f"collet_{size}", f"insert_{size}", f"nut_{size}")
    return Compound(children=[body, collet, ins, nut], label=f"gland_{size}")
