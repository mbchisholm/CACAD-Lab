"""Cap: the roof over the tray. Its skirt drops over the body's top, its shoulder rests on the tray's rim band, its
ceiling slopes with the top, the eave in front is solid (slice it with sparse infill), and the panel's lead comes
in through a hole under the panel, square to the top. Prints upside down on its top face: walls lean 10 deg, the
ceiling and shoulder face up, nothing needs support.

    .venv/bin/python projects/birdhouse/cap.py
"""
from __future__ import annotations

from build123d import Part, Plane, Pos, Solid

from projects.birdhouse.geom import below, rbox, slope_plane
from projects.birdhouse.params import derive


def top_plane(d: dict) -> Plane:
    y0 = d["cavity_y"][0]
    return slope_plane(d["top_z"](y0), y0, d["slope"])


def ceiling_plane(d: dict) -> Plane:
    y0 = d["cavity_y"][0]
    return slope_plane(d["ceil_z"](y0), y0, d["slope"])


def build_cap(size: str = "V0") -> Part:
    d = derive(size)
    f, r = d["fit"], d["corner_r"]
    ox, (y0, y1) = d["cap_out_x"], d["cap_y"]
    zs, zt = d["skirt_z"], d["tray_z"][1]
    big = d["top_z"](y1) + 10
    part = rbox(-ox, ox, y0, y1, zs, big, r + f + d["cap_wall"]) & below(top_plane(d))
    ix, iy = d["cap_in"]
    part -= rbox(-ix, ix, -iy, iy, zs - 1, zt, r + f)                 # skirt pocket: body top and tray
    ux, (cy0, cy1) = d["usable"][0], d["cavity_y"]
    part -= rbox(-ux, ux, cy0, cy1, zt - 1, big, max(r - d["rim"], 1.0)) & below(ceiling_plane(d))
    hx_, hy_, hd = d["cable_hole"]
    tp = top_plane(d)
    local = tp.to_local_coords(Pos(hx_, hy_, d["top_z"](hy_)).position)
    hole = Solid.make_cylinder(hd / 2, 40, Plane(origin=tp.from_local_coords((local.X, local.Y, -30)), z_dir=tp.z_dir))
    part -= hole
    return part


def check_cap(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "cap must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.min.Z - d["skirt_z"]) < 1e-3 and abs(bb.size.X - 2 * d["cap_out_x"]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_cap()
    check_cap(p)
    print("cap", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "cap", __file__.rsplit("/", 1)[0] + "/out")
