"""Lid: a plate that bears on the cell box's walls and on the mask wall's top
(so no light crosses over the mask), with a skirt outside the walls as the
light trap. Prints plate down.

    .venv/bin/python projects/camera_reader/lid.py
"""
from __future__ import annotations

from build123d import Part

from projects.camera_reader.geom import box
from projects.camera_reader.params import derive


def build_lid(size: str = "V0") -> Part:
    d = derive(size)
    b, w, f = d["box"], d["wall"], d["fit"]
    (x0, x1), (y0, y1), z1 = b["x"], b["y"], b["z"][1]
    ox0, ox1, oy0, oy1 = x0 - f - w, x1 + f + w, y0 - f - w, y1 + f + w
    part = box(ox0, ox1, oy0, oy1, z1, z1 + d["lid_t"])
    part += box(ox0, ox1, oy0, oy1, z1 - d["lid_skirt"], z1) - box(x0 - f, x1 + f, y0 - f, y1 + f,
                                                                    z1 - d["lid_skirt"] - 1, z1 + 0.01)
    return part


if __name__ == "__main__":
    from cacad import export
    p = build_lid()
    assert p.is_valid and len(p.solids()) == 1
    print("lid", [round(v, 2) for v in p.bounding_box().size])
    export(p, "lid", __file__.rsplit("/", 1)[0] + "/out")
