"""Riser: a 2.4 mm tube from the table to the cell box's underside, a 45 deg
inner corbel under the box's walls, a centre rib under the rack floor, and a
lip that locates the box (fit all round, notched for the box's insert
pads). Sets the optical axis on the lens.
Prints standing.

    .venv/bin/python projects/camera_reader/riser.py
"""
from __future__ import annotations

from build123d import Part, Plane, Rectangle, loft

from projects.camera_reader.geom import box
from projects.camera_reader.params import derive


def _rect_z(z, x0, x1, y0, y1):
    return Plane(origin=((x0 + x1) / 2, (y0 + y1) / 2, z)) * Rectangle(x1 - x0, y1 - y0)


def build_riser(size: str = "V0") -> Part:
    d = derive(size)
    b, w, f, r = d["box"], d["riser_rib"], d["fit"], d["riser"]
    (x0, x1), (y0, y1) = r["x"], r["y"]
    zt, zl = r["z"][1], r["lip_top"]
    ix0, ix1, iy0, iy1 = x0 + w, x1 - w, y0 + w, y1 - w                 # tube inside = box outside + fit
    bx0, bx1, by0, by1 = b["x"][0] + d["wall"], b["x"][1] - d["wall"], b["y"][0] + d["wall"], b["y"][1] - d["wall"]
    part = box(x0, x1, y0, y1, 0, zl) - box(ix0, ix1, iy0, iy1, -1, zl + 1)
    # Corbel: 45 deg from the tube's inside to the box's inside, then a flat band up to the box's underside
    k = max(ix1 - bx1, bx0 - ix0, iy1 - by1, by0 - iy0)
    za = zt - d["corbel"] - k
    band = box(ix0, ix1, iy0, iy1, za, zt)
    hole = loft([_rect_z(za - 0.01, ix0 - 0.01, ix1 + 0.01, iy0 - 0.01, iy1 + 0.01),
                 _rect_z(za + k, bx0, bx1, by0, by1)])
    band -= hole
    band -= box(bx0, bx1, by0, by1, za + k - 0.01, zt + 1)
    part += band
    # Notch the lip where the box's insert pads come down the back wall
    pad = d["insert_pad"]
    for sx, _ in d["retainer"]["screws"]:
        part -= box(sx - pad["w"] / 2 - f, sx + pad["w"] / 2 + f, b["y"][1] - 1, y1 + 1, zt, zl + 1)
    cx = (x0 + x1) / 2
    part += box(cx - w / 2, cx + w / 2, iy0, iy1, 0, zt)
    return part


if __name__ == "__main__":
    from cacad import export
    p = build_riser()
    assert p.is_valid and len(p.solids()) == 1
    print("riser", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "riser", __file__.rsplit("/", 1)[0] + "/out")
