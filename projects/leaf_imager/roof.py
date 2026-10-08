"""Roof: the lid on the chamber's tongue (groove underneath), with the Pi on four bosses on top (M2.5 nut in each
boss top, blind bore below it), the ribbon slot just past the Pi's SD-card end, two M3 holes for the camera
carrier, and the LED cable hole. Felt flaps close the slot and the cable hole. Prints on its underside; the groove
ceiling is the one bridge.

    .venv/bin/python projects/leaf_imager/roof.py
"""
from __future__ import annotations

from build123d import Part

from projects.leaf_imager.geom import box, cyl, hex_prism
from projects.leaf_imager.params import derive


def build_roof(size: str = "V0") -> Part:
    d = derive(size)
    o = d["outer"] / 2
    z0, z1 = d["z_roof"], d["z_roof_top"]
    part = box(-o, o, -o, o, z0, z1)
    m, g = d["inner"] / 2 + d["wall"] / 2, d["groove"]
    part -= box(-m - g["w"] / 2, m + g["w"] / 2, -m - g["w"] / 2, m + g["w"] / 2, z0 - 1, z0 + g["depth"]) - \
        box(-m + g["w"] / 2, m - g["w"] / 2, -m + g["w"] / 2, m - g["w"] / 2, z0 - 2, z0 + g["depth"] + 1)
    part -= box(*d["slot_x"], *d["slot_y"], z0 - 1, z1 + 1)
    cx, cy, cd = d["cable_hole"]
    part -= cyl(cx, cy, cd / 2, z0 - 1, z1 + 1)
    for x, y in d["m3_carrier_xy"]:
        part -= cyl(x, y, d["m3_bore"] / 2, z0 - 1, z1 + 1)
    zt = d["z_pi_bot"]
    for x, y in d["pi_holes"]:
        part += cyl(x, y, d["pi_boss_r"], z1, zt)
        part -= hex_prism(x, y, d["m25_pocket"]["r"], zt - d["m25_pocket"]["depth"], zt + 1)
        part -= cyl(x, y, d["pi_bore"] / 2, zt - d["pi_bore_depth"], zt + 1)
    return part


def check_roof(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "roof must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - d["outer"]) < 1e-3 and abs(bb.min.Z - d["z_roof"]) < 1e-3
    assert abs(bb.max.Z - d["z_pi_bot"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_roof()
    check_roof(p)
    print("roof", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "roof", __file__.rsplit("/", 1)[0] + "/out")
