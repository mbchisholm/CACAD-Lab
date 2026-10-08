"""Nutrient controller, concept B (wall mount), revision B1: every number.

A printed PETG box that hangs on a wall plate bolted to the outside of the
HDX 27 gal tote's short end wall. The box hangs by three keyholes on printed
mushroom posts and lifts off for service; it sits parallel to the wall, so
the wall's draft never enters a dimension (it tilts the screen up a few
degrees). Probe cables come out of a window in the plate, run down the gap
behind the box and enter cable glands in its bottom wall from below (drip
loop). The pump flange bolts to the outside of the -Y side wall, motor
inside; both tubes leave the head towards the plate, the outlet through a
tote-wall hole, the inlet down to a concentrate bottle standing on the floor.

Electronics from sprout-cut `nutrient-analog-xiao` (NOTES.md), with a MOSFET
driver in place of the relay (active-high: firmware `activeHigh=true`).

Frames. BOX: x out of the wall from the box's back face (x = 0), y across
(+y to the right looking at the front), z up from the box's bottom face
(z = 0). Every part file builds in the box frame. The wall plate's front face
is at x = -gap, the tote wall's outer face at x = -gap - plate_t. A box z
maps to a tote height below the rim as z - H - top_below_rim (measured along
the drafted wall, so it overstates depth: conservative for the waterline).

Tags (PARAMS_CONVENTION rule 5): each bought-part row says VENDOR (sheet
named), STANDARD, INFERRED (from what), DESIGN or PLACEHOLDER. Sheets are in
ref/vendor_sheets/ (gitignored).

    .venv/bin/python projects/nutrient_controller/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.boards import BOARDS
from cacad.registries.connectors import MATINGS
from cacad.registries.materials import (BED, FDM_HOLE_ALLOWANCE, FIT_CLEAR, INSERT_BORE_M3, INSERT_LEN_M3,
                                        INSERT_WALL_M3, LAYER, NOZZLE, clearance_bore)
from cacad.registries.reservoirs import HDX_27GAL

STATUS = "passes"   # concept | passes | printed | parked

# ---------------------------------------------------------------------------
# Fasteners. ISO 7045 pan head (M2-M3), ISO 4762 socket head (M5), ISO 4032
# nuts, ISO 10511 nylon-insert nut, ISO 7089 washer. `lengths` is the stocked
# ladder. A head wider than a board's nearest top copper takes a PA (nylon)
# screw of the same standard.
# ---------------------------------------------------------------------------
SCREWS = MappingProxyType(dict(
    M2=dict(d=2.0, head_dk=4.0, head_k=1.6, nut_s=4.0, nut_m=1.6, lengths=(4, 5, 6, 8, 10, 12, 16, 20),
            std="ISO 7045 / ISO 4032"),
    M2_5=dict(d=2.5, head_dk=5.0, head_k=2.0, nut_s=5.0, nut_m=2.0, lengths=(4, 5, 6, 8, 10, 12, 16, 20),
              std="ISO 7045 / ISO 4032"),
    M3=dict(d=3.0, head_dk=5.6, head_k=2.4, nut_s=5.5, nut_m=2.4, lengths=(5, 6, 8, 10, 12, 16, 20, 25),
            std="ISO 7045 / ISO 4032"),
    M5=dict(d=5.0, head_dk=8.5, head_k=5.0, nut_s=8.0, nut_m=5.0, nut_m_plain=4.7, washer_d=10.0, washer_h=1.0,
            lengths=(10, 12, 16, 20, 25, 30, 35, 40), std="ISO 4762 / ISO 10511 nyloc (m 5.0) / ISO 4032 (m 4.7) / ISO 7089"),
    M6=dict(d=6.0, head_s=10.0, head_k=4.0, nut_s=10.0, nut_m=5.2,
            lengths=(12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70), std="ISO 4017 hex screw / ISO 4032"),
))

# ---------------------------------------------------------------------------
# Bought parts. One row each; the tag says where the numbers come from.
# ---------------------------------------------------------------------------
PARTS = MappingProxyType(dict(
    pump=dict(tag="VENDOR", model="Kamoer NKP-DC-S06, 12 V, straight bracket",
              source="Kamoer NKP datasheet p.2 'Straight Bracket' (ref/vendor_sheets/pump), p.1 code table",
              hole_d=3.2, hole_pitch=48.5, flange=(54.5, 40.3), head_depth=23.5, motor_d=30.5, motor_l=44.0,
              volts=12.0, amps=0.25, tube_id=2.0, tube_od=4.0,
              # INFERRED: drawn, not dimensioned. The holes sit on the line through the shaft; the two tube
              # ends 18.6 apart about it. Slots and a sliding nut tolerate the first, a slot the second.
              tube_pitch=18.6),
    gland_tds=dict(tag="VENDOR", model="Lapp SKINTOP ST-M M16x1.5 (53111010) + GMP-GL-M M16 locknut (53119010)",
                   source="Lapp DB53111000EN p.2, DB53119000EN p.2, T21 hole table",
                   hole=16.0, hole_tol=0.2, sw=19.0, a=21.1, c_max=34.0, thread=8.0, clamp=(4.0, 10.0),
                   nut_sw=22.0, nut_a=24.2, nut_b=5.0),
    gland_ds=dict(tag="VENDOR", model="Lapp SKINTOP ST-M M12x1.5 (53111000) + GMP-GL-M M12 locknut (53119000)",
                  source="Lapp DB53111000EN p.2, DB53119000EN p.2, T21 hole table",
                  hole=12.0, hole_tol=0.2, sw=15.0, a=16.6, c_max=30.0, thread=8.0, clamp=(3.5, 7.0),
                  nut_sw=17.0, nut_a=18.7, nut_b=5.0),
    dc_jack=dict(tag="VENDOR", model="Switchcraft 722A, 2.0 mm pin (5.5 x 2.1 plug)",
                 source="Switchcraft 722A sheet, 'Mounting' and drawing 722A_CD",
                 hole=7.95, panel_max=3.18, body_d=11.0, body_l=15.2),
    button=dict(tag="VENDOR", model="E-Switch PV0 IP67 12 mm momentary",
                source="E-Switch PV0 datasheet p.2", hole=12.0, hole_tol=0.2, panel=(1.0, 6.0),
                bezel_d=14.0, behind=19.0),       # 18.0 +/- 1: the larger
    led=dict(tag="VENDOR", model="Bivar CR-174 T-1 3/4 clip and ring + 5 mm LED",
             source="Bivar CR-174 datasheet", hole=6.86, panel=(0.8, 3.2), ring_d=8.9, ring_h=4.1,
             body_l=8.6),                     # LED body behind the ring: PLACEHOLDER (T-1 3/4 lamps, typical)
    oled=dict(tag="VENDOR", board="OLED_938", source="boards.OLED_938 (Eagle): glass and active area from the panel package",
              glass=(34.5, 23.0), glass_off=(0.0, 0.06), active=(29.4, 14.7), active_off=(0.0, 2.11),
              panel_t=1.6,                    # PLACEHOLDER: not in the Eagle file; the boss height clears 3.0
              back_h=MATINGS["JST_SH4"].header_h),
    xiao=dict(tag="VENDOR", size=(20.955, 17.78),
              source="Seeed XIAO ESP32C3_v1.3.kicad_pcb Edge.Cuts (ref/vendor_sheets/xiao_esp32c3)",
              pcb_t=1.6,                      # PLACEHOLDER: KiCad default, no stackup published
              usb_h=MATINGS["USB_C"].header_h,
              spacer=2.54),                   # PLACEHOLDER: 0.1 in pin header body under the board
    pololu=dict(tag="VENDOR", model="Pololu D24V10F5 5 V 1 A step-down, 5.1-36 V in",
                source="d24v10fx dimensions PDF (pololu.com/file/0J1662), product 2831",
                size=(17.8, 12.7), h=1.02 + 2.8, vin=(5.1, 36.0)),
    tds_probe=dict(tag="VENDOR", source="DFRobot wiki SEN0244: probe 'Length 83cm' with XH2.54-2P plug",
                   length_total=830.0, plug="JST_XH2",
                   d=12.0, l=60.0, cable_d=3.5),   # PLACEHOLDER: probe body and cable not published
    ds18b20=dict(tag="PLACEHOLDER", source="generic stainless DS18B20, 1 m lead, bare ends",
                 d=6.0, l=50.0, cable_d=4.0, length_total=1000.0),
    usb_plug=dict(tag="PLACEHOLDER", source="USB-C plug overmold: USB-IF spec not read",
                  overmold=(12.35, 6.5)),
))

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    fit_clear=FIT_CLEAR,                 # radial: printed bore - bought part it slips over (materials)
    hole_allow=FDM_HOLE_ALLOWANCE,       # diametral: added to every vendor panel-hole size (materials)
    part_air=2.0,                        # DESIGN: any bought-part envelope to another or to a wall
    board_air=1.0,                       # DESIGN: pin tails under a board to the boss base
    boss_pin_margin=1.0,                 # DESIGN: boss outer radius stays this far inside a board's nearest pin
    nut_pocket_clear=0.3,                # DESIGN: across flats, hex pocket - nut
    nut_pocket_extra=0.8,                # DESIGN: pocket depth - nut m
    keyhole_clear=0.4,                   # DESIGN radial: keyhole - post neck and head
    plug_finger=5.0,                     # DESIGN: room beyond a pulled plug, to grip it
    rest_pad_d=4.0,                      # DESIGN: pad under a board edge that has no holes
    tds_sleeve_wall=1.0,                 # DESIGN: heat-shrink built up on the TDS cable at its gland
    # --- geometry rules ---
    wall=2.4,                            # DESIGN: 6 perimeters; glands torque against it
    back_t=3.2,                          # DESIGN: holds M2 / M2.5 nut pockets from the back face
    cover_t=2.5,                         # DESIGN: inside the PV0 and CR-174 panel ranges
    corner_r=5.0,
    standoff=5.0,                        # DESIGN minimum: board underside above the back plate's inner face
    screw_tip_min=0.4,                   # DESIGN: a board screw's tip stays this far inside the back face
    insert_boss_od=INSERT_BORE_M3 + 2 * 2.0,   # wall 2.0 >= vendor minimum INSERT_WALL_M3
    insert_depth=INSERT_LEN_M3 + 1.0,    # CNC Kitchen: insert length + about 1 mm
    teardrop_cap=0.6,                    # DESIGN: a horizontal hole's teardrop is cut flat this far above r
    tote_wall_t=(2.0, 5.0),              # DESIGN: HDX wall thickness unpublished; the bolt length covers the range
    hole_over_water=50.0,                # DESIGN: least height of any tote-wall hole over the waterline
    immersion=40.0,                      # DESIGN: probe tip below the waterline
    service_slack=150.0,                 # DESIGN: lead to lift a probe out
    nozzle_d=NOZZLE, layer=LAYER, min_wall=1.2, bed=BED, material="PETG",
))

PRINT_ORIENTATION = MappingProxyType(dict(
    body=dict(up=(1, 0, 0), bed_face="back face, x = 0", bed_z="0",
              known_overhangs=["side- and bottom-wall holes: truncated teardrops, apex +x"],
              overhang_exceptions=[]),
    cover=dict(up=(-1, 0, 0), bed_face="front face", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
    plate=dict(up=(1, 0, 0), bed_face="tote-side face", bed_z="0",
               known_overhangs=["post heads: 45 deg cone underside"], overhang_exceptions=[]),
    backing=dict(up=(1, 0, 0), bed_face="either face", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
    hook=dict(up=(0, 0, -1), bed_face="bridge top", bed_z="z_bridge top",
              known_overhangs=["cable groove ceiling (bridged, 16 mm)", "leg holes: teardrops, apex -z"],
              overhang_exceptions=["groove ceiling"]),
    knob=dict(up=(0, 0, 1), bed_face="underside", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
    pad=dict(up=(0, 0, 1), bed_face="contact face", bed_z="0", known_overhangs=[], overhang_exceptions=[]),
))

# ---------------------------------------------------------------------------
# Revisions (the family axis). Inputs only.
# ---------------------------------------------------------------------------
_B1 = dict(
        mount="wall",                              # wall plate bolted through the tote wall
        W=110.0, H=150.0, D=44.0,                  # DESIGN: box outer, D = back face to front rim
        skirt=3.0,                                 # DESIGN: cover lip over the body's outer edge; ends short of the pump flange
        gap=12.0,                                  # DESIGN: plate front face to box back (cables, bolt heads)
        plate_t=5.0, backing_t=4.0,
        plate_y=(-88.0, 60.0), plate_z=(0.0, 150.0),
        top_below_rim=20.0,                        # DESIGN: box top under the rim; the lid's lip clears
        # boards on the back plate: registry board, centre (y, z), rot deg in the y-z plane, screw
        back_boards=dict(
            tds=("SEN0244", (-30.0, 39.0), 90, "M2_5"),
            ads=("ADS1115", (-24.0, 82.0), 0, "M2"),          # above the TDS PH plug, under the motor, plug clear of the nut block
            mosfet=("MOSFET_5648", (25.0, 70.0), 0, "M2"),
            carrier=("PERMAPROTO_QUARTER", (22.0, 30.8), 0, "M3"),   # M3 into heat-set inserts
        ),
        # on the carrier: centre (y, z) in the box frame; the XIAO's USB end down at the carrier's edge
        xiao_yz=(33.0, None), pololu_yz=(12.0, 20.0),
        # front cover UI, (y, z)
        oled_yz=(20.0, 125.0), buttons_yz=((-30.0, 80.0), (0.0, 80.0), (30.0, 80.0)), led_yz=(45.0, 100.0),
        # bottom wall: (y, x)
        gland_tds_yx=(-30.0, 21.0), gland_ds_yx=(0.0, 21.0), jack_yx=(15.0, 30.0),
        usb_opening=(13.5, 8.0),                   # DESIGN: (y, x), around the PLACEHOLDER overmold
        # pump on the -Y wall: motor axis (x, z)
        pump_xz=(19.5, 108.0), pump_slot=1.5,      # DESIGN: flange clears the skirt, motor clears the back plate
        # keyholes: rest positions (y, z) of the posts; the box slides down `slide` onto them
        keyholes=((-36.0, 140.0), (36.0, 140.0), (-7.0, 18.0)), slide=10.0,
        post_neck_d=6.0, post_head_d=10.0, post_head_t=3.0,
        plate_bolts=((-75.0, 140.0), (50.0, 140.0), (-75.0, 60.0), (50.0, 60.0)), plate_bolt="M5",
        cable_hole=(-20.0, 100.0), cable_hole_d=16.0, plate_window_d=20.0,   # tote hole (y, z), DESIGN
        tube_hole_d=8.0,                           # DESIGN: tote hole for the 4 mm outlet tube
        tube_slot_w=12.0,                          # DESIGN: plate slot width around both tube ends
)

_WALL_ONLY = ("plate_bolts", "plate_bolt", "cable_hole", "cable_hole_d", "plate_window_d", "tube_hole_d", "backing_t")

# B2: the same box and post plate, hung from a clamp over the container's rim. No hole in the container.
# The hook bolts to the post plate through vertical slots (box height under the rim adjustable); an M6 screw
# with a printed knob and pad clamps the rim wall or lip against the hook's inner jaw. Probe cables and the
# dosing tube go over the rim in a groove on the bridge; the lid rests on the bridge there.
_B2 = {k: v for k, v in _B1.items() if k not in _WALL_ONLY}
_B2.update(
    mount="rim",
    plate_z=(0.0, 150.0),                          # DESIGN: post plate ends at the box top; the hook carries it
    top_below_rim=35.0,                            # DESIGN nominal; the hook slots give +/- slot_half
    rim_c=(2.0, 35.0),                             # DESIGN: container wall or lip thickness at the screw, mm
    throat=45.0,                                   # DESIGN: hook leg to inner jaw
    leg_t=9.0, bridge_t=6.0, jaw_t=5.0, jaw_len=40.0,
    hook_w=60.0, hook_y=-30.0,                     # DESIGN: narrow, so it sits on a round bucket rim too
    leg_below_box_top=40.0,                        # DESIGN: overlap of the hook leg on the post plate
    hook_bolts_y=(-50.0, -10.0), hook_bolts_z=125.0, slot_half=6.0, hook_bolt="M5",
    plate_nut_boss=(14.0, 4.0),                    # DESIGN: (d, h) boss on the plate's box side holding an M5 nut
    screw="M6", screw_below_rim=15.0,
    pad=(20.0, 6.0, 4.0),                          # DESIGN: (d, t, blind-hole depth)
    knob=(26.0, 12.0),                             # DESIGN: (d, t); captures the ISO 4017 head
    groove=(16.0, 3.0),                            # DESIGN: cable/tube groove on the bridge top (w, depth)
    bucket_r_min=150.0,                            # DESIGN: smallest rim radius the 60 mm hook is meant for
    rim_to_waterline_max=200.0,                    # DESIGN: universal case for the probe-lead check
)

SIZES = {"B1": _B1, "B2": _B2}

ACTIVE_SIZES = ("B2",)


def _rot(u, v, deg):
    a = math.radians(deg)
    return u * math.cos(a) - v * math.sin(a), u * math.sin(a) + v * math.cos(a)


def _stock(lengths, need):
    ok = [L for L in lengths if L >= need]
    return min(ok) if ok else None


def derive(size: str, **overrides) -> dict:
    s = dict(SIZES[size])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(size=size, **s, **c)
    P = PARTS
    d["parts"], d["screws"] = P, SCREWS
    W, H, D, w = s["W"], s["H"], s["D"], c["wall"]
    d["inner_y"] = (-W / 2 + w, W / 2 - w)
    d["inner_z"] = (w, H - w)
    d["inner_x"] = (c["back_t"], D)

    # --- boards on the back plate: outline, holes and connectors in the box frame ---
    boards = {}
    for key, (bname, (cy, cz), rot, screw) in s["back_boards"].items():
        b = BOARDS[bname]
        sx, sy = b.size
        ex, ey = (sx, sy) if rot % 180 == 0 else (sy, sx)
        holes = [(cy + _rot(u, v, rot)[0], cz + _rot(u, v, rot)[1]) for u, v in b.holes]
        conns = []
        for cn in b.connectors:
            m = MATINGS[cn.kind]
            py, pz = _rot(cn.x, cn.y, rot)
            fy, fz = _rot(*cn.facing, rot)
            conns.append(dict(kind=cn.kind, at=(cy + py, cz + pz), facing=(round(fy), round(fz)), mating=m))
        sc = SCREWS[screw]
        bore = clearance_bore(screw.replace("_", ".")) if screw.replace("_", ".") in ("M3",) else sc["d"] + 0.4 + c["hole_allow"]
        boards[key] = dict(name=bname, centre=(cy, cz), rot=rot, extent=(ex, ey), holes=holes, conns=conns,
                           screw=screw, bore=bore, board=b)
    d["boards"] = boards
    # board heights above the underside (tallest part on top); thickness from the registry or PLACEHOLDER 1.6
    tops = dict(tds=MATINGS["JST_XH2"].header_h, ads=MATINGS["JST_SH4"].header_h, mosfet=4.5,   # WAGO 2060: 4.5, INFERRED from the 2060 series
                carrier=P["xiao"]["spacer"] + P["xiao"]["pcb_t"] + P["xiao"]["usb_h"])
    d["pcb_t"] = 1.6                                     # PLACEHOLDER for every board: no Eagle file states it
    d["board_tops"] = tops

    # boss per board hole. M2 / M2.5: nut pocket open to the back face, the boss height raised until a
    # stocked screw ends inside the nut and short of the back face (rule 7: the governing need is recorded).
    # M3 (carrier): heat-set insert from the boss top, screw = PCB + insert length.
    bosses = []
    for key, b in boards.items():
        sc = SCREWS[b["screw"]]
        insert = b["screw"] == "M3"
        boss_h = c["standoff"]
        if insert:
            od, pocket = c["insert_boss_od"], None
            L = _stock(sc["lengths"], d["pcb_t"] + INSERT_LEN_M3)
            b["governed_by"] = "standoff minimum"
        else:
            pocket = dict(s=sc["nut_s"] + c["nut_pocket_clear"], depth=sc["nut_m"] + c["nut_pocket_extra"])
            od = b["bore"] + 2 * c["min_wall"]
            nut_far = pocket["depth"] - sc["nut_m"]                   # nut face nearest the back face, x
            L = _stock(sc["lengths"], c["back_t"] + boss_h + d["pcb_t"] - nut_far)
            tip = c["back_t"] + boss_h + d["pcb_t"] - (L or 0)
            b["governed_by"] = "standoff minimum"
            if L is not None and tip < c["screw_tip_min"]:
                boss_h += c["screw_tip_min"] - tip
                b["governed_by"] = f"M{sc['d']:g}x{L} tip inside the back face"
        b["boss_h"], b["x0"] = boss_h, c["back_t"] + boss_h
        for (y, z) in b["holes"]:
            bosses.append(dict(board=key, at=(y, z), od=od, bore=b["bore"], pocket=pocket, insert=insert,
                               screw=b["screw"], length=L, h=boss_h))
        nb = b["board"]
        b["boss_vs_pin"] = None if nb.nearest_pin is None else nb.nearest_pin - c["boss_pin_margin"] - od / 2
        b["head_vs_copper"] = None if nb.nearest_top_copper is None else nb.nearest_top_copper - sc["head_dk"] / 2
        b["nylon_screw"] = b["head_vs_copper"] is not None and b["head_vs_copper"] < 0
    d["bosses"] = bosses

    # --- the carrier's passengers ---
    for k, b in boards.items():
        b["top_x"] = b["x0"] + d["pcb_t"] + tops[k]
    car = boards["carrier"]
    cy0, cz0 = car["centre"]
    x_car_top = car["x0"] + d["pcb_t"]
    xz = P["xiao"]
    xiao_z0 = cz0 - car["extent"][1] / 2                  # USB end at the carrier's bottom edge
    d["xiao"] = dict(y=s["xiao_yz"][0], z=(xiao_z0, xiao_z0 + xz["size"][0]), width=xz["size"][1],
                     x=(x_car_top + xz["spacer"], x_car_top + xz["spacer"] + xz["pcb_t"] + xz["usb_h"]))
    d["usb_x"] = x_car_top + xz["spacer"] + xz["pcb_t"] + xz["usb_h"] / 2
    pl = P["pololu"]
    d["pololu"] = dict(y=s["pololu_yz"][0], z=s["pololu_yz"][1], size=pl["size"],
                       x=(x_car_top + xz["spacer"], x_car_top + xz["spacer"] + pl["h"]))

    # --- cover ---
    sk_in = c["fit_clear"]
    d["cover_outer"] = (W + 2 * (sk_in + c["min_wall"] + 0.4), H + 2 * (sk_in + c["min_wall"] + 0.4))
    d["cover_inner_x"] = D                                # cover inner face sits on the rim
    ob = BOARDS["OLED_938"]
    d["oled_boss_h"] = 4.0                                # DESIGN: clears a panel up to 4.0 - air
    d["oled_board_x"] = D - d["oled_boss_h"] - d["pcb_t"]   # component-side face of the OLED PCB
    d["oled_holes"] = [(s["oled_yz"][0] + u, s["oled_yz"][1] + v) for u, v in ob.holes]
    d["oled_window"] = (P["oled"]["active"][0] + 1.0, P["oled"]["active"][1] + 1.0)   # DESIGN: 0.5 each side
    d["oled_window_c"] = (s["oled_yz"][0] + P["oled"]["active_off"][0], s["oled_yz"][1] + P["oled"]["active_off"][1])
    d["button_hole"] = P["button"]["hole"] + P["button"]["hole_tol"] / 2 + c["hole_allow"]
    d["led_hole"] = P["led"]["hole"] + c["hole_allow"]
    # corner insert columns sink `sink` into both walls: a column tangent to a wall meshes non-manifold (F31)
    sink = 0.6
    r_ib = c["insert_boss_od"] / 2 - sink
    d["cover_screw_pts"] = [(sy * (W / 2 - w - r_ib), z) for sy in (-1, 1) for z in (w + r_ib, H - w - r_ib)]
    d["cover_screw"] = _stock(SCREWS["M3"]["lengths"], c["cover_t"] + INSERT_LEN_M3 - 0.2)

    # --- bottom wall ---
    d["gland_holes"] = {k: P[k]["hole"] + P[k]["hole_tol"] / 2 + c["hole_allow"] for k in ("gland_tds", "gland_ds")}
    d["jack_hole"] = P["dc_jack"]["hole"] + c["hole_allow"]

    # --- pump ---
    pp = P["pump"]
    px, pz = s["pump_xz"]
    d["pump_hole_z"] = (pz - pp["hole_pitch"] / 2, pz + pp["hole_pitch"] / 2)
    d["pump_slot_w"] = clearance_bore("M3")
    d["motor_hole"] = pp["motor_d"] + 2 * c["fit_clear"]
    d["pump_head_y"] = (-W / 2 - pp["head_depth"], -W / 2)
    d["pump_screw"] = _stock(SCREWS["M3"]["lengths"], 3.0 + w + SCREWS["M3"]["nut_m"] + 0.5)   # flange 3.0 PLACEHOLDER
    d["nut_channel_s"] = SCREWS["M3"]["nut_s"] + c["nut_pocket_clear"]
    d["tube_z"] = (pz - pp["tube_pitch"] / 2, pz + pp["tube_pitch"] / 2)     # outlet = the upper one (DESIGN)

    # --- hanging: posts and keyholes ---
    kc = c["keyhole_clear"]
    d["keyhole_big"] = s["post_head_d"] + 2 * kc
    d["keyhole_slot"] = s["post_neck_d"] + 2 * kc
    d["post_neck_l"] = s["gap"] + c["back_t"] + kc        # plate face to under the head
    # --- tote mapping and the water (HDX 27 gal, the container this was drawn for) ---
    t_in = HDX_27GAL.interior_bottom
    waterline_below_rim = t_in[2] - HDX_27GAL.fill_depth
    d["waterline_z"] = H + s["top_below_rim"] - waterline_below_rim     # box frame
    d["z_rim"] = H + s["top_below_rim"]
    gl = {"tds_probe": s["gland_tds_yx"], "ds18b20": s["gland_ds_yx"]}
    target = {"tds_probe": boards["tds"]["conns"][0]["at"], "ds18b20": (s["pololu_yz"][0], s["pololu_yz"][1])}
    reach = {}
    if s["mount"] == "wall":
        # --- plate bolts through the tote wall ---
        b5 = SCREWS[s["plate_bolt"]]
        grip = [s["plate_t"] + t + s["backing_t"] + b5["washer_h"] for t in c["tote_wall_t"]]
        d["plate_bolt_len"] = _stock(b5["lengths"], max(grip) + b5["nut_m"] + 1.0)
        d["plate_bolt_grip"] = grip
        d["plate_bolt_hole"] = clearance_bore("M5")
        d["tote_holes"] = {"cable": s["cable_hole"], "tube": (-W / 2 - pp["head_depth"] / 2, d["tube_z"][1])}
        d["tote_holes"].update({f"bolt{i}": p for i, p in enumerate(s["plate_bolts"])})
        d["lowest_hole_over_water"] = min(z for _, z in d["tote_holes"].values()) - d["waterline_z"]
        # probe reach: tote hole -> tip below the waterline; tote hole -> down the gap -> gland -> board
        for p in ("tds_probe", "ds18b20"):
            hy, hz = s["cable_hole"]
            tip_z = d["waterline_z"] - c["immersion"]
            wet = (hz - tip_z) + P[p]["l"] + 50.0                 # 50: DESIGN, hole to the water surface sideways
            gy = gl[p][0]
            dry = (hz - (-30.0)) + abs(hy - gy) + 30.0 + abs(target[p][1] - 0.0) + abs(target[p][0] - gy)   # loop 30 below the box
            need = wet + dry + c["service_slack"]
            reach[p] = dict(need=need, have=P[p]["length_total"], margin=P[p]["length_total"] - need)
    else:
        # --- rim clamp (box frame): post plate | hook leg | throat (container wall) | inner jaw ---
        xp0 = -s["gap"] - s["plate_t"]                                  # post plate's container-side face
        d["x_leg"] = (xp0 - s["leg_t"], xp0)
        d["x_jaw_face"] = xp0 - s["leg_t"] - s["throat"]
        d["x_jaw"] = (d["x_jaw_face"] - s["jaw_t"], d["x_jaw_face"])
        zr = d["z_rim"]
        d["z_bridge"] = (zr, zr + s["bridge_t"])
        d["z_jaw"] = (zr - s["jaw_len"], zr + s["bridge_t"])
        d["z_leg"] = (H - s["leg_below_box_top"], zr + s["bridge_t"])
        d["rim_adjust"] = (s["top_below_rim"] - s["slot_half"], s["top_below_rim"] + s["slot_half"])
        d["hook_bolt_hole"] = clearance_bore("M5")
        d["screw_z"] = zr - s["screw_below_rim"]
        m6, m5 = SCREWS[s["screw"]], SCREWS[s["hook_bolt"]]
        pad_d, pad_t, pad_hole = s["pad"]
        knob_d, knob_t = s["knob"]
        d["screw_hole"] = clearance_bore("M6")
        d["screw_nut_pocket"] = dict(s=m6["nut_s"] + c["nut_pocket_clear"], depth=m6["nut_m"] + 0.3)
        # screw extension past the leg's container face, for the thinnest and thickest container
        lo, hi = s["rim_c"]
        d["screw_ext"] = (s["throat"] - hi - pad_t, s["throat"] - lo - pad_t)
        need = (knob_t - m6["head_k"]) + s["leg_t"] + d["screw_ext"][1] + pad_hole
        d["screw_len"] = _stock(m6["lengths"], need)
        d["screw_need"] = need
        # the knob, at its farthest out (thickest container), must clear the post plate and the box top
        d["knob_z_min"] = H + d["rim_adjust"][0] - s["screw_below_rim"] - knob_d / 2   # at the lowest rim setting
        # hook bolts: ISO 4762 head on the leg's container face, nut in a boss on the plate's box side
        nb_d, nb_h = s["plate_nut_boss"]
        d["plate_nut_pocket"] = dict(s=m5["nut_s"] + c["nut_pocket_clear"], depth=m5["nut_m_plain"] + 0.8)
        grip = s["leg_t"] + s["plate_t"] + nb_h - d["plate_nut_pocket"]["depth"] + m5["nut_m_plain"]
        d["hook_bolt_len"] = _stock(m5["lengths"], grip + 1.0)
        d["hook_bolt_tip_x"] = d["x_leg"][0] + (d["hook_bolt_len"] or 0)
        d["bucket_sagitta"] = s["bucket_r_min"] - math.sqrt(s["bucket_r_min"] ** 2 - (s["hook_w"] / 2) ** 2)
        # probe reach, universal case: rim -> tip inside; over the bridge; down outside to under the box -> gland
        over = s["throat"] + s["jaw_t"] + s["leg_t"] + 2 * s["bridge_t"]
        for case, rtw in (("universal", s["rim_to_waterline_max"]), ("HDX", waterline_below_rim)):
            for p in ("tds_probe", "ds18b20"):
                wet = rtw + c["immersion"] + P[p]["l"] + 30.0             # 30: DESIGN, jaw to the probe sideways
                gy = gl[p][0]
                dry = (zr + 30.0) + abs(s["hook_y"] - gy) + 30.0 + target[p][1] + abs(target[p][0] - gy)
                need = wet + over + dry + c["service_slack"]
                reach[f"{p} ({case})"] = dict(need=need, have=P[p]["length_total"], margin=P[p]["length_total"] - need)
        d["jaw_over_water"] = d["z_jaw"][0] - d["waterline_z"]
    d["reach"] = reach

    # --- glands: what passes and what seals ---
    xh = MATINGS[P["tds_probe"]["plug"]]
    d["xh_diag"] = math.hypot(xh.plug_w, xh.plug_h)
    d["tds_cable_sealed"] = P["tds_probe"]["cable_d"] + 2 * c["tds_sleeve_wall"]
    # pads under the hole-less end of a board whose holes are all on one end (MOSFET 5648)
    pads = []
    for key, b in boards.items():
        us = [u for u, _ in b["board"].holes]
        if all(u > 0 for u in us) or all(u < 0 for u in us):
            for u, v in b["board"].holes:
                py, pz = _rot(-u, v, b["rot"])
                pads.append(dict(board=key, at=(b["centre"][0] + py, b["centre"][1] + pz), h=b["boss_h"]))
    d["rest_pads"] = pads
    # plug envelopes: plug length + finger room, except where the cable comes straight in from a gland
    d["finger"] = {("tds", "JST_XH2"): 0.0}
    sc2 = SCREWS["M2"]
    d["oled_screw"] = _stock(sc2["lengths"], c["cover_t"] + d["oled_boss_h"] + d["pcb_t"] + sc2["nut_m"] + 0.4)
    d["oled_boss_od"] = d["boards"]["ads"]["bore"] + 2 * c["min_wall"]
    d["oled_boss_flat"] = 0.3                            # DESIGN: boss trimmed flat this far from the glass edge
    # print-frame z of each bridged ceiling (overhang exceptions): nut-pocket ceilings, teardrop flats, USB slot top
    r = lambda dia: dia / 2 + c["teardrop_cap"]
    ex = [("nut pocket ceiling " + k, b["pocket"]["depth"]) for k, b in
          {bb["screw"]: bb for bb in bosses if bb["pocket"]}.items()]
    ex += [("motor hole flat", s["pump_xz"][0] + r(d["motor_hole"])),
           ("gland_tds flat", s["gland_tds_yx"][1] + r(d["gland_holes"]["gland_tds"])),
           ("gland_ds flat", s["gland_ds_yx"][1] + r(d["gland_holes"]["gland_ds"])),
           ("jack flat", s["jack_yx"][1] + r(d["jack_hole"])),
           ("usb opening top", d["usb_x"] + s["usb_opening"][1] / 2)]
    d["body_overhang_exceptions"] = ex
    d["print_orientation"] = PRINT_ORIENTATION
    d["walls"] = {"body wall": w, "back": c["back_t"], "cover": c["cover_t"],
                  "insert boss": (c["insert_boss_od"] - INSERT_BORE_M3) / 2}
    d["printed_sizes"] = {"body": (W, H, D), "cover": (*d["cover_outer"], c["cover_t"] + max(s["skirt"], d["oled_boss_h"])),
                          "plate": (s["plate_y"][1] - s["plate_y"][0], s["plate_z"][1] - s["plate_z"][0],
                                    s["plate_t"] + d["post_neck_l"] + s["post_head_t"])}
    if s["mount"] == "wall":
        d["printed_sizes"]["backing"] = (s["plate_y"][1] - s["plate_y"][0], s["plate_z"][1] - s["plate_z"][0], s["backing_t"])
    else:
        d["printed_sizes"]["hook"] = (d["x_leg"][1] - d["x_jaw"][0], s["hook_w"], d["z_leg"][1] - d["z_leg"][0])
        d["walls"]["hook leg behind the M6 nut"] = s["leg_t"] - d["screw_nut_pocket"]["depth"]
        d["walls"]["bridge under the groove"] = s["bridge_t"] - s["groove"][1]
        d["hook_overhang_exceptions"] = [("groove ceiling", s["groove"][1])]   # print frame: bridge top on the bed
        d["printed_sizes"]["knob"] = (s["knob"][0], s["knob"][0], s["knob"][1])
        d["printed_sizes"]["pad"] = (s["pad"][0], s["pad"][0], s["pad"][1])
    return d


def validate(size: str, **overrides) -> dict:
    """Raise AssertionError on anything not buyable, printable or assemblable. Overrides: what-if only."""
    d = derive(size, **overrides)
    P, c = d["parts"], d
    for name, wv in d["walls"].items():
        assert wv >= d["min_wall"] and wv >= 2 * d["nozzle_d"], f"{size}: {name} {wv:.2f}"
    assert d["walls"]["insert boss"] >= INSERT_WALL_M3, f"{size}: insert boss wall under the vendor minimum"
    for name, sz in d["printed_sizes"].items():
        assert all(a <= b for a, b in zip(sorted(sz), sorted(d["bed"]))), f"{size}: {name} {sz} exceeds the bed"
    # panel thickness ranges of the panel parts
    lo, hi = P["button"]["panel"]
    assert lo <= d["cover_t"] <= hi, f"{size}: cover {d['cover_t']} outside the PV0 panel range {P['button']['panel']}"
    lo, hi = P["led"]["panel"]
    assert lo <= d["cover_t"] <= hi, f"{size}: cover outside the CR-174 panel range"
    assert d["wall"] <= P["dc_jack"]["panel_max"], f"{size}: bottom wall thicker than the 722A takes"
    for g in ("gland_tds", "gland_ds"):
        assert P[g]["thread"] >= d["wall"] + P[g]["nut_b"], f"{size}: {g} thread too short for wall + locknut"
    # the TDS probe's XH plug passes the open M16 gland; the cables seal
    assert d["xh_diag"] <= P["gland_tds"]["clamp"][1], f"{size}: XH plug {d['xh_diag']:.1f} does not pass the TDS gland"
    lo, hi = P["gland_tds"]["clamp"]
    assert lo <= d["tds_cable_sealed"] <= hi, f"{size}: TDS cable + sleeve {d['tds_cable_sealed']} outside {P['gland_tds']['clamp']}"
    lo, hi = P["gland_ds"]["clamp"]
    assert lo <= P["ds18b20"]["cable_d"] <= hi, f"{size}: DS18B20 cable outside the M12 clamp range"
    # electrical ratings
    assert P["pump"]["amps"] <= 1.5 and P["pump"]["volts"] <= 30, f"{size}: pump over the MOSFET 5648 rating"
    lo, hi = P["pololu"]["vin"]
    assert lo <= P["pump"]["volts"] <= hi, f"{size}: 12 V supply outside the Pololu input range"
    # fasteners are stocked; bosses clear pins
    for b in d["bosses"]:
        assert b["length"] is not None, f"{size}: no stocked {b['screw']} for {b['board']}"
        if b["insert"]:
            assert b["length"] <= d["pcb_t"] + d["insert_depth"], f"{size}: {b['board']} M3 bottoms out in its insert"
    for k, b in d["boards"].items():
        if b["boss_vs_pin"] is not None:
            assert b["boss_vs_pin"] >= 0, f"{size}: {k} boss reaches {-b['boss_vs_pin']:.2f} into the pin margin"
    assert d["cover_screw"] is not None and d["pump_screw"] is not None
    if d["mount"] == "wall":
        assert d["plate_bolt_len"] is not None, f"{size}: no stocked M5 for the plate grip {d['plate_bolt_grip']}"
        assert d["plate_bolt_len"] - max(d["plate_bolt_grip"]) >= SCREWS["M5"]["nut_m"] + 0.8, f"{size}: M5 too short at the thick wall"
        assert d["lowest_hole_over_water"] >= d["hole_over_water"], \
            f"{size}: a tote-wall hole sits {d['lowest_hole_over_water']:.0f} mm over the waterline (< {d['hole_over_water']})"
    else:
        assert d["screw_ext"][0] >= 1.0, f"{size}: throat too small: the pad cannot clear a {d['rim_c'][1]} mm wall"
        assert d["screw_len"] is not None, f"{size}: no stocked M6 >= {d['screw_need']:.1f}"
        assert d["knob_z_min"] >= d["H"] + 1.0, f"{size}: knob reaches {d['knob_z_min']:.1f}, under the box top / plate top"
        assert d["hook_bolt_len"] is not None, f"{size}: no stocked M5 for the hook"
        assert d["hook_bolt_tip_x"] <= -1.0, f"{size}: hook bolt tip within 1 mm of the box back"
        assert d["throat"] - SCREWS["M5"]["head_k"] >= d["rim_c"][1], f"{size}: M5 heads in the throat leave less than rim_c max"
        assert d["jaw_over_water"] >= d["hole_over_water"], f"{size}: inner jaw within {d['hole_over_water']} mm of the water"
    for p, r in d["reach"].items():
        assert r["margin"] >= 0, f"{size}: {p} lead short by {-r['margin']:.0f} mm"
    assert d["oled_boss_h"] - P["oled"]["panel_t"] >= 1.0, f"{size}: OLED glass within 1 mm of the window"
    assert d["oled_screw"] is not None, f"{size}: no stocked M2 for the OLED"
    # the OLED bosses are trimmed flat towards the glass; what is left beside the bore must still print
    hz = abs(BOARDS["OLED_938"].holes[0][1])
    glass_edge = P["oled"]["glass"][1] / 2 + abs(P["oled"]["glass_off"][1])
    flat_wall = hz - glass_edge - d["oled_boss_flat"] - d["boards"]["ads"]["bore"] / 2
    assert flat_wall >= 2 * d["nozzle_d"], f"{size}: OLED boss wall at the glass {flat_wall:.2f} < 2 nozzles"
    return d


if __name__ == "__main__":
    for size in SIZES:
        try:
            d = validate(size)
            print(f"{size}: ok")
        except AssertionError as e:
            d = derive(size)
            print(f"{size}: FAIL: {e}")
        print(f"  mount {d['mount']}; box {d['W']} x {d['H']} x {d['D']}, cover {d['cover_outer'][0]:.1f} x "
              f"{d['cover_outer'][1]:.1f}, waterline at box z {d['waterline_z']:.0f} (HDX)")
        if d["mount"] == "wall":
            print(f"  lowest tote hole +{d['lowest_hole_over_water']:.0f}; plate M5x{d['plate_bolt_len']} "
                  f"(grip {d['plate_bolt_grip'][0]:.0f}-{d['plate_bolt_grip'][1]:.0f})")
        else:
            print(f"  rim clamp: container {d['rim_c'][0]}-{d['rim_c'][1]} mm at the screw, M6x{d['screw_len']} ISO 4017 "
                  f"(need {d['screw_need']:.0f}), extension {d['screw_ext'][0]:.0f}-{d['screw_ext'][1]:.0f}; hook M5x"
                  f"{d['hook_bolt_len']}; box top {d['rim_adjust'][0]:.0f}-{d['rim_adjust'][1]:.0f} under the rim; "
                  f"bucket sagitta {d['bucket_sagitta']:.1f} over {d['hook_w']:.0f}; jaw +{d['jaw_over_water']:.0f} over water")
        fmt = lambda v: "n/a" if v is None else f"{v:+.2f}"
        for k, b in d["boards"].items():
            print(f"  {k:8s} {b['name']:19s} screw {b['screw']:4s} bore {b['bore']:.2f}  "
                  f"boss-pin {fmt(b['boss_vs_pin'])}  head-copper {fmt(b['head_vs_copper'])}"
                  f"{'  -> PA screw' if b['nylon_screw'] else ''}")
        for k, b in d["boards"].items():
            print(f"  {k:8s} boss {b['boss_h']:.2f} ({b['governed_by']}), top of parts at x {b['top_x']:.1f}")
        lens = sorted({(b['screw'], b['length']) for b in d['bosses']})
        print(f"  board screws {lens}; cover M3x{d['cover_screw']}; pump M3x{d['pump_screw']}")
        print(f"  XH plug diagonal {d['xh_diag']:.2f} vs M16 clamp max {d['parts']['gland_tds']['clamp'][1]}; "
              f"TDS cable + sleeve {d['tds_cable_sealed']:.1f}")
        for p, r in d["reach"].items():
            print(f"  {p}: lead need {r['need']:.0f} of {r['have']:.0f}, margin {r['margin']:+.0f}")
