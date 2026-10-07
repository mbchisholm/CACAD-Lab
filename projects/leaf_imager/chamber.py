"""Chamber: an open square tube standing on the base. A 45 deg corbelled ledge carries the LED ring PCB, four corner
bosses take its M3 heat-set inserts, a tongue on top locates the roof and laps the joint, and a notch at the front
wall's foot lets a petiole through. Prints on its bottom edge; the notch top is the one bridge.

    .venv/bin/python projects/leaf_imager/chamber.py
"""
from __future__ import annotations

from build123d import Part

from cacad.registries.materials import INSERT_BORE_M3, INSERT_DEPTH_M3
from projects.leaf_imager.geom import box, corner_corbel, cyl, frustum
from projects.leaf_imager.params import derive


def build_chamber(size: str = "V0") -> Part:
    d = derive(size)
    S, w = d["inner"], d["wall"]
    h, o = S / 2, d["outer"] / 2
    z0, z1 = d["z_base_top"], d["z_roof"]
    part = box(-o, o, -o, o, z0, z1) - box(-h, h, -h, h, z0 - 1, z1 + 1)
    # tongue on the wall's centreline
    tw, _ = d["tongue"]
    m = h + w / 2
    part += box(-m - tw / 2, m + tw / 2, -m - tw / 2, m + tw / 2, *d["tongue_z"]) - \
        box(-m + tw / 2, m - tw / 2, -m + tw / 2, m - tw / 2, d["tongue_z"][0] - 1, d["tongue_z"][1] + 1)
    # ledge: a flat band, then a 45 deg corbel back to the wall (into the wall by w/2 so the union is solid)
    lw = d["ledge_w"]
    zl0, zl1 = d["z_ledge"]
    part += box(-m, m, -m, m, zl0, zl1) - box(-h + lw, h - lw, -h + lw, h - lw, zl0 - 1, zl1 + 1)
    corbel = box(-m, m, -m, m, d["z_ledge_corbel_bot"], zl0) - frustum((h - lw, h - lw), (h, h), zl0, d["z_ledge_corbel_bot"])
    part += corbel
    # corner insert bosses: a c x c block down from the PCB seat, then a 45 deg corbel into the corner
    c = d["boss_c"]
    zb = d["z_pcb"] - d["boss_block_h"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            xs = sorted((sx * (h - c), sx * (h + w / 2)))
            ys = sorted((sy * (h - c), sy * (h + w / 2)))
            part += box(*xs, *ys, zb, d["z_pcb"])
            part += corner_corbel(sx, sy, h, w / 2, c, zb)
    for x, y in d["insert_xy"]:
        part -= cyl(x, y, INSERT_BORE_M3 / 2, d["z_pcb"] - INSERT_DEPTH_M3, d["z_pcb"] + 1)
    # petiole notch at the front wall's foot
    part -= box(*d["notch_x"], -o - 1, -h + 1, z0 - 1, d["notch_z"][1])
    return part


def check_chamber(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "chamber must be one valid solid"
    bb = part.bounding_box()
    o = d["outer"]
    assert abs(bb.size.X - o) < 1e-3 and abs(bb.size.Y - o) < 1e-3, f"chamber footprint {bb.size}"
    assert abs(bb.min.Z - d["z_base_top"]) < 1e-3 and abs(bb.max.Z - d["tongue_z"][1]) < 1e-3, f"chamber z {bb.min.Z}..{bb.max.Z}"


if __name__ == "__main__":
    from cacad import export
    p = build_chamber()
    check_chamber(p)
    print("chamber", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "chamber", __file__.rsplit("/", 1)[0] + "/out")
