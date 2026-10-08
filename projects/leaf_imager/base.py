"""Base: the platen. Its top carries the black lining, the PTFE strip in its pocket (face in the leaf plane) and two
pins that locate the hold-down frame. A rim all round locates the chamber when it is lowered on and laps the joint
against light; a notch in the rim's front lines up with the chamber's, for a leaf still on its plant. Prints on
its bottom.

    .venv/bin/python projects/leaf_imager/base.py
"""
from __future__ import annotations

from build123d import Part

from projects.leaf_imager.geom import box, cyl
from projects.leaf_imager.params import derive


def build_base(size: str = "V0") -> Part:
    d = derive(size)
    b, ri = d["base_half"], d["rim_in"]
    part = box(-b, b, -b, b, d["z_base_bot"], d["z_base_top"])
    part += box(-b, b, -b, b, d["z_base_top"], d["z_rim_top"]) - box(-ri, ri, -ri, ri, d["z_base_top"] - 1, d["z_rim_top"] + 1)
    part -= box(*d["notch_x"], -b - 1, -ri + 1, d["z_base_top"], d["z_rim_top"] + 1)
    sp = d["strip_pocket"]
    part -= box(*sp["x"], *sp["y"], sp["z"][0], sp["z"][1] + 1)
    for x, y in d["pins"]:
        part += cyl(x, y, d["pin_d"] / 2, *d["pin_z"])
    return part


def check_base(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "base must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - 2 * d["base_half"]) < 1e-3 and abs(bb.size.Y - 2 * d["base_half"]) < 1e-3
    assert abs(bb.min.Z - d["z_base_bot"]) < 1e-3 and abs(bb.max.Z - d["z_rim_top"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_base()
    check_base(p)
    print("base", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "base", __file__.rsplit("/", 1)[0] + "/out")
