"""Bought and cut parts as envelopes, placed in the assembly frame: the Camera Module 2 (board, lens block, back-side
connector), the Pi 4B (board and its tall parts, rotated onto the roof), the LED ring PCB with its 20 packages, the
PTFE strip, the platen lining, and the fasteners. Plus the camera's view pyramid and the LED light rays the
assembly checks against. Every number is from params.derive.
"""
from __future__ import annotations

from build123d import Compound, Part

from projects.leaf_imager.geom import box, cone, cyl, hex_prism, rod
from projects.leaf_imager.params import BANDS, derive


def build_camera(d: dict) -> Part:
    cam, t = d["cam"], sum(d["cam_pcb_t"]) / 2               # mid-range board for the envelope
    (x0, x1), (y0, y1) = d["cam_xy"]
    zb = d["z_cam_back"]
    board = box(x0, x1, y0, y1, zb - t, zb)
    for x, y in d["cam_holes"]:
        board -= cyl(x, y, cam["hole_d"] / 2, zb - t - 1, zb + 1)
    half = 8.5 / 2                                             # lens block, RP-008149 (camera_reader lens_sq)
    lens = box(-half, half, -half, half, d["wd"], zb - t)
    # back-side FFC connector, UNVERIFIED 2.5 tall (camera_reader); board-frame x 18.36..23.86, y 2..23
    conn = box(2.0 - 12.5, 23.0 - 12.5, d["cam_conn_y"], d["cam_conn_y"] + 5.5, zb, zb + 2.5)
    return board + lens + conn


def build_pi(d: dict) -> Part:
    pi = d["pi"]
    to = d["pi_to_asm"]
    (x0, x1), (y0, y1) = d["pi_xy"]
    board = box(x0, x1, y0, y1, d["z_pi_bot"], d["z_pi_top"])
    for x, y in d["pi_holes"]:
        board -= cyl(x, y, pi["hole_d"] / 2, d["z_pi_bot"] - 1, d["z_pi_top"] + 1)
    px0, px1, py0, py1, h = pi["csi"]
    (ax0, ay0), (ax1, ay1) = to(px0, py0), to(px1, py1)
    csi = box(min(ax0, ax1), max(ax0, ax1), min(ay0, ay1), max(ay0, ay1), d["z_pi_top"], d["z_pi_top"] + h)
    return board + csi


def build_led_pcb(d: dict) -> dict:
    h = d["pcb_side"] / 2
    zp = d["z_pcb"]
    pcb = box(-h, h, -h, h, zp, zp + d["pcb_t"]) - cyl(0, 0, d["pcb_hole_r"], zp - 1, zp + d["pcb_t"] + 1)
    for x, y in d["insert_xy"]:
        pcb -= cyl(x, y, d["pcb_hole_d"] / 2, zp - 1, zp + d["pcb_t"] + 1)
    leds = {}
    for b in BANDS:
        px, py, ph = d["leds"][b]["pkg"]
        for i, (x, y, z) in enumerate(d["led_xyz"][b]):
            leds[f"{b}_{i}"] = box(x - px / 2, x + px / 2, y - py / 2, y + py / 2, z, z + ph)
    return dict(led_pcb=pcb, leds=Compound(children=list(leds.values())))


def build_platen(d: dict) -> dict:
    sx, sy = d["strip_x"], d["strip_y"]
    strip = box(*sx, *sy, d["z_strip_floor"], 0.0)
    sp = d["strip_pocket"]
    flock = box(*d["flock"]["x"], *d["flock"]["y"], d["z_base_top"], 0.0) - box(*sp["x"], *sp["y"], -10, 1)
    for x, y in d["pins"]:
        flock -= cyl(x, y, d["pin_d"] / 2 + 0.5, -10, 1)
    return dict(ptfe_strip=strip, flock=flock)


def _screw(scr: dict, x, y, z_head_face, L, down: bool) -> Part:
    """Pan head screw: head on the face at z_head_face, shank L toward -Z (down=True) or +Z."""
    s = 1 if not down else -1
    head = cyl(x, y, scr["head_dk"] / 2, *sorted((z_head_face, z_head_face - s * scr["head_k"])))
    shank = cyl(x, y, scr["d"] / 2, *sorted((z_head_face, z_head_face + s * L)))
    return head + shank


def _nut(scr: dict, x, y, z0) -> Part:
    r = scr["nut_s"] / (2 * 0.8660254037844386)
    return hex_prism(x, y, r, z0, z0 + scr["nut_m"]) - cyl(x, y, scr["d"] / 2, z0 - 1, z0 + scr["nut_m"] + 1)


def build_fasteners(d: dict) -> dict:
    S = d["screws"]
    out = {}
    # LED PCB: M3 down through the PCB into the corner inserts
    out["pcb_screws"] = Compound(children=[_screw(S["M3"], x, y, d["z_pcb"] + d["pcb_t"], d["pcb_screw"], True)
                                           for x, y in d["insert_xy"]])
    # camera: M2 up from under the board, nut in the carrier's top pocket (seated on the pocket ceiling)
    t = sum(d["cam_pcb_t"]) / 2
    z_front = d["z_cam_back"] - t
    m2 = S["M2"]
    out["cam_screws"] = Compound(children=[_screw(m2, x, y, z_front, d["cam_screw"], False) for x, y in d["cam_holes"]])
    z_nut2 = d["z_roof"] - d["m2_pocket"]["depth"]
    out["cam_nuts"] = Compound(children=[_nut(m2, x, y, z_nut2) for x, y in d["cam_holes"]])
    # roof to carrier: M3 down from the roof top, nut in the carrier's bottom pocket against its ceiling
    m3 = S["M3"]
    out["roof_screws"] = Compound(children=[_screw(m3, x, y, d["z_roof_top"], d["roof_screw"], True)
                                            for x, y in d["m3_carrier_xy"]])
    z_nut3 = d["z_carrier"][0] + d["m3_pocket"]["depth"] - m3["nut_m"]
    out["roof_nuts"] = Compound(children=[_nut(m3, x, y, z_nut3) for x, y in d["m3_carrier_xy"]])
    # Pi: M2.5 down through the Pi into the nut in each boss top
    m25 = S["M2_5"]
    out["pi_screws"] = Compound(children=[_screw(m25, x, y, d["z_pi_top"], d["pi_screw"], True) for x, y in d["pi_holes"]])
    z_nut25 = d["z_pi_bot"] - d["m25_pocket"]["depth"]
    out["pi_nuts"] = Compound(children=[_nut(m25, x, y, z_nut25) for x, y in d["pi_holes"]])
    return out


def build_hardware(size: str = "V0") -> dict:
    d = derive(size)
    hw = dict(camera=build_camera(d), pi4b=build_pi(d), **build_led_pcb(d), **build_platen(d), **build_fasteners(d))
    return hw


def view_cone(d: dict) -> Part:
    return cone(d["wd"], d["cam"]["fov"])


def ray_targets(d: dict) -> dict:
    """Points every LED must light: the corners of the uniformity area and of the PTFE strip, and the centre."""
    hx, hy = (d["uniform_frac"] * f / 2 for f in d["field"])
    (sx0, sx1), (sy0, sy1) = d["strip_x"], d["strip_y"]
    pts = {"centre": (0.0, 0.0, 0.0)}
    pts.update({f"uniform{i}": (x, y, 0.0) for i, (x, y) in enumerate(((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)))})
    pts.update({f"strip{i}": (x, y, 0.0) for i, (x, y) in enumerate(((sx0, sy0), (sx1, sy0), (sx0, sy1), (sx1, sy1)))})
    return pts


def rays(d: dict) -> dict:
    """One thin rod from each LED's emitting face (just below it) to each target."""
    out = {}
    for b in BANDS:
        for i, (x, y, z) in enumerate(d["led_xyz"][b]):
            for k, p in ray_targets(d).items():
                out[f"{b}_{i}->{k}"] = rod((x, y, z - 0.05), p)
    return out
