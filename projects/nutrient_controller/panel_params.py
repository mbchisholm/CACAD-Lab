"""Concept D, the instrument panel: B2's box face redrawn for the full analog node (pH + TDS + temperature,
three pumps) as an old-school instrument. Readouts are three red 7-segment LED displays behind red filter
windows; each pump has a column of its own (amber RUN lamp wired across the pump, AUTO / OFF / PRIME toggle,
the pump head on the panel with its tubes hanging down); POWER and ALERT pilot lamps and one big knob sit in
the corner. Legends are engraved in the panel's bed face; a filament change after the third layer shows them
in the second colour.

A concept: the massing and the front are the design question, so every bought part is an envelope with its
source tag, and the checks are the concept checks (fit, depth, bed, layout). B2 stays the active revision.

Frame: front view. X right, Z up, Y into the box; the panel's front face is y = 0, origin at the panel centre.

    .venv/bin/python projects/nutrient_controller/panel_params.py     # the layout, printed
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.boards import BOARDS
from cacad.registries.materials import BED
from projects.nutrient_controller.params import PARTS as B2_PARTS

STATUS = "concept"

# ---------------------------------------------------------------------------
# Bought parts. tag: VENDOR (datasheet or vendor STEP), INFERRED (read off a vendor STEP or drawing, not
# dimensioned), UNVERIFIED (estimate; fine for a concept, never passes a part that has to fit).
# ---------------------------------------------------------------------------
PARTS = MappingProxyType(dict(
    display=dict(tag="VENDOR", model="Adafruit 878: 0.56in 4-digit red 7-segment on the HT16K33 I2C backpack",
                 source="Adafruit_CAD_Parts '878 7-segment display backpack.step' (ref/vendor_step)",
                 pcb=(50.04, 26.67, 1.60), face=(50.40, 19.40), body_h=8.0,
                 back_parts=3.0,        # UNVERIFIED: HT16K33 and header tails behind the PCB (the STEP draws neither)
                 i2c=(0x70, 0x71, 0x72)),   # A0/A1 solder jumpers
    encoder=dict(tag="VENDOR", model="Adafruit 4991: STEMMA QT rotary encoder (seesaw, I2C 0x36) with its encoder",
                 source="Adafruit_CAD_Parts '4991 QT Rotary Encoder.step'", pcb=(25.4, 25.4, 1.57), i2c=0x36,
                 body_top=8.32,         # STEP: above the PCB underside, the four 1 x 1 frame tabs that stand 0.25 over
                                        # the body top (8.07); they bear on the panel back
                 bushing_d=7.0, bushing_top=15.07,   # STEP; thread M7x0.75 UNVERIFIED (the STEP draws it smooth)
                 shaft_d=6.0, shaft_top=28.07, under=2.96, nut_t=2.0),   # nut_t UNVERIFIED
    lamp=dict(tag="VENDOR", model="APEM Q8P1CXX?12E: 8 mm, prominent bright-chrome bezel, IP67, 12 V, solder lugs",
              source="APEM Q series datasheet pp.1-2 (ref/vendor_sheets/pilot_lamp)",
              hole=8.0, bezel_d=9.5, bezel_h=5.1, length=28.75, lugs=10.0, nut_af=10.0, nut_t=2.0, panel_max=7.0,
              colour=dict(run="Y", power="G", alert="R")),
    toggle=dict(tag="UNVERIFIED", model="C&K 7000-series SPDT ON-OFF-(ON), 1/4-40 bushing, + APM Hexseal full boot",
                source="C&K 7000 datasheet not read (the host refuses scripted downloads); typical miniature-toggle sizes",
                hole=6.4, nut_t=2.4, body=(8.1, 12.7, 10.0), terminals=5.0, boot_d=12.7, boot_h=16.0, panel_max=4.0),
    pump=dict(B2_PARTS["pump"], head_d=37.0),   # head_d UNVERIFIED: drawn, not dimensioned (~ flange height less the ears)
    filter=dict(tag="DESIGN", model="red transparent cast acrylic, 2 mm, cut to size", t=2.0, overlap=3.0),
    gland_tds=B2_PARTS["gland_tds"], gland_ph=B2_PARTS["gland_tds"],   # M16: the pH probe's SMA plug passes it open
    gland_ds=B2_PARTS["gland_ds"], dc_jack=B2_PARTS["dc_jack"],
))

# ---------------------------------------------------------------------------
# The layout. Every number here is a DESIGN choice.
# ---------------------------------------------------------------------------
LAYOUT = MappingProxyType(dict(
    W=204.0, H=190.0, corner_r=8.0, panel_t=3.0, front_chamfer=1.0,
    depth=56.0,                    # panel front to case back: the pump motor (44) + 9 of air for its terminals
    wall=2.4, back_t=3.0, boss_d=8.0, boss_l=12.0, boss_skin=1.0, panel_screw="M3", lip=1.6, lip_h=3.0,
    engrave=0.6,                   # three layers (F22)
    font="DIN Alternate", font_min=6.0,   # bold; at 5.6 "ALERT" and "PRIME" stood 3.99 tall: under 4 mm (F22)
    # readouts: three displays in a column, labels to their left
    display_x=-40.0, display_z=(72.0, 44.0, 16.0), display_labels=("pH", "EC", "°C"), label_size=9.0,
    window_margin=0.8,             # window edge outside the display face, each side
    window_bevel=1.5,              # 45 deg on the front: the digits sit 5 deep and the window walls hid them off-axis
    # system corner
    wordmark=("SPROUT", (52.0, 86.0), 8.0),
    power_lamp=(34.0, 66.0), alert_lamp=(70.0, 66.0), lamp_label_dz=-11.0, small_size=6.0,
    knob_xz=(52.0, 24.0), knob=dict(skirt_d=40.0, skirt_h=3.0, d=34.0, h=13.0, flutes=24, flute_r=1.8,
                                    dimple_d=9.0, dimple_depth=1.2, dimple_r=9.0, gap=1.5),
    knob_label=("PUSH = ACK", -1.0),
    divider_z=-8.0, divider_w=0.8,
    # channels: one column per pump
    channel_x=(-62.0, 0.0, 62.0), channel_names=("ACID", "NUTR A", "NUTR B"), channel_label_z=-18.0, channel_size=6.4,
    run_lamp_dx=-16.0, row_z=-32.0, toggle_dx=2.0, toggle_legend_dx=11.0, toggle_legends=("AUTO", "OFF", "PRIME"),
    legend_pitch=7.0,
    pump_z=-65.0, motor_hole_clear=1.0, tube_len=30.0,
    # boards on the back wall, facing the panel: (registry board, (x, z) centre), standoff and the tallest part on top
    back_boards=(("SEN0244", (-72.0, 70.0)), ("SURVEYOR_PH", (-24.0, 70.0)), ("ADS1115", (14.0, 80.0)),
                 ("PERMAPROTO_QUARTER", (74.0, 50.0)),
                 ("MOSFET_5648", (-84.0, 30.0)), ("MOSFET_5648", (-56.0, 30.0)), ("MOSFET_5648", (-28.0, 30.0)),
                 ("MOSFET_5648", (0.0, 30.0))),   # acid, nutrient A, nutrient B, ALERT lamp
    board_standoff=5.0, board_tallest=10.0,          # 10: the XIAO on its headers, UNVERIFIED
    # bottom wall: cable entries (x), at mid depth. The M16 glands sit in the gaps between the motors; the M12 and
    # the jack fit outboard of the outer motors
    entries=(("gland_ds", -84.0), ("gland_tds", -31.0), ("gland_ph", 31.0), ("dc_jack", 88.0)),
    entry_y=30.0,
    air=2.0,                       # any envelope to any other, or to a wall
    min_wall=1.2,
))

# Firmware (sprout-cut nutrient-analog-xiao) as this panel needs it: displays and encoder on the existing I2C bus,
# one more output for the ALERT lamp. The RUN lamps need no pin: they sit across the pump terminals.
PINS = MappingProxyType(dict(D4="I2C SDA", D5="I2C SCL", D10="DS18B20", D1="acid pump", D2="nutrient A pump",
                             D3="nutrient B pump", D7="ALERT lamp (4th MOSFET)"))
STRAPPING = ("D0", "D8", "D9")
I2C = MappingProxyType(dict(ADS1115=0x48, display_pH=0x70, display_EC=0x71, display_temp=0x72, encoder=0x36))


def derive(**overrides) -> dict:
    """Every number panel.py needs. Overrides are for planted-defect tests and what-ifs only."""
    d = dict(LAYOUT)
    for k, v in overrides.items():
        assert k in d, f"unknown layout key {k}"
        d[k] = dict(d[k], **v) if isinstance(d[k], dict) else v
    P = PARTS
    W, H, t = d["W"], d["H"], d["panel_t"]
    d["x0"], d["x1"], d["z0"], d["z1"] = -W / 2, W / 2, -H / 2, H / 2
    d["back_inner_y"] = d["depth"] - d["back_t"]
    # readouts
    fw, fh = P["display"]["face"]
    d["window"] = (fw + 2 * d["window_margin"], fh + 2 * d["window_margin"])
    d["filter"] = (d["window"][0] + 2 * P["filter"]["overlap"], d["window"][1] + 2 * P["filter"]["overlap"], P["filter"]["t"])
    d["display_face_y"] = t + P["filter"]["t"]                       # the display face bears on the filter
    d["display_back_y"] = d["display_face_y"] + P["display"]["body_h"] + P["display"]["pcb"][2] + P["display"]["back_parts"]
    # panel holes: (kind, (x, z), diameter or (w, h))
    holes = [("window", (d["display_x"], z), d["window"]) for z in d["display_z"]]
    lamps = [("power", d["power_lamp"]), ("alert", d["alert_lamp"])]
    for x in d["channel_x"]:
        lamps.append(("run", (x + d["run_lamp_dx"], d["row_z"])))
    holes += [("lamp", xz, P["lamp"]["hole"]) for _, xz in lamps]
    d["lamps"] = lamps
    d["toggles"] = [(x + d["toggle_dx"], d["row_z"]) for x in d["channel_x"]]
    holes += [("toggle", xz, P["toggle"]["hole"]) for xz in d["toggles"]]
    holes.append(("encoder", d["knob_xz"], P["encoder"]["bushing_d"] + 0.4))
    pump = P["pump"]
    d["pumps"] = [(x, d["pump_z"]) for x in d["channel_x"]]
    for x, z in d["pumps"]:
        holes.append(("motor", (x, z), pump["motor_d"] + 2 * d["motor_hole_clear"]))
        for s in (-1, 1):
            holes.append(("pump screw", (x + s * pump["hole_pitch"] / 2, z), pump["hole_d"]))
    # insert bosses in the corners: out along the diagonal from the corner arc's centre until boss_skin is left
    # outside them, so they fuse with the corner wall and do not break through its rounding
    r, off = d["corner_r"], (d["corner_r"] - d["boss_d"] / 2 - d["boss_skin"]) / math.sqrt(2)
    d["panel_screws"] = [(sx * (W / 2 - r + off), sz * (H / 2 - r + off)) for sx in (-1, 1) for sz in (-1, 1)]
    holes += [("panel screw", xz, 3.4) for xz in d["panel_screws"]]
    d["holes"] = holes
    # depth stack (y): what reaches furthest behind the panel, by zone
    enc = P["encoder"]
    d["encoder_pcb_y"] = t + enc["body_top"]                       # PCB underside; the board's own underside parts beyond it
    d["encoder_back_y"] = d["encoder_pcb_y"] + enc["under"]
    d["shaft_tip_y"] = t + enc["body_top"] - enc["shaft_top"]
    k = d["knob"]
    d["bushing_tip_y"] = t + enc["body_top"] - enc["bushing_top"]   # the bushing stands proud of its nut
    d["knob_base_y"] = d["bushing_tip_y"] - k["gap"]
    d["knob_front_y"] = d["knob_base_y"] - k["skirt_h"] - k["h"]
    d["lamp_back_y"] = P["lamp"]["length"] - P["lamp"]["bezel_h"] + P["lamp"]["lugs"]
    d["toggle_back_y"] = t + P["toggle"]["body"][2] + P["toggle"]["terminals"]
    d["motor_end_y"] = pump["motor_l"]                              # from the flange's back face on the panel front
    d["board_front_y"] = d["back_inner_y"] - d["board_standoff"] - 1.6 - d["board_tallest"]
    d["motor_zone_z"] = (d["pump_z"] - pump["motor_d"] / 2, d["pump_z"] + pump["motor_d"] / 2)
    return d


def validate(**overrides) -> dict:
    """Concept checks: everything on the bed, inside the panel, apart, and deep enough. Raises."""
    d = derive(**overrides)
    P = PARTS
    for name, size in (("panel", (d["W"], d["H"])), ("case", (d["W"], d["H"], d["depth"] - d["panel_t"]))):
        assert all(a <= b for a, b in zip(sorted(size), sorted(BED))), f"{name} {size} exceeds the bed {BED}"
    # every hole inside the panel with min_wall to the edge, and apart from every other
    def extent(h):   # a window's extent is its bevelled front opening
        (x, z), s = h[1], h[2]
        b = d["window_bevel"] if h[0] == "window" else 0.0
        rx, rz = (s[0] / 2 + b, s[1] / 2 + b) if isinstance(s, tuple) else (s / 2, s / 2)
        return x - rx, x + rx, z - rz, z + rz
    for h in d["holes"]:
        a = extent(h)
        assert a[0] - d["x0"] >= d["min_wall"] and d["x1"] - a[1] >= d["min_wall"] and \
               a[2] - d["z0"] >= d["min_wall"] and d["z1"] - a[3] >= d["min_wall"], f"{h[0]} at {h[1]} too near the edge"
    for i, h in enumerate(d["holes"]):
        for g in d["holes"][i + 1:]:
            a, b = extent(h), extent(g)
            gap = max(b[0] - a[1], a[0] - b[1], b[2] - a[3], a[2] - b[3])
            assert gap >= d["min_wall"], f"{h[0]} {h[1]} and {g[0]} {g[1]} leave {gap:.2f}"
    # panel thickness against what mounts through it
    assert d["panel_t"] <= P["lamp"]["panel_max"] and d["panel_t"] <= P["toggle"]["panel_max"]
    enc = P["encoder"]
    assert enc["bushing_top"] - enc["body_top"] >= d["panel_t"] + enc["nut_t"], "encoder bushing too short for panel + nut"
    assert d["shaft_tip_y"] > d["knob_front_y"] + 1.0, "shaft pokes through the knob"
    # legends: bold and >= font_min (F22)
    for size in (d["label_size"], d["small_size"], d["channel_size"], d["wordmark"][2]):
        assert size >= d["font_min"], f"legend size {size} under {d['font_min']}"
    # depth: the motors end short of the back wall; the boards on the back wall clear everything in front of them
    assert d["motor_end_y"] + d["air"] <= d["back_inner_y"], f"motor ends at {d['motor_end_y']} vs back {d['back_inner_y']}"
    front = max(d["display_back_y"], d["lamp_back_y"], d["toggle_back_y"], d["encoder_back_y"])
    assert front + d["air"] <= d["board_front_y"], f"panel parts reach y {front:.1f}, boards start at {d['board_front_y']:.1f}"
    for name, (x, z) in d["back_boards"]:
        sx, sz = BOARDS[name].size
        assert z - sz / 2 >= d["motor_zone_z"][1] + d["air"], f"{name} over the pump motors"
        assert d["x0"] + d["wall"] + d["air"] <= x - sx / 2 and x + sx / 2 <= d["x1"] - d["wall"] - d["air"], f"{name} outside the case"
        assert d["z0"] + d["wall"] + d["air"] <= z - sz / 2 and z + sz / 2 <= d["z1"] - d["wall"] - d["air"], f"{name} outside the case"
    bb = [(n, x - BOARDS[n].size[0] / 2, x + BOARDS[n].size[0] / 2, z - BOARDS[n].size[1] / 2, z + BOARDS[n].size[1] / 2)
          for n, (x, z) in d["back_boards"]]
    for i, a in enumerate(bb):
        for b in bb[i + 1:]:
            gap = max(b[1] - a[2], a[1] - b[2], b[3] - a[4], a[3] - b[4])
            assert gap >= d["air"], f"boards {a[0]} and {b[0]} {gap:.2f} apart"
    # cable entries: inside the case and below the motors
    for key, x in d["entries"]:
        g = P[key]
        r = (g.get("nut_a") or g.get("body_d")) / 2
        assert d["x0"] + d["wall"] <= x - r and x + r <= d["x1"] - d["wall"], f"{key} outside the bottom wall"
        inside = d["z0"] + max(g.get("thread", 0.0), d["wall"] + g.get("nut_b", 0.0), d["wall"] + g.get("body_l", 0.0))
        mr = PARTS["pump"]["motor_d"] / 2
        under = [mx for mx, _ in d["pumps"] if x - r < mx + mr + d["air"] and x + r > mx - mr - d["air"]]
        assert not under or inside + d["air"] <= d["motor_zone_z"][0], (
            f"{key} at x {x} reaches z {inside:.1f} under the motor at x {under[0]}, which starts at {d['motor_zone_z'][0]}")
    # firmware: no strapping pin drives anything, I2C addresses distinct
    assert not set(PINS) & set(STRAPPING), "a strapping pin is in use"
    assert len(set(I2C.values())) == len(I2C), "I2C address clash"
    return d


def report() -> str:
    d = validate()
    return "\n".join([
        f"concept D: panel {d['W']:.0f} x {d['H']:.0f} x {d['panel_t']}, case depth {d['depth']}, "
        f"pump heads to y {-PARTS['pump']['head_depth']}, knob to y {d['knob_front_y']:.1f}",
        f"  holes: {len(d['holes'])} ({', '.join(sorted({h[0] for h in d['holes']}))})",
        f"  depth: displays to y {d['display_back_y']:.1f}, lamps {d['lamp_back_y']:.1f}, toggles {d['toggle_back_y']:.1f}, "
        f"encoder {d['encoder_back_y']:.1f}; boards from y {d['board_front_y']:.1f}; motors to {d['motor_end_y']:.1f} "
        f"of {d['back_inner_y']:.1f}",
        "  I2C " + ", ".join(f"{k} 0x{v:02X}" for k, v in I2C.items()),
        "  pins " + ", ".join(f"{k} {v}" for k, v in PINS.items()),
    ])


if __name__ == "__main__":
    print(report())
