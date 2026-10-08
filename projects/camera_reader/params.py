"""Camera absorbance reader v0 (ref/camera-reader-v0.md): every number.

A Pi 4B stands in elric's MakerWorld "Dev stand for Raspberry Pi and Camera
Module 2" (bought file, ref/stand/, Standard Digital File License: not
redistributed). Its Camera Module 2 NoIR looks horizontally out of the
stand's top pocket. The printed additions turn that into the reader's
optical bench, in the order the spec lays out:

    camera pocket -> snout (collar + baffled tunnel, ~150 mm of dark air)
      -> cell box: [REF window | 10 mm cuvette | 50 mm cuvette] against a
         masked datum wall -> 3 mm opal diffuser -> 30 mm white-lined mixing
         cavity -> 7 LEDs clamped by a retainer plate
      -> lid (light-trap skirt) on top, riser underneath.

The riser sets the box at lens height on the same table as the stand; the
collar locates the snout on the camera pocket's rim and carries no load.

Frame ASM: Z up from the table, Y along the optical axis (the camera looks
+Y), X across, so +X is the camera's right. Origin under the centre of the
stand's base. The stand's meshes come in their print frame ("flat": plate on
the bed, camera facing +z, Pi long axis along +y); `FLAT_TO_ASM` places them.

Tags (PARAMS_CONVENTION rule 5): VENDOR (sheet named, ref/vendor_sheets/),
NOTES (ref/camera-reader-v0.md, the author's unpublished spec), INFERRED (from what),
DESIGN, UNVERIFIED (estimate; ideation only).

    .venv/bin/python projects/camera_reader/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import (BED, FDM_HOLE_ALLOWANCE, FIT_CLEAR, INSERT_BORE_M3, INSERT_LEN_M3,
                                        INSERT_WALL_M3, NOZZLE, clearance_bore)

# ---------------------------------------------------------------------------
# The bought stand, measured on the designer's meshes (ref/stand/upright.stl,
# base.stl) by sectioning, in the flat print frame. INFERRED: the designer
# worked in inches (plate 0.100 in, walls 0.600 in), every level below is a
# round inch fraction. Each number names the feature it locates.
# ---------------------------------------------------------------------------
STAND = MappingProxyType(dict(
    tag="INFERRED", source="sections of ref/stand/*.stl (CaseForPi5WithCamera v7, elric, MakerWorld)",
    plate_x=(150.592, 212.060),       # upright plate width (flat x)
    plate_y=(44.500, 211.505),        # plate length; y = 44.5 is the end that drops into the base slot
    plate_t=2.540,                    # back plate, z 0..2.54
    pi_ledge_z=5.715,                 # Pi PCB back face rests here
    pi_wall_x=(153.130, 209.520),     # inner faces of the side walls: 56.39 for the 56.0 board
    pi_stop_y=69.260,                 # inner face of the two bottom stops: the Pi's SD-card end
    wall_h=15.240,                    # side walls and bottom stops top out here
    cam_outer_x=(181.070, 212.060), cam_outer_y=(182.290, 211.500),
    cam_inner_x=(183.610, 209.520), cam_inner_y=(184.830, 208.960),
    cam_top_z=12.700,                 # pocket rim (0.5 in), chamfered from 12.0
    cam_seat_z=6.223,                 # camera PCB back face rests on four pads
    cam_gap_x=(188.500, 204.630),     # the pocket's open side faces -y (ribbon exit)
    rear_hole_d=14.6, rear_hole_c=(196.56, 196.90),   # chamfered through-hole in the plate behind the camera
    base_size=(104.648, 48.260), base_h=14.605, base_top=(72.87, 16.48),
    base_c=(96.266, 128.000),         # base mesh centre (flat)
    slot=(61.722, 2.800), slot_floor_z=5.080,
))

# Flat (upright mesh) -> ASM: X = c - x, Y = z - plate_t/2, Z = y + dz. A proper rotation (det +1):
# Rz(180) . Rx(90). The plate stands centred in the base slot on the slot floor.
_UP_CX = (STAND["plate_x"][0] + STAND["plate_x"][1]) / 2
_UP_DZ = STAND["slot_floor_z"] - STAND["plate_y"][0]
FLAT_TO_ASM = MappingProxyType(dict(
    upright=dict(matrix=((-1, 0, 0), (0, 0, 1), (0, 1, 0)), offset=(_UP_CX, -STAND["plate_t"] / 2, _UP_DZ)),
    base=dict(matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), offset=(-STAND["base_c"][0], -STAND["base_c"][1], 0.0)),
))


def flat_to_asm(x: float, y: float, z: float) -> tuple:
    """A point of the upright mesh, flat print frame -> ASM."""
    return (_UP_CX - x, z - STAND["plate_t"] / 2, y + _UP_DZ)


# ---------------------------------------------------------------------------
# Bought parts. One row each.
# ---------------------------------------------------------------------------
PARTS = MappingProxyType(dict(
    pi4b=dict(tag="VENDOR", source="RP-008343-DS-1 raspberry-pi-4-mechanical-drawing.pdf (Raspberry Pi PIP)",
              size=(85.0, 56.0), corner_r=3.0, holes=((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)),
              hole_d=2.7,
              pcb_t=1.4,   # UNVERIFIED: not on the drawing; the commonly quoted Pi PCB thickness
              # Components: (x0, x1, y0, y1, height above PCB top). Heights are the drawing's Z labels (VENDOR);
              # extents are INFERRED, scaled off the same drawing (drawn, not dimensioned).
              parts=dict(gpio=(7.1, 57.9, 50.0, 55.0, 8.5), ethernet=(66.7, 87.9, 38.0, 53.7, 13.5),
                         usb_a=(70.4, 88.1, 20.3, 33.8, 16.0), usb_b=(70.4, 88.1, 2.4, 15.8, 16.0),
                         usb_c=(6.8, 15.4, -1.2, 6.4, 3.2), hdmi0=(22.8, 29.7, -1.2, 6.7, 3.0),
                         hdmi1=(36.2, 43.1, -1.2, 6.7, 3.0), audio=(50.5, 57.9, -2.7, 12.7, 6.0),
                         csi=(45.0, 48.8, 0.3, 22.8, 5.5), dsi=(1.5, 5.1, 16.7, 38.9, 5.5),
                         soc=(21.8, 36.6, 25.2, 40.1, 2.4))),
    cam_v2=dict(tag="VENDOR", source="RP-008149-DS-1 camera-module-2-mechanical-drawing.pdf; "
                                     "raspberrypi.com/documentation/accessories/camera.html (spec table)",
                # drawing frame: x from the hole edge to the connector edge (23.862), y along the 25 side
                size=(23.862, 25.0), corner_r=2.0, hole_d=2.2,
                holes=((2.0, 2.0), (14.5, 2.0), (2.0, 23.0), (14.5, 23.0)),
                lens_xy=(23.862 - 9.462, 12.5), lens_sq=8.5,
                depth=9.0,              # "around 25 x 24 x 9 mm" (docs table): PCB back to lens front
                fov=(62.2, 48.8),       # degrees, horizontal x vertical (docs table)
                focal=3.04,
                pcb_t=1.0,              # UNVERIFIED: not on the drawing
                conn=(23.862 - 5.5, 23.862, 2.0, 23.0, 2.5),   # UNVERIFIED height; x extent from the drawing's 5.5
                ribbon_w=16.0),         # UNVERIFIED: 15-way 1 mm FFC, usually quoted 16 mm wide
    cuvette_50=dict(tag="VENDOR", source="MSE Supplies LS4035 product page (H x W x D 45 x 12.5 x 52.5, inside "
                                         "width 10, 17.5 ml), msesupplies.com, 2026-10-06",
                    h=45.0, w=12.5, d=52.5, inside_w=10.0, path=50.0, volume_ml=17.5,
                    cap_h=8.0),         # UNVERIFIED: PTFE lid height above the rim
    cuvette_10=dict(tag="INFERRED", source="standard macro cuvette 12.5 x 12.5 x 45 (NOTES spec lists it; "
                                           "vendor TODO there). UNVERIFIED until a vendor is picked",
                    h=45.0, w=12.5, d=12.5, inside_w=10.0, path=10.0, cap_h=8.0),
    diffuser=dict(tag="DESIGN", source="NOTES spec: 3 mm opal (white) acrylic, cut to size by the builder",
                  t=3.0, t_tol=0.3),    # UNVERIFIED: cast acrylic sheet is commonly +/-10 %
    led=dict(tag="UNVERIFIED", source="generic 5 mm (T-1 3/4) LED; part numbers are an open item in the spec",
             body_d=5.0, flange_d=5.8, flange_t=1.0, lead_pitch=2.54, body_len=8.6),
    m3=dict(tag="STANDARD", source="ISO 7045 pan head, ISO 4032 nut", d=3.0, head_dk=5.6, head_k=2.4,
            nut_s=5.5, nut_m=2.4, lengths=(5, 6, 8, 10, 12, 16, 20, 25)),
))

# ---------------------------------------------------------------------------
# Rules and clearances. DESIGN unless tagged.
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(dict(
    wall=2.4,               # dark-box walls: 6 perimeters. Black PETG can pass NIR; the spec's felt/flocking lining
                            # does the light-tightness, the wall the stiffness
    fit=FIT_CLEAR,          # radial, printed part around a bought part (collar on the stand's rim, cuvette pockets,
                            # diffuser slot): materials.FIT_CLEAR
    lens_to_cells=150.0,    # NOTES spec "~150 mm dark air gap": lens front to the 50 mm cell's near face
    cell_pitch=16.0,        # window centres across X, camera's left to right: REF, 50 mm (on the axis: its rays run
                            # 52.5 mm through the liquid, so it gets the least parallax), 10 mm
    window=(7.0, 18.0),     # mask window W x H: every ray from the pupil to the window stays inside each cuvette's
                            # 10 mm inside width (validate), tall for pixels, under the fill
    window_zc=18.0,         # window centre above the cuvette's outside bottom: a part-filled cell still works
    pocket_depth=6.0,       # cuvette pockets in the rack floor
    floor_t=2.4,            # under the pockets
    side_margin=8.0,        # outermost pocket to the side wall, inside: room for the flange nuts (validate)
    front_margin=4.0,       # box front wall inside face to the 50 mm cell's near face
    cavity=30.0,            # NOTES spec: white-walled mixing cavity, diffuser to LED wall
    rib=2.0, rib_h=3.0,     # ribs (Y thickness, inward height) that hold the diffuser against the mask wall
    corbel=2.0,             # riser: flat band under its 45 deg inner corbel, which carries the box's walls
    head_room=4.0,          # cuvette cap top to the lid underside
    led_pitch=2.54,         # LED cluster on a 0.1 in grid (spacing between centres checked against the flange)
    led_grid=((0, 0), (-3, 0), (3, 0), (-2, -3), (2, -3), (-2, 3), (2, 3)),   # in grid units (X, Z)
    led_hole_clear=0.2,     # diametral, LED body in its hole (+ FDM_HOLE_ALLOWANCE)
    led_preload=0.2,        # retainer nubs squeeze the LED flanges this much: the LEDs are clamped
    lead_hole=4.0,          # retainer hole for the two leads (2.54 apart, 0.5 square)
    retainer_t=3.0,
    collar_overlap=8.0,     # collar length over the stand's camera rim
    collar_wall=2.4,
    ribbon_notch=(18.0, 6.0),   # W x depth (Y) notch in the collar floor for the camera ribbon; felt-flapped
    snout_wall=2.4,
    snout_margin=6.0,       # tunnel inside to the ray envelope at the far end, per side
    baffles=(0.30, 0.55, 0.80),   # baffle stations, fraction of the tunnel length from the collar
    baffle_margin=2.5,      # baffle aperture to the ray envelope, per side
    pupil_r=1.0,            # INFERRED: f/2.0, 3.04 mm focal -> ~0.76 mm entrance pupil radius, rounded up
    flange_t=3.0, flange_margin=8.0,
    lid_t=2.4, lid_skirt=8.0,   # lid plate bears on the walls and on the mask wall's top; skirt outside
    riser_lip=3.0, riser_rib=2.4,
))

SIZES = MappingProxyType(dict(V0=dict()))
ACTIVE_SIZES = ("V0",)

# Print orientation per part (PARAMS_CONVENTION rule 9). ASM axis that points up on the bed.
PRINT_ORIENTATION = MappingProxyType(dict(
    snout=dict(up="-Y", bed_face="flange back (+Y face)", known_overhangs=(
        "baffles: 45 deg undersides by construction", "front opening of the collar: open end, no roof")),
    cell_box=dict(up="+Z", bed_face="floor", known_overhangs=(
        "front opening and mask windows: bridges (front opening is the widest)",
        "LED holes, flange bolt holes, insert bores: teardrops")),
    lid=dict(up="-Z", bed_face="lid plate top", known_overhangs=()),
    retainer=dict(up="-Y", bed_face="plate back", known_overhangs=()),
    riser=dict(up="+Z", bed_face="feet", known_overhangs=()),
))


def derive(size: str = "V0", **overrides) -> dict:
    c = dict(COMMON, **SIZES[size], **overrides)
    S, P = STAND, PARTS
    pi, cam, c50, c10 = P["pi4b"], P["cam_v2"], P["cuvette_50"], P["cuvette_10"]
    d = dict(size=size, **c)
    w = c["wall"]

    # --- the stand, in ASM ---------------------------------------------------
    fx = lambda x: _UP_CX - x                # noqa: E731  flat x -> ASM X
    fy = lambda y: y + _UP_DZ                # noqa: E731  flat y -> ASM Z
    fz = lambda z: z - S["plate_t"] / 2      # noqa: E731  flat z -> ASM Y
    rng = lambda f, a: tuple(sorted((f(a[0]), f(a[1]))))   # noqa: E731
    d["plate_front_y"] = fz(S["plate_t"])
    d["cam_rim"] = dict(x=rng(fx, S["cam_outer_x"]), z=rng(fy, S["cam_outer_y"]), y_top=fz(S["cam_top_z"]),
                        inner_x=rng(fx, S["cam_inner_x"]), inner_z=rng(fy, S["cam_inner_y"]),
                        gap_x=rng(fx, S["cam_gap_x"]))
    # Camera board centred in the pocket; the connector edge is the open (low) side, the lens 9.462 from it.
    inner_z = d["cam_rim"]["inner_z"]
    cam_board_z0 = (inner_z[0] + inner_z[1]) / 2 - cam["size"][0] / 2
    d["cam"] = dict(back_y=fz(S["cam_seat_z"]), board_z=(cam_board_z0, cam_board_z0 + cam["size"][0]),
                    x_c=sum(d["cam_rim"]["inner_x"]) / 2)
    d["cam"]["front_y"] = d["cam"]["back_y"] + cam["depth"]
    d["lens"] = (d["cam"]["x_c"], d["cam"]["front_y"], cam_board_z0 + (cam["size"][0] - cam["lens_xy"][0]))
    LX, LY, LZ = d["lens"]
    d["pi"] = dict(back_y=fz(S["pi_ledge_z"]), x_c=fx(sum(S["pi_wall_x"]) / 2), z0=fy(S["pi_stop_y"]))
    d["pi"]["top_z"] = d["pi"]["z0"] + pi["size"][0]
    d["pi"]["front_y_max"] = d["pi"]["back_y"] + pi["pcb_t"] + max(v[4] for v in pi["parts"].values())

    # --- cells, windows, mask --------------------------------------------------
    y_near50 = LY + c["lens_to_cells"]
    y_datum = y_near50 + c50["d"]                 # every cuvette's far face, against the mask wall
    cell_bottom = LZ - c["window_zc"]
    d["cells"] = dict(
        ref=dict(x=LX - c["cell_pitch"], cuvette=None),
        c50=dict(x=LX, cuvette="cuvette_50", y=(y_near50, y_datum)),
        c10=dict(x=LX + c["cell_pitch"], cuvette="cuvette_10", y=(y_datum - c10["d"], y_datum)))
    d["y_datum"], d["cell_bottom"] = y_datum, cell_bottom
    ww, wh = c["window"]
    d["windows"] = {k: (v["x"] - ww / 2, v["x"] + ww / 2, LZ - wh / 2, LZ + wh / 2) for k, v in d["cells"].items()}
    d["fill_h"] = c50["volume_ml"] * 1000 / (c50["inside_w"] * c50["path"])   # liquid height in the 50 mm cell

    # --- cell box ---------------------------------------------------------------
    half_cells = c["cell_pitch"] + c50["w"] / 2 + c["fit"]
    inner_half_w = half_cells + c["side_margin"]
    bx = (LX - inner_half_w - w, LX + inner_half_w + w)
    y_front_in = y_near50 - c["fit"] - c["front_margin"]
    y_mask = (y_datum, y_datum + w)
    y_diff = (y_mask[1], y_mask[1] + P["diffuser"]["t"] + 2 * c["fit"])
    y_rib = (y_diff[1], y_diff[1] + c["rib"])
    y_led_in = y_diff[1] + c["cavity"]
    by = (y_front_in - w, y_led_in + w)
    floor_top = cell_bottom - c["pocket_depth"]
    bz0 = floor_top - c["floor_t"]
    cap_top = cell_bottom + max(c50["h"] + c50["cap_h"], c10["h"] + c10["cap_h"])
    bz1 = cap_top + c["head_room"]
    d["box"] = dict(x=bx, y=by, z=(bz0, bz1), floor_top=floor_top, y_front_in=y_front_in, y_mask=y_mask,
                    y_diff=y_diff, y_rib=y_rib, y_led_in=y_led_in, inner_half_w=inner_half_w)
    # Diffuser sheet, cut by the builder: full inner width and from the floor to the wall top, less the fit
    d["diffuser_cut"] = (2 * inner_half_w - 2 * c["fit"], bz1 - floor_top - c["fit"])

    # --- ray envelope: lens pupil to every window, at a given Y ---------------------
    win_hx = max(abs(v) for k in d["windows"] for v in (d["windows"][k][0] - LX, d["windows"][k][1] - LX))
    win_hz = wh / 2

    def ray_half(y):
        t = (y - LY) / (y_datum - LY)
        return (c["pupil_r"] + (win_hx - c["pupil_r"]) * t, c["pupil_r"] + (win_hz - c["pupil_r"]) * t)
    d["ray_half"] = ray_half
    d["win_half"] = (win_hx, win_hz)

    # --- snout ---------------------------------------------------------------
    rim = d["cam_rim"]
    sw, cw, f = c["snout_wall"], c["collar_wall"], c["fit"]
    y_c0 = rim["y_top"] - c["collar_overlap"]
    y_far = by[0] - c["flange_t"]                 # flange back face sits on the box front wall
    far_rx, far_rz = ray_half(y_far)
    rim_cz = sum(rim["z"]) / 2
    near_in = (rim["inner_x"][1] - rim["inner_x"][0], rim["inner_z"][1] - rim["inner_z"][0])
    far_in = (max(near_in[0], 2 * (far_rx + c["snout_margin"])), max(near_in[1], 2 * (far_rz + c["snout_margin"])))
    collar_in = (rim["x"][1] - rim["x"][0] + 2 * f, rim["z"][1] - rim["z"][0] + 2 * f)
    collar_out = (collar_in[0] + 2 * cw, collar_in[1] + 2 * cw)
    far_out = (far_in[0] + 2 * sw, far_in[1] + 2 * sw)
    fm = c["flange_margin"]
    flange = (far_out[0] + 2 * fm, far_out[1] + 2 * fm)
    L = y_far - rim["y_top"]
    d["snout"] = dict(y_collar=y_c0, y_stop=rim["y_top"], y_far=y_far, y_flange=(y_far, y_far + c["flange_t"]),
                      collar_in=collar_in, collar_out=collar_out, near_in=near_in, far_in=far_in, far_out=far_out,
                      near_c=(rim["inner_x"][0] + near_in[0] / 2, rim_cz), far_c=(LX, LZ), flange=flange,
                      length=y_far + c["flange_t"] - y_c0, tunnel_len=L,
                      baffles=[rim["y_top"] + s * L for s in c["baffles"]])

    def tunnel_in(y):
        t = (y - rim["y_top"]) / L
        cx = d["snout"]["near_c"][0] + (LX - d["snout"]["near_c"][0]) * t
        cz = rim_cz + (LZ - rim_cz) * t
        return (cx, cz, near_in[0] + (far_in[0] - near_in[0]) * t, near_in[1] + (far_in[1] - near_in[1]) * t)
    d["tunnel_in"] = tunnel_in
    d["baffle_ap"] = [(2 * (ray_half(y)[0] + c["baffle_margin"]), 2 * (ray_half(y)[1] + c["baffle_margin"]))
                      for y in d["snout"]["baffles"]]
    # Flange screws: four M3 at the flange corners, through flange and box front wall, nut inside the box.
    m3 = P["m3"]
    # Holes in the flange's side margins at the tunnel's height: clear of the rack floor and of the ray envelope.
    fx2, fz2 = far_out[0] / 2 + fm / 2, far_in[1] / 2
    d["flange_holes"] = [(LX + sx * fx2, LZ + sz * fz2) for sx in (-1, 1) for sz in (-1, 1)]
    d["m3_bore"] = clearance_bore("M3")
    grip = c["flange_t"] + w + m3["nut_m"] + 1.0
    d["flange_screw"] = min(L_ for L_ in m3["lengths"] if L_ >= grip)

    # --- LEDs and retainer -------------------------------------------------------
    led = P["led"]
    d["leds"] = [(LX + gx * c["led_pitch"], LZ + gz * c["led_pitch"]) for gx, gz in c["led_grid"]]
    d["led_hole"] = led["body_d"] + c["led_hole_clear"] + FDM_HOLE_ALLOWANCE
    # Insert bore: vendor length + 1 mm, stopping 1 mm short of the cavity (no light path through the wall).
    d["insert_pad"] = dict(w=INSERT_BORE_M3 + 2 * INSERT_WALL_M3, depth=INSERT_LEN_M3 + 1.0 - w + 1.0,
                           bore=INSERT_LEN_M3 + 1.0)
    led_xs, led_zs = [p[0] for p in d["leds"]], [p[1] for p in d["leds"]]
    ret_half = (max(led_xs) - min(led_xs)) / 2 + led["flange_d"] / 2 + 4.0
    ret_x = (LX - ret_half - d["insert_pad"]["w"] - 2.0, LX + ret_half + d["insert_pad"]["w"] + 2.0)
    ret_z = (min(led_zs) - led["flange_d"] / 2 - 4.0, max(led_zs) + led["flange_d"] / 2 + 4.0)
    y_ret = by[1] + d["insert_pad"]["depth"]
    d["retainer"] = dict(x=ret_x, z=ret_z, y=(y_ret, y_ret + c["retainer_t"]),
                         nub_h=d["insert_pad"]["depth"] - (led["flange_t"] - c["led_preload"]),
                         screws=[(ret_x[0] + d["insert_pad"]["w"] / 2 + 1.0, LZ),
                                 (ret_x[1] - d["insert_pad"]["w"] / 2 - 1.0, LZ)])
    rgrip = c["retainer_t"] + INSERT_LEN_M3 - 0.5
    d["retainer_screw"] = max(L_ for L_ in m3["lengths"] if L_ <= rgrip + 1.0)

    # --- lid and riser ---------------------------------------------------------------
    d["lid"] = dict(z_top=bz1 + c["lid_t"], skirt_in=(bx[1] - bx[0] + 2 * f, by[1] - by[0] + 2 * f))
    # The box drops into the riser's top lip (fit all round); the lip is a riser wall carried up riser_lip.
    d["riser"] = dict(z=(0.0, bz0), lip_top=bz0 + c["riser_lip"], x=(bx[0] - f - w, bx[1] + f + w),
                      y=(by[0] - f - w, by[1] + f + w))
    # ROI size: 2x2 binned raw is 1640 px across the 62.2 deg field (NOTES spec, VENDOR FOV)
    px_mm = 1640 / (2 * (y_datum - LY) * math.tan(math.radians(cam["fov"][0] / 2)))
    d["roi_px"] = (px_mm, int(c["window"][0] * c["window"][1] * px_mm ** 2))
    return d


def validate(size: str = "V0") -> dict:
    d = derive(size)
    P, c = PARTS, d
    LX, LY, LZ = d["lens"]
    # Lens: the vendor's depth puts the lens front beyond the stand's rim, inside the tunnel's stop face.
    assert d["cam"]["front_y"] > d["cam_rim"]["y_top"], "lens must clear the collar's stop face"
    # Light only through liquid: the window is narrower than every cuvette's inside width, and below the fill.
    assert c["window"][0] < min(P["cuvette_50"]["inside_w"], P["cuvette_10"]["inside_w"])
    assert c["window_zc"] + c["window"][1] / 2 + 4.0 <= d["fill_h"], "window top must sit under the 17.5 ml fill"
    # Parallax: every ray from the pupil to a cell's window stays inside that cuvette's inside width at its near and
    # far inner faces, and clears every other cuvette's outside.
    pr = c["pupil_r"]
    def ray_x(xw, xp, y):
        return xp + (xw - xp) * (y - LY) / (d["y_datum"] - LY)
    for k, cell in d["cells"].items():
        x0w, x1w = d["windows"][k][:2]
        rays = [(xw, LX + s * pr) for xw in (x0w, x1w) for s in (-1, 1)]
        for k2, other in d["cells"].items():
            if other["cuvette"] is None:
                continue
            cv = P[other["cuvette"]]
            gw = (cv["w"] - cv["inside_w"]) / 2
            ys = (other["y"][0] + gw, other["y"][1] - gw) if k2 == k else other["y"]
            for y in ys:
                xs = [ray_x(xw, xp, y) for xw, xp in rays]
                if k2 == k:
                    lo, hi = other["x"] - cv["inside_w"] / 2, other["x"] + cv["inside_w"] / 2
                    assert lo < min(xs) and max(xs) < hi, f"{k}: rays {min(xs):.2f}..{max(xs):.2f} leave the liquid at Y={y:.1f}"
                else:
                    lo, hi = other["x"] - cv["w"] / 2, other["x"] + cv["w"] / 2
                    assert max(xs) < lo or min(xs) > hi, f"{k}: rays cross the {k2} cuvette at Y={y:.1f}"
    # Flange nuts inside the box: corners clear of the side walls and the rack floor, behind no pocket.
    m3, b = P["m3"], d["box"]
    nut_r = m3["nut_s"] / math.sqrt(3)
    for hx, hz in d["flange_holes"]:
        assert b["x"][0] + c["wall"] + 0.5 <= hx - nut_r and hx + nut_r <= b["x"][1] - c["wall"] - 0.5, \
            f"flange nut at X={hx:.2f} hits a side wall"
        assert hz - nut_r >= b["floor_top"] + 0.5, f"flange nut at Z={hz:.2f} hits the rack floor"
    assert b["y_front_in"] + m3["nut_m"] <= d["cells"]["c50"]["y"][0] - c["fit"], "nut collides with a pocket"
    # LEDs: centres at least a flange apart.
    for i, a in enumerate(d["leds"]):
        for b in d["leds"][i + 1:]:
            assert math.dist(a, b) >= P["led"]["flange_d"] + 0.5, f"LEDs {a} {b} closer than a flange"
    assert d["led_hole"] < P["led"]["flange_d"], "LED flange must bear on the wall around its hole"
    assert d["retainer"]["nub_h"] > 0
    # Rays: the tunnel's far end and every baffle clear the envelope.
    for y, (ax, az) in zip(d["snout"]["baffles"], d["baffle_ap"]):
        cx, cz, tw, th = d["tunnel_in"](y)
        assert ax < tw and az < th, f"baffle at Y={y:.1f}: aperture {ax:.1f}x{az:.1f} is wider than the tunnel"
    # The cells fit across the box and the FOV covers every window.
    hx = math.degrees(math.atan(d["win_half"][0] / (d["y_datum"] - LY)))
    hz = math.degrees(math.atan(d["win_half"][1] / (d["y_datum"] - LY)))
    assert hx < P["cam_v2"]["fov"][0] / 2 and hz < P["cam_v2"]["fov"][1] / 2
    # Snout clears the Pi: tunnel bottom outside face over the Pi's top edge, with finger room for the USB plugs.
    snout_bottom = min(d["snout"]["near_c"][1] - d["snout"]["collar_out"][1] / 2,
                       LZ - d["snout"]["far_out"][1] / 2)
    assert snout_bottom - d["pi"]["top_z"] >= 15.0, "snout must clear the Pi's USB/Ethernet end"
    # Ribbon: notch at least the ribbon wide.
    assert c["ribbon_notch"][0] >= P["cam_v2"]["ribbon_w"] + 1.0
    # Printable: walls >= 2 nozzles; every part fits the bed.
    assert min(c["wall"], c["snout_wall"], c["collar_wall"]) >= 2 * NOZZLE
    b = d["box"]
    sizes = dict(snout=(d["snout"]["flange"][0], d["snout"]["flange"][1], d["snout"]["length"]),
                 cell_box=(b["x"][1] - b["x"][0], b["y"][1] - b["y"][0], b["z"][1] - b["z"][0]),
                 riser=(d["riser"]["x"][1] - d["riser"]["x"][0], d["riser"]["y"][1] - d["riser"]["y"][0],
                        d["riser"]["z"][1]))
    for k, s in sizes.items():
        assert all(v <= B for v, B in zip(sorted(s), sorted(BED))), f"{k} {s} does not fit the bed {BED}"
    d["print_sizes"] = sizes
    return d


if __name__ == "__main__":
    for s in SIZES:
        d = validate(s)
        r = lambda v: tuple(round(x, 2) for x in v)   # noqa: E731
        print(f"== camera_reader {s} {'(active)' if s in ACTIVE_SIZES else ''}")
        print(f"lens (X, Y, Z)            {r(d['lens'])}   optical axis {d['lens'][2]:.1f} mm above the table")
        print(f"camera rim Y top          {d['cam_rim']['y_top']:.2f}   lens front Y {d['cam']['front_y']:.2f}")
        print(f"Pi PCB back Y             {d['pi']['back_y']:.2f}   Pi top edge Z {d['pi']['top_z']:.2f}")
        print(f"cells: near face (50 mm)  Y {d['cells']['c50']['y'][0]:.2f}   datum/mask Y {d['y_datum']:.2f}")
        for k, v in d["cells"].items():
            print(f"   {k:4s} X {v['x']:7.2f}  window {r(d['windows'][k])}")
        print(f"cell bottom Z {d['cell_bottom']:.2f}   50 mm fill height {d['fill_h']:.1f}")
        print(f"ROI: {d['roi_px'][0]:.2f} px/mm at the datum, {d['roi_px'][1]} px per window (2x2 binned)")
        b = d["box"]
        print(f"cell box X {r(b['x'])} Y {r(b['y'])} Z {r(b['z'])}")
        print(f"diffuser cut {r(d['diffuser_cut'])} x {PARTS['diffuser']['t']} opal acrylic")
        s_ = d["snout"]
        print(f"snout: collar Y {s_['y_collar']:.2f}..{s_['y_stop']:.2f}, tunnel {s_['tunnel_len']:.1f} long, "
              f"in {r(s_['near_in'])} -> {r(s_['far_in'])}, flange {r(s_['flange'])}")
        print(f"   baffles Y {[round(y, 1) for y in s_['baffles']]} apertures {[r(a) for a in d['baffle_ap']]}")
        print(f"   flange screws ISO 7045 M3x{d['flange_screw']} + ISO 4032 nut (x4)")
        print(f"LEDs (X, Z): {[r(p) for p in d['leds']]}  hole {d['led_hole']:.2f}")
        print(f"retainer {r(d['retainer']['x'])} Z {r(d['retainer']['z'])}, nubs {d['retainer']['nub_h']:.2f}, "
              f"M3x{d['retainer_screw']} into heat-set inserts (x2)")
        print(f"riser Z 0..{d['riser']['z'][1]:.1f}   lid top Z {d['lid']['z_top']:.1f}")
        print(f"print sizes {{{', '.join(f'{k}: {r(v)}' for k, v in d['print_sizes'].items())}}}")
