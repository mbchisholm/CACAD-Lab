"""Cell box: rack floor with keyed pockets (50 mm cell on the axis, 10 mm cell
beside it) whose far faces bear on the masked datum wall; the opal diffuser
drops in behind the mask between the side and floor ribs; a 30 mm mixing
cavity (line it white); seven LED holes in the back wall (horizontal holes
are teardrops); two insert pads for
the LED retainer. Open top under the lid. Prints on its floor.

    .venv/bin/python projects/camera_reader/cell_box.py
"""
from __future__ import annotations

from build123d import Part

from cacad.registries.materials import INSERT_BORE_M3
from projects.camera_reader.geom import box, prism_y, teardrop_y
from projects.camera_reader.params import PARTS, derive


def build_cell_box(size: str = "V0") -> Part:
    d = derive(size)
    b, w, f = d["box"], d["wall"], d["fit"]
    LX, LY, LZ = d["lens"]
    (x0, x1), (y0, y1), (z0, z1) = b["x"], b["y"], b["z"]
    ft = b["floor_top"]
    part = box(x0, x1, y0, y1, z0, z1) - box(x0 + w, x1 - w, y0 + w, y1 - w, ft, z1 + 1)
    # Pockets: cuvette + fit across and towards the camera; the far face is the mask (datum)
    for k, cell in d["cells"].items():
        if cell["cuvette"] is None:
            continue
        cv = PARTS[cell["cuvette"]]
        part -= box(cell["x"] - cv["w"] / 2 - f, cell["x"] + cv["w"] / 2 + f, cell["y"][0] - f, d["y_datum"],
                    ft - d["pocket_depth"], ft + 0.01)
    # Mask wall with the three windows
    mask = box(x0 + w, x1 - w, *b["y_mask"], ft, z1)
    for wx0, wx1, wz0, wz1 in d["windows"].values():
        mask -= box(wx0, wx1, b["y_mask"][0] - 1, b["y_mask"][1] + 1, wz0, wz1)
    part += mask
    # Diffuser ribs: both side walls full height, and across the floor
    rh = d["rib_h"]
    part += box(x0 + w, x0 + w + rh, *b["y_rib"], ft, z1)
    part += box(x1 - w - rh, x1 - w, *b["y_rib"], ft, z1)
    part += box(x0 + w, x1 - w, *b["y_rib"], ft, ft + rh)
    # Front wall: the snout's opening and its four bolt holes
    s = d["snout"]
    part -= prism_y(y0 - 1, y0 + w + 1, LX, LZ, *s["far_in"])
    for hx, hz in d["flange_holes"]:
        part -= teardrop_y(d["m3_bore"], hx, hz, y0 - 1, y0 + w + 1)
    # Back wall: LED holes; insert pads (floor to above the retainer) with blind bores
    for x, z in d["leds"]:
        part -= teardrop_y(d["led_hole"], x, z, y1 - w - 1, y1 + 1)
    pad = d["insert_pad"]
    r = d["retainer"]
    for sx, sz in r["screws"]:
        part += box(sx - pad["w"] / 2, sx + pad["w"] / 2, y1, y1 + pad["depth"], z0, r["z"][1])
        part -= teardrop_y(INSERT_BORE_M3, sx, sz, y1 + pad["depth"] - pad["bore"], y1 + pad["depth"] + 1)
    return part


def check_cell_box(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "cell box must be one valid solid"
    bb = part.bounding_box()
    b = d["box"]
    assert abs(bb.min.Z - b["z"][0]) < 1e-3 and abs(bb.max.Z - b["z"][1]) < 1e-3
    assert abs(bb.max.Y - (b["y"][1] + d["insert_pad"]["depth"])) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_cell_box()
    check_cell_box(p)
    print("cell_box", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "cell_box", __file__.rsplit("/", 1)[0] + "/out")
