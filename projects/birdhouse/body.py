"""Body: the U-shaped shell (sides and back), two front jambs with the panel's slots, the floor ledge and front sill
on the bed, and the hanging lug on the back (M6 down through a bracket flange on top, nut under the bridge between
two gussets). Prints upright on its bottom; the lug's underside between the gussets is the one bridge.

    .venv/bin/python projects/birdhouse/body.py
"""
from __future__ import annotations

from build123d import Part, Plane, Polyline, extrude, make_face

from projects.birdhouse.geom import box, cyl, rbox
from projects.birdhouse.params import derive


def _gusset(x0: float, x1: float, y0: float, reach: float, z_top: float) -> Part:
    """45 deg triangle under the lug, from the back wall out to its reach."""
    tri = make_face(Polyline((y0, z_top), (y0 + reach, z_top), (y0, z_top - reach), close=True))
    return extrude(Plane.YZ.offset(x0) * tri, amount=x1 - x0)


def build_body(size: str = "V0") -> Part:
    d = derive(size)
    hx, hy, H, f = d["hx"], d["hy"], d["body_h"], d["fit"]
    outer = rbox(-hx, hx, -hy, hy, 0, H, d["corner_r"])
    cavity = box(-d["in_x"], d["in_x"], -hy - 1, d["in_back"], -1, H + 1)
    for s in (-1, 1):   # keep the jambs
        cavity -= box(*sorted((s * d["jamb_x"], s * (hx + 1))), -hy - 2, d["jamb_y"][1], -2, H + 2)
    part = outer - cavity
    for s in (-1, 1):   # panel slots, from the sill up and out through the top
        part -= box(*sorted((s * (d["jamb_x"] - 1), s * d["slot_x"])), *d["slot_y"], d["ledge_t"], H + 1)
    (lx0, lx1), (ly0, ly1) = d["ledge_open"]
    ring = box(-d["in_x"] - 1, d["in_x"] + 1, -hy - 1, d["in_back"] + 1, 0, d["ledge_t"]) - box(lx0, lx1, ly0, ly1, -1, d["ledge_t"] + 1)
    part += ring & outer
    (ax0, ax1), (ay0, ay1), (az0, az1) = d["lug_box"]
    part += box(ax0, ax1, ay0, ay1, az0, az1)
    reach = ay1 - ay0
    for g0, g1 in ((ax0, ax0 + d["gusset_w"]), (ax1 - d["gusset_w"], ax1)):
        part += _gusset(g0, g1, ay0, reach, az0)
    bx, by = d["lug_bolt"]
    part -= cyl(bx, by, d["bolt_bore"] / 2, az0 - 1, az1 + 1)
    return part


def check_body(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "body must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - 2 * d["hx"]) < 1e-3 and abs(bb.min.Z) < 1e-3 and abs(bb.max.Z - d["body_h"]) < 1e-3
    assert abs(bb.max.Y - d["lug_box"][1][1]) < 1e-3 and abs(bb.min.Y + d["hy"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_body()
    check_body(p)
    print("body", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "body", __file__.rsplit("/", 1)[0] + "/out")
