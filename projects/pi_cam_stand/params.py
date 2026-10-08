r"""Pi camera desk stand: a printed stand for a Pi 4B and a Camera Module 2, every number.

The Pi lies flat on four bosses in the base, screwed down with M2.5 screws into nuts captured from underneath. A
U-section column rises behind its GPIO edge. The camera is screwed by its four holes (M2, nuts captured in the
carrier's back) to a carrier whose knuckle sits between the column's side walls: one M3 bolt through walls and
knuckle is the hinge, and tightening it clamps the tilt by friction. The ribbon runs up inside the column.

Frame: Z up, Z = 0 the table (base underside). Origin under the hinge axis, which runs along X at y = 0. The camera
looks +Y at tilt 0; tilt is a rotation about the hinge axis, negative looks down.

               cheek   knuckle   carrier plate, camera on 4 bosses
                 |  [==O==]  ->  lens 150 mm up at tilt 0
                 |  |  ribbon up inside the U
             web |  |
     Pi (flat) ===========  <- bosses, M2.5 nuts from below
     base ===================

Every input is a (value, TAG, source) triple; validate() refuses an untagged one (PARAMS_CONVENTION rule 5).

    .venv/bin/python projects/pi_cam_stand/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import BED, FDM_HOLE_ALLOWANCE, NOZZLE, WALL

TAGS = ("STANDARD", "VENDOR", "INFERRED", "DESIGN", "CONVENIENCE", "PLACEHOLDER")

_RPI_DOCS = "raspberrypi.com/documentation/accessories/camera.html, hardware_specification.adoc (spec table)"
_CAM_DWG = "RP-008149-DS-1 camera-module-2-mechanical-drawing.pdf"
_PI_DWG = "RP-008343-DS-1 raspberry-pi-4-mechanical-drawing.pdf"

# ---------------------------------------------------------------------------
# Bought parts. The board solids come from camera_reader/hardware.py (same drawings).
# ---------------------------------------------------------------------------
CAMERA = MappingProxyType(dict(
    # Drawing frame: x from the hole edge (0) to the connector edge (23.862), y along the 25 side.
    size=((23.862, 25.0), "VENDOR", _CAM_DWG),
    holes=(((2.0, 2.0), (14.5, 2.0), (2.0, 23.0), (14.5, 23.0)), "VENDOR", _CAM_DWG),
    hole_d=(2.2, "VENDOR", _CAM_DWG),
    lens_xy=((23.862 - 9.462, 12.5), "VENDOR", _CAM_DWG + ": lens 9.462 from the connector edge"),
    lens_sq=(8.5, "VENDOR", _CAM_DWG + ": lens block"),
    connector_x=((23.862 - 5.5, 23.862), "VENDOR", _CAM_DWG + ": 5.5 deep at the connector edge"),
    connector_h=(3.5, "INFERRED", "back-side FFC connector height is unpublished; leaf_imager allows up to 3.5"),
    depth=(9.0, "VENDOR", _RPI_DOCS + ": 'around 25 x 24 x 9 mm', PCB back to lens front"),
    pcb_t=((0.8, 1.6), "DESIGN", "PCB thickness is unpublished; the M2 screws fit any board in this range"),
    fov=((62.2, 48.8), "VENDOR", _RPI_DOCS + ": horizontal x vertical, degrees"),
    image_x=("connector edge", "INFERRED", "the image's long axis runs parallel to the connector edge (leaf_imager): "
                                           "connector edge down gives a landscape image along X"),
))

PI4B = MappingProxyType(dict(
    size=((85.0, 56.0), "VENDOR", _PI_DWG),
    holes=(((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)), "VENDOR", _PI_DWG),
    hole_d=(2.7, "VENDOR", _PI_DWG),
    pcb_t=(1.4, "INFERRED", "not on the drawing; the commonly quoted Pi PCB thickness (camera_reader params)"),
    csi=((45.0, 48.8, 0.3, 22.8, 5.5), "INFERRED", _PI_DWG + ": x0, x1, y0, y1, height; scaled (camera_reader params)"),
    gpio=((7.1, 57.9, 50.0, 55.0, 8.5), "INFERRED", _PI_DWG + ": x0, x1, y0, y1, height; scaled (camera_reader params)"),
))

RIBBON = MappingProxyType(dict(
    part=("Adafruit 1648, Flex Cable for Raspberry Pi Camera or Display - 300mm", "VENDOR",
          "adafruit.com/product/1648 (2026-10-07: in stock, 'drop-in replacement for the standard 150mm cable')"),
    length=(300.0, "VENDOR", "adafruit.com/product/1648: 300 mm x 16 mm"),
    width=(16.0, "VENDOR", "adafruit.com/product/1648: 300 mm x 16 mm"),
    stock_length=(150.0, "INFERRED", "raspberrypi.com Camera Module 2 product page: '15cm ribbon cable' (leaf_imager)"),
))

# Bought fasteners: ISO 7045 pan head screws, ISO 4032 nuts, ISO 273 medium clearance (+ the FDM allowance when the
# hole is printed). Lengths are the ISO 7045 preferred ladder. Same table as leaf_imager, with M3 to 30.
_ISO = "ISO 7045 (dk, k max), ISO 4032 (s, m), ISO 273 medium"
SCREWS = MappingProxyType(dict(
    M2=(dict(d=2.0, clear=2.4, head_dk=4.0, head_k=1.6, nut_s=4.0, nut_m=1.6, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
        "STANDARD", _ISO),
    M2_5=(dict(d=2.5, clear=2.9, head_dk=5.0, head_k=2.0, nut_s=5.0, nut_m=2.0, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
          "STANDARD", _ISO),
    M3=(dict(d=3.0, clear=3.4, head_dk=5.6, head_k=2.4, nut_s=5.5, nut_m=2.4,
             lengths=(4, 5, 6, 8, 10, 12, 16, 20, 25, 30)), "STANDARD", _ISO),
    M4=(dict(d=4.0, clear=4.5, head_dk=8.0, head_k=3.1, nut_s=7.0, nut_m=3.2, lengths=(6, 8, 10, 12, 16, 20, 25)),
        "STANDARD", _ISO),
))

# ---------------------------------------------------------------------------
# Design rules and choices.
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(dict(
    # --- what the stand is for ---
    lens_h=(150.0, "DESIGN", "lens centre above the table at tilt 0: about the bought dev stand's 155 (camera_reader)"),
    tilt_range=((-90.0, 30.0), "DESIGN", "straight down to 30 deg up; the carrier must clear the stand over all of it"),
    view_clear_to=(-45.0, "DESIGN", "the view meets no part of the stand or Pi from straight ahead to 45 deg down"),
    view_len=(400.0, "DESIGN", "length of the view pyramid checked against the stand"),
    # --- base and Pi ---
    base_t=(3.0, "DESIGN", "base plate: the Pi bosses and nut pockets stand on it; ribs are the column's walls"),
    base_mx=(10.0, "DESIGN", "base beyond the Pi's ends along X: room for the fixing holes outside the Pi"),
    fix_inset=(5.0, "DESIGN", "fixing hole centre from the base edges"),
    standoff=(6.0, "DESIGN", "base top to Pi PCB underside: air under the board, plug overmoulds clear the base"),
    pi_boss_wall=(1.6, "DESIGN", "materials.WALL around the M2.5 clearance bore"),
    gpio_clear=(2.0, "DESIGN", "ribbon run above the GPIO header's top"),
    pi_gap=(6.0, "DESIGN", "Pi GPIO edge to the column web: a 40-way IDC plug on the header, fingers"),
    # --- column (U: two side walls, web at the back) ---
    web_t=(3.0, "DESIGN", "column web, Pi side"),
    side_t=(4.0, "DESIGN", "side walls: an M3 nut pocket (2.4) plus a 1.6 web, and the column's stiffness"),
    ribbon_clear=(1.0, "DESIGN", "ribbon edge to each side wall"),
    ribbon_gap=(2.0, "DESIGN", "web front to the carrier's back at tilt 0: the ribbon runs up between them"),
    window_h=(6.0, "DESIGN", "ribbon window through the web, above the GPIO header: ribbon plus its fold"),
    # --- hinge ---
    clamp_gap=(0.2, "DESIGN", "knuckle side to side wall, each side: the bolt closes it and clamps the tilt"),
    knuckle=((8.0, 10.0), "DESIGN", "knuckle Y x Z around the M3 bore: >= bore + 2 x 2.2"),
    cheek_r=(5.0, "DESIGN", "side wall material beyond the hinge axis, forward and up: >= nut pocket r + 1.6"),
    sweep_clear=(0.5, "DESIGN", "anything that swings past anything else"),
    # --- carrier ---
    cam_gap=(4.0, "DESIGN", "camera PCB back to the carrier: the back-side connector (<= 3.5)"),
    cam_margin=(2.0, "DESIGN", "carrier plate beyond the camera board"),
    cam_boss_wall=(1.6, "DESIGN", "materials.WALL around the M2 clearance bore"),
    pocket_web=(1.2, "DESIGN", "carrier material between the M2 nut pocket ceiling and its front face"),
    slot_h=(3.0, "DESIGN", "ribbon slot through the carrier under the camera's connector edge"),
    slot_bar=(1.6, "DESIGN", "carrier material below the slot"),
    # --- fasteners ---
    nut_clear=(0.3, "DESIGN", "hex pocket across flats over the nut (standoff_plate); nuts are captive, not pressed"),
    nut_extra_min=(0.2, "DESIGN", "least pocket depth over the nut height"),
    thread_past_nut=(1.0, "DESIGN", "screw tip beyond the nut's far face"),
    # --- ribbon path ---
    bend_allow=(10.0, "DESIGN", "ribbon taken up by its fold over the GPIO and its bends"),
    ribbon_slack=(20.0, "DESIGN", "path <= ribbon - this (leaf_imager rule)"),
    # --- printing ---
    max_overhang_deg=(45.0, "DESIGN", "PETG, no support"),
))

SIZES = MappingProxyType(dict(V0=dict()))
ACTIVE_SIZES = ("V0",)
PARTS = ("stand", "carrier")


def _tagged(tables) -> list:
    out = []
    for tname, t in tables:
        for k, v in t.items():
            out.append((f"{tname}.{k}", *v) if isinstance(v, tuple) and len(v) == 3 else (f"{tname}.{k}", v, None, None))
    return out


def _tables():
    return [("CAMERA", CAMERA), ("PI4B", PI4B), ("RIBBON", RIBBON), ("COMMON", COMMON), ("SCREWS", SCREWS)]


def hexr(s: float, clear: float) -> float:
    """Circumradius of a hex pocket over a nut of across-flats s."""
    return (s + clear) / math.sqrt(3)


def _screw_into_nut(L_min: float, lengths) -> float:
    ok = [L for L in lengths if L >= L_min - 1e-9]
    assert ok, f"no stocked length >= {L_min:.2f}"
    return ok[0]


def derive(size: str = "V0", **overrides) -> dict:
    raw = dict(COMMON, **SIZES[size])
    for k, v in overrides.items():
        assert k in raw, f"unknown override {k}"
        raw[k] = (v, "DESIGN", "override")
    c = {k: v[0] for k, v in raw.items()}
    cam = {k: v[0] for k, v in CAMERA.items()}
    pi = {k: v[0] for k, v in PI4B.items()}
    rib = {k: v[0] for k, v in RIBBON.items()}
    scr = {k: v[0] for k, v in SCREWS.items()}
    d = dict(size=size, **c, cam=cam, pi=pi, ribbon=rib, screws=scr)
    bore = lambda m: scr[m]["clear"] + FDM_HOLE_ALLOWANCE

    # --- Pi on the base. CSI connector centred on the column (X = 0), GPIO edge toward the column --------------------
    x0, x1, y0, y1, h_csi = pi["csi"]
    d["inner"] = rib["width"] + 2 * c["ribbon_clear"]                 # between the side walls
    d["y_cb"] = -c["knuckle"][0] / 2                                  # carrier back face at tilt 0
    d["y_wf"] = d["y_cb"] - c["ribbon_gap"]
    d["y_wb"] = d["y_wf"] - c["web_t"]
    d["pi_x0"] = -(x0 + x1) / 2
    d["pi_y0"] = d["y_wb"] - c["pi_gap"] - pi["size"][1]
    d["z_pi_bot"] = c["base_t"] + c["standoff"]
    d["z_pi_top"] = d["z_pi_bot"] + pi["pcb_t"]
    d["pi_holes"] = [(d["pi_x0"] + x, d["pi_y0"] + y) for x, y in pi["holes"]]
    d["pi_bore"] = bore("M2_5")
    d["pi_boss_r"] = d["pi_bore"] / 2 + c["pi_boss_wall"]
    m25 = scr["M2_5"]
    # M2.5 down through the Pi, nut against the pocket ceiling; the tip may not leave the base's underside
    d["pi_screw"] = max(L for L in m25["lengths"] if L <= d["z_pi_top"] + 1e-9)
    tip = d["z_pi_top"] - d["pi_screw"]
    d["pi_pocket"] = dict(r=hexr(m25["nut_s"], c["nut_clear"]),
                          depth=max(m25["nut_m"] + c["nut_extra_min"], tip + c["thread_past_nut"] + m25["nut_m"]))
    d["pi_tip"] = tip
    d["z_gpio_top"] = d["z_pi_top"] + pi["gpio"][4]
    d["z_csi_top"] = d["z_pi_top"] + h_csi
    d["y_csi"] = d["pi_y0"] + (y0 + y1) / 2
    d["z_ribbon_run"] = d["z_gpio_top"] + c["gpio_clear"]

    # base: the Pi's port edges (y = pi_y0 and x = pi end) are flush or inside it; the column's front closes it
    d["base_x"] = (d["pi_x0"] - c["base_mx"], d["pi_x0"] + pi["size"][0] + c["base_mx"])
    d["base_y"] = (d["pi_y0"], c["cheek_r"])
    (bx0, bx1), (by0, by1) = d["base_x"], d["base_y"]
    fi = c["fix_inset"]
    d["fix_xy"] = [(bx0 + fi, by0 + fi), (bx1 - fi, by0 + fi), (bx0 + fi, by1 - fi), (bx1 - fi, by1 - fi)]
    d["fix_bore"] = bore("M4")

    # --- carrier, in its own print frame: back face on the bed at z = 0, +z forward (asm +Y at tilt 0), +y up (asm
    # +Z), x = -asm X. The hinge axis is at (y, z) = (0, knuckle_y / 2). ---------------------------------------------
    ky, kz = c["knuckle"]
    d["hinge_bore"] = bore("M3")
    d["k_axis_z"] = ky / 2
    d["w_k"] = d["inner"] - 2 * c["clamp_gap"]
    d["r_sweep"] = math.hypot(ky / 2, kz / 2)                         # knuckle corners about the axis
    d["r_cheek"] = math.hypot(c["cheek_r"], c["cheek_r"])             # side walls' far corner about the axis
    d["y_plate0"] = d["r_cheek"] + c["sweep_clear"]                   # the wide plate swings outside the walls
    m2 = scr["M2"]
    tb0, tb1 = cam["pcb_t"]
    d["cam_bore"] = bore("M2")
    d["cam_boss_r"] = d["cam_bore"] / 2 + c["cam_boss_wall"]
    # M2 from the camera front into a nut against its pocket ceiling, the tip inside the pocket for any board:
    #   tip = t_p + gap + tb - L in [0, depth - nut_m - thread_past_nut],  t_p = depth + pocket_web
    d["cam_screw"] = _screw_into_nut(c["pocket_web"] + c["cam_gap"] + tb1 + m2["nut_m"] + c["thread_past_nut"],
                                     m2["lengths"])
    depth = max(m2["nut_m"] + c["nut_extra_min"], d["cam_screw"] - c["pocket_web"] - c["cam_gap"] - tb0)
    d["cam_pocket"] = dict(r=hexr(m2["nut_s"], c["nut_clear"]), depth=depth)
    d["plate_t"] = depth + c["pocket_web"]
    d["cam_tips"] = [d["plate_t"] + c["cam_gap"] + tb - d["cam_screw"] for tb in (tb0, tb1)]
    d["z_cam_back"] = d["plate_t"] + c["cam_gap"]
    d["y_cam_bot"] = d["y_plate0"] + c["slot_bar"] + c["slot_h"]      # camera connector edge
    d["y_cam_top"] = d["y_cam_bot"] + cam["size"][0]
    d["plate_x"] = cam["size"][1] / 2 + c["cam_margin"]
    d["y_plate1"] = d["y_cam_top"] + c["cam_margin"]
    # camera holes and lens in the carrier frame: drawing x runs down from the top, drawing y along x
    d["cam_holes_c"] = [(y - cam["size"][1] / 2, d["y_cam_top"] - x) for x, y in cam["holes"]]
    lx, ly = cam["lens_xy"]
    d["lens_c"] = (ly - cam["size"][1] / 2, d["y_cam_top"] - lx, d["z_cam_back"] + cam["depth"])
    d["slot_c"] = ((-d["inner"] / 2, d["inner"] / 2), (d["y_cam_bot"] - c["slot_h"], d["y_cam_bot"]))

    # --- hinge height from the lens height; asm positions at tilt 0 ------------------------------------------------
    d["hinge_z"] = c["lens_h"] - d["lens_c"][1]
    d["lens_asm0"] = (0.0, d["lens_c"][2] - d["k_axis_z"], d["hinge_z"] + d["lens_c"][1])
    d["z_web_top"] = d["hinge_z"] - d["r_sweep"] - c["sweep_clear"]
    d["z_col_top"] = d["hinge_z"] + c["cheek_r"]
    d["side_x"] = (d["inner"] / 2, d["inner"] / 2 + c["side_t"])
    d["window_z"] = (d["z_ribbon_run"] - c["window_h"] / 2, d["z_ribbon_run"] + c["window_h"] / 2)
    # hinge bolt: head on the -X wall, nut in a pocket in the +X wall's outer face
    m3 = scr["M3"]
    xo = d["side_x"][1]
    d["hinge_pocket"] = dict(r=hexr(m3["nut_s"], c["nut_clear"]), depth=m3["nut_m"] + c["nut_extra_min"])
    d["hinge_screw"] = _screw_into_nut(2 * xo - c["nut_extra_min"] + c["thread_past_nut"], m3["lengths"])
    d["hinge_tip_out"] = -xo + d["hinge_screw"] - xo                  # past the +X wall's outer face

    # --- ribbon path at tilt 0 (polyline), plus the arc the slot travels over the tilt range -------------------------
    slot_y = (d["slot_c"][1][0] + d["slot_c"][1][1]) / 2
    run = (d["z_ribbon_run"] - d["z_csi_top"]) + ((d["y_wf"] + d["y_cb"]) / 2 - d["y_csi"]) \
        + (d["hinge_z"] + slot_y - d["z_ribbon_run"]) + d["z_cam_back"] + cam["connector_h"]
    lo, hi = c["tilt_range"]
    d["tilt_allow"] = slot_y * math.radians(max(abs(lo), abs(hi)))
    d["ribbon_path"] = run + c["bend_allow"] + d["tilt_allow"]

    d["print_orientation"] = dict(
        stand=dict(up=(0, 0, 1), bed_face="base underside", bed_z=0.0,
                   known_overhangs=["M2.5 nut pocket ceilings (open to the bed): bridged annuli",
                                    f"ribbon window top: a {d['inner']:.0f} mm bridge",
                                    "hinge nut pocket roof: two faces 60 deg off vertical, 3 mm long"],
                   exceptions=[("Pi nut pocket ceiling", d["pi_pocket"]["depth"]), ("ribbon window top", d["window_z"][1]),
                               ("hinge nut pocket roof", d["hinge_z"] + 0.75 * d["hinge_pocket"]["r"])]),
        carrier=dict(up=(0, 0, 1), bed_face="carrier back", bed_z=0.0,
                     known_overhangs=["M2 nut pocket ceilings (open to the bed): bridged annuli"],
                     exceptions=[("M2 pocket ceiling", d["cam_pocket"]["depth"])]),
    )
    d["walls"] = {"Pi boss": c["pi_boss_wall"], "camera boss": c["cam_boss_wall"], "web": c["web_t"],
                  "side wall at the hinge nut": c["side_t"] - d["hinge_pocket"]["depth"],
                  "carrier over the M2 pocket": c["pocket_web"], "slot bar": c["slot_bar"]}
    return d


def validate(size: str = "V0") -> dict:
    """Raise on anything not buildable, buyable or usable. No warnings."""
    for name, v, tag, src in _tagged(_tables()):
        assert tag in TAGS and src, f"{name}: untagged or unsourced ({v!r})"
        assert tag not in ("PLACEHOLDER", "CONVENIENCE"), f"{name}: {tag} in a part that has to fit"
    d = derive(size)
    cam, scr = d["cam"], d["screws"]
    for name, w in d["walls"].items():
        assert w >= 2 * NOZZLE, f"{name} wall {w:.2f} < 2 x nozzle"
    # fasteners: lengths stocked, tips where they belong
    assert 0 <= d["pi_tip"] <= d["pi_pocket"]["depth"] - scr["M2_5"]["nut_m"] - d["thread_past_nut"] + 1e-9
    assert d["pi_pocket"]["depth"] < d["z_pi_bot"], "Pi nut pocket reaches the boss top"
    for t in d["cam_tips"]:
        assert -1e-9 <= t <= d["cam_pocket"]["depth"] - scr["M2"]["nut_m"] - d["thread_past_nut"] + 1e-9, \
            f"M2 tip {t:.2f} outside the pocket window"
    assert d["hinge_tip_out"] >= d["thread_past_nut"] - d["nut_extra_min"] - 1e-9
    assert d["cam_gap"] >= cam["connector_h"], "camera's back-side connector hits the carrier"
    # hinge: knuckle and plate swing clear of the web and walls
    assert d["y_cb"] - d["y_wf"] >= d["ribbon_gap"] - 1e-9
    assert d["z_web_top"] > d["window_z"][1] + 10, "column web too short"
    assert d["knuckle"][0] >= d["hinge_bore"] + 2 * 2.2 and d["knuckle"][1] >= d["hinge_bore"] + 2 * 2.2
    assert d["cheek_r"] >= d["hinge_pocket"]["r"] + WALL, "side wall too small round the hinge nut"
    assert d["w_k"] >= d["ribbon"]["width"] - 1e-9
    # slot and plate
    assert d["slot_c"][0][1] - d["slot_c"][0][0] >= d["ribbon"]["width"] + 2 * d["ribbon_clear"] - 1e-9
    assert d["plate_x"] >= max(abs(x) for x, _ in d["cam_holes_c"]) + d["cam_boss_r"] - 1e-9
    # the Pi stays on the base and its ports are not walled in
    (bx0, bx1), (by0, by1) = d["base_x"], d["base_y"]
    assert bx0 < d["pi_x0"] and d["pi_x0"] + d["pi"]["size"][0] < bx1
    assert abs(by0 - d["pi_y0"]) < 1e-9, "base must stop at the Pi's port edge"
    for x, y in d["fix_xy"]:
        assert not (d["pi_x0"] - d["fix_bore"] < x < d["pi_x0"] + d["pi"]["size"][0] + d["fix_bore"]), \
            "fixing hole under the Pi"
    assert d["pi_y0"] + d["pi"]["size"][1] + d["pi_gap"] <= d["y_wb"] + 1e-9
    # ribbon
    assert d["ribbon_path"] <= d["ribbon"]["length"] - d["ribbon_slack"], \
        f"ribbon path {d['ribbon_path']:.0f} > {d['ribbon']['length']:.0f} - {d['ribbon_slack']:.0f}"
    # bed
    for k, v in (("X", bx1 - bx0), ("Y", by1 - by0), ("Z", d["z_col_top"])):
        assert v <= BED[0], f"stand {k} {v:.0f} exceeds the bed"
    assert d["window_z"][0] > d["base_t"] + 2, "ribbon window runs into the base"
    return d


if __name__ == "__main__":
    d = validate()
    s = d["screws"]
    print(f"pi_cam_stand {d['size']}: ok")
    print(f"  lens {d['lens_h']:.0f} mm up at tilt 0, hinge axis z {d['hinge_z']:.1f}, column top {d['z_col_top']:.1f}")
    print(f"  base {d['base_x'][1] - d['base_x'][0]:.0f} x {d['base_y'][1] - d['base_y'][0]:.0f} x {d['base_t']:.0f}, "
          f"Pi underside z {d['z_pi_bot']:.1f}")
    print(f"  column U: inner {d['inner']:.1f}, walls {d['side_t']:.1f}, depth {d['y_cb'] - d['y_wb'] + d['cheek_r'] + d['knuckle'][0] / 2:.1f}, "
          f"web top z {d['z_web_top']:.1f}, ribbon window z {d['window_z'][0]:.1f}-{d['window_z'][1]:.1f}")
    print(f"  carrier: plate {2 * d['plate_x']:.1f} wide, {d['plate_t']:.1f} thick, knuckle {d['w_k']:.1f} wide "
          f"(clamp gap {d['clamp_gap']} each side)")
    print(f"  screws: 4 x M2x{d['cam_screw']:.0f} (camera; tips {', '.join(f'{t:.2f}' for t in d['cam_tips'])} into a "
          f"{d['cam_pocket']['depth']:.1f} pocket), 4 x M2.5x{d['pi_screw']:.0f} (Pi), 1 x M3x{d['hinge_screw']:.0f} "
          f"(hinge, tip {d['hinge_tip_out']:.1f} past the nut side), ISO 4032 nuts for each")
    print(f"  ribbon path {d['ribbon_path']:.0f} mm (incl. {d['tilt_allow']:.0f} tilt, {d['bend_allow']:.0f} bends) vs "
          f"{d['ribbon']['length']:.0f} ({RIBBON['part'][0]}); the stock {d['ribbon']['stock_length']:.0f} mm is too short")
