"""module_grid base: a back plate with ribs along the cell-centre lines, a rim,
an M3 heat-set insert boss at every cell centre (tiles seat on the boss tops)
and wall-screw holes at four grid nodes. Printed plate down; every bore is
vertical and nothing overhangs. Every number is from params.derive_base.

    .venv/bin/python projects/module_grid/base.py     # ACTIVE_BASES -> out/
"""
from __future__ import annotations

import math

from build123d import Axis, Box, BuildPart, Cylinder, Hole, Locations, Mode, Part, fillet

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, single_solid
from projects.module_grid.params import ACTIVE_BASES, derive_base


def build_base(name: str) -> Part:
    d = derive_base(name)
    sx, sy = d["size"]
    w, h = d["rib_w"], d["rib_top_z"] - d["plate_t"]
    with BuildPart() as bp:
        Box(sx, sy, d["rib_top_z"], align=ALIGN_MIN_Z)
        fillet(bp.edges().filter_by(Axis.Z), radius=d["corner_r"])
        with Locations((0, 0, d["plate_t"])):   # hollow it to a rim
            Box(sx - 2 * d["rim_w"], sy - 2 * d["rim_w"], h, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        with Locations(*[(x, 0, d["plate_t"]) for x in d["rib_x"]]):
            Box(w, sy - 2 * d["rim_w"], h, align=ALIGN_MIN_Z)
        with Locations(*[(0, y, d["plate_t"]) for y in d["rib_y"]]):
            Box(sx - 2 * d["rim_w"], w, h, align=ALIGN_MIN_Z)
        with Locations(*[(x, y, d["plate_t"]) for x, y in d["inserts"]]):
            Cylinder(d["boss_r"], d["boss_top_z"] - d["plate_t"], align=ALIGN_MIN_Z)
        with Locations(*[(x, y, d["boss_top_z"]) for x, y in d["inserts"]]):
            Hole(d["insert_bore_d"] / 2, d["insert_bore_depth"])
        with Locations(*[(x, y, d["plate_t"]) for x, y in d["wall_holes"]]):
            Hole(d["wall_bore_d"] / 2, d["plate_t"])
    return bp.part


def _strip(r: float, w: float) -> float:
    """Area of the strip |y| <= w/2 inside a circle of radius r."""
    return 2 * ((w / 2) * math.sqrt(r * r - w * w / 4) + r * r * math.asin(w / (2 * r)))


def expected_volume(d: dict) -> float:
    sx, sy = d["size"]
    r, w, rim = d["corner_r"], d["rib_w"], d["rim_w"]
    h = d["rib_top_z"] - d["plate_t"]
    outline = sx * sy - (4 - math.pi) * r * r
    nx, ny = len(d["rib_x"]), len(d["rib_y"])
    v = outline * d["plate_t"]
    v += (outline - (sx - 2 * rim) * (sy - 2 * rim)) * h                             # rim
    v += (nx * (sy - 2 * rim) + ny * (sx - 2 * rim)) * w * h - nx * ny * w * w * h   # ribs, crossings once
    n = len(d["inserts"])
    rb = d["boss_r"]
    v += n * (math.pi * rb * rb * (d["boss_top_z"] - d["plate_t"]) - (2 * _strip(rb, w) - w * w) * h)   # bosses beyond the ribs
    v -= n * math.pi * (d["insert_bore_d"] / 2) ** 2 * d["insert_bore_depth"]
    v -= len(d["wall_holes"]) * math.pi * (d["wall_bore_d"] / 2) ** 2 * d["plate_t"]
    return v


def check_base(name: str, part: Part) -> dict:
    d = derive_base(name)
    label = f"base {name}"
    assert part.is_valid, f"{label}: invalid"
    single_solid(part)
    assert_bbox(part, (*d["size"], d["boss_top_z"]), 0.0, d["bbox_tol"], label)
    vol = expected_volume(d)
    assert abs(part.volume - vol) < 1e-3 * vol, f"{label}: volume {part.volume:.2f} vs hand {vol:.2f}"
    p, rb = d["pitch"], d["boss_r"]
    probes = {}
    for i, (x, y) in enumerate(d["inserts"]):
        z_floor = d["boss_top_z"] - d["insert_bore_depth"]
        probes.update({
            f"insert{i} bore": ((x, y, d["boss_top_z"] - 0.1), False),
            f"insert{i} bore bottom": ((x, y, z_floor + 0.05), False),
            f"insert{i} floor": ((x, y, z_floor - 0.05), True),
            f"insert{i} boss wall": ((x + d["insert_bore_d"] / 2 + 0.1, y + 0.0, d["boss_top_z"] - 0.1), True),
            f"insert{i} past boss": ((x + rb * 0.75, y + rb * 0.75, d["boss_top_z"] - 0.1), False),
            f"cell{i} pocket": ((x + p / 4, y + p / 4, d["plate_t"] + 0.1), False),
            f"cell{i} plate": ((x + p / 4, y + p / 4, d["plate_t"] - 0.1), True),
            f"cell{i} rib": ((x + p / 4, y, d["rib_top_z"] - 0.1), True),
            f"cell{i} above rib": ((x + p / 4, y, d["rib_top_z"] + 0.1), False),
        })
    for i, (x, y) in enumerate(d["wall_holes"]):
        probes[f"wall{i} bore"] = ((x, y, d["plate_t"] / 2), False)
        probes[f"wall{i} plate"] = ((x + d["wall_bore_d"] / 2 + 0.2, y, d["plate_t"] / 2), True)
    sx, sy = d["size"]
    probes["rim"] = ((0, sy / 2 - d["rim_w"] / 2, d["rib_top_z"] - 0.1), True)
    assert_material(part, probes)
    return dict(volume=part.volume, expected_volume=vol, bbox=part.bounding_box().size)


result = build_base(ACTIVE_BASES[0])

if __name__ == "__main__":
    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys in this file (F23)
    for name in ACTIVE_BASES:
        part = build_base(name)
        rep = check_base(name, part)
        bb = rep["bbox"]
        print(f"base {name}: bbox {bb.X:.2f} x {bb.Y:.2f} x {bb.Z:.2f}, volume {rep['volume']:.1f} "
              f"(hand {rep['expected_volume']:.1f}), solids {len(part.solids())}, valid {part.is_valid}")
        export(part, f"module_grid_base_{name}", OUT)
