"""Floor: a plate that drops in onto the body's ledge, the fit clear of the walls, jambs and front panel, its front
corners notched round the jambs, four drain holes over the ledge opening, and a 45 deg chamfer on its bed edge so
the elephant's foot never reaches the fit. Prints flat.

    .venv/bin/python projects/birdhouse/floor.py
"""
from __future__ import annotations

from build123d import Part

from cacad import line_edges_at_z, try_chamfer
from projects.birdhouse.geom import box, cyl
from projects.birdhouse.params import derive


def build_floor(size: str = "V0") -> Part:
    d = derive(size)
    fx, (fy0, fy1), (z0, z1) = d["floor_x"], d["floor_y"], d["floor_z"]
    part = box(-fx, fx, fy0, fy1, z0, z1)
    nx, ny = d["floor_notch"]
    for s in (-1, 1):
        part -= box(*sorted((s * nx, s * (fx + 1))), fy0 - 1, ny, z0 - 1, z1 + 1)
    part = try_chamfer(part, line_edges_at_z(part, z0), d["foot_chamfer"], (), "floor foot", required=True)
    dx, dy = d["drain_xy"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            part -= cyl(sx * dx, sy * dy, d["drain_d"] / 2, z0 - 1, z1 + 1)
    return part


def check_floor(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "floor must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - 2 * d["floor_x"]) < 1e-3 and abs(bb.min.Z - d["floor_z"][0]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_floor()
    check_floor(p)
    print("floor", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "floor", __file__.rsplit("/", 1)[0] + "/out")
