"""Camera carrier: a plate under the roof that holds the Camera Module 2 face down with the lens on the optical axis.
Four bosses set the camera's back 'cam_gap' below it; M2 screws come up through the camera into nuts captured in
pockets in its top face, which the roof closes. Two M3 screws from the roof top hold it, nuts in pockets in its
bottom face. The camera's connector edge faces -Y, past the carrier, so the ribbon turns straight up into the
roof slot. Prints upside down (top face on the bed); the M2 pocket ceilings are bridged annuli.

    .venv/bin/python projects/leaf_imager/carrier.py
"""
from __future__ import annotations

from build123d import Part

from projects.leaf_imager.geom import box, cyl, hex_prism
from projects.leaf_imager.params import derive


def build_carrier(size: str = "V0") -> Part:
    d = derive(size)
    (x0, x1), (y0, y1) = d["carrier_xy"]
    zc0, zc1 = d["z_carrier"]
    part = box(x0, x1, y0, y1, zc0, zc1)
    for x, y in d["cam_holes"]:
        part += cyl(x, y, d["cam_boss_r"], d["z_cam_back"], zc0)
        part -= cyl(x, y, d["cam_bore"] / 2, d["z_cam_back"] - 1, zc1 + 1)
        part -= hex_prism(x, y, d["m2_pocket"]["r"], zc1 - d["m2_pocket"]["depth"], zc1 + 1)
    for x, y in d["m3_carrier_xy"]:
        part -= cyl(x, y, d["m3_bore"] / 2, zc0 - 1, zc1 + 1)
        part -= hex_prism(x, y, d["m3_pocket"]["r"], zc0 - 1, zc0 + d["m3_pocket"]["depth"])
    return part


def check_carrier(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "carrier must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.min.Z - d["z_cam_back"]) < 1e-3 and abs(bb.max.Z - d["z_roof"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_carrier()
    check_carrier(p)
    print("carrier", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "carrier", __file__.rsplit("/", 1)[0] + "/out")
