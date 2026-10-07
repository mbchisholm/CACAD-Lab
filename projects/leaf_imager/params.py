r"""Leaf NDVI imager v0 (SPEC.md): every number.

A Camera Module 2 NoIR on the roof's underside looks straight down at a leaf on a
drawer, 100 mm away, in a dark chamber. One flat PCB ring of SMD LEDs, five bands,
lights the leaf at 45 deg from 60 mm up and 60 mm out (CIE 45/0). The Pi 4B sits on
the roof. A white PTFE strip in the leaf plane, along one field edge, cancels LED
drift in every frame; a black, NIR-dark platen sits under the leaf.

This file holds the optics, the ring, the drive and the envelope the parts will be
drawn into. The parts themselves (chamber, ring clamp, roof, carrier, drawer,
hold-down) come next and read only `derive()`.

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

from cacad.registries.materials import FIT_CLEAR, NOZZLE

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
    strip_gap=(2.0, "DESIGN", "leaf area to strip: the hold-down frame's edge sits here"),
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
    ledge_w=(4.0, "DESIGN", "chamber ledge the PCB rim rests on; the clamp bears on the same band"),
    fit=(FIT_CLEAR, "DESIGN", "cacad.registries.materials.FIT_CLEAR: radial, PCB edge to the printed chamber"),
    # --- stack above the lens ---
    carrier_t=(3.0, "DESIGN", "camera carrier plate between the camera PCB back and the roof underside"),
    roof_t=(3.0, "DESIGN", "roof plate"),
    pi_standoff=(6.0, "DESIGN", "roof top to Pi PCB underside: air under the Pi"),
    trap_len=(25.0, "DESIGN", "extra ribbon the roof's light trap adds over a straight pass"),
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

SIZES = MappingProxyType(dict(V0=dict()))
ACTIVE_SIZES = ("V0",)

# Print orientation per part (PARAMS_CONVENTION rule 9), from SPEC's Parts table. Geometry not drawn yet.
PRINT_ORIENTATION = MappingProxyType(dict(
    chamber=dict(up="+Z", bed_face="bottom rim", known_overhangs=()),
    ring_clamp=dict(up="+Z", bed_face="clamp top", known_overhangs=()),
    roof=dict(up="+Z", bed_face="roof underside", known_overhangs=()),
    carrier=dict(up="-Z", bed_face="carrier face against the roof", known_overhangs=()),
    drawer=dict(up="+Z", bed_face="drawer bottom", known_overhangs=()),
    hold_down=dict(up="+Z", bed_face="frame underside", known_overhangs=()),
))

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
    return [("CAMERA", CAMERA), ("PI4B", PI4B), ("COMMON", COMMON)] + [(f"LEDS.{b}", LEDS[b]) for b in BANDS]


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
    # leaf area and strip inside field_use of the half-field; the strip along +Y
    ux, uy = c["field_use"] * hx, c["field_use"] * hy
    d["strip_y"] = (uy - c["strip_w"], uy)
    d["leaf_area"] = ((-ux, ux), (-uy, uy - c["strip_w"] - c["strip_gap"]))
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
    d["pcb_side"] = d["inner"] - 2 * c["fit"]                 # square PCB, round hole
    d["pcb_outer_band"] = d["pcb_side"] / 2 - (c["ring_r"] + max(pkg_max) / 2)   # LED edge to the PCB edge
    d["z_lens"] = c["wd"]
    d["z_roof"] = c["wd"] + cam["depth"] + c["carrier_t"]     # roof underside = chamber inside height

    # --- ribbon: camera connector (back of the board, lens on the axis, connector toward +X) to the Pi's CSI ---
    cam_conn = (cam["connector_x"][1] - cam["lens_xy"][0], 0.0)          # mouth at the board's connector edge
    x0, x1, y0, y1, csi_h = pi["csi"]
    csi = ((x0 + x1) / 2 - pi["size"][0] / 2, (y0 + y1) / 2 - pi["size"][1] / 2)   # Pi centred on the roof
    flat = abs(csi[0] - cam_conn[0]) + abs(csi[1] - cam_conn[1])
    rise = c["carrier_t"] + c["roof_t"] + c["pi_standoff"] + pi["pcb_t"] + csi_h
    d["ribbon_path"] = flat + rise + c["trap_len"] + c["bend_allow"]
    d["ribbon_budget"] = cam["ribbon_len"] - c["ribbon_slack"]

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
    return d


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
