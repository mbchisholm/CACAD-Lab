"""Nutrient controller: a printed PETG housing that regulates one HDX 27 gal
tote. XIAO ESP32-C3, ADS1115, DFRobot SEN0244 TDS board and probe, DS18B20
probe, one peristaltic dosing pump on a relay, SSD1306 128x64 OLED, three
buttons, one LED. Electronics from sprout-cut env `nutrient-analog-xiao`
(platformio.ini:309-363): TDS on ADS1115 AIN1 at 0x48, OLED 0x3D on the same
I2C (D4/D5), DS18B20 on D10, pumps on active-low relays. That env drives three
relays and a pH probe; this housing carries one pump and no pH (owner,
2026-10-04).

Stage: IDEATION. Three concepts, massing only. Envelopes of bought parts are
PLACEHOLDER unless a source is named; nothing here passes a part that has to
fit. Each concept answers the questions in NOTES.md with a number.

Frame (all concepts): the tote. Origin at the centre of the rim top, +X along
the tote length, +Z up. The rim top is z = 0, the lid sits on it, the inside
floor is at z = -inside depth, the waterline at floor + fill_depth.

Every downstream script reads `derive(concept)`.
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.boards import ADS1115
from cacad.registries.connectors import USB_C
from cacad.registries.materials import BED, LAYER, NOZZLE, WALL, clearance_bore
from cacad.registries.reservoirs import HDX_27GAL

# ---------------------------------------------------------------------------
# Bought parts: (x, y, z) envelope, mm, lying flat, z = height above its base.
# tag/source per row (PARAMS_CONVENTION rule 5). PLACEHOLDER = drawn for a
# part whose geometry is not yet sourced; a concept may place it, never fit it.
# ---------------------------------------------------------------------------
PARTS = MappingProxyType(dict(
    xiao=dict(size=(21.0, 17.8, 1.0 + USB_C.header_h), tag="VENDOR",
              source="Seeed wiki XIAO_ESP32C3_Getting_Started: 21 x 17.8; height = PCB 1.0 PLACEHOLDER + USB-C receptacle "
                     "(connectors.USB_C). No mounting holes: held by a printed edge cradle."),
    ads1115=dict(size=(ADS1115.size[0], ADS1115.size[1], 1.6 + 2.9), tag="VENDOR",
                 source="boards.ADS1115 (Eagle); height = PCB 1.6 PLACEHOLDER + JST SH header 2.9 (connectors.JST_SH4)"),
    tds_board=dict(size=(42.0, 32.0, 12.0), tag="VENDOR",
                   source="DFRobot wiki SEN0244: board 42 x 32, PH2.0-3P out, XH2.54-2P probe; height 12 PLACEHOLDER; "
                          "holes unpublished: held by a printed edge rail"),
    oled=dict(size=(35.4, 33.5, 5.0), window=(30.0, 16.0), tag="PLACEHOLDER",
              source="generic 1.3in SSD1306 128x64 module; panel module not chosen (sprout-cut names only SSD1306 0x3D)"),
    relay=dict(size=(50.0, 26.0, 19.0), tag="PLACEHOLDER", source="generic 1-channel opto relay module, active-low"),
    buck=dict(size=(22.0, 17.0, 6.0), tag="PLACEHOLDER", source="MP1584-class 12 V -> 5 V module"),
    dc_jack=dict(d=11.0, l=16.0, hole_d=8.0, tag="PLACEHOLDER", source="5.5 x 2.1 panel jack"),
    button=dict(size=(12.0, 12.0, 7.3), cap_d=11.5, hole_d=12.4, tag="PLACEHOLDER", source="12 mm tact switch + round cap"),
    led=dict(d=5.0, flange_d=5.8, l=8.6, tag="PLACEHOLDER", source="T-1 3/4 (5 mm) LED in a printed bezel"),
    pump_head=dict(size=(48.0, 30.0, 34.0), tag="PLACEHOLDER",
                   source="generic 12 V DC peristaltic, Kamoer NKP class; model not chosen"),
    pump_motor=dict(d=28.0, l=50.0, tag="PLACEHOLDER", source="as pump_head"),
    tube_od=dict(d=4.0, tag="PLACEHOLDER", source="pump tubing, model not chosen"),
    tds_probe=dict(d=12.0, l=60.0, cable_d=3.5, length_total=830.0, tag="VENDOR",
                   source="DFRobot wiki SEN0244: probe 'Length 83cm' (probe + cable); body d, l and cable d PLACEHOLDER"),
    ds18b20=dict(d=6.0, l=50.0, cable_d=4.0, length_total=1000.0, tag="PLACEHOLDER",
                 source="generic stainless DS18B20 probe, 1 m lead"),
    stock_bottle=dict(d=75.0, h=170.0, tag="PLACEHOLDER", source="500 mL concentrate bottle; not chosen"),
))

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    part_air=3.0,          # DESIGN: any bought-part envelope to any inner wall or other envelope
    window_lip=1.0,        # DESIGN: OLED window edge inside the module's active-area edge
    cable_hole_extra=2.0,  # DESIGN: cable/tube hole d - cable d; a printed split grommet seals it at fidelity stage
    # --- geometry rules ---
    wall=2.0,              # DESIGN: 5 perimeters, above materials.WALL for a part that gets handled
    floor=2.0,
    corner_r=4.0,          # DESIGN: outer vertical corner radius
    lid_t=max(HDX_27GAL.lid_t_range),   # DESIGN context: thickest lid the tote range admits
    standoff=4.0,          # DESIGN: board underside above the cavity floor (cradle height)
    tote_wall=3.0,         # PLACEHOLDER context: draws the tote, never fits to it
    tote_lip=15.0,         # PLACEHOLDER context: rim flange overhang beyond the wall at the top
    immersion=40.0,        # DESIGN: probe tip this far below the waterline
    service_slack=150.0,   # DESIGN: cable slack to lift a probe out without unmounting anything
    nozzle_d=NOZZLE,
    layer=LAYER,
    min_wall=1.2,
    bed=BED,
    material="PETG",
))

# ---------------------------------------------------------------------------
# Concepts (the family axis). Inputs only.
#   A_lid    wedge box screwed to the lid; probes and tube drop through the lid
#   B_wall   tall box bolted to the outside of the short wall; one grommet hole
#            in the tote wall above the waterline; lid untouched
#   C_split  slim UI head on a 2020 rail beside the tote + wet pod on the lid
#            (pump, probe guides, bottle)
# ---------------------------------------------------------------------------
CONCEPTS = {
    "A_lid": dict(
        box=(150.0, 110.0), h_front=42.0, h_back=78.0,    # DESIGN: footprint (X, Y), wedge heights
        split_z=36.0,                                      # DESIGN: base/cover split above the box floor
        at=(220.0, 0.0),                                   # DESIGN: box centre on the lid; tube drop clears the end wall
        flange=10.0, lid_screw="M5",                       # DESIGN: skirt flange width, screws through the lid
        # DESIGN layout, box frame (x, y from the box centre; rot deg about Z; xiao USB faces +X at rot 0)
        floor_parts=dict(relay=(-20, -37, 0), buck=(45, -38, 0), tds_board=(-45, 32, 0), ads1115=(-5, 38, 0),
                         xiao=(20, 39.5, 90)),
        ui=dict(oled=(-35, 62), buttons=((15, 45), (35, 45), (55, 45)), led=(35, 82)),   # (x, s along the slope)
        cable_holes=((-50, -4), (-35, -4)),               # floor, x, y
        jack=("+Y", 50, 12), usb=("+Y", 20),               # wall, along-wall position, z above floor
        pump=("+X", 0, 18),                                # wall, y, motor axis z above floor
        bottle_at=(95.0, 0.0),                             # bottle holster centre on the lid, tote frame
    ),
    "B_wall": dict(
        box=(120.0, 62.0, 170.0),                          # DESIGN: (width Y, depth X, height Z)
        top_z=-20.0,                                       # DESIGN: box top below the rim, so the lid clears
        wall_hole_z=-60.0, wall_hole_d=22.0,               # DESIGN: one grommet hole through the tote wall
        bolt="M5", bolt_dy=80.0,                           # DESIGN: two bolts through the tote wall
        bottle_below=True,
        spacer_z=(-25.0, -100.0),                          # DESIGN: wedge spacer span on the drafted wall
        # DESIGN layout on the back plate: (y, z below the box top, rot about X; xiao USB faces -Z at rot 0)
        back_parts=dict(tds_board=(-34, -45), ads1115=(35, -40), xiao=(35, -75), relay=(-25, -110), buck=(35, -110)),
        ui=dict(oled=(0, -35), buttons=((-25, -75), (0, -75), (25, -75)), led=(40, -35)),   # front face (y, z)
        jack=("bottom", 5), usb=("bottom", 35),
        pump=("-Y", -140),                                 # side wall, motor axis z below the box top
        bolt_z=-25.0, tube_hole=(-85.0, -40.0),            # tote-wall tube hole (y, z)
    ),
    "C_split": dict(
        head=(96.0, 64.0), head_h_front=26.0, head_h_back=46.0,   # DESIGN: slim wedge, UI + all electronics
        head_at=(430.0, -140.0, 120.0),                    # DESIGN: head centre, on a 2020 post beside the tote end
        pod=(130.0, 90.0, 44.0), pod_at=(220.0, 0.0),      # DESIGN: wet pod on the lid
        rail=20.0,                                         # 2020 extrusion section, as projects/nft_table
        head_floor_parts=dict(tds_board=(-20, 10, 0), ads1115=(22, 15, 0), xiao=(32, -16, 0)),
        head_ui=dict(oled=(-24, 34), buttons=((5, 20), (20, 20), (35, 20)), led=(20, 46)),
        head_usb=("+X", -16), head_gland=("+Y", 30),
        pod_floor_parts=dict(relay=(-25, -25, 0), buck=(-30, 25, 0)),
        pod_cable_holes=((-45, 0), (-33, 0)), pod_jack=("-X", 25, 14), pod_gland=("-Y", 20, 26),
        pump=("+X", 0, 18),
        bottle_at=(95.0, 0.0),
    ),
}

ACTIVE_CONCEPTS = ("A_lid", "B_wall", "C_split")


def _tote() -> dict:
    L, W, H = HDX_27GAL.exterior_top
    li, wi, hi = HDX_27GAL.interior_bottom
    floor_z = -hi
    return dict(top=(L, W), bottom_in=(li, wi), depth_in=hi, height=H, floor_z=floor_z,
                waterline_z=floor_z + HDX_27GAL.fill_depth)


def derive(concept: str, **overrides) -> dict:
    s = dict(CONCEPTS[concept])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(concept=concept, **s, **c)
    d["parts"] = PARTS
    d["tote"] = t = _tote()
    w = c["wall"]
    # the short-end wall face at the rim, inside the lip; its draft follows from the vendor top and bottom
    end_x_top = t["top"][0] / 2 - c["tote_lip"]
    end_x_bot = t["bottom_in"][0] / 2 + c["tote_wall"]
    d["tote_end_x_top"] = end_x_top
    d["tote_draft_deg"] = math.degrees(math.atan2(end_x_top - end_x_bot, t["height"]))   # INFERRED, context only

    # electronics the dry box carries, in every concept
    d["dry_parts"] = ("xiao", "ads1115", "tds_board", "relay", "buck")
    d["ui_parts"] = ("oled", "button", "button", "button", "led")

    # probe reach: cable from the housing exit to a probe tip `immersion` below the waterline, plus service slack
    def reach(exit_xyz, probe):
        p = PARTS[probe]
        tip_z = t["waterline_z"] - c["immersion"]
        run = abs(exit_xyz[2] - tip_z) + p["l"]
        need = run + c["service_slack"]
        return dict(need=need, have=p["length_total"], margin=p["length_total"] - need)

    if concept == "A_lid":
        bx, by = s["box"]
        d["slope_deg"] = math.degrees(math.atan2(s["h_back"] - s["h_front"], by))
        d["box_z0"] = c["lid_t"]                       # box floor underside on the lid top
        d["lid_screw_d"] = clearance_bore(s["lid_screw"])
        d["exits"] = {"cables": (s["at"][0] - 50.0, s["at"][1] - 4.0, 0.0),
                      "tube": (s["at"][0] + bx / 2 + PARTS["pump_head"]["size"][1] / 2, 0.0, 0.0)}
        d["lid_removable_alone"] = False               # the box rides on the lid
        d["printed"] = {"base": (bx + 2 * s["flange"], by + 2 * s["flange"], s["split_z"]),
                        "cover": (bx, by, s["h_back"] - s["split_z"])}
    elif concept == "B_wall":
        wy, dx, hz = s["box"]
        d["box_x0"] = end_x_top                        # box back on the end wall at the rim (wall draft: NOTES)
        d["box_z0"] = s["top_z"] - hz
        d["wall_bolt_d"] = clearance_bore(s["bolt"])
        d["exits"] = {"cables": (end_x_top, 0.0, s["wall_hole_z"]), "tube": (end_x_top, 0.0, s["wall_hole_z"])}
        d["lid_removable_alone"] = True
        d["printed"] = {"body": (dx, wy, hz), "front": (dx * 0.3, wy, hz)}
    else:
        hx, hy = s["head"]
        px, py, pz = s["pod"]
        d["slope_deg"] = math.degrees(math.atan2(s["head_h_back"] - s["head_h_front"], hy))
        d["pod_z0"] = c["lid_t"]
        d["exits"] = {"cables": (s["pod_at"][0] - 45.0, 0.0, 0.0),
                      "tube": (s["pod_at"][0] + px / 2 + PARTS["pump_head"]["size"][1] / 2, 0.0, 0.0)}
        # the probe cables run pod -> head: add the straight-line run between them
        hx0, hy0, hz0 = s["head_at"]
        d["pod_to_head"] = math.dist((s["pod_at"][0], s["pod_at"][1], c["lid_t"] + pz), (hx0, hy0, hz0))
        d["lid_removable_alone"] = False               # the pod rides the lid; the head does not
        d["printed"] = {"head_base": (hx, hy, s["head_h_front"] * 0.6), "head_cover": (hx, hy, s["head_h_back"]),
                        "pod": (px, py, pz)}

    lowest_exit = min(e[2] for e in d["exits"].values())
    d["exit_above_water"] = lowest_exit - t["waterline_z"]
    probes = {}
    for p in ("tds_probe", "ds18b20"):
        r = reach(d["exits"]["cables"], p)
        if concept == "C_split":
            r["need"] += d["pod_to_head"]
            r["margin"] = r["have"] - r["need"]
        probes[p] = r
    d["reach"] = probes
    return d


def validate(concept: str) -> dict:
    """Arithmetic of a concept. Ideation: placeholders allowed, impossibilities not."""
    d = derive(concept)
    assert d["wall"] >= d["min_wall"] and d["wall"] >= 2 * d["nozzle_d"], f"{concept}: wall {d['wall']}"
    for name, size in d["printed"].items():
        assert all(a <= b for a, b in zip(sorted(size), sorted(d["bed"]))), f"{concept}: {name} {size} exceeds the bed"
    assert d["exit_above_water"] > 0, f"{concept}: an opening sits {-d['exit_above_water']:.0f} mm under the waterline"
    for p, r in d["reach"].items():
        assert r["margin"] >= 0, f"{concept}: {p} lead short by {-r['margin']:.0f} mm (need {r['need']:.0f})"
    return d


if __name__ == "__main__":
    for name in CONCEPTS:
        try:
            d = validate(name)
            flag = "ok  "
        except AssertionError as e:
            d, flag = derive(name), f"FAIL: {e}\n      "
        reach = ", ".join(f"{p} margin {r['margin']:+.0f}" for p, r in d["reach"].items())
        print(f"{name}: {flag}exit {d['exit_above_water']:+.0f} mm over water; {reach}; "
              f"lid lifts alone: {d['lid_removable_alone']}; printed {d['printed']}")
    t = derive("A_lid")
    print(f"tote: waterline z {t['tote']['waterline_z']:.0f}, floor z {t['tote']['floor_z']:.0f}, "
          f"end-wall draft {t['tote_draft_deg']:.1f} deg (INFERRED from vendor envelope + PLACEHOLDER lip)")
