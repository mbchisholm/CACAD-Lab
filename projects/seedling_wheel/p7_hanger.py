"""P7 light hanger: a ladder under the ridge that carries the three T5 bars, one at each end of the light.

The bars rest on the lower beam between locating ribs (FIT_CLEAR each side) with a gap above, and are strapped
to it (hook-and-loop): the interface needs only the bar's width, not its clips, which are unpublished. One M5 up
into the ridge's bottom slot, its head seated in the top beam. Printed flat; the M5 bore and seat lie
horizontal, so both are teardrops pointing up.
Local frame: x = assembly Y, y = assembly Z - z_ridge (<= 0), z = 0 .. t along assembly X.

    .venv/bin/python projects/seedling_wheel/p7_hanger.py     # -> out/p7_hanger.step, .stl
"""
from __future__ import annotations

import math

from build123d import Align, BuildPart, BuildSketch, Box, Circle, Locations, Mode, Part, Plane, Polygon, Rectangle, \
    extrude, Pos

from cacad import assert_bbox, assert_material, single_solid
from projects.seedling_wheel.params import derive


def _rect(x0, x1, y0, y1):
    with Locations(((x0 + x1) / 2, (y0 + y1) / 2)):
        Rectangle(x1 - x0, y1 - y0)


def _teardrop_bore(r: float, y0: float, y1: float, zc: float) -> Part:
    """A bore along local y with a teardrop section in the (x, z) plane, tip toward +z."""
    k = r / math.sqrt(2)
    with BuildSketch(Plane.XZ.offset(-y0)) as sk:
        with Locations((0, zc)):
            Circle(r)
            Polygon((-k, k), (0, r * math.sqrt(2)), (k, k), (0, 0), align=None)
    return extrude(sk.sketch, amount=y1 - y0, dir=(0, 1, 0))


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p7"]
    h, vl, lo, tb = p["half"], p["v_l"], p["lower"], p["top"]
    with BuildPart() as bp:
        with BuildSketch():
            _rect(-h, h, -tb, 0)                                   # top beam under the ridge
            _rect(-h, h, vl - lo, vl)                               # lower beam the bars rest on
            for s in (-1, 1):
                _rect(*sorted((s * p["inner"], s * h)), vl - lo, -tb)   # side drops, inner faces locate the outer bars
            for x0, x1 in p["ribs"]:
                _rect(x0, x1, vl, vl + p["rib"][1])
        extrude(amount=p["t"])
    part = bp.part
    zc = p["t"] / 2
    part = part - _teardrop_bore(d["bore5"] / 2, -tb - 0.01, 0.01, zc)
    part = part - _teardrop_bore(d["cb_d5"] / 2, -tb - 0.01, -tb + d["cb_depth5"], zc)
    return part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p7"]
    assert part.is_valid, f"{size}: P7 invalid"
    single_solid(part)
    assert_bbox(part, (2 * p["half"], p["lower"] - p["v_l"], p["t"]), 0.0, d["bbox_tol"], "P7")
    zc = p["t"] / 2
    sec = d["light"]["section"]
    probes = {"M5 bore is air": ((0, -1.0, zc), False),
              "M5 seat is air": ((d["bore5"] / 2 + 1.0, -p["top"] + 1.0, zc), False),
              "under the head": ((d["bore5"] / 2 + 1.0, -1.0, zc), True),
              "lower beam": ((0, p["v_l"] - p["lower"] / 2, zc), True)}
    for i, b in enumerate(p["bars"]):
        probes[f"bar {i} seat is air"] = ((b, p["v_l"] + sec / 2, zc), False)
    assert_material(part, probes)


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p7_hanger", OUT)
    print(f"P7: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
