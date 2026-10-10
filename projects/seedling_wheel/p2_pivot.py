"""P2 pivot plate: on each rotor arm end, the stop face and M6 nut for the gondola's ISO 7379 shoulder screw.

Printed flat on its arm face, bores vertical. The shoulder screw's shoulder clamps on P2's gondola face; the M6 nut
sits captive in a hex pocket opening on the arm face. Two M5, counterbored below the gondola face, hold it on the arm.
Local frame: z = 0 the arm face, z = t the gondola face, origin on the pivot, +X along the arm (outward).

    .venv/bin/python projects/seedling_wheel/p2_pivot.py     # -> out/p2_pivot.step, .stl
"""
from __future__ import annotations

from build123d import BuildPart, BuildSketch, Cylinder, Locations, Mode, Part, Plane, RegularPolygon, SlotCenterToCenter, \
    extrude

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid
from projects.seedling_wheel.params import derive


def build_part(size: str = "T1020") -> Part:
    d = derive(size)
    p = d["p2"]
    with BuildPart() as bp:
        with BuildSketch():
            SlotCenterToCenter(2 * p["screw_r"], p["w"])
        extrude(amount=p["t"])
        Cylinder(d["p2_bore"] / 2, p["t"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY):
            RegularPolygon(d["p2_pocket"][0] / 2, 6, major_radius=False)
        extrude(amount=d["p2_pocket_depth"], mode=Mode.SUBTRACT)
        for x in (-p["screw_r"], p["screw_r"]):
            with Locations((x, 0, 0)):
                Cylinder(d["bore5"] / 2, p["t"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
            with Locations((x, 0, p["t"] - d["cb_depth5"])):
                Cylinder(d["cb_d5"] / 2, d["cb_depth5"], align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    return bp.part


def check_part(size: str, part: Part) -> None:
    d = derive(size)
    p = d["p2"]
    assert part.is_valid, f"{size}: P2 invalid"
    single_solid(part)
    assert_bbox(part, (p["len"], p["w"], p["t"]), 0.0, d["bbox_tol"], "P2")
    assert_material(part, {
        "pivot bore is air": ((0, 0, p["t"] - 0.5), False),
        "nut pocket is air": ((d["p2_pocket"][0] / 2 - 0.3, 0, 1.0), False),
        "web over the nut": ((d["p2_bore"] / 2 + 1.0, 0, d["p2_pocket_depth"] + d["c"]["p2_web"] / 2), True),
        "M5 counterbore is air": ((p["screw_r"] + d["bore5"] / 2 + 1.0, 0, p["t"] - 0.5), False),
        "under the M5 head": ((p["screw_r"] + d["bore5"] / 2 + 1.0, 0, 1.0), True),
    })


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    p = build_part()
    check_part("T1020", p)
    export(p, "p2_pivot", OUT)
    print(f"P2: ok, volume {p.volume:.0f} mm^3, bbox {p.bounding_box().size}")
    maybe_show(p)
