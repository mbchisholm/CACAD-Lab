"""P10 leg shoe: ties each leg's foot to the foot crossbar, on their common outboard face.

The leg is cut square to the floor and stands on the crossbar's top; P10 is a flat plate across the joint with two
M5 into the crossbar's outboard slot and two into the leg's. Flat on the frame face, symmetric through its
thickness: the same part serves all four feet, turned over for the other hand.
Local frame: x = |assembly Y| - foot_y, y = assembly Z, z = 0 .. t outboard.

    .venv/bin/python projects/seedling_wheel/p10_shoe.py     # -> out/p10_shoe.step, .stl
"""
from __future__ import annotations

from build123d import BuildPart, BuildSketch, Cylinder, Locations, Mode, Part, Polygon, extrude

from cacad import ALIGN_MIN_Z, assert_material, single_solid, try_chamfer
from cacad.selectors import planar_faces_with_normal
from projects.seedling_wheel.params import derive


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p10"]
    with BuildPart() as bp:
        with BuildSketch():
            Polygon(*p["poly"], align=None)
        extrude(amount=p["t"])
        for xy in p["screws"]:
            with Locations((*xy, 0)):
                Cylinder(d["bore5"] / 2, p["t"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    part = bp.part
    top = planar_faces_with_normal(part, (0, 0, 1), p["t"])[0]
    return try_chamfer(part, top.outer_wire().edges(), 1.0, (0.6,), "P10 face rim")


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p10"]
    assert part.is_valid, f"{size}: P10 invalid"
    single_solid(part)
    assert abs(part.bounding_box().size.Z - p["t"]) < 0.05
    probes = {f"M5 {i} is air": ((*xy, p["t"] / 2), False) for i, xy in enumerate(p["screws"])}
    x, y = p["screws"][2]
    probes["plate round the leg screw"] = ((x + d["bore5"] / 2 + 2.0, y, p["t"] / 2), True)
    assert_material(part, probes)


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p10_shoe", OUT)
    print(f"P10: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
