r"""Leaf NDVI imager v0 (SPEC.md): every number.

A Camera Module 2 NoIR on the roof's underside looks straight down at a leaf on the
base, 100 mm away, in a dark chamber that lifts off the base. One flat PCB ring of SMD
LEDs, five bands, lights the leaf at 45 deg from 60 mm up and 60 mm out (CIE 45/0). The Pi 4B sits on
the roof. A white PTFE strip in the leaf plane, along one field edge, cancels LED
drift in every frame; a black, NIR-dark platen sits under the leaf.

This file holds the optics, the ring, the drive and the envelope the parts will be
drawn into. The printed parts (base, chamber, hold-down, roof, carrier) read only
`derive()`.

Frame: Z up, Z = 0 the leaf plane (platen top, PTFE strip face). Origin on the
optical axis. +X along the field's long side (the sensor's 3280 px). The strip runs
along the field's +Y edge.

            roof underside   z = z_roof
            camera carrier   (carrier_t)
            camera PCB back  z = wd + cam depth
            lens front       z = wd (100)
              |   view cone, 62.2 x 48.8 deg
     ring PCB [=====]   [=====]   underside z = z_pcb; LED faces at ring_h and up
              |  LEDs on r = 60, aimed by position: 45 deg to the field centre
     leaf plane ---------------- z = 0, platen + PTFE strip

Every input is a (value, TAG, source) triple; validate() refuses an untagged one and
fails on any PLACEHOLDER or CONVENIENCE it uses (PARAMS_CONVENTION rule 5).

    STANDARD     a published standard (named)
    VENDOR       published by the vendor of the part used (sheet named)
    INFERRED     follows from a published number, not stated (says from what)
    DESIGN       this model's choice; the part that meets it tolerates it
    CONVENIENCE  set to draw the model, awaits derivation
    PLACEHOLDER  drawn for a part whose geometry is unknown

    .venv/bin/python projects/leaf_imager/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import (BED, FDM_HOLE_ALLOWANCE, FIT_CLEAR, FLOOR, INSERT_BORE_M3, INSERT_DEPTH_M3,
                                        INSERT_LEN_M3, INSERT_WALL_M3, LAYER, NOZZLE, WALL)

STATUS = "passes"   # concept | passes | printed | parked

TAGS = ("STANDARD", "VENDOR", "INFERRED", "DESIGN", "CONVENIENCE", "PLACEHOLDER")

_RPI_DOCS = "raspberrypi.com/documentation/accessories/camera.html, hardware_specification.adoc (spec table)"
_CAM_DWG = "RP-008149-DS-1 camera-module-2-mechanical-drawing.pdf"
_PI_DWG = "RP-008343-DS-1 raspberry-pi-4-mechanical-drawing.pdf"

# ---------------------------------------------------------------------------
# Bought parts.
# ---------------------------------------------------------------------------
CAMERA = MappingProxyType(dict(
    # Camera Module 2 NoIR (IMX219). Drawing frame: x from the hole edge to the connector edge, y along the 25 side.
    size=((23.862, 25.0), "VENDOR", _CAM_DWG),
    holes=(((2.0, 2.0), (14.5, 2.0), (2.0, 23.0), (14.5, 23.0)), "VENDOR", _CAM_DWG),
    hole_d=(2.2, "VENDOR", _CAM_DWG),
    lens_xy=((23.862 - 9.462, 12.5), "VENDOR", _CAM_DWG + ": lens 9.462 from the connector edge"),
    connector_x=((23.862 - 5.5, 23.862), "VENDOR", _CAM_DWG + ": 5.5 deep at the connector edge"),
    depth=(9.0, "VENDOR", _RPI_DOCS + ": 'around 25 x 24 x 9 mm', PCB back to lens front"),
    fov=((62.2, 48.8), "VENDOR", _RPI_DOCS + ": horizontal x vertical, degrees"),
    focal=(3.04, "VENDOR", _RPI_DOCS),
    f_number=(2.0, "VENDOR", _RPI_DOCS),
    pixel=(1.12e-3, "VENDOR", _RPI_DOCS + ": 1.12 um x 1.12 um"),
    sensor_px=((3280, 2464), "VENDOR", _RPI_DOCS),
    binned_px=((1640, 1232), "VENDOR", _RPI_DOCS + ": 2x2 binned mode"),
    focus_min=(100.0, "VENDOR", _RPI_DOCS + ": focus 'Adjustable', 'approx 10 cm to infinity'"),
    image_x=("board y", "INFERRED", "the image's long (3280 px) axis runs parallel to the connector edge: the module's "
                                    "normal landscape use, ribbon down. Sets the field's long side along assembly X"),
    ribbon_len=(150.0, "INFERRED", "raspberrypi.com Camera Module 2 product page: '15cm ribbon cable'; the NoIR page "
                                   "states none, and it is the same board"),
))

PI4B = MappingProxyType(dict(
    size=((85.0, 56.0), "VENDOR", _PI_DWG),
    holes=(((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)), "VENDOR", _PI_DWG),
    hole_d=(2.7, "VENDOR", _PI_DWG),
    pcb_t=(1.4, "INFERRED", "not on the drawing; the commonly quoted Pi PCB thickness (camera_reader params)"),
    # CSI connector (x0, x1, y0, y1, height): height is the drawing's Z label, extents scaled off the drawing
    csi=((45.0, 48.8, 0.3, 22.8, 5.5), "INFERRED", _PI_DWG + ": scaled, not dimensioned (camera_reader params)"),
    current_typ=(600.0, "VENDOR", "raspberrypi.com/documentation/computers/raspberry-pi.html: Pi 4B typical bare-board "
                                  "active current 600 mA"),
    supply=(3000.0, "VENDOR", "same page: recommended PSU 5 V / 3.0 A"),
))

# One row per band. Wavelengths in nm, currents in mA, Vf at the datasheet's test current, beam = full angle at 50 %
# intensity. pkg = (x, y, h) mm. Stock at order time is UNVERIFIED for every part (SPEC.md).
_OS = "look.ams-osram.com"
LEDS = MappingProxyType(dict(
    b450=dict(part=("ams-OSRAM OSLON SSL 120 GD CSSPM1.14", "VENDOR", f"{_OS}/m/5b1bbb68c11c5d82/original/GD-CSSPM1-14.pdf "
                                                                     "v1.4 2021-08-01; product page: full production"),
              peak=(445.0, "VENDOR", "GD-CSSPM1-14.pdf p3"), fwhm=(None, "VENDOR", "not stated"),
              beam=(120.0, "VENDOR", "p3"), vf=(2.85, "VENDOR", "p3, typ."), vf_max=(3.25, "VENDOR", "p3"),
              vf_at=(350.0, "VENDOR", "p3"), i_min=(100.0, "VENDOR", "p2"), i_max=(1000.0, "VENDOR", "p2"),
              pkg=((3.0, 3.0, 2.21), "VENDOR", "product page")),
    g525=dict(part=("Cree LED XLamp XP-E2 green XPEBGR-L1-0000-00K03", "VENDOR",
                    "downloads.cree-led.com/files/ds/x/XLamp-XPE2.pdf CLD-DS56 rev 25B, current order-code table"),
              peak=(530.0, "INFERRED", "CLD-DS56: dominant 525-535 (bins G3-G4); peak not tabulated, mid-bin used"),
              fwhm=(None, "VENDOR", "spectrum given only as a plot"),
              beam=(135.0, "VENDOR", "CLD-DS56: viewing angle royal blue, blue, green"),
              vf=(2.7, "VENDOR", "CLD-DS56 typ."), vf_max=(3.25, "VENDOR", "CLD-DS56"), vf_at=(350.0, "VENDOR", "CLD-DS56"),
              i_min=(0.0, "VENDOR", "CLD-DS56 states none"), i_max=(1500.0, "VENDOR", "CLD-DS56 DC forward current"),
              pkg=((3.45, 3.45, 2.0), "VENDOR", "CLD-DS56 mechanical dimensions (XP-E footprint); height UNVERIFIED")),
    r660=dict(part=("ams-OSRAM OSLON SSL 120 GH CSSPM1.24", "VENDOR", f"{_OS}/m/6196f85319e7edbd/original/GH-CSSPM1-24.pdf "
                                                                     "v1.15 2024-11-28; product page: full production"),
              peak=(660.0, "VENDOR", "GH-CSSPM1-24.pdf p4"), fwhm=(25.0, "VENDOR", "p4"),
              beam=(120.0, "VENDOR", "p4"), vf=(2.07, "VENDOR", "p4, typ."), vf_max=(2.60, "VENDOR", "p4"),
              vf_at=(350.0, "VENDOR", "p4"), i_min=(100.0, "VENDOR", "p3"), i_max=(1000.0, "VENDOR", "p3"),
              pkg=((3.0, 3.0, 1.88), "VENDOR", "product page")),
    fr730=dict(part=("ams-OSRAM OSLON Optimal GF CSSRML.24", "VENDOR", f"{_OS}/m/7658ecbd48b382fb/original/GF-CSSRML-24.pdf "
                                                                      "v1.3 2025-07-11; product page: full production"),
               peak=(727.0, "VENDOR", "GF-CSSRML-24.pdf p4"), fwhm=(30.0, "VENDOR", "p4"),
               beam=(120.0, "VENDOR", "p4"), vf=(1.84, "VENDOR", "p4, typ."), vf_max=(2.20, "VENDOR", "p4"),
               vf_at=(350.0, "VENDOR", "p4"), i_min=(30.0, "VENDOR", "p3"), i_max=(1000.0, "VENDOR", "p3"),
               pkg=((3.0, 3.0, 2.17), "VENDOR", "product page")),
    nir850=dict(part=("Vishay VSMY3850X01", "VENDOR", "vishay.com/docs/80225/vsmy3850x01.pdf"),
                peak=(850.0, "VENDOR", "vsmy3850x01.pdf basic characteristics"), fwhm=(30.0, "VENDOR", "same"),
                beam=(120.0, "VENDOR", "product summary: phi = +/-60 deg"), vf=(1.6, "VENDOR", "typ. at 100 mA"),
                vf_max=(1.9, "VENDOR", "at 100 mA"), vf_at=(100.0, "VENDOR", "basic characteristics"),
                i_min=(0.0, "VENDOR", "none stated"), i_max=(100.0, "VENDOR", "absolute maximum ratings: IF 100 mA"),
                pkg=((3.5, 2.8, 1.75), "VENDOR", "dimensions L x W x H")),
))
BANDS = tuple(LEDS)

# ---------------------------------------------------------------------------
# Design rules and choices.
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(dict(
    # --- optics ---
    wd=(100.0, "DESIGN", "SPEC: lens front to leaf plane; a whole basil or small lettuce leaf, veins resolved"),
    field_use=(0.90, "DESIGN", "SPEC validate 1: leaf area and strip inside 90 % of the half-field"),
    uniform_frac=(0.80, "DESIGN", "SPEC: uniformity judged over 80 % of the field"),
    uniform_max=(2.0, "DESIGN", "SPEC validate 4: brightest : darkest <= 2 : 1"),
    beam_match=(15.0, "DESIGN", "SPEC: the same beam in every band; full angles within this of each other"),
    min_leaf=((100.0, 60.0), "DESIGN", "SPEC: a whole basil or small lettuce leaf"),
    strip_w=(8.0, "DESIGN", "SPEC: PTFE strip width, along the +Y field edge"),
    strip_clear=(1.0, "DESIGN", "hold-down frame's +Y bar shadow to the strip: the strip stays lit from every LED"),
    strip_t=(5.0, "DESIGN", "SPEC: PTFE >= 5 mm so its reflectance stops depending on the backing (Labsphere, Ghosh 2020)"),
    wall_clear=(2.0, "DESIGN", "field edge at the leaf plane to the chamber's inner wall: the camera sees no wall"),
    # --- ring ---
    ring_r=(60.0, "DESIGN", "SPEC: LED radius"),
    ring_h=(60.0, "DESIGN", "SPEC: lowest LED emitting face above the leaf plane; 45 deg at the field centre"),
    angle_tol=(1.0, "DESIGN", "SPEC validate 3: 45 +/- 1 deg"),
    per_band=(4, "DESIGN", "SPEC: N/E/S/W per band; bands interleaved at 360 / 20 = 18 deg"),
    pcb_t=(1.6, "DESIGN", "our own fabbed board: the fab's default FR-4"),
    pad_margin=(4.0, "DESIGN", "LED package edge to the PCB's inner or outer edge: pads, traces, a clamp band"),
    cone_margin=(3.0, "DESIGN", "view cone to the ring PCB's inner hole"),
    ledge_w=(4.0, "DESIGN", "chamber ledge the PCB rim rests on, 45 deg corbel under it"),
    ledge_t=(2.0, "DESIGN", "flat band of the ledge above its corbel"),
    boss_c=(8.0, "DESIGN", "square corner boss for an M3 insert: >= insert bore + 2 x vendor wall (7.2)"),
    pcb_engage_min=(3.0, "DESIGN", "M3 thread into the insert: one diameter"),
    fit=(FIT_CLEAR, "DESIGN", "cacad.registries.materials.FIT_CLEAR: radial, printed part to a bought or printed mate"),
    # --- chamber, base (platen), hold-down (z = 0 is the leaf plane). The chamber lifts off the base: a drawer would
    # need a full-width opening in the front wall to pass the pins, frame and strip, and its lintel a 140 mm bridge ---
    wall=(2.4, "DESIGN", "chamber walls: 6 perimeters; the black lining does the light-tightness (camera_reader rule)"),
    flock_t=(1.0, "DESIGN", "platen lining over the base top: its top is the leaf plane; a thinner foil "
                            "(Acktar ~0.1) sits within the 4.8 mm depth of field"),
    pocket_floor=(1.2, "DESIGN", "materials.FLOOR: base under the PTFE pocket"),
    rim_h=(8.0, "DESIGN", "base rim around the chamber's foot: locates it on all four sides, laps the joint"),
    rim_wall=(2.4, "DESIGN", "base rim thickness"),
    notch=((10.0, 8.0), "DESIGN", "petiole notch W x H above the leaf plane, chamber wall and base rim; foam-lined"),
    frame_bar=(4.0, "DESIGN", "hold-down frame bar width over the leaf's edge"),
    frame_t=(2.0, "DESIGN", "hold-down frame thickness: its 45 deg shadow is this wide"),
    pin_d=(4.0, "DESIGN", "frame locating pins on the base"),
    pin_h=(3.0, "DESIGN", "pin height above the base top"),
    pin_clear=(2.0, "DESIGN", "pin edge outside the field at the leaf plane: pins stay out of the picture"),
    tab_wall=(2.4, "DESIGN", "frame tab material around the pin hole"),
    tongue=((1.6, 2.0), "DESIGN", "chamber top tongue W x H into the roof's groove: locates the roof, laps the joint"),
    # --- stack above the lens ---
    cam_pcb_t=((0.8, 1.6), "DESIGN", "Camera Module 2 PCB thickness is unpublished; the M2 screws fit any in this range"),
    cam_gap_min=(4.0, "DESIGN", "camera PCB back to the carrier: room for a back-side FFC connector up to 3.5 mm "
                                "(unpublished; camera_reader estimated 2.5)"),
    cam_boss_wall=(1.6, "DESIGN", "materials.WALL around the M2 clearance bore"),
    carrier_t=(5.0, "DESIGN", "carrier plate: holds the M2 nut pockets (top) and M3 nut pockets (bottom)"),
    carrier_margin=(1.6, "DESIGN", "carrier edge beyond its outermost pocket or the camera board"),
    roof_t=(4.0, "DESIGN", "roof plate: groove depth + 1.6 web"),
    pi_standoff=(6.0, "DESIGN", "roof top to Pi PCB underside: air under the Pi"),
    pi_slot_clear=(4.0, "DESIGN", "ribbon slot to the Pi's SD-card end: room for the card's overhang (UNVERIFIED ~2.5)"),
    nut_clear=(0.3, "DESIGN", "hex pocket across flats over the nut (standoff_plate); nuts are captive, not pressed"),
    nut_extra=(dict(M2=1.6, M2_5=0.2, M3=1.2), "DESIGN", "pocket depth over the nut height: the screw-tip window"),
    thread_past_nut=(1.0, "DESIGN", "screw tip beyond the nut's far face"),
    ribbon_w=(16.0, "INFERRED", "15-way 1.0 mm pitch FFC, 15 mm of contacts plus edges; camera_reader used 16"),
    slot=((18.0, 4.0), "DESIGN", "roof ribbon slot X x Y: ribbon + 1 each side; a felt flap closes it"),
    ribbon_bend=(1.0, "DESIGN", "camera connector edge to the slot: the ribbon turns up here"),
    cable_hole=((60.0, 60.0, 6.0), "DESIGN", "LED wires through the roof (x, y, d): outside the Pi, over no boss"),
    trap_len=(25.0, "DESIGN", "extra ribbon allowance over a straight pass (felt flap, any detour)"),
    bend_allow=(10.0, "DESIGN", "ribbon taken up by its bends"),
    ribbon_slack=(20.0, "DESIGN", "SPEC validate 5: path <= ribbon - 20 mm"),
    # --- drive ---
    v_supply=(5.0, "DESIGN", "Pi 5 V rail, taken at 5.0 (the PSU is 5.1 V)"),
    vds_max=(0.10, "DESIGN", "MOSFET drop allowed at 400 mA: a requirement on the part still to pick"),
    i_led=(dict(b450=100.0, g525=100.0, r660=100.0, fr730=100.0, nir850=60.0), "DESIGN",
           "per LED: at least each part's minimum (OSRAM 100 mA); 850 under 0.7 x its 100 mA absolute max after the "
           "E24 resistor rounds the current up"),
    i_derate=(0.7, "DESIGN", "drive current <= this x the datasheet maximum"),
    r_rating=(0.5, "DESIGN", "resistor power rating, W"),
    r_load=(0.75, "DESIGN", "resistor dissipation <= this x its rating"),
    camera_current=(300.0, "DESIGN", "allowance for the camera module and a DS18B20, mA"),
))

# Bought fasteners: ISO 7045 pan head screws, ISO 4032 nuts, ISO 273 medium clearance (+ the FDM allowance when the
# hole is printed). Lengths are the ISO 7045 preferred ladder.
_ISO = "ISO 7045 (dk, k max), ISO 4032 (s, m), ISO 273 medium"
SCREWS = MappingProxyType(dict(
    M2=(dict(d=2.0, clear=2.4, head_dk=4.0, head_k=1.6, nut_s=4.0, nut_m=1.6, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
        "STANDARD", _ISO),
    M2_5=(dict(d=2.5, clear=2.9, head_dk=5.0, head_k=2.0, nut_s=5.0, nut_m=2.0, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
          "STANDARD", _ISO),
    M3=(dict(d=3.0, clear=3.4, head_dk=5.6, head_k=2.4, nut_s=5.5, nut_m=2.4, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
        "STANDARD", _ISO),
))

SIZES = MappingProxyType(dict(V0=dict()))
ACTIVE_SIZES = ("V0",)
PARTS = ("base", "chamber", "hold_down", "roof", "carrier")

E24 = (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1)


def _e24_floor(r: float) -> float:
    """Largest E24 value <= r: the current never falls under the design value."""
    dec = 10 ** math.floor(math.log10(r))
    return round(max(v * dec for v in E24 if v * dec <= r + 1e-9), 6)


def _tagged(tables) -> list:
    """Every input triple, as (table.key, value, tag, source)."""
    out = []
    for tname, t in tables:
        for k, v in t.items():
            out.append((f"{tname}.{k}", *v) if isinstance(v, tuple) and len(v) == 3 else (f"{tname}.{k}", v, None, None))
    return out


def _tables():
    return ([("CAMERA", CAMERA), ("PI4B", PI4B), ("COMMON", COMMON), ("SCREWS", SCREWS)]
            + [(f"LEDS.{b}", LEDS[b]) for b in BANDS])


def irradiance_ratio(beam_full: float, leds: list, half: tuple) -> float:
    """Brightest : darkest irradiance over a rectangle (+/-half) on the leaf plane, from downward-facing LEDs at
    (x, y, z) with a cos^m beam (m from the half-power half-angle). INFERRED model, SPEC's 'The LED ring' table."""
    m = math.log(0.5) / math.log(math.cos(math.radians(beam_full / 2)))
    n = 41
    vals = []
    for i in range(n):
        for j in range(n):
            px, py = -half[0] + 2 * half[0] * i / (n - 1), -half[1] + 2 * half[1] * j / (n - 1)
            e = 0.0
            for lx, ly, lz in leds:
                dx, dy = px - lx, py - ly
                d = math.sqrt(dx * dx + dy * dy + lz * lz)
                cos_t = lz / d                  # angle off the LED's axis = angle of incidence (both vertical)
                e += cos_t ** m * cos_t / (d * d)
            vals.append(e)
    return max(vals) / min(vals)


def derive(size: str = "V0", **overrides) -> dict:
    """Every number the part files and tests need. Overrides replace COMMON values (what-if only)."""
    raw = dict(COMMON, **SIZES[size])
    for k, v in overrides.items():
        assert k in raw, f"unknown override {k}"
        raw[k] = (v, "DESIGN", "override")
    c = {k: v[0] for k, v in raw.items()}
    cam = {k: v[0] for k, v in CAMERA.items()}
    pi = {k: v[0] for k, v in PI4B.items()}
    leds = {b: {k: v[0] for k, v in LEDS[b].items()} for b in BANDS}
    d = dict(size=size, **c, cam=cam, pi=pi, leds=leds)

    # --- optics -------------------------------------------------------------------------------------------
    hx, hy = (c["wd"] * math.tan(math.radians(a / 2)) for a in cam["fov"])
    d["field"] = (2 * hx, 2 * hy)
    d["um_px_binned"] = 1000 * d["field"][0] / cam["binned_px"][0]
    d["um_px_full"] = 1000 * d["field"][0] / cam["sensor_px"][0]
    mag = (c["wd"] / cam["focal"]) ** 2
    d["dof_full"] = 2 * cam["f_number"] * cam["pixel"] * mag           # 1 px blur, u >> f
    d["dof_binned"] = 2 * cam["f_number"] * 2 * cam["pixel"] * mag
    d["focus_margin"] = c["wd"] - cam["focus_min"]
    # leaf area, hold-down frame and strip inside field_use of the half-field; the strip along +Y, beyond the frame's
    # +Y bar and that bar's shadow. The longest shadow is from the LED across the ring (y = -ring_r), which sees the
    # bar's edge (taken at y = uy, conservative) at its shallowest elevation, not 45 deg.
    ux, uy = c["field_use"] * hx, c["field_use"] * hy
    d["frame_shadow"] = c["frame_t"] * (uy + c["ring_r"]) / (c["ring_h"] - c["frame_t"])
    d["strip_gap"] = c["frame_bar"] + d["frame_shadow"] + c["strip_clear"]
    d["strip_x"], d["strip_y"] = (-ux, ux), (uy - c["strip_w"], uy)
    d["leaf_area"] = ((-ux, ux), (-uy, uy - c["strip_w"] - d["strip_gap"]))
    d["leaf_size"] = (2 * ux, d["leaf_area"][1][1] - d["leaf_area"][1][0])

    # --- ring ---------------------------------------------------------------------------------------------
    pkg_max = max(leds[b]["pkg"][:2] for b in BANDS)
    h_max = max(leds[b]["pkg"][2] for b in BANDS)
    d["z_pcb"] = c["ring_h"] + h_max                         # PCB underside: the tallest package's face at ring_h
    d["pcb_hole_r"] = c["ring_r"] - max(pkg_max) / 2 - c["pad_margin"]
    n = len(BANDS) * c["per_band"]
    d["led_xyz"] = {}
    d["led_angle"] = {}
    for bi, b in enumerate(BANDS):
        z = d["z_pcb"] - leds[b]["pkg"][2]
        pts = []
        for k in range(c["per_band"]):
            a = math.radians(360.0 * (bi + k * len(BANDS)) / n)
            pts.append((c["ring_r"] * math.cos(a), c["ring_r"] * math.sin(a), z))
        d["led_xyz"][b] = pts
        d["led_angle"][b] = math.degrees(math.atan2(z, c["ring_r"]))
    uf = c["uniform_frac"]
    d["uniformity"] = {b: irradiance_ratio(leds[b]["beam"], d["led_xyz"][b], (uf * hx, uf * hy)) for b in BANDS}
    # view cone at the PCB underside: its rectangle's corner radius
    dz = c["wd"] - d["z_pcb"]
    d["cone_r_at_pcb"] = math.hypot(dz * math.tan(math.radians(cam["fov"][0] / 2)),
                                    dz * math.tan(math.radians(cam["fov"][1] / 2)))

    # --- chamber envelope (square inside), competing needs meet in max() ------------------------------------
    needs = {
        "ring PCB on its ledge": 2 * (c["ring_r"] + max(pkg_max) / 2 + c["pad_margin"] + c["ledge_w"] + c["fit"]),
        "field clear of the walls": d["field"][0] + 2 * c["wall_clear"],
    }
    d["inner_governed_by"], d["inner"] = max(needs.items(), key=lambda kv: kv[1])
    d["inner_needs"] = needs
    S, w, f = d["inner"], c["wall"], c["fit"]
    d["pcb_side"] = S - 2 * f                                  # square PCB, round hole
    d["pcb_outer_band"] = d["pcb_side"] / 2 - (c["ring_r"] + max(pkg_max) / 2)   # LED edge to the PCB edge
    d["outer"] = S + 2 * w
    scr = {k: v[0] for k, v in SCREWS.items()}
    d["screws"] = scr

    # --- z levels below the leaf plane ----------------------------------------------------------------------
    d["z_base_top"] = -c["flock_t"]                           # platen surface under the lining; the chamber stands here
    d["z_strip_floor"] = -c["strip_t"]                        # PTFE strip face at z = 0
    d["z_base_bot"] = d["z_strip_floor"] - c["pocket_floor"]
    d["z_rim_top"] = d["z_base_top"] + c["rim_h"]

    # --- ledge and corner insert bosses carry the PCB; M3 screws through its corner holes ----------------------
    d["z_ledge"] = (d["z_pcb"] - c["ledge_t"], d["z_pcb"])
    d["z_ledge_corbel_bot"] = d["z_ledge"][0] - c["ledge_w"]
    ai = S / 2 - c["boss_c"] / 2
    d["insert_xy"] = [(sx * ai, sy * ai) for sx in (-1, 1) for sy in (-1, 1)]
    d["boss_block_h"] = INSERT_DEPTH_M3 + FLOOR
    d["z_boss_corbel_bot"] = d["z_pcb"] - d["boss_block_h"] - c["boss_c"]
    d["insert_wall"] = c["boss_c"] / 2 - INSERT_BORE_M3 / 2
    d["pcb_hole_d"] = scr["M3"]["clear"]                       # drilled in FR-4: no FDM allowance
    room = INSERT_DEPTH_M3 - 0.5 + c["pcb_t"]
    fits = [L for L in scr["M3"]["lengths"] if c["pcb_t"] + c["pcb_engage_min"] <= L <= room]
    d["pcb_screw"] = max(fits) if fits else None
    d["pcb_engage"] = d["pcb_screw"] - c["pcb_t"] if d["pcb_screw"] else None

    # --- chamber: open tube on the base, tongue on top, petiole notch in the front wall ------------------------
    nw, nh = c["notch"]
    d["notch_x"], d["notch_z"] = (-nw / 2, nw / 2), (d["z_base_top"], nh)
    d["z_cam_back"] = c["wd"] + cam["depth"]

    # --- carrier: camera bosses under it, M2 nuts in its top, M3 nuts (roof screws) in its bottom --------------
    # Camera board frame -> assembly: X = by - lens_by, Y = lens_bx - bx (connector edge toward -Y, image_x).
    lbx, lby = cam["lens_xy"]
    to_asm = lambda bx, by: (by - lby, lbx - bx)               # noqa: E731
    d["cam_holes"] = [to_asm(*h) for h in cam["holes"]]
    d["cam_xy"] = ((-lby, cam["size"][1] - lby), (lbx - cam["size"][0], lbx))   # board footprint, assembly X, Y
    d["cam_conn_y"] = lbx - cam["connector_x"][1]              # the connector edge: the ribbon leaves toward -Y
    m2, m3, m25 = scr["M2"], scr["M3"], scr["M2_5"]
    hexr = lambda s_, cl=c["nut_clear"]: (s_ + cl) / (2 * math.cos(math.radians(30)))   # noqa: E731
    d["cam_bore"] = m2["clear"] + FDM_HOLE_ALLOWANCE
    d["cam_boss_r"] = d["cam_bore"] / 2 + c["cam_boss_wall"]
    d["m2_pocket"] = dict(r=hexr(m2["nut_s"]), depth=m2["nut_m"] + c["nut_extra"]["M2"])
    d["m3_pocket"] = dict(r=hexr(m3["nut_s"]), depth=m3["nut_m"] + c["nut_extra"]["M3"])
    d["m25_pocket"] = dict(r=hexr(m25["nut_s"]), depth=m25["nut_m"] + c["nut_extra"]["M2_5"])
    # camera gap: raised in layer steps from its minimum until one stocked M2 fits every PCB thickness in range:
    # tip past the nut's far face at the thickest board, tip no higher than the carrier top at the thinnest
    t0, t1 = c["cam_pcb_t"]
    gap, d["cam_screw"] = c["cam_gap_min"], None
    for _ in range(100):
        lo = t1 + gap + c["carrier_t"] - d["m2_pocket"]["depth"] + m2["nut_m"]
        hi = t0 + gap + c["carrier_t"]
        ok = [L for L in m2["lengths"] if lo - 1e-9 <= L <= hi + 1e-9]
        if ok:
            d["cam_screw"] = ok[0]
            break
        gap = round(gap + LAYER, 6)
    d["cam_gap"] = gap
    d["cam_gap_governed_by"] = "back-side connector room" if gap == c["cam_gap_min"] else "stocked M2 length"
    d["z_carrier"] = (d["z_cam_back"] + gap, d["z_cam_back"] + gap + c["carrier_t"])
    d["z_roof"] = d["z_carrier"][1]                            # roof underside = chamber wall top
    d["z_roof_top"] = d["z_roof"] + c["roof_t"]
    (cx0, cx1), (cy0, cy1) = d["cam_xy"]
    d["m3_carrier_xy"] = [(sx * (cx1 + c["carrier_margin"] + d["m3_pocket"]["r"]),
                           sum(y for _, y in d["cam_holes"]) / len(d["cam_holes"])) for sx in (-1, 1)]
    hx_c = d["m3_carrier_xy"][1][0] + d["m3_pocket"]["r"] + c["carrier_margin"]
    hy0 = min(y for _, y in d["cam_holes"]) - d["cam_boss_r"] - c["carrier_margin"]
    hy1 = max(cy1, max(y for _, y in d["cam_holes"]) + d["cam_boss_r"]) + c["carrier_margin"]
    d["carrier_xy"] = ((-hx_c, hx_c), (hy0, hy1))
    stack = c["roof_t"] + c["carrier_t"]
    ok = [L for L in m3["lengths"] if stack - d["m3_pocket"]["depth"] + m3["nut_m"] - 1e-9 <= L <= stack + 1e-9]
    d["roof_screw"] = ok[0] if ok else None
    d["m3_bore"] = m3["clear"] + FDM_HOLE_ALLOWANCE

    # --- roof: groove over the tongue, ribbon slot, Pi bosses (nut at the top), cable hole -----------------------
    tw, th = c["tongue"]
    d["tongue_z"] = (d["z_roof"], d["z_roof"] + th)
    d["groove"] = dict(w=tw + 2 * f, depth=th + f)
    d["roof_web"] = c["roof_t"] - d["groove"]["depth"]
    sw, sd = c["slot"]
    d["slot_y"] = (d["cam_conn_y"] - c["ribbon_bend"] - sd, d["cam_conn_y"] - c["ribbon_bend"])
    d["slot_x"] = (-sw / 2, sw / 2)
    # Pi rotated +90 deg about Z: its long axis along Y, its SD-card end (x = 0) facing the slot, the CSI connector
    # on the ribbon's line (X = 0). Pi frame -> assembly: X = pi_xc - (y - W/2), Y = pi_y0 + x.
    x0, x1, y0, y1, csi_h = pi["csi"]
    W = pi["size"][1]
    d["pi_xc"] = (y0 + y1) / 2 - W / 2
    d["pi_y0"] = d["slot_y"][1] + c["pi_slot_clear"]
    pi_asm = lambda px, py: (d["pi_xc"] - (py - W / 2), d["pi_y0"] + px)   # noqa: E731
    d["pi_to_asm"] = pi_asm
    d["pi_holes"] = [pi_asm(*h) for h in pi["holes"]]
    d["pi_xy"] = ((d["pi_xc"] - W / 2, d["pi_xc"] + W / 2), (d["pi_y0"], d["pi_y0"] + pi["size"][0]))
    d["z_pi_bot"] = d["z_roof_top"] + c["pi_standoff"]
    d["z_pi_top"] = d["z_pi_bot"] + pi["pcb_t"]
    d["pi_boss_r"] = d["m25_pocket"]["r"] + WALL
    d["pi_bore"] = m25["clear"] + FDM_HOLE_ALLOWANCE
    need = pi["pcb_t"] + d["m25_pocket"]["depth"] + c["thread_past_nut"]
    ok = [L for L in m25["lengths"] if L >= need - 1e-9]
    d["pi_screw"] = ok[0] if ok else None
    d["pi_bore_depth"] = d["pi_screw"] - pi["pcb_t"] + 0.5      # blind from the boss top: no hole into the chamber
    d["pi_bore_room"] = c["pi_standoff"] + c["roof_t"] - FLOOR

    # --- base (platen), hold-down frame ---------------------------------------------------------------------------
    d["base_half"] = d["outer"] / 2 + f + c["rim_wall"]         # square base, rim all round
    d["rim_in"] = d["outer"] / 2 + f
    d["strip_pocket"] = dict(x=(-ux - f, ux + f), y=(d["strip_y"][0] - f, d["strip_y"][1] + f),
                             z=(d["z_strip_floor"], d["z_base_top"]))
    (lx0, lx1), (ly0, ly1) = d["leaf_area"]
    fb = c["frame_bar"]
    d["frame"] = dict(x=(lx0 - fb, lx1 + fb), y=(ly0 - fb, ly1 + fb), z=(0.0, c["frame_t"]), window=d["leaf_area"])
    fcy = (d["frame"]["y"][0] + d["frame"]["y"][1]) / 2
    d["pin_x"] = hx + c["pin_clear"] + c["pin_d"] / 2
    d["pins"] = [(sx * d["pin_x"], fcy) for sx in (-1, 1)]
    d["pin_z"] = (d["z_base_top"], d["z_base_top"] + c["pin_h"])
    d["tab_hole_d"] = c["pin_d"] + 2 * f
    tr = d["tab_hole_d"] / 2 + c["tab_wall"]
    d["tabs"] = [dict(x=tuple(sorted((sx * (lx1 + fb), sx * (d["pin_x"] + tr)))), y=(fcy - tr, fcy + tr))
                 for sx in (-1, 1)]
    d["flock"] = dict(x=(-S / 2 + f, S / 2 - f), y=(-S / 2 + f, S / 2 - f))   # lining inside the chamber's foot

    # --- ribbon: connector edge -> slot -> up past the Pi's end -> over the Pi to the CSI connector ---------------
    slot_cy = sum(d["slot_y"]) / 2
    run = d["cam_conn_y"] - slot_cy
    rise = d["z_pi_top"] + csi_h - d["z_cam_back"]
    over = pi_asm((x0 + x1) / 2, (y0 + y1) / 2)[1] - slot_cy
    d["ribbon_parts"] = dict(run=run, rise=rise, over=over, bends=c["bend_allow"], trap=c["trap_len"])
    d["ribbon_path"] = sum(d["ribbon_parts"].values())
    d["ribbon_budget"] = cam["ribbon_len"] - c["ribbon_slack"]

    # --- print orientation (PARAMS_CONVENTION rule 9): exceptions are declared bridges, by z -------------------
    d["print_orientation"] = dict(
        base=dict(up=(0, 0, 1), bed_face="base bottom", bed_z=d["z_base_bot"], known_overhangs=[], exceptions=[]),
        chamber=dict(up=(0, 0, 1), bed_face="wall bottom edge", bed_z=d["z_base_top"],
                     known_overhangs=["petiole notch top: a 10 mm bridge"], exceptions=[("notch top", nh)]),
        hold_down=dict(up=(0, 0, 1), bed_face="frame underside", bed_z=0.0, known_overhangs=[], exceptions=[]),
        roof=dict(up=(0, 0, 1), bed_face="roof underside", bed_z=d["z_roof"],
                  known_overhangs=["groove ceiling: a 2.4 mm bridge"],
                  exceptions=[("groove ceiling", d["z_roof"] + d["groove"]["depth"])]),
        carrier=dict(up=(0, 0, -1), bed_face="carrier top, against the roof", bed_z=d["z_roof"],
                     known_overhangs=["M2 nut pocket ceilings (open to the bed): bridged annuli"],
                     exceptions=[("M2 pocket ceiling", d["z_roof"] - d["m2_pocket"]["depth"])]),
    )
    d["bed"] = BED
    d["max_overhang_deg"] = 45.0

    # --- drive: one MOSFET per band, one resistor per LED ----------------------------------------------------
    d["drive"] = {}
    for b in BANDS:
        L, i = leds[b], c["i_led"][b]
        r_ideal = (c["v_supply"] - L["vf"] - c["vds_max"]) / (i / 1000)
        r = _e24_floor(r_ideal)
        i_nom = 1000 * (c["v_supply"] - L["vf"] - c["vds_max"]) / r
        d["drive"][b] = dict(i_design=i, r=r, i_nom=i_nom, p_r=(i_nom / 1000) ** 2 * r,
                             p_led=i_nom / 1000 * L["vf"], band_ma=i_nom * c["per_band"])
    d["band_ma_max"] = max(v["band_ma"] for v in d["drive"].values())
    d["supply_ma"] = pi["current_typ"] + c["camera_current"] + d["band_ma_max"]
    return d


def validate(size: str = "V0", **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    rows = _tagged(_tables())
    for name, v, tag, src in rows:
        assert tag in TAGS and src, f"{name}: value/tag/source missing"
        assert tag not in ("PLACEHOLDER", "CONVENIENCE"), f"{name} is {tag}: unsourced, fails (cad-design-review rule 2)"
    d = derive(size, **overrides)
    cam, leds = d["cam"], d["leds"]

    # SPEC validate 1: field covers the leaf area and the strip, inside field_use of the half-field (by construction);
    # the leaf area is at least a whole leaf.
    assert d["leaf_size"][0] >= d["min_leaf"][0] and d["leaf_size"][1] >= d["min_leaf"][1], (
        f"leaf area {d['leaf_size'][0]:.1f} x {d['leaf_size'][1]:.1f} < minimum leaf {d['min_leaf']}")
    assert d["focus_margin"] >= 0, f"working distance {d['wd']} is inside the lens's closest focus {cam['focus_min']}"
    # SPEC validate 2: nothing of the ring in the view cone.
    assert d["pcb_hole_r"] >= d["cone_r_at_pcb"] + d["cone_margin"], (
        f"ring PCB hole r {d['pcb_hole_r']:.2f} < view cone {d['cone_r_at_pcb']:.2f} + margin {d['cone_margin']}")
    # SPEC validate 3: every LED sees the field centre at 45 +/- tol.
    for b, a in d["led_angle"].items():
        assert abs(a - 45.0) <= d["angle_tol"], f"{b}: LEDs at {a:.2f} deg to the field centre"
    # SPEC validate 4: uniformity per band, and the same beam in every band.
    for b, u in d["uniformity"].items():
        assert u <= d["uniform_max"], f"{b}: irradiance {u:.2f} : 1 over {d['uniform_frac']:.0%} of the field"
    beams = [leds[b]["beam"] for b in BANDS]
    assert max(beams) - min(beams) <= d["beam_match"], f"beams {min(beams)}..{max(beams)} deg differ by more than {d['beam_match']}"
    # SPEC validate 5: ribbon.
    assert d["ribbon_path"] <= d["ribbon_budget"], f"ribbon path {d['ribbon_path']:.1f} > {d['ribbon_budget']:.1f}"
    # Ring PCB: a band outside the LEDs for pads and the ledge, and a printable ledge.
    assert d["pcb_outer_band"] >= d["pad_margin"] + d["ledge_w"] - 1e-9, "no room on the PCB rim for the ledge"
    assert d["ledge_w"] >= 2 * NOZZLE
    # Drive: every band inside its part's ratings; resistors inside their rating; the supply holds.
    for b, v in d["drive"].items():
        L = leds[b]
        assert v["i_nom"] >= L["i_min"], f"{b}: {v['i_nom']:.0f} mA under the datasheet minimum {L['i_min']:.0f}"
        assert v["i_nom"] <= d["i_derate"] * L["i_max"], (
            f"{b}: {v['i_nom']:.0f} mA over {d['i_derate']} x the {L['i_max']:.0f} mA maximum")
        assert v["p_r"] <= d["r_load"] * d["r_rating"], f"{b}: resistor {v['p_r']:.2f} W over {d['r_load']} x {d['r_rating']} W"
        assert d["v_supply"] - L["vf_max"] - d["vds_max"] > 0, f"{b}: no headroom at the maximum Vf"
    assert d["supply_ma"] <= d["pi"]["supply"], f"5 V draw {d['supply_ma']:.0f} mA over the {d['pi']['supply']:.0f} mA supply"

    # --- mechanics ---
    assert d["insert_wall"] >= INSERT_WALL_M3, f"corner boss leaves {d['insert_wall']:.2f} around the insert"
    assert d["pcb_screw"] is not None, "no stocked M3 reaches one diameter into the insert without bottoming"
    for L, name in ((d["cam_screw"], "camera M2"), (d["roof_screw"], "roof-carrier M3"), (d["pi_screw"], "Pi M2.5")):
        assert L is not None, f"no stocked {name} screw fits its stack"
    assert d["pi_bore_depth"] <= d["pi_bore_room"], "Pi screw bore would open into the chamber"
    assert d["roof_web"] >= FLOOR, f"roof web over the groove {d['roof_web']:.2f} < {FLOOR}"
    for k in ("m2_pocket", "m3_pocket"):
        assert c_web(d, k) >= FLOOR, f"carrier web over the {k} {c_web(d, k):.2f} < {FLOOR}"
    # the ribbon turns up beyond the carrier, and the slot sits outside the carrier and the Pi
    assert d["slot_y"][1] < d["carrier_xy"][1][0], "ribbon slot under the carrier"
    assert d["slot_y"][1] < d["pi_xy"][1][0], "ribbon slot under the Pi"
    assert d["slot_x"][1] - d["slot_x"][0] >= d["ribbon_w"] + 1.0, "slot narrower than the ribbon"
    # Pi bosses and the cable hole over the roof, clear of the groove; Pi screws clear of the carrier
    half_in = d["inner"] / 2 - d["groove"]["w"]
    for x, y in d["pi_holes"]:
        assert abs(x) + d["pi_boss_r"] <= half_in and abs(y) + d["pi_boss_r"] <= half_in, f"Pi boss ({x:.1f}, {y:.1f}) off the roof"
    cxh, cyh, cd = d["cable_hole"]
    (px0, px1), (py0, py1) = d["pi_xy"]
    assert not (px0 - cd < cxh < px1 + cd and py0 - cd < cyh < py1 + cd), "cable hole under the Pi"
    assert max(abs(cxh), abs(cyh)) + cd / 2 <= half_in - 1.0, "cable hole over the wall or the groove"
    sx_, sy_ = d["insert_xy"][-1]   # the PCB corner screw the wires drop beside
    assert math.dist((abs(cxh), abs(cyh)), (sx_, sy_)) >= d["screws"]["M3"]["head_dk"] / 2 + cd / 2 + 1.0, \
        "LED wires drop onto a PCB corner screw head"
    # frame and pins inside the chamber's foot, pins out of the picture, the strip outside the frame and its shadow
    assert d["tabs"][1]["x"][1] <= d["inner"] / 2 - d["fit"] - 0.5, "frame tab past the chamber wall"
    assert d["pin_x"] - d["pin_d"] / 2 >= d["field"][0] / 2 + d["pin_clear"] - 1e-9
    assert d["frame"]["y"][1] + d["frame_shadow"] + d["strip_clear"] <= d["strip_y"][0] + 1e-9, "strip in the frame's shadow"
    assert d["frame"]["y"][0] >= d["flock"]["y"][0] and d["strip_pocket"]["y"][1] <= d["flock"]["y"][1]
    assert d["z_rim_top"] <= d["notch_z"][1], "rim taller than the chamber's petiole notch"
    # every part fits the bed
    for name, size_ in part_sizes(d).items():
        assert all(v <= B for v, B in zip(sorted(size_), sorted(d["bed"]))), f"{name} {size_} does not fit the bed"
    return d


def c_web(d: dict, pocket: str) -> float:
    """Carrier plate left over a nut pocket."""
    return d["carrier_t"] - d[pocket]["depth"]


def part_sizes(d: dict) -> dict:
    """Envelope of each printed part (X, Y, Z), for the bed check."""
    o = d["outer"]
    return dict(
        base=(2 * d["base_half"], 2 * d["base_half"], d["z_rim_top"] - d["z_base_bot"]),
        chamber=(o, o, d["tongue_z"][1] - d["z_base_top"]),
        hold_down=(d["tabs"][1]["x"][1] * 2, d["frame"]["y"][1] - d["frame"]["y"][0], d["frame_t"]),
        roof=(o, o, d["roof_t"] + d["pi_standoff"]),
        carrier=(d["carrier_xy"][0][1] * 2, d["carrier_xy"][1][1] - d["carrier_xy"][1][0], d["carrier_t"] + d["cam_gap"]),
    )


def report(size: str = "V0") -> str:
    d = derive(size)
    cam = d["cam"]
    r = lambda v: tuple(round(x, 2) for x in v)   # noqa: E731
    lines = [
        f"== leaf_imager {size} {'(active)' if size in ACTIVE_SIZES else ''}",
        f"camera: Camera Module 2 NoIR, lens {d['wd']:.0f} mm above the leaf "
        f"({d['focus_margin']:.0f} mm beyond its {cam['focus_min']:.0f} mm closest focus)",
        f"field {d['field'][0]:.1f} x {d['field'][1]:.1f} mm; {d['um_px_binned']:.0f} um/px binned, "
        f"{d['um_px_full']:.0f} um/px full; depth of field {d['dof_full']:.1f} mm full, {d['dof_binned']:.1f} mm binned",
        f"leaf area X {r(d['leaf_area'][0])} Y {r(d['leaf_area'][1])} = {d['leaf_size'][0]:.1f} x {d['leaf_size'][1]:.1f}; "
        f"PTFE strip Y {r(d['strip_y'])}, {d['strip_t']:.0f} mm thick",
        f"ring: {len(BANDS)} bands x {d['per_band']} LEDs on r {d['ring_r']:.0f}, PCB underside z {d['z_pcb']:.2f}, "
        f"square {d['pcb_side']:.1f} with hole r {d['pcb_hole_r']:.2f} (view cone r {d['cone_r_at_pcb']:.2f} there)",
        f"chamber inside {d['inner']:.1f} square x {d['z_roof']:.1f} high, governed by '{d['inner_governed_by']}' "
        + ", ".join(f"{k} {v:.1f}" for k, v in d["inner_needs"].items()),
        f"ribbon path {d['ribbon_path']:.1f} of {d['ribbon_budget']:.1f} allowed ({cam['ribbon_len']:.0f} ribbon)",
        "band    part                                              beam  angle  uniform   I mA   R ohm  P_R W  band mA",
    ]
    for b in BANDS:
        L, v = d["leds"][b], d["drive"][b]
        lines.append(f"{b:7s} {L['part']:49s} {L['beam']:5.0f} {d['led_angle'][b]:6.2f} {d['uniformity'][b]:6.2f}:1 "
                     f"{v['i_nom']:6.1f} {v['r']:7.1f} {v['p_r']:6.2f} {v['band_ma']:8.0f}")
    lines.append(f"5 V draw, worst band on: {d['supply_ma']:.0f} of {d['pi']['supply']:.0f} mA")
    return "\n".join(lines)


if __name__ == "__main__":
    for s in SIZES:
        try:
            validate(s)
            print(report(s), "\n  ok" + ("" if s in ACTIVE_SIZES else " (inactive)"))
        except AssertionError as e:
            print(report(s))
            print(f"{s}: FAIL: {e}")
