"""Bought parts as solids: the Pi 4B and Camera Module 2 from the vendor
drawings (Raspberry Pi publishes no STEP for either), the two cuvettes, the
diffuser sheet, the LEDs, and an envelope of the bought stand built from the
numbers measured on its meshes (params.STAND). The stand's own meshes are for
viewing (FreeCAD, renders); checks use the envelope.

Each board is built in its drawing frame and placed with a Location, so the
same solid exports as a local STEP (for FreeCAD) and sits in the assembly.

    .venv/bin/python projects/camera_reader/hardware.py   # writes out/pi4b.step, out/cam_v2.step
"""
from __future__ import annotations

from build123d import Location, Part, Plane, Pos, RectangleRounded, extrude, loft

from projects.camera_reader.geom import box, cyl_y, rect_y
from projects.camera_reader.params import FLAT_TO_ASM, PARTS, STAND, derive

UPRIGHT_STL = "ref/stand/upright.stl"   # relative to the project directory
BASE_STL = "ref/stand/base.stl"


def _board(size, corner_r, holes, hole_d, t) -> Part:
    pcb = extrude(Pos(size[0] / 2, size[1] / 2) * RectangleRounded(size[0], size[1], corner_r), amount=t)
    for hx, hy in holes:
        pcb -= Pos(hx, hy, t / 2) * extrude(RectangleRounded(hole_d, hole_d, hole_d / 2 - 1e-3), amount=t + 2,
                                            both=True)
    return pcb


def build_pi4b_local() -> Part:
    """Drawing frame: x 0..85 (USB/Ethernet at x = 85), y 0..56 (GPIO at y = 56), z up from the PCB's back face."""
    p = PARTS["pi4b"]
    t = p["pcb_t"]
    part = _board(p["size"], p["corner_r"], p["holes"], p["hole_d"], t)
    for x0, x1, y0, y1, h in p["parts"].values():
        part += box(x0, x1, y0, y1, t, t + h)
    return part


def build_cam_local() -> Part:
    """Drawing frame: x from the hole edge (0) to the connector edge (23.862), y along the 25 side, z up from the
    PCB's back face; the lens points +z."""
    p = PARTS["cam_v2"]
    t = p["pcb_t"]
    part = _board(p["size"], p["corner_r"], p["holes"], p["hole_d"], t)
    lx, ly = p["lens_xy"]
    s = p["lens_sq"] / 2
    part += box(lx - s, lx + s, ly - s, ly + s, t, p["depth"])
    x0, x1, y0, y1, h = p["conn"]
    part += box(x0, x1, y0, y1, t, t + h)
    return part


def pi_location(d) -> Location:
    """Drawing x -> +Z (USB end up), drawing y -> +X, drawing z -> +Y (components face the camera's way)."""
    pi = d["pi"]
    return Location(Plane(origin=(pi["x_c"] - PARTS["pi4b"]["size"][1] / 2, pi["back_y"], pi["z0"]),
                          x_dir=(0, 0, 1), z_dir=(0, 1, 0)))


def cam_location(d) -> Location:
    """Drawing x -> -Z (connector edge down, at the pocket's open side), drawing y -> -X, z -> +Y."""
    cam = d["cam"]
    return Location(Plane(origin=(cam["x_c"] + PARTS["cam_v2"]["size"][1] / 2, cam["back_y"], cam["board_z"][1]),
                          x_dir=(0, 0, -1), z_dir=(0, 1, 0)))


def flat_location(which: str) -> Location:
    """The stand meshes' print frame -> ASM (params.FLAT_TO_ASM)."""
    m, off = FLAT_TO_ASM[which]["matrix"], FLAT_TO_ASM[which]["offset"]
    return Location(Plane(origin=off, x_dir=(m[0][0], m[1][0], m[2][0]), z_dir=(m[0][2], m[1][2], m[2][2])))


def build_stand_envelope(d) -> dict:
    """Upright and base as simple solids from the measured numbers, in ASM."""
    S = STAND
    (x0, x1), (y0, y1), t = S["plate_x"], S["plate_y"], S["plate_t"]
    up = box(x0, x1, y0, y1, 0, t)
    wi0, wi1 = S["pi_wall_x"]
    for a, b in ((x0, wi0), (wi1, x1)):                                # side walls and their ledges
        up += box(a, b, 127.49, 156.89, 0, S["wall_h"])
        up += box(a, a + 8.51 if a == x0 else b, 127.49, 156.89, 0, S["pi_ledge_z"]) if a == x0 else \
            box(b - 8.51, b, 127.49, 156.89, 0, S["pi_ledge_z"])
    for a, b in ((x0, 172.29), (190.36, x1)):                          # bottom stops
        up += box(a, b, 66.72, S["pi_stop_y"], 0, S["wall_h"])
    (ox0, ox1), (oy0, oy1) = S["cam_outer_x"], S["cam_outer_y"]
    (ix0, ix1), (iy0, iy1) = S["cam_inner_x"], S["cam_inner_y"]
    frame = box(ox0, ox1, oy0, oy1, t, S["cam_top_z"]) - box(ix0, ix1, iy0, iy1, t - 1, S["cam_top_z"] + 1)
    frame -= box(*S["cam_gap_x"], oy0 - 1, iy0 + 0.01, t - 1, S["cam_top_z"] + 1)
    up += frame
    up = flat_location("upright") * up
    (bw, bd), (tw, td), h = S["base_size"], S["base_top"], S["base_h"]
    base = loft([Plane.XY * RectangleRounded(bw, bd, 0.5), Plane.XY.offset(h) * RectangleRounded(tw, td, 0.5)])
    sw, st = S["slot"]
    base -= box(-sw / 2, sw / 2, -st / 2, st / 2, S["slot_floor_z"], h + 1)
    return dict(stand_upright=up, stand_base=base)


def build_hardware(size: str = "V0") -> dict:
    d = derive(size)
    P = PARTS
    hw = dict(pi4b=pi_location(d) * build_pi4b_local(), cam_v2=cam_location(d) * build_cam_local())
    hw.update(build_stand_envelope(d))
    # Cuvettes: glass shell (outside less inside, open top) and a cap block on the rim
    for k, cell in d["cells"].items():
        if cell["cuvette"] is None:
            continue
        cv = P[cell["cuvette"]]
        g = (cv["w"] - cv["inside_w"]) / 2
        y0, y1 = cell["y"]
        z0 = d["cell_bottom"]
        shell = box(cell["x"] - cv["w"] / 2, cell["x"] + cv["w"] / 2, y0, y1, z0, z0 + cv["h"])
        shell -= box(cell["x"] - cv["inside_w"] / 2, cell["x"] + cv["inside_w"] / 2, y0 + g, y1 - g, z0 + g,
                     z0 + cv["h"] + 1)
        shell += box(cell["x"] - cv["w"] / 2, cell["x"] + cv["w"] / 2, y0, y1, z0 + cv["h"], z0 + cv["h"] + cv["cap_h"])
        hw[f"cuvette_{k}"] = shell
    b, f = d["box"], d["fit"]
    w = d["box"]["inner_half_w"]
    LX = d["lens"][0]
    hw["diffuser"] = box(LX - w + f, LX + w - f, b["y_diff"][0] + f, b["y_diff"][0] + f + P["diffuser"]["t"],
                         b["floor_top"], b["floor_top"] + d["diffuser_cut"][1])
    led = P["led"]
    y_wall = b["y"][1]
    for i, (x, z) in enumerate(d["leds"]):
        body = cyl_y(led["body_d"], x, z, y_wall - (led["body_len"] - led["flange_t"]), y_wall)
        body += cyl_y(led["flange_d"], x, z, y_wall, y_wall + led["flange_t"])
        hw[f"led{i}"] = body
    return hw


def ray_solids(d) -> dict:
    """The light each window sends to the lens: a loft from a pupil square at the lens to the window."""
    LX, LY, LZ = d["lens"]
    pr = d["pupil_r"]
    out = {}
    for k, (x0, x1, z0, z1) in d["windows"].items():
        out[f"ray_{k}"] = loft([rect_y(LY, LX, LZ, 2 * pr, 2 * pr),
                                rect_y(d["y_datum"], (x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0)])
    return out


if __name__ == "__main__":
    from cacad import export
    here = __file__.rsplit("/", 1)[0]
    for name, part in (("pi4b_local", build_pi4b_local()), ("cam_v2_local", build_cam_local())):
        print(name, [round(v, 2) for v in part.bounding_box().size], part.is_valid)
        export(part, name, here + "/out")
