"""P4 tray corner guide: one per gondola corner, it locates the 1020 flat by its rim with tray_clear all round.

The tray drops in loose and lifts straight out; nothing presses on it. A pad sits on the end crossbar's top with one
M5 into its slot; an end fence and a side fence rise to the rim. Printed on the pad, walls vertical, no overhang.
Print two of this hand and two mirrored (the slicer's mirror; the part is symmetric otherwise).
Local frame: origin at the crossbar's outer top corner, x' inboard is negative, y' inward is negative, z' up.

    .venv/bin/python projects/seedling_wheel/p4_corner.py     # -> out/p4_corner.step, .stl
"""
from __future__ import annotations

from build123d import Axis, BuildPart, Box, Cylinder, Locations, Mode, Part, Align

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid, try_chamfer
from projects.seedling_wheel.params import derive

_MAX = (Align.MAX, Align.MAX, Align.MIN)


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p4"]
    px, py, pt = p["pad"]
    w, h = p["wall"], p["h"]
    with BuildPart() as bp:
        with Locations((px, 0, 0)):
            Box(px + w, py, pt, align=_MAX)                       # pad over the crossbar and under the end fence
        Box(w, p["end_y"], h, align=_MAX)                         # end fence, x' in [-w, 0]
        Box(p["side_x"], w, h, align=_MAX)                        # side fence, y' in [-w, 0]
        with Locations((p["screw"][0], p["screw"][1], 0)):
            Cylinder(d["bore5"] / 2, pt, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    part = bp.part
    # finish: soften the fences' tops and the outer corner (cosmetic: fallback sizes)
    top = part.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[-1]
    part = try_chamfer(part, top, 1.0, (0.6,), "P4 fence tops")
    return part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p4"]
    px, py, pt = p["pad"]
    assert part.is_valid, f"{size}: P4 invalid"
    single_solid(part)
    assert_bbox(part, (px + p["side_x"], max(py, p["end_y"]), p["h"]), 0.0, d["bbox_tol"], "P4")
    w = p["wall"]
    assert_material(part, {
        "pad over the crossbar": ((px / 2, -30.0, pt / 2), True),
        "M5 bore is air": ((p["screw"][0], p["screw"][1], pt / 2), False),
        "end fence up to the rim": ((-w / 2, -10.0, p["h"] - 2.0), True),
        "side fence up to the rim": ((-p["side_x"] + 2.0, -w / 2, p["h"] - 2.0), True),
        "tray side of the fences is air": ((-w - 2.0, -w - 2.0, p["h"] / 2), False),
    })


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p4_corner", OUT)
    print(f"P4: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
