"""Tray: the nest's ceiling and the electronics carrier. It lies on the body's wall tops, located by the cap's skirt.
On it: the ESP32-CAM face down on two end ledges, corner walls round it, the lens window under it; the two IR LED
bores beside it; corner walls round the 18650 holder (two zip ties through the tray hold it), the charger and the
timer. A rim band stays clear for the cap's shoulder. Prints flat; every bore and slot is vertical.

    .venv/bin/python projects/birdhouse/tray.py
"""
from __future__ import annotations

from build123d import Part

from projects.birdhouse.geom import box, cradle_corners, cyl, rbox
from projects.birdhouse.params import derive


def build_tray(size: str = "V0") -> Part:
    d = derive(size)
    hx, hy, (z0, z1), f = d["hx"], d["hy"], d["tray_z"], d["fit"]
    part = rbox(-hx, hx, -hy, hy, z0, z1, d["corner_r"])
    for k, (x0, x1, y0, y1) in d["cradles"].items():
        part += cradle_corners(x0, x1, y0, y1, f, d["cradle_wall"], d["cradle_leg"], z1, z1 + d["cradle_h"][k])
    (cx0, cx1), (cy0, cy1) = d["cam_box"]
    rb = d["rest_band"]
    for y0, y1 in ((cy0, cy0 + rb), (cy1 - rb, cy1)):          # end ledges under the board
        part += box(cx0, cx1, y0, y1, z1, d["cam_face_z"])
    lx, ly = d["lens_xy"]
    wx, wy = d["window"]
    part -= box(lx - wx / 2, lx + wx / 2, ly - wy / 2, ly + wy / 2, z0 - 1, z1 + 1)
    for x, y in d["led_xy"]:
        part -= cyl(x, y, d["led_bore"] / 2, z0 - 1, z1 + 1)
    sw, sl = d["tie_slot"]
    _, _, hy0, hy1 = d["cradles"]["holder"]
    off = f + d["cradle_wall"] + sl / 2 + 0.5
    for x in d["tie_x"]:                                        # two ties round the holder, outside its corner walls
        for y in (hy0 - off, hy1 + off):
            part -= box(x - sw / 2, x + sw / 2, y - sl / 2, y + sl / 2, z0 - 1, z1 + 1)
    return part


def check_tray(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "tray must be one valid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - 2 * d["hx"]) < 1e-3 and abs(bb.min.Z - d["tray_z"][0]) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_tray()
    check_tray(p)
    print("tray", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "tray", __file__.rsplit("/", 1)[0] + "/out")
