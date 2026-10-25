"""P3 hanger: the gondola's pivot. Bolted to the top of each gondola post, it turns on the shoulder screw.

Printed flat on its post face, bores vertical. The ISO 7379 shoulder turns in P3's printed bore (FIT_CLEAR radial,
greased) between two ISO 7089 washers: a plain bearing, at a few degrees per second it needs no ball bearing. Two M5,
counterbored below the face P2 sweeps over, hold it on the post's slot.
Local frame: z = 0 the post face, z = t the arm side, origin on the pivot, +Y up the post (assembly +Z).

    .venv/bin/python projects/seedling_wheel/p3_hanger.py     # -> out/p3_hanger.step, .stl
"""
from __future__ import annotations

from build123d import BuildPart, BuildSketch, Circle, Cylinder, Locations, Mode, Part, Rectangle, extrude, Align

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid
from projects.seedling_wheel.params import derive


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p3"]
    with BuildPart() as bp:
        with BuildSketch():
            Circle(p["w"] / 2)
            with Locations((0, p["bot"])):
                Rectangle(p["w"], -p["bot"], align=(Align.CENTER, Align.MIN))
        extrude(amount=p["t"])
        Cylinder(d["p3_bore"] / 2, p["t"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        for y in p["screws"]:
            with Locations((0, y, 0)):
                Cylinder(d["bore5"] / 2, p["t"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
            with Locations((0, y, p["t"] - d["cb_depth5"])):
                Cylinder(d["cb_d5"] / 2, d["cb_depth5"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    return bp.part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p3"]
    assert part.is_valid, f"{size}: P3 invalid"
    single_solid(part)
    assert_bbox(part, (p["w"], p["top"] - p["bot"], p["t"]), 0.0, d["bbox_tol"], "P3")
    gap = d["c"]["post_top_gap"]
    assert_material(part, {
        "pivot bore is air": ((0, 0, p["t"] / 2), False),
        "wall around the bore": ((0, d["p3_bore"] / 2 + 2.0, p["t"] / 2), True),
        "M5 counterbore is air": ((d["bore5"] / 2 + 1.0, p["screws"][0], p["t"] - 0.5), False),
        "under the M5 head": ((d["bore5"] / 2 + 1.0, p["screws"][0], 1.0), True),
        "solid across the post top": ((0, -gap - 2.0, p["t"] / 2), True),
    })


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p3_hanger", OUT)
    print(f"P3: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
