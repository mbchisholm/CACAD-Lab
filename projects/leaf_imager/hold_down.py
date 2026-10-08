"""Hold-down frame: an open frame that lies on the leaf's edges and keeps it flat; two tabs drop over the base's
pins, so it lands in the same place every read. Its window is the leaf area; its +Y bar and that bar's shadow stay
clear of the PTFE strip. Prints flat. Line its top black: black PETG can be bright at 850 nm.

    .venv/bin/python projects/leaf_imager/hold_down.py
"""
from __future__ import annotations

from build123d import Part

from projects.leaf_imager.geom import box, cyl
from projects.leaf_imager.params import derive


def build_hold_down(size: str = "V0") -> Part:
    d = derive(size)
    fr = d["frame"]
    (wx0, wx1), (wy0, wy1) = fr["window"]
    part = box(*fr["x"], *fr["y"], *fr["z"]) - box(wx0, wx1, wy0, wy1, -1, fr["z"][1] + 1)
    for tab, (px, py) in zip(d["tabs"], d["pins"]):
        part += box(*tab["x"], *tab["y"], *fr["z"])
        part -= cyl(px, py, d["tab_hole_d"] / 2, -1, fr["z"][1] + 1)
    return part


def check_hold_down(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "hold-down frame must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.Z - d["frame_t"]) < 1e-3 and abs(bb.max.X - d["tabs"][1]["x"][1]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_hold_down()
    check_hold_down(p)
    print("hold_down", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "hold_down", __file__.rsplit("/", 1)[0] + "/out")
