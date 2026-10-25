"""Front panel: slides down the jamb slots onto the sill, the entry hole, and the larger perch below it (a 10 mm
rod on a root cone). Prints on its inner face: the perch and the hole are vertical, nothing overhangs.

    .venv/bin/python projects/birdhouse/front.py
"""
from __future__ import annotations

from build123d import Part

from projects.birdhouse.geom import box, cone_y, cyl_y
from projects.birdhouse.params import derive


def build_front(size: str = "V0") -> Part:
    d = derive(size)
    px, (py0, py1), (z0, z1) = d["panel_x"], d["panel_y"], d["panel_z"]
    part = box(-px, px, py0, py1, z0, z1)
    part -= cyl_y(0.0, d["hole_z"], d["hole_d"] / 2, py0 - 1, py1 + 1)
    cd, cl = d["perch_collar"]
    zp, r = d["perch_z"], d["perch_d"] / 2
    part += cone_y(0.0, zp, r, cd / 2, py0 - cl, py0 + 0.01)   # root cone, wide at the panel
    part += cyl_y(0.0, zp, r, py0 - d["perch_len"], py0 + 0.01)
    return part


def check_front(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "front must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - 2 * d["panel_x"]) < 1e-3
    assert abs(bb.min.Y - (d["panel_y"][0] - d["perch_len"])) < 1e-3 and abs(bb.max.Z - d["body_h"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_front()
    check_front(p)
    print("front", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "front", __file__.rsplit("/", 1)[0] + "/out")
