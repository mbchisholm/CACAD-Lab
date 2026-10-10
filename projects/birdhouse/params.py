r"""Solar ESP32-CAM nest box v0: every number.

A parametric rebuild of "Nisthaus Vogelhaus Nistkasten ESP32-CAM V1" (Juchala, Bambu/MakerWorld, CC BY-NC-SA; the
3MF is reference only, its meshes are not reused). Same architecture: a U-shaped body with a front panel that slides
up out of two jamb slots, a floor that drops in onto a ledge, a ceiling tray on the body top, and a roof cap over
the tray. Changes: a larger perch, a designed floor fit (clearance plus an elephant-foot chamfer), drain holes, a
hanging lug with a vertical bolt, and the tray became the electronics carrier: the ESP32-CAM face down over the nest,
two 850 nm IR LEDs beside the lens, an 18650, a solar charger with 5 V boost and a nano-power timer. A 6 V panel is
bonded to the cap's sloped top.

Frame: Z up, Z = 0 the body's bottom (its bed face). X across the front, origin on the centreline. -Y is the
front (entry hole), +Y the back (mounting lug).

            panel on the sloped cap top (slope deg, rising to the back)
     cap   /=================================\    eave (solid, sparse infill)
           |  ESP32-CAM  18650  bq25185  TPL  |    cap shoulder rests on the tray rim
     tray  [=====[lens]==[IR]===================]  z = body_h .. + tray_t
     body  |  |                              |  |  entry hole, perch on the front panel
           |  |  nest                        |  |
     floor |  [==========================]   |  |  floor_t on the ledge
     ledge [==]                          [==]      z = 0 .. ledge_t

Power (DESIGN.md has the wiring): panel -> bq25185 VIN; 18650 on the bq25185's JST; its boosted 5 V feeds the
TPL5110's VDD; the TPL5110's switched DRV feeds the ESP32-CAM's 5V pin. Every interval the timer powers the camera,
which boots, lights the IR LEDs for the exposure, takes and uploads a frame, then raises DONE and is switched off.

Every input is a (value, TAG, source) triple; validate() refuses an untagged one and fails on any PLACEHOLDER or
CONVENIENCE (PARAMS_CONVENTION rule 5). "UNVERIFIED" in a source marks an estimate: fine for ideation, never for fit.

    .venv/bin/python projects/birdhouse/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import BED, FDM_HOLE_ALLOWANCE, FIT_CLEAR, FLOOR, ISO_273, NOZZLE, WALL

STATUS = "concept"   # concept | passes | printed | parked

TAGS = ("STANDARD", "VENDOR", "INFERRED", "DESIGN", "CONVENIENCE", "PLACEHOLDER")

_REF = "Nisthaus ESP32-CAM V1 3MF (~/Downloads/Nisthaus.3mf), measured in FreeCAD 2026-10-07"
_AIT = "Ai-Thinker ESP32-CAM spec, as quoted by open-electronics.org/?p=25254 (original PDF not read)"
_RNT = "randomnerdtutorials.com/esp32-cam-ai-thinker-pinout (pinout figure)"
_BQ = "learn.adafruit.com/adafruit-bq25185-usb-dc-solar-charger-with-5v-boost-board (product 6106), pinouts page"

# ---------------------------------------------------------------------------
# Bought parts.
# ---------------------------------------------------------------------------
ESP32CAM = MappingProxyType(dict(
    size=((27.0, 40.5), "VENDOR", _AIT + ": 'footprint 27*40.5*4.5mm'"),
    height=(4.5, "VENDOR", _AIT + ": the 4.5 of 27*40.5*4.5, PCB plus the ESP32 shield"),
    pcb_t=(1.0, "INFERRED", "UNVERIFIED: a thin 2-layer board; only sets where the shield envelope starts"),
    lens_from_end=(9.2, "INFERRED", _REF + ": lens window centre in the original tray, relative to its board pocket"),
    lens_drop=(7.0, "INFERRED", "UNVERIFIED: OV2640 module and lens below the board's camera face; the window is "
                                "through the tray, so a longer lens only reaches further into it"),
    header_stack=(27.0, "DESIGN", "board back to the top of the wiring: 2.5 header spacer + 14 Dupont housing + "
                                  "10 for the wires to bend over"),
    supply_v=(5.0, "VENDOR", _AIT + ": 'power is supplied via the 5V pin'; RNT also advises the 5V pin"),
    active_ma=(180.0, "INFERRED", "Ai-Thinker spec, flash off, 180 mA @ 5 V (widely quoted; original PDF not read)"),
    sleep_ma=(6.0, "VENDOR", _AIT + ": 'deep-sleep current 6mA @ 5V min': why the timer cuts power instead"),
    pins=((("5V", "GND", "IO12", "IO13", "IO15", "IO14", "IO2", "IO4"),
           ("3V3", "IO16", "IO0", "GND", "VCC", "IO3/U0RXD", "IO1/U0TXD", "GND")), "INFERRED",
          _RNT + ": two 8-pin rows, listed from the 5V/3V3 end"),
    fov_diag=(66.0, "INFERRED", "UNVERIFIED: stock OV2640 lens, diagonal, as commonly listed"),
))

# Night: an OV2640 module without the IR-cut filter (sold as 'night vision 850 nm' on the same 24-pin FPC) and two
# 850 nm emitters. Birds do not see 850 nm (Cuthill 2000: avian cones end near 700 nm); the white flash LED (IO4)
# is never used.
IR_LED = MappingProxyType(dict(
    part=("Vishay TSHG6400", "VENDOR", "vishay.com/en/product/84636, tshg6400.pdf rev 1.5"),
    peak=(850.0, "VENDOR", "tshg6400.pdf"),
    half_angle=(27.0, "VENDOR", "tshg6400.pdf rev 1.5: phi = +/-27 deg (rev 1.2 said 22)"),
    body_d=(5.0, "VENDOR", "tshg6400.pdf: T-1 3/4, 5 mm"),
    flange_d=(5.8, "INFERRED", "T-1 3/4 flange, the usual 5.8 max; seats on the tray top"),
    length=(8.6, "INFERRED", "UNVERIFIED: T-1 3/4 body below the flange"),
    vf=(1.5, "VENDOR", "tshg6400.pdf, at 100 mA"),
    i_max=(100.0, "VENDOR", "tshg6400.pdf, IF DC"),
))

BQ25185 = MappingProxyType(dict(
    size=((25.0, 30.0, 6.0), "INFERRED", "UNVERIFIED: Adafruit 6106 listing, 'approximately 25 x 30 x 6 mm'; no fab print "
                                         "read. Held by its outline in a pocket, so its holes do not matter"),
    vin=((5.0, 18.0), "VENDOR", _BQ + ": VIN for solar or DC, 5-18 V"),
    charge_ma=(500.0, "VENDOR", _BQ + ": 1 A default; cut the rate jumper for 500 mA, which the 1.2 W panel cannot "
                                      "exceed anyway"),
    boost_ma=(1000.0, "VENDOR", _BQ + ": TPS61023 boost, 5 V at 1 A max"),
    en=("high", "VENDOR", _BQ + ": 'bring this pin low to disable the 5V output'"),
))

TPL5110 = MappingProxyType(dict(
    size=((19.3, 18.0, 4.5), "VENDOR", "adafruit.com/product/3435"),
    iq_ua=(20.0, "VENDOR", "adafruit.com/product/3435: ~20 uA with the project de-powered"),
    interval_s=((0.1, 7200.0), "VENDOR", "adafruit.com/product/3435: 100 ms to 2 h, trim pot or fixed resistor"),
    vdd=((3.0, 5.0), "VENDOR", "adafruit.com/product/3435: VDD 3-5 V"),
))

CELL = MappingProxyType(dict(
    part=("Samsung INR18650-30Q", "VENDOR", "Samsung 30Q spec; ~/Downloads/esp32-restock-list.md Pass 4"),
    mah=(3000.0, "VENDOR", "Samsung 30Q spec: 3000 mAh"),
    v_nom=(3.6, "VENDOR", "Samsung 30Q spec: 3.6 V nominal"),
    d=(18.5, "INFERRED", "18650 nominal diameter, max; protected cells run larger"),
))

HOLDER = MappingProxyType(dict(
    part=("Keystone 1042", "VENDOR", "digikey.com/en/products/detail/keystone-electronics/1042/2745668"),
    size=((77.05, 20.65, 14.86), "VENDOR", "Digi-Key listing for Keystone 1042: L x W x H"),
    cell_top=(20.0, "INFERRED", "UNVERIFIED: the cell's crown above the holder base (cell 18.5 on a ~1.5 floor)"),
))

PANEL = MappingProxyType(dict(
    part=("Adafruit 3809, 6 V 1 W", "VENDOR", "adafruit.com/product/3809"),
    size=((89.0, 113.0, 5.0), "VENDOR", "adafruit.com/product/3809: 113 x 89 x 5 mm; laid 89 across X"),
    p_peak=(1.2, "VENDOR", "adafruit.com/product/3809: peak power 1.2 W"),
    v_mp=(6.5, "VENDOR", "adafruit.com/product/3809: peak voltage 6.5 V"),
    cable=(260.0, "VENDOR", "adafruit.com/product/3809: 26 cm, 3.5 x 1.1 mm male DC plug"),
))

# ---------------------------------------------------------------------------
# Design rules and choices.
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(dict(
    # --- body (outline from the reference, everything else ours) ---
    outer=((100.0, 120.0), "INFERRED", _REF + ": body 100 x 120 without its lug"),
    body_h=(130.0, "INFERRED", _REF + ": body height"),
    wall=(3.2, "DESIGN", "2 x materials.WALL: an outdoor shell"),
    corner_r=(8.0, "DESIGN", "outer vertical edges, as the reference's rounded corners"),
    opening=(70.0, "INFERRED", _REF + ": front panel 69.8 wide between the jambs"),
    panel_t=(3.0, "DESIGN", "front panel"),
    groove_depth=(3.0, "DESIGN", "panel edge into each jamb slot"),
    jamb_skin=(WALL, "DESIGN", "materials.WALL each side of a jamb slot"),
    fit=(FIT_CLEAR, "DESIGN", "materials.FIT_CLEAR: radial, every sliding printed-to-printed joint"),
    ledge_w=(5.0, "DESIGN", "floor ledge inward from the walls and the front sill"),
    ledge_t=(3.0, "DESIGN", "floor ledge and front sill thickness, on the bed"),
    # --- floor ---
    floor_t=(4.0, "DESIGN", "floor plate"),
    foot_chamfer=(0.6, "DESIGN", "45 deg on the floor's bed edge: takes the elephant's foot (first layers squashed "
                                 "out ~0.2-0.4) out of the fit, the reason the reference's floor bound"),
    drain_d=(6.0, "DESIGN", "four drain and air holes through the floor, over the ledge opening"),
    drain_xy=((30.0, 35.0), "DESIGN", "drain holes at (+/-x, +/-y)"),
    # --- front panel ---
    hole_d=(38.0, "INFERRED", _REF + ": entry hole 37.8 (1.5 in, the bluebird standard)"),
    hole_z_panel=(91.7, "INFERRED", _REF + ": hole centre above the panel's bottom edge"),
    perch_d=(10.0, "DESIGN", "larger perch: a 10 mm rod (the reference has none worth the name)"),
    perch_len=(50.0, "DESIGN", "perch reach beyond the panel face"),
    perch_gap=(12.0, "DESIGN", "hole edge to the perch's top"),
    perch_collar=((18.0, 6.0), "DESIGN", "root cone dia x length: 34 deg from the print axis, stiffens the root"),
    # --- hanging lug: an M6 hex bolt down through a bracket flange on the lug, nut underneath ---
    lug=((30.0, 13.5, 10.0), "DESIGN", "lug W x reach x thickness on the back wall; reach from " + _REF + " (133.5 - 120)"),
    lug_top=(100.0, "DESIGN", "lug top above the body bottom"),
    gusset_w=(6.0, "DESIGN", "two 45 deg gussets under the lug; the 18 mm between them is the nut's bridge"),
    bolt=("M6", "DESIGN", "hex bolt ISO 4017, ISO 273 medium clearance + the FDM allowance"),
    # --- tray: the ceiling and electronics carrier ---
    tray_t=(3.0, "DESIGN", "tray plate"),
    rim=(4.0, "DESIGN", "tray perimeter band the cap's shoulder rests on; nothing stands on it"),
    board_rest=(5.0, "DESIGN", "tray top to the ESP32-CAM's camera face: shield (4.5 - PCB) + 1"),
    rest_band=(2.0, "DESIGN", "UNVERIFIED: ledges under the board's short ends, 2 mm in; check that band is "
                              "component-free on the board in hand"),
    cradle_wall=(WALL, "DESIGN", "L-shaped corner walls round each board; open sides for fingers and wires"),
    cradle_leg=(8.0, "DESIGN", "corner wall leg length"),
    cradle_lip=(2.0, "DESIGN", "corner walls stand this far above a board's top face"),
    window=((12.0, 14.0), "DESIGN", "lens window X x Y through the tray, centred on the lens"),
    led_bore=(5.0 + 2 * 0.2, "DESIGN", "IR LED body + 0.2 radial; flange seats on the tray top, silicone holds it"),
    led_gap=(2.0, "DESIGN", "LED flange to the ESP32-CAM's corner walls"),
    tie_slot=((3.5, 2.0), "DESIGN", "zip-tie slot for a 2.5 mm tie, through the tray"),
    tie_x=((-23.5, 8.0), "DESIGN", "the two ties round the 18650 holder: clear of the charger's cradle"),
    edge=(1.0, "DESIGN", "battery/board cradles inside the rim by at least this"),
    # --- cap ---
    cap_wall=(2.4, "DESIGN", "6 perimeters"),
    cap_top_t=(3.0, "DESIGN", "cap top plate under the panel"),
    skirt_drop=(12.0, "DESIGN", "cap skirt below the body top: laps the tray joint"),
    eave=(35.0, "INFERRED", _REF + ": roof cap overhangs the front by 35"),
    slope=(10.0, "DESIGN", "cap top rises to the back: sheds water, tilts the panel; 10 deg prints its walls fine"),
    headroom=(3.0, "DESIGN", "tallest thing under the cap to the cap's ceiling"),
    cable_hole=((30.0, 20.0, 10.0), "DESIGN", "panel lead through the cap top (x, y, d), under the panel: passes "
                                              "the 3.5 x 1.1 plug, sealed with silicone"),
    # --- electronics placement on the tray (x, y of each cradle centre) ---
    cam_xy=((0.0, -10.0), "DESIGN", "lens near the floor's centre, board's long axis along Y, lens end to the front: the board then clears the battery at the back"),
    holder_y=(42.0, "DESIGN", "18650 holder along X at the back, where the cap is tallest"),
    bq_xy=((30.0, 12.0), "DESIGN", "charger at the right, under the cable hole"),
    tpl_xy=((33.0, -30.0), "DESIGN", "timer at the right front"),
    # --- operation and energy ---
    interval_s=(600.0, "DESIGN", "one frame every 10 min, day and night"),
    wake_s=(10.0, "DESIGN", "UNVERIFIED: boot + WiFi join + capture + upload per wake; measure with the INA219"),
    ir_ma=(50.0, "DESIGN", "IR string current: 0.5 x the TSHG6400's 100 mA"),
    ir_s=(1.0, "DESIGN", "IR on per wake: exposure and auto-exposure settle"),
    divider_ua=(2.1, "INFERRED", "1 M + 1 M battery divider at 4.2 V"),
    boost_eff=(0.85, "DESIGN", "UNVERIFIED: TPS61023 3.7 -> 5 V at 200 mA, typical of its class"),
    boost_iq_ua=(50.0, "DESIGN", "UNVERIFIED allowance: boost + charger + their pull-ups with the load off; the "
                                 "board's green 5V LED must be removed or it alone draws ~1 mA"),
    sun_hours=(1.5, "INFERRED", "UNVERIFIED: December peak-sun hours, Hudson Valley, panel near horizontal; check "
                                "NREL PVWatts for the site"),
    harvest_eff=(0.6, "DESIGN", "panel to cell: the bq25185 has no MPPT, plus dirt and heat"),
    harvest_margin=(1.5, "DESIGN", "December harvest >= this x the daily load"),
    autonomy_min=(7.0, "DESIGN", "days on a full cell with no sun"),
    dod=(0.8, "DESIGN", "usable fraction of the cell"),
))

BOLTS = MappingProxyType(dict(
    M6=(dict(d=6.0, clear=ISO_273["M6"][1], nut_s=10.0, nut_m=5.2), "STANDARD", "ISO 273 medium, ISO 4032 (s, m max)"),
))

SIZES = MappingProxyType(dict(V0=dict()))
ACTIVE_SIZES = ("V0",)
PARTS = ("body", "floor", "front", "tray", "cap")

# What connects to the ESP32-CAM's pins (DESIGN.md, 'Wiring'). (pin, to, why).
WIRING = (
    ("5V", "TPL5110 DRV", "switched 5 V: the camera has power only while the timer says so"),
    ("GND", "common ground", "bq25185 (-), TPL5110 GND, IR string, divider"),
    ("IO13", "TPL5110 DONE", "high when the upload finishes: the timer cuts power until the next interval"),
    ("IO12", "IR MOSFET gate (AO3400A), 10 k to GND", "strapping pin: must be low at boot, which the pull-down "
                                                      "guarantees; high lights the IR string"),
    ("IO14", "battery divider midpoint (1 M / 1 M, 100 nF)", "ADC2: read before WiFi starts"),
    ("IO15", "spare", "strapping pin; free for a PIR or a BME280 later"),
    ("IO2", "spare", "strapping pin; SDA if a sensor is added"),
    ("IO4", "unused", "drives the white flash LED: keep low, or lift the LED"),
    ("IO0", "jumper to GND to flash", "camera XCLK at run time"),
    ("U0RXD/U0TXD", "programmer, bench only", "or OTA: the board lifts out of its cradle onto an ESP32-CAM-MB"),
    ("3V3, VCC, IO16", "nothing", "IO16 is the PSRAM chip select"),
)


def _tagged(tables) -> list:
    """Every input triple, as (table.key, value, tag, source)."""
    out = []
    for tname, t in tables:
        for k, v in t.items():
            out.append((f"{tname}.{k}", *v) if isinstance(v, tuple) and len(v) == 3 else (f"{tname}.{k}", v, None, None))
    return out


def _tables():
    return [("ESP32CAM", ESP32CAM), ("IR_LED", IR_LED), ("BQ25185", BQ25185), ("TPL5110", TPL5110), ("CELL", CELL),
            ("HOLDER", HOLDER), ("PANEL", PANEL), ("COMMON", COMMON), ("BOLTS", BOLTS)]


def _vals(t) -> dict:
    return {k: v[0] for k, v in t.items()}


def derive(size: str = "V0", **overrides) -> dict:
    """Every number the part files and tests need. Overrides replace COMMON values (what-if only)."""
    raw = dict(COMMON, **SIZES[size])
    for k, v in overrides.items():
        assert k in raw, f"unknown override {k}"
        raw[k] = (v, "DESIGN", "override")
    c = {k: v[0] for k, v in raw.items()}
    cam, led, bq, tpl, cell, hold, pan = (_vals(t) for t in (ESP32CAM, IR_LED, BQ25185, TPL5110, CELL, HOLDER, PANEL))
    d = dict(size=size, **c, cam=cam, led=led, bq=bq, tpl=tpl, cell=cell, holder=hold, panel=pan)
    f, w = c["fit"], c["wall"]
    W, D = c["outer"]
    d["hx"], d["hy"] = W / 2, D / 2

    # --- body: U shell, jambs with panel slots, ledge ring + front sill on the bed ---------------------------------
    d["in_x"] = d["hx"] - w                                    # inner wall face, X
    d["in_back"] = d["hy"] - w                                 # inner back wall face, Y
    d["slot_w"] = c["panel_t"] + 2 * f
    d["jamb_d"] = d["slot_w"] + 2 * c["jamb_skin"]             # jamb depth along Y
    d["jamb_y"] = (-d["hy"], -d["hy"] + d["jamb_d"])
    d["jamb_x"] = c["opening"] / 2                             # jamb inner face
    d["slot_y"] = (-d["hy"] + c["jamb_skin"], -d["hy"] + c["jamb_skin"] + d["slot_w"])
    d["slot_x"] = d["jamb_x"] + c["groove_depth"] + f          # slot bottom
    d["ledge_open"] = ((-(d["in_x"] - c["ledge_w"]), d["in_x"] - c["ledge_w"]),
                       (d["jamb_y"][1] + c["ledge_w"], d["in_back"] - c["ledge_w"]))
    # --- front panel ---------------------------------------------------------------------------------------------
    d["panel_x"] = d["jamb_x"] + c["groove_depth"]
    d["panel_y"] = (d["slot_y"][0] + f, d["slot_y"][1] - f)
    d["panel_z"] = (c["ledge_t"], c["body_h"])
    d["hole_z"] = c["ledge_t"] + c["hole_z_panel"]
    d["perch_z"] = d["hole_z"] - c["hole_d"] / 2 - c["perch_gap"] - c["perch_d"] / 2
    # --- floor: on the ledge, inside the walls, jambs and panel by the fit ------------------------------------------
    d["floor_z"] = (c["ledge_t"], c["ledge_t"] + c["floor_t"])
    d["floor_x"] = d["in_x"] - f
    d["floor_y"] = (d["panel_y"][1] + f, d["in_back"] - f)
    d["floor_notch"] = (d["jamb_x"] - f, d["jamb_y"][1] + f)   # front corners cut round the jambs: |x| > , y <
    # --- lug ------------------------------------------------------------------------------------------------------
    lw, lr, lt = c["lug"]
    d["lug_box"] = ((-lw / 2, lw / 2), (d["hy"], d["hy"] + lr), (c["lug_top"] - lt, c["lug_top"]))
    d["lug_bolt"] = (0.0, d["hy"] + lr / 2)
    bolt = BOLTS[c["bolt"]][0]
    d["bolt_bore"] = bolt["clear"] + FDM_HOLE_ALLOWANCE
    d["bolt"] = bolt
    d["bridge_w"] = lw - 2 * c["gusset_w"]
    # --- tray -----------------------------------------------------------------------------------------------------
    zt = c["body_h"] + c["tray_t"]
    d["tray_z"] = (c["body_h"], zt)
    d["usable"] = (d["hx"] - c["rim"], d["hy"] - c["rim"])      # half extents inside the rim
    bx, by = cam["size"]
    cx, cy = c["cam_xy"]
    d["lens_xy"] = (cx, cy)
    # board long axis along Y, lens end toward -Y
    d["cam_box"] = ((cx - bx / 2, cx + bx / 2), (cy - cam["lens_from_end"], cy - cam["lens_from_end"] + by))
    d["cam_face_z"] = zt + c["board_rest"]                     # camera-side face of the PCB
    d["cam_back_z"] = d["cam_face_z"] + cam["pcb_t"]
    d["shield_z"] = (d["cam_face_z"] - (cam["height"] - cam["pcb_t"]), d["cam_face_z"])
    d["lens_z"] = d["cam_face_z"] - cam["lens_drop"]
    d["wiring_top"] = d["cam_back_z"] + cam["header_stack"]
    # IR LEDs either side of the ESP32-CAM's corner walls, on the lens line
    ox = bx / 2 + f + c["cradle_wall"] + c["led_gap"] + led["flange_d"] / 2
    d["led_xy"] = [(cx - ox, cy), (cx + ox, cy)]
    d["led_z"] = (zt - led["length"], zt + 1.0)                 # body below, flange on the tray top
    # battery holder, charger, timer: (x0, x1, y0, y1, z_top)
    hl, hw_, hh = hold["size"]
    d["holder_box"] = (-hl / 2, hl / 2, c["holder_y"] - hw_ / 2, c["holder_y"] + hw_ / 2, zt + max(hh, hold["cell_top"]))
    bw, bl, bh = bq["size"]
    d["bq_box"] = (c["bq_xy"][0] - bw / 2, c["bq_xy"][0] + bw / 2, c["bq_xy"][1] - bl / 2, c["bq_xy"][1] + bl / 2, zt + bh)
    tw, tl, th = tpl["size"]
    d["tpl_box"] = (c["tpl_xy"][0] - tw / 2, c["tpl_xy"][0] + tw / 2, c["tpl_xy"][1] - tl / 2, c["tpl_xy"][1] + tl / 2, zt + th)
    (cx0, cx1), (cy0, cy1) = d["cam_box"]
    d["cam_env"] = (cx0, cx1, cy0, cy1, d["wiring_top"])
    d["cradles"] = dict(cam=(cx0, cx1, cy0, cy1), holder=d["holder_box"][:4], bq=d["bq_box"][:4], tpl=d["tpl_box"][:4])
    d["cradle_h"] = dict(cam=c["board_rest"] + cam["pcb_t"] + c["cradle_lip"], holder=6.0, bq=c["cradle_lip"] + 1.6,
                         tpl=c["cradle_lip"] + 1.6)

    # --- cap: shoulder on the tray rim, skirt over the body top, ceiling sloped, solid eave -------------------------
    t = math.tan(math.radians(c["slope"]))
    d["cap_in"] = (d["hx"] + f, d["hy"] + f)                    # skirt inner half extents (around body and tray)
    d["cap_out_x"] = d["cap_in"][0] + c["cap_wall"]
    d["cap_y"] = (-d["hy"] - f - c["cap_wall"] - c["eave"], d["hy"] + f + c["cap_wall"])
    d["cavity_y"] = (-d["hy"] + c["rim"], d["hy"] - c["rim"])   # above the tray, inside the shoulder
    d["skirt_z"] = c["body_h"] - c["skirt_drop"]
    tops = dict(cam=d["cam_env"], holder=d["holder_box"], bq=d["bq_box"], tpl=d["tpl_box"])
    y_ref = d["cavity_y"][0]
    need = {k: b[4] + c["headroom"] - (b[2] - y_ref) * t for k, b in tops.items()}
    d["ceiling_governed_by"], d["ceil_front"] = max(need.items(), key=lambda kv: kv[1])
    d["ceil_needs"] = need
    d["ceil_z"] = lambda y: d["ceil_front"] + (y - y_ref) * t   # noqa: E731  cap underside, cavity
    d["top_z"] = lambda y: d["ceil_front"] + c["cap_top_t"] / math.cos(math.radians(c["slope"])) + (y - y_ref) * t  # noqa: E731
    d["cap_height"] = d["top_z"](d["cap_y"][1]) - d["skirt_z"]
    # panel on the top, centred across, its centre over the cavity's middle
    pw, pl, pt = pan["size"]
    d["panel_c"] = (0.0, (d["cavity_y"][0] + d["cavity_y"][1]) / 2)
    hx_c, hy_c, hd = c["cable_hole"]
    d["cable_xy"] = (hx_c, hy_c)
    d["slope_t"] = t

    # --- camera field at the floor (UNVERIFIED lens) -----------------------------------------------------------------
    dist = d["lens_z"] - d["floor_z"][1]
    half_diag = dist * math.tan(math.radians(cam["fov_diag"] / 2))
    d["field_floor"] = (half_diag * 2 * 0.6, half_diag * 2 * 0.8)   # 4:3 sensor, long side along Y
    d["floor_size"] = (2 * d["floor_x"], d["floor_y"][1] - d["floor_y"][0])
    d["lens_to_floor"] = dist

    # --- IR drive: two TSHG6400 in series from the switched 5 V, one resistor, one AO3400A ----------------------------
    v = cam["supply_v"] - 2 * led["vf"] - 0.05
    d["ir_r"] = v / (c["ir_ma"] / 1000)
    d["ir_p_r"] = (c["ir_ma"] / 1000) ** 2 * d["ir_r"]

    # --- energy, battery side ----------------------------------------------------------------------------------------
    vb = cell["v_nom"]
    wake_w = (cam["supply_v"] * cam["active_ma"] / 1000) / c["boost_eff"]
    ir_w = (cam["supply_v"] * c["ir_ma"] / 1000) / c["boost_eff"]
    wakes = 86400 / c["interval_s"]
    d["wakes_per_day"] = wakes
    d["wh_wake"] = wakes * (wake_w * c["wake_s"] + ir_w * c["ir_s"]) / 3600
    stby_ua = tpl["iq_ua"] * cam["supply_v"] / vb / c["boost_eff"] + c["boost_iq_ua"] + c["divider_ua"]
    d["standby_ua"] = stby_ua
    d["wh_standby"] = stby_ua * 1e-6 * vb * 24
    d["wh_day"] = d["wh_wake"] + d["wh_standby"]
    d["wh_cell"] = cell["mah"] / 1000 * vb * c["dod"]
    d["autonomy_days"] = d["wh_cell"] / d["wh_day"]
    d["wh_harvest_dec"] = pan["p_peak"] * c["sun_hours"] * c["harvest_eff"]
    d["peak_5v_ma"] = cam["active_ma"] + c["ir_ma"]

    # --- print orientation ---------------------------------------------------------------------------------------------
    d["print_orientation"] = dict(
        body=dict(up=(0, 0, 1), rot_x=0.0, bed_face="body bottom: walls, jambs, ledge and sill", bed_z=0.0,
                  known_overhangs=[f"lug underside between the gussets: an {d['bridge_w']:.0f} mm bridge"],
                  exceptions=[("lug bridge", d["lug_box"][2][0])]),
        floor=dict(up=(0, 0, 1), rot_x=0.0, bed_face="floor underside", bed_z=d["floor_z"][0], known_overhangs=[],
                   exceptions=[]),
        front=dict(up=(0, 0, 1), rot_x=-90.0, bed_face="panel inner face; perch and hole vertical", bed_z=0.0,
                   known_overhangs=[], exceptions=[]),
        tray=dict(up=(0, 0, 1), rot_x=0.0, bed_face="tray underside", bed_z=d["tray_z"][0], known_overhangs=[],
                  exceptions=[]),
        cap=dict(up=(0, 0, 1), rot_x=180.0 - c["slope"], bed_face="cap top (the panel face), printed upside down",
                 bed_z=0.0, known_overhangs=[], exceptions=[]),
    )
    d["bed"] = BED
    d["max_overhang_deg"] = 45.0
    return d


def validate(size: str = "V0", **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    for name, v, tag, src in _tagged(_tables()):
        assert tag in TAGS and src, f"{name}: value/tag/source missing"
        assert tag not in ("PLACEHOLDER", "CONVENIENCE"), f"{name} is {tag}: unsourced, fails (cad-design-review rule 2)"
    d = derive(size, **overrides)
    c = d
    # --- printability ---
    for k in ("wall", "jamb_skin", "cradle_wall", "cap_wall", "panel_t", "tray_t"):
        assert c[k] >= 2 * NOZZLE, f"{k} {c[k]} under two lines"
    assert c["floor_t"] >= 2 * FLOOR and c["ledge_t"] >= 2 * FLOOR
    # --- body / floor / panel ---
    assert d["jamb_x"] + c["groove_depth"] + c["fit"] + c["jamb_skin"] <= d["in_x"] + 1e-9, "slot cuts through the side wall"
    assert d["floor_y"][0] > d["panel_y"][1], "floor runs into the panel"
    lo_x, lo_y = d["ledge_open"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * c["drain_xy"][0], sy * c["drain_xy"][1]
            r = c["drain_d"] / 2
            assert lo_x[0] + r <= x <= lo_x[1] - r and lo_y[0] + r <= y <= lo_y[1] - r, "drain hole over the ledge"
    assert d["hole_z"] + c["hole_d"] / 2 + 3.0 <= d["skirt_z"], "cap skirt hangs in front of the entry hole"
    assert d["perch_z"] - c["perch_collar"][0] / 2 >= d["floor_z"][1], "perch root below the floor top"
    assert abs(c["perch_d"] / 2 - c["perch_collar"][0] / 2) / c["perch_collar"][1] <= 1.0, "perch collar steeper than 45"
    # --- lug: the nut fits between the gussets ---
    assert d["bridge_w"] >= d["bolt"]["nut_s"] / math.cos(math.radians(30)) + 2.0, "M6 nut does not fit under the lug"
    # --- tray: every cradle inside the rim, nothing over the lens window or LEDs ---
    ux, uy = d["usable"]
    for k, (x0, x1, y0, y1) in d["cradles"].items():
        m = c["fit"] + c["cradle_wall"] + c["edge"]
        assert -ux <= x0 - m and x1 + m <= ux and -uy <= y0 - m and y1 + m <= uy, f"{k} cradle on the rim or off the tray"
    for x, _ in d["led_xy"]:
        assert abs(x) + d["led"]["flange_d"] / 2 <= ux, "IR LED off the tray"
    # --- cap ---
    hx_, hy_, hd = c["cable_hole"]
    assert d["cavity_y"][0] + hd / 2 + c["cap_wall"] <= hy_ <= d["cavity_y"][1] - hd / 2, "cable hole outside the cavity"
    pw, pl, _ = d["panel"]["size"]
    py0, py1 = d["panel_c"][1] - pl / 2 * math.cos(math.radians(c["slope"])), d["panel_c"][1] + pl / 2 * math.cos(math.radians(c["slope"]))
    assert d["cap_y"][0] <= py0 and py1 <= d["cap_y"][1] and pw / 2 <= d["cap_out_x"], "panel overhangs the cap top"
    assert py0 + hd <= hy_ <= py1 - hd and abs(hx_) + hd / 2 <= pw / 2, "cable hole not under the panel"
    # --- power ---
    bq, tpl = d["bq"], d["tpl"]
    assert bq["vin"][0] <= d["panel"]["v_mp"] <= bq["vin"][1], "panel voltage outside the charger's VIN range"
    assert tpl["vdd"][0] <= d["cam"]["supply_v"] <= tpl["vdd"][1] + 0.5, "TPL5110 VDD off the 5 V rail"
    assert tpl["interval_s"][0] <= c["interval_s"] <= tpl["interval_s"][1], "interval outside the timer's range"
    assert d["peak_5v_ma"] <= 0.7 * bq["boost_ma"], f"5 V peak {d['peak_5v_ma']:.0f} mA over 0.7 x the boost's 1 A"
    assert c["ir_ma"] <= 0.7 * d["led"]["i_max"], "IR current over 0.7 x the LED maximum"
    assert d["ir_r"] > 0, "no headroom for two IR LEDs in series on 5 V"
    assert d["autonomy_days"] >= c["autonomy_min"], f"{d['autonomy_days']:.1f} days on a full cell < {c['autonomy_min']}"
    assert d["wh_harvest_dec"] >= c["harvest_margin"] * d["wh_day"], (
        f"December harvest {d['wh_harvest_dec']:.2f} Wh < {c['harvest_margin']} x load {d['wh_day']:.2f} Wh")
    # --- bed ---
    for name, s in part_sizes(d).items():
        assert all(v <= B for v, B in zip(sorted(s), sorted(d["bed"]))), f"{name} {s} does not fit the bed"
    return d


def part_sizes(d: dict) -> dict:
    """Envelope of each printed part (X, Y, Z), for the bed check."""
    lw, lr, _ = d["lug"]
    return dict(
        body=(2 * d["hx"], 2 * d["hy"] + lr, d["body_h"]),
        floor=(2 * d["floor_x"], d["floor_y"][1] - d["floor_y"][0], d["floor_t"]),
        front=(2 * d["panel_x"], d["panel_z"][1] - d["panel_z"][0], d["panel_t"] + d["perch_len"]),
        tray=(2 * d["hx"], 2 * d["hy"], d["tray_t"] + max(d["cradle_h"].values())),
        cap=(2 * d["cap_out_x"], d["cap_y"][1] - d["cap_y"][0], d["cap_height"]),
    )


def report(size: str = "V0") -> str:
    d = derive(size)
    fl, ff = d["floor_size"], d["field_floor"]
    lines = [
        f"== birdhouse {size} {'(active)' if size in ACTIVE_SIZES else ''}",
        f"body {2 * d['hx']:.0f} x {2 * d['hy']:.0f} x {d['body_h']:.0f}, floor {fl[0]:.1f} x {fl[1]:.1f} on a "
        f"{d['ledge_w']:.0f} mm ledge, {d['fit']} mm fit all round, {d['foot_chamfer']} mm foot chamfer",
        f"entry hole {d['hole_d']:.0f} at z {d['hole_z']:.1f} ({d['hole_z'] - d['floor_z'][1]:.0f} above the floor); "
        f"perch {d['perch_d']:.0f} x {d['perch_len']:.0f} at z {d['perch_z']:.1f}",
        f"cap: ceiling governed by '{d['ceiling_governed_by']}' "
        + ", ".join(f"{k} {v:.1f}" for k, v in d["ceil_needs"].items())
        + f"; {d['cap_height']:.1f} tall, eave {d['eave']:.0f}, slope {d['slope']:.0f} deg",
        f"camera: lens {d['lens_to_floor']:.0f} above the floor; field there ~{ff[0]:.0f} x {ff[1]:.0f} over a "
        f"{fl[0]:.0f} x {fl[1]:.0f} floor (UNVERIFIED stock-lens FOV)",
        f"IR: 2 x TSHG6400 in series, {d['ir_ma']:.0f} mA, R {d['ir_r']:.0f} ohm ({d['ir_p_r'] * 1000:.0f} mW)",
        f"5 V peak {d['peak_5v_ma']:.0f} mA of the boost's {d['bq']['boost_ma']:.0f}",
        f"energy: {d['wakes_per_day']:.0f} wakes/day = {d['wh_wake']:.2f} Wh, standby {d['standby_ua']:.0f} uA = "
        f"{d['wh_standby']:.2f} Wh; load {d['wh_day']:.2f} Wh/day",
        f"cell {d['wh_cell']:.1f} Wh usable -> {d['autonomy_days']:.1f} days dark; December harvest "
        f"{d['wh_harvest_dec']:.2f} Wh/day = {d['wh_harvest_dec'] / d['wh_day']:.1f} x load",
        "wiring (ESP32-CAM pin -> what):",
    ] + [f"  {p:15s} -> {to:45s} {why}" for p, to, why in WIRING]
    return "\n".join(lines)


if __name__ == "__main__":
    for s in SIZES:
        try:
            validate(s)
            print(report(s), "\n  ok" + ("" if s in ACTIVE_SIZES else " (inactive)"))
        except AssertionError as e:
            print(report(s))
            print(f"{s}: FAIL: {e}")
