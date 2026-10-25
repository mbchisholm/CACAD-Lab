"""P5 tower head: the round hub disc where each tower's three spokes meet, and the gearmotor's mount.

The two legs and the mast end short of the axis; P5 bolts to their inboard faces with two M5 each and ties the A
together. The gearbox face bolts to P5's spoke face, its pilot in P5's bore, and the gearmotor passes between the
spoke ends into the P8 nacelle. Every screw head sits below the inboard face, 2 mm from the turning Pololu hub.
Printed on its spoke face, bores vertical. Local frame: z = 0 the spoke face, +y up (assembly +Z), origin on the axis.

    .venv/bin/python projects/seedling_wheel/p5_head.py     # -> out/p5_head.step, .stl
"""
from __future__ import annotations

from build123d import BuildPart, Cylinder, Locations, Mode, Part

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid, try_chamfer
from projects.seedling_wheel.params import derive


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p5"]
    t = p["t"]
    with BuildPart() as bp:
        Cylinder(p["d"] / 2, t, align=ALIGN_MIN_Z)
        Cylinder(p["bore"] / 2, t, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        for xy in p["screws5"]:
            with Locations((*xy, 0)):
                Cylinder(d["bore5"] / 2, t, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
            with Locations((*xy, t - d["cb_depth5"])):
                Cylinder(d["cb_d5"] / 2, d["cb_depth5"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        for xy in p["holes3"]:
            with Locations((*xy, 0)):
                Cylinder(p["bore3"] / 2, t, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
            with Locations((*xy, t - p["cb_depth3"])):
                Cylinder(p["cb_d3"] / 2, p["cb_depth3"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    part = bp.part
    # finish: a cosmetic chamfer round the inboard face's rim, the edge you see
    from cacad.selectors import circular_edges
    part = try_chamfer(part, circular_edges(part, p["d"] / 2, t), 2.0, (1.2, 0.6), "P5 rim")
    return part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p5"]
    assert part.is_valid, f"{size}: P5 invalid"
    single_solid(part)
    assert_bbox(part, (p["d"], p["d"], p["t"]), 0.0, d["bbox_tol"], "P5")
    x5, y5 = p["screws5"][0]
    x3, y3 = p["holes3"][0]
    assert_material(part, {
        "pilot bore is air": ((p["bore"] / 2 - 1.0, 0, 1.0), False),
        "M5 bore on the mast is air": ((x5, y5, 1.0), False),
        "under the M5 head": ((x5 + d["bore5"] / 2 + 1.0, y5, 1.0), True),
        "M5 counterbore is air": ((x5 + d["bore5"] / 2 + 1.0, y5, p["t"] - 0.5), False),
        "M3 counterbore is air": ((x3, y3 + p["bore3"] / 2 + 0.6, p["t"] - 0.5), False),
        "disc between spokes": ((0.0, -60.0, p["t"] / 2), True),
    })


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p5_head", OUT)
    print(f"P5: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
