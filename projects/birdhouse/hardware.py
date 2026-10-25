"""Bought parts as envelopes, placed in the assembly frame: the ESP32-CAM (board, shield, lens) and the room its
header wiring needs, the two IR LEDs, the 18650 in its holder, the bq25185 charger, the TPL5110 timer and the solar
panel on the cap. Plus the camera's view pyramid the assembly checks against. Every number is from params.derive.
"""
from __future__ import annotations

import math

from build123d import Part, Plane, Pos, Rectangle, Solid, loft

from projects.birdhouse.cap import top_plane
from projects.birdhouse.geom import box, cyl, on_plane
from projects.birdhouse.params import derive


def build_esp32cam(d: dict) -> Part:
    (x0, x1), (y0, y1) = d["cam_box"]
    rb = d["rest_band"] + 0.5
    board = box(x0, x1, y0, y1, d["cam_face_z"], d["cam_back_z"])
    shield = box(x0 + 1.5, x1 - 1.5, y0 + rb, y1 - rb, *d["shield_z"])       # UNVERIFIED envelope, clear of the ledges
    lx, ly = d["lens_xy"]
    lens = box(lx - 4.25, lx + 4.25, ly - 4.25, ly + 4.25, d["lens_z"], d["cam_face_z"])   # 8.5 holder, UNVERIFIED
    return board + shield + lens


def build_wiring_room(d: dict) -> Part:
    """Header pins, Dupont housings and the wires' bend over the board: a keep-out, not a part."""
    x0, x1, y0, y1, zt = d["cam_env"]
    return box(x0, x1, y0, y1, d["cam_back_z"], zt)


def build_ir_leds(d: dict) -> Part:
    led, zt = d["led"], d["tray_z"][1]
    out = None
    for x, y in d["led_xy"]:
        one = cyl(x, y, led["body_d"] / 2, d["led_z"][0], zt) + cyl(x, y, led["flange_d"] / 2, zt, zt + 1.0)
        out = one if out is None else out + one
    return out


def build_battery(d: dict) -> Part:
    x0, x1, y0, y1, _ = d["holder_box"]
    zt = d["tray_z"][1]
    holder = box(x0, x1, y0, y1, zt, zt + d["holder"]["size"][2])
    r = d["cell"]["d"] / 2
    zc = zt + d["holder"]["cell_top"] - r
    cell = Solid.make_cylinder(r, 65.0, Plane(origin=(-32.5, (y0 + y1) / 2, zc), z_dir=(1, 0, 0)))   # 18650: 65 long
    return holder + cell


def build_board(d: dict, key: str) -> Part:
    x0, x1, y0, y1, ztop = d[key]
    return box(x0, x1, y0, y1, d["tray_z"][1], ztop)


def build_panel(d: dict) -> Part:
    pw, pl, pt = d["panel"]["size"]
    tp = top_plane(d)
    cy = d["panel_c"][1]
    local = tp.to_local_coords(Plane.XY.from_local_coords((0, cy, d["top_z"](cy))))
    return on_plane(tp, pw, pl, pt, 0.0, local.Y)


def build_hardware(size: str = "V0") -> dict:
    d = derive(size)
    return dict(esp32cam=build_esp32cam(d), wiring_room=build_wiring_room(d), ir_leds=build_ir_leds(d),
                battery=build_battery(d), bq25185=build_board(d, "bq_box"), tpl5110=build_board(d, "tpl_box"),
                solar_panel=build_panel(d))


def view_cone(d: dict, z_bot: float | None = None) -> Solid:
    """The camera's view pyramid from just under the lens down to z_bot (default: just above the floor's top),
    stock-lens FOV, UNVERIFIED."""
    lx, ly = d["lens_xy"]
    hdiag = math.tan(math.radians(d["cam"]["fov_diag"] / 2))
    tx, ty = 0.6 * hdiag, 0.8 * hdiag                                       # 4:3, long side along Y
    zt, zb = d["lens_z"] - 0.5, d["floor_z"][1] + 0.5 if z_bot is None else z_bot
    h0, h1 = 0.5, d["lens_z"] - zb
    return loft([Plane.XY.offset(zb) * Pos(lx, ly) * Rectangle(2 * h1 * tx, 2 * h1 * ty),
                 Plane.XY.offset(zt) * Pos(lx, ly) * Rectangle(2 * h0 * tx, 2 * h0 * ty)])
