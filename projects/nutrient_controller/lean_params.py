"""Nutrient controller, lean revision L1: every number for the logic box.

The analog node split in two flat-mounted prints. The analog front end (SEN0244 TDS, Surveyor pH, ADS1115) is
an open standoff plate, `standoff_plate` ANALOG_NODE. This file is the other part: a low box for the XIAO
ESP32-C3 + Pololu 5 V regulator on their Perma-Proto, the three MOSFET pump drivers and the 12 V jack. No
display, no buttons, no pumps on the box: the node reports over Wi-Fi, and the pumps are a later print.

Mounting. Four keyhole ears flush with the back face take M4 or #8 pan-head screws. The box hangs on a wall
(cable notches down, the main orientation), screws flat to a bench or shelf, or hangs under a shelf or table top
(lid down), and lifts off its screws for service. The lid is one flat plate on four M3 screws; the cables leave
through U-notches in the bottom wall that the lid closes, so a plug never has to pass a hole.

Frame (also the print frame): X across the box, +Y up the wall, +Z out of the wall. z = 0 is the back face,
which is the bed face; the lid sits on the rim at z = D. Body outline x in [-W/2, W/2], y in [0, H].

Tags: VENDOR (sheet named), STANDARD, INFERRED, DESIGN, UNVERIFIED (estimate, tolerated by the design).

    .venv/bin/python projects/nutrient_controller/lean_params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.boards import BOARDS
from cacad.registries.connectors import MATINGS
from cacad.registries.materials import BED, CLEAR_LOOSE, FDM_HOLE_ALLOWANCE, FIT_CLEAR, LAYER, NOZZLE, clearance_bore
from projects.nutrient_controller.params import PARTS as B_PARTS

STATUS = "passes"

# ---------------------------------------------------------------------------
# Fasteners. ISO 4762 socket head, ISO 4032 nuts, ISO 7045 pan head (mount), ISO 7089 washer. `lengths` is the
# stocked ladder. The MOSFET boards take PA (nylon) M2: a metal head would overlap their top copper (1.27 from the
# hole, Eagle), as on standoff_plate MOSFET_5648x3.
# ---------------------------------------------------------------------------
SCREWS = MappingProxyType(dict(
    M2=dict(d=2.0, head_dk=3.8, head_k=2.0, nut_s=4.0, nut_m=1.6, lengths=(4, 5, 6, 8, 10, 12, 16, 20),
            std="ISO 4762 / ISO 4032"),
    M3=dict(d=3.0, head_dk=5.5, head_k=3.0, nut_s=5.5, nut_m=2.4, lengths=(5, 6, 8, 10, 12, 16, 20, 25, 30, 35),
            std="ISO 4762 / ISO 4032"),
    # mount: ISO 7045 M4 pan head. A #8 pan-head wood screw (ASME B18.6.1: 0.164 in = 4.17, head 0.311 in = 7.9) is
    # the same envelope
    M4=dict(d=4.0, head_dk=8.0, head_k=3.1, std="ISO 7045 / #8 wood screw"),
))

# ---------------------------------------------------------------------------
# Bought parts the box is built around (boards come from cacad.registries.boards).
# ---------------------------------------------------------------------------
PARTS = MappingProxyType(dict(
    carrier=dict(board="PERMAPROTO_QUARTER", screw="M2", pa=False,
                 # XIAO on 2.54 headers plus its USB-C shell: B1 drew 7.4 from the spacer, PCB and receptacle; the
                 # header and XIAO PCB are UNVERIFIED, so the box allows 10.0 (standoff_plate PERMAPROTO, concept D)
                 top=10.0),
    driver=dict(board="MOSFET_5648", screw="M2", pa=True,
                top=4.8,                       # Adafruit STEP '5648 MOSFET Driver': the WAGO 2060 terminal
                rest_nearest_pin=3.81),        # rest pad to the JP1 header pin on the -X end, Eagle
    dc_jack=B_PARTS["dc_jack"],                # Switchcraft 722A: hole 7.95, panel <= 3.18, body 11.0 x 15.2 inside
))

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    hole_allow=FDM_HOLE_ALLOWANCE,     # diametral: added to every vendor panel-hole size (materials)
    fit_clear=FIT_CLEAR,               # radial: printed opening around a bought part's head or body (materials)
    air=2.0,                           # DESIGN: board or bought-part envelope to a wall, a column or another envelope
    board_air=1.0,                     # DESIGN: pin tails under a board to the back plate
    underside=3.5,                     # DESIGN allowance: trimmed through-hole tails under every board (standoff_plate)
    boss_pin_margin=1.0,               # DESIGN: boss outer radius stays this far inside a board's nearest pin
    boss_wall=1.6,                     # DESIGN: 4 perimeters round the M2 bore
    nut_pocket_clear=0.3,              # DESIGN: across flats, hex pocket - nut
    nut_pocket_extra=0.8,              # DESIGN: pocket depth - nut m; the screw tip lands in this window
    screw_tip_min=0.4,                 # DESIGN: a screw tip stays this far inside the back (bed) face
    plug_finger=5.0,                   # DESIGN: room beyond a plug to grip it (nutrient_controller COMMON)
    wire_room=5.0,                     # DESIGN: wire bends between the tallest part and the lid
    rest_pad_d=4.0,                    # DESIGN: pad under the hole-less end of a MOSFET board
    # --- geometry rules ---
    wall=2.4,                          # DESIGN: 6 perimeters; the jack nut clamps it (722A panel <= 3.18)
    web=1.2,                           # DESIGN: back plate over an M2 nut pocket (6 layers)
    corner_r=4.0,                      # DESIGN: outer vertical edges
    lid_t=2.4,                         # DESIGN
    column_d=10.0,                     # DESIGN: lid-screw column in each inner corner
    column_sink=0.6,                   # DESIGN: columns sunk into both walls, never tangent (FINDINGS F31)
    teardrop_cap=0.6,                  # DESIGN: the jack's horizontal hole is cut flat this far above r
    nozzle_d=NOZZLE, layer=LAYER, min_wall=1.2, bed=BED, material="PETG",
))

PRINT_ORIENTATION = MappingProxyType(dict(
    body=dict(up=(0, 0, 1), bed_face="back face", bed_z="0",
              known_overhangs=["M2 and M3 nut-pocket ceilings (bridged)", "jack hole: truncated teardrop, apex +z"]),
    lid=dict(up=(0, 0, -1), bed_face="outer face", bed_z="lid_top", known_overhangs=[]),
))

# ---------------------------------------------------------------------------
# L1 inputs. Every one is a DESIGN choice; validate() checks the ones a requirement bounds.
# ---------------------------------------------------------------------------
L1 = MappingProxyType(dict(
    jst_gap=10.5,          # carrier edge to the drivers' JST PH end: the plug plus finger room (validate)
    driver_gap=4.0,        # between the three drivers; their bosses stay apart (validate)
    right_strip=12.0,      # drivers' WAGO end to the +X wall: wire entry, clear of the corner columns (validate)
    cable_zone=18.0,       # bottom wall to the lowest board: the jack body, cable bends to the notches (validate)
    # bottom-wall cable notches, open to the rim and closed by the lid: (name, x offset, from what)
    notch=(6.0, 6.0),      # (width, depth from the rim): a 3-7 mm cable lies in it; a cable tie inside is the strain relief
    notches=(("I2C", -8.0, "carrier"), ("DS18B20", 8.0, "carrier"),
             ("P1", -8.0, "drivers"), ("P2", 0.0, "drivers"), ("P3", 8.0, "drivers")),
    # keyhole ears on the +-X walls, flush with the back face
    ear_t=5.0,             # thickness; the box hangs on the screw heads by it
    ear_wall=2.4,          # material round the keyhole
    keyhole_slide=8.0,     # big hole centre to the slot's top (the rest position of the screw)
))

# The pump outputs, as the sprout-cut `nutrient-analog-xiao` env drives them (panel_params.PINS on concept D)
PUMPS = MappingProxyType(dict(P1="acid (D1)", P2="nutrient A (D2)", P3="nutrient B (D3)"))


def _stock(lengths, lo, hi):
    """Shortest stocked length in [lo, hi], or None."""
    ok = [L for L in lengths if lo - 1e-9 <= L <= hi + 1e-9]
    return min(ok) if ok else None


def _rect_circle_gap(rect, centre, r):
    """Distance from a circle's edge to an axis-aligned rectangle (x0, x1, y0, y1); negative = overlap."""
    x0, x1, y0, y1 = rect
    dx = max(x0 - centre[0], 0.0, centre[0] - x1)
    dy = max(y0 - centre[1], 0.0, centre[1] - y1)
    return math.hypot(dx, dy) - r


def derive(**overrides) -> dict:
    """Every number lean_box.py and the tests need. Overrides are for planted-defect tests and what-ifs only."""
    s, c = dict(L1), dict(COMMON)
    for k, v in overrides.items():
        assert k in s or k in c, f"unknown key {k}"
        (s if k in s else c)[k] = v
    d = dict(**s, **c)
    d["screws"], d["parts"] = SCREWS, PARTS
    w = c["wall"]
    m2, m3 = SCREWS["M2"], SCREWS["M3"]

    # --- back plate and M2 board bosses (nut pockets open to the back face, as standoff_plate) ---
    # ISO 273 has no M2 row: 0.4 diametral as M3 medium (CLEAR_LOOSE), without the FDM allowance, as standoff_plate.
    # With it the boss (5.8) would reach the Perma-Proto's nearest via (3.81 - 1.0 margin = 2.81 > 2.9). The screw
    # only passes through to its nut, so a bore printed 0.2 under still passes M2.
    d["m2_bore"] = m2["d"] + CLEAR_LOOSE
    d["m2_boss_d"] = d["m2_bore"] + 2 * c["boss_wall"]
    d["m2_pocket"] = dict(s=m2["nut_s"] + c["nut_pocket_clear"], depth=m2["nut_m"] + c["nut_pocket_extra"])
    d["back_t"] = round(math.ceil((d["m2_pocket"]["depth"] + c["web"]) / c["layer"] - 1e-9) * c["layer"], 6)
    # standoff: max() of the underside clearance and a stocked M2 landing its tip in the pocket window on every board
    tks = {k: BOARDS[PARTS[k]["board"]].thickness for k in ("carrier", "driver")}
    needs = {"underside clearance": c["underside"] + c["board_air"]}
    h = math.ceil(needs["underside clearance"] / c["layer"] - 1e-9) * c["layer"]
    for _ in range(200):
        Ls = {}
        for k, t in tks.items():
            stack = d["back_t"] + h + t
            Ls[k] = _stock(m2["lengths"], stack - d["m2_pocket"]["depth"] + m2["nut_m"], stack - c["screw_tip_min"])
        if all(Ls.values()):
            break
        h += c["layer"]
    else:
        raise AssertionError("no stocked M2 length fits any standoff")
    needs["stock M2 length"] = round(h, 6)
    d["standoff_governed_by"], d["standoff"] = max(needs.items(), key=lambda kv: kv[1])
    d["standoff_needs"], d["m2_len"] = needs, Ls
    d["z_board"] = d["back_t"] + d["standoff"]                      # board underside
    d["board_t"] = tks

    # --- layout in the cavity, from the boards (inner-local: cavity corner at 0, 0) ---
    car, drv = BOARDS[PARTS["carrier"]["board"]], BOARDS[PARTS["driver"]["board"]]
    a = c["air"]
    col_h = 3 * drv.size[1] + 2 * s["driver_gap"]
    Wi = a + car.size[0] + s["jst_gap"] + drv.size[0] + s["right_strip"]
    # cavity height: max() of the drivers' stack and the carrier under the top-left lid column (rule 7)
    keep = c["column_d"] - c["column_sink"]
    d["height_needs"] = {"driver stack": col_h + a, "carrier under the lid column": car.size[1] + keep + a}
    d["height_governed_by"], top_need = max(d["height_needs"].items(), key=lambda kv: kv[1])
    Hi = s["cable_zone"] + top_need
    W, H = Wi + 2 * w, Hi + 2 * w
    d["W"], d["H"] = W, H
    d["inner_x"], d["inner_y"] = (-Wi / 2, Wi / 2), (w, H - w)
    X = lambda u: u - Wi / 2                                       # inner-local -> body frame
    Y = lambda v: v + w
    carrier_c = (X(a + car.size[0] / 2), Y(s["cable_zone"] + car.size[1] / 2))   # bottom-aligned with the drivers
    drv_x = X(a + car.size[0] + s["jst_gap"] + drv.size[0] / 2)
    drivers = [(drv_x, Y(s["cable_zone"] + drv.size[1] / 2 + i * (drv.size[1] + s["driver_gap"]))) for i in range(3)]
    d["drivers_x"] = (drv_x - drv.size[0] / 2, drv_x + drv.size[0] / 2)

    def placed(key, board, centre, name):
        x, y = centre
        sx, sy = board.size
        p = PARTS[key]
        pl = dict(key=key, name=name, board=board, centre=centre, rect=(x - sx / 2, x + sx / 2, y - sy / 2, y + sy / 2),
                  holes=[(x + u, y + v) for u, v in board.holes], t=tks[key], top=p["top"], screw=p["screw"], pa=p["pa"],
                  m2_len=Ls[key], rests=[])
        us = [u for u, _ in board.holes]
        if all(u > 0 for u in us) or all(u < 0 for u in us):       # holes on one end: rest pads under the other
            pl["rests"] = [(x - u, y + v) for u, v in board.holes]
        pl["conns"] = []
        for cn in board.connectors:
            m = MATINGS[cn.kind]
            mouth = (x + cn.x + cn.facing[0] * m.header_depth / 2, y + cn.y + cn.facing[1] * m.header_depth / 2)
            pl["conns"].append(dict(kind=cn.kind, mating=m, facing=cn.facing, mouth=mouth,
                                    reach=m.plug_len + c["plug_finger"]))
        return pl

    d["boards"] = [placed("carrier", car, carrier_c, "carrier")] + \
                  [placed("driver", drv, xy, f"P{i + 1}") for i, xy in enumerate(drivers)]
    d["bosses"] = [dict(at=h_, board=b["name"], len=b["m2_len"]) for b in d["boards"] for h_ in b["holes"]]
    d["rest_pads"] = [dict(at=r, board=b["name"]) for b in d["boards"] for r in b["rests"]]

    # --- depth: max() of what stands on the boards and a stocked M3 lid screw landing in its pocket window ---
    d["m3_bore"] = clearance_bore("M3")
    d["m3_pocket"] = dict(s=m3["nut_s"] + c["nut_pocket_clear"], depth=m3["nut_m"] + c["nut_pocket_extra"])
    tip = (c["screw_tip_min"] + d["m3_pocket"]["depth"] - m3["nut_m"]) / 2   # middle of the tip window
    content = max(d["z_board"] + b["t"] + b["top"] for b in d["boards"]) + c["wire_room"]
    L = min(L for L in m3["lengths"] if L + tip - c["lid_t"] >= content - 1e-9)
    d["lid_screw_len"] = L
    d["D"] = round(L + tip - c["lid_t"], 6)
    d["depth_needs"] = {"tallest part + wire room": content, f"M3 x {L} lid screw": d["D"]}
    d["depth_governed_by"] = max(d["depth_needs"].items(), key=lambda kv: kv[1])[0]
    d["lid_screw_tip"] = d["D"] + c["lid_t"] - L
    d["lid_top"] = d["D"] + c["lid_t"]

    # --- lid-screw columns in the inner corners ---
    off = c["column_d"] / 2 - c["column_sink"]
    (xi0, xi1), (yi0, yi1) = d["inner_x"], d["inner_y"]
    d["columns"] = [(xi0 + off, yi0 + off), (xi1 - off, yi0 + off), (xi0 + off, yi1 - off), (xi1 - off, yi1 - off)]

    # --- bottom wall: the jack between the carrier and the drivers, the notches under what they serve ---
    jk = PARTS["dc_jack"]
    d["jack_hole"] = jk["hole"] + c["hole_allow"]
    d["jack"] = dict(x=(d["boards"][0]["rect"][1] + d["drivers_x"][0]) / 2,
                     z=d["back_t"] + c["board_air"] + jk["body_d"] / 2, body_d=jk["body_d"], body_l=jk["body_l"])
    nw, nd = s["notch"]
    ref = dict(carrier=carrier_c[0], drivers=drv_x)
    d["notch_list"] = [dict(name=n, x=ref[r] + dx, w=nw, z0=d["D"] - nd) for n, dx, r in s["notches"]]

    # --- keyhole ears (+-X walls, flush with the back face) ---
    m4 = SCREWS["M4"]
    d["keyhole_slot"] = clearance_bore("M4")
    d["keyhole_big"] = m4["head_dk"] + 2 * c["fit_clear"] + c["hole_allow"]
    ew = d["keyhole_big"] + 2 * s["ear_wall"]                      # ear length beyond the wall
    eh = s["keyhole_slide"] + (d["keyhole_big"] + d["keyhole_slot"]) / 2 + 2 * s["ear_wall"]
    d["ear_size"] = (ew, eh)
    y_lo, y_hi = c["corner_r"], H - c["corner_r"] - eh               # ears clear the outer corner rounding
    d["ears"] = []
    for sx in (-1, 1):
        for y0 in (y_lo, y_hi):
            x = sx * (W / 2 + ew / 2)
            rest = y0 + s["ear_wall"] + d["keyhole_big"] / 2 + s["keyhole_slide"]
            d["ears"].append(dict(side=sx, y=(y0, y0 + eh), x=(W / 2 if sx > 0 else -W / 2 - ew, W / 2 + ew if sx > 0 else -W / 2),
                                  rest=(x, rest), big=(x, rest - s["keyhole_slide"])))
    rx = sorted({round(e["rest"][0], 3) for e in d["ears"]})
    ry = sorted({round(e["rest"][1], 3) for e in d["ears"]})
    d["mount_pitch"] = (rx[-1] - rx[0], ry[-1] - ry[0])

    # --- what the print checks read ---
    cap = lambda dia: dia / 2 + c["teardrop_cap"]
    d["body_overhang_exceptions"] = [("M2 nut pocket ceilings", d["m2_pocket"]["depth"]),
                                     ("M3 nut pocket ceilings", d["m3_pocket"]["depth"]),
                                     ("jack hole flat", d["jack"]["z"] + cap(d["jack_hole"]))]
    d["print_orientation"] = {k: dict(v, bed_z=0.0 if v["bed_z"] == "0" else d[v["bed_z"]]) for k, v in PRINT_ORIENTATION.items()}
    d["walls"] = {"body wall": w, "back over M2 pocket": d["back_t"] - d["m2_pocket"]["depth"], "lid": c["lid_t"],
                  "M2 boss": c["boss_wall"], "column round M3 pocket": c["column_d"] / 2 - d["m3_pocket"]["s"] / math.sqrt(3),
                  "ear round keyhole": s["ear_wall"]}
    d["walls"] = {k: round(v, 6) for k, v in d["walls"].items()}
    d["printed_sizes"] = {"body": (W + 2 * ew, H, d["D"]), "lid": (W, H, c["lid_t"])}
    return d


def validate(**overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(**overrides)
    a = d["air"]
    for name, size in d["printed_sizes"].items():
        assert all(u <= v for u, v in zip(sorted(size), sorted(d["bed"]))), f"{name} {size} exceeds the bed"
    for name, t in d["walls"].items():
        assert t >= d["min_wall"] and t >= 2 * d["nozzle_d"], f"wall {name} = {t:.2f}"
    # boards: bosses inside the pin margin, heads on copper only if nylon, every board inside the cavity and apart
    for b in d["boards"]:
        bd = b["board"]
        assert SCREWS["M2"]["d"] < bd.hole_dia, f"{b['name']}: hole {bd.hole_dia} does not pass M2"
        assert d["m2_boss_d"] / 2 <= bd.nearest_pin - d["boss_pin_margin"], f"{b['name']}: boss reaches a pin"
        assert b["pa"] or SCREWS["M2"]["head_dk"] / 2 <= bd.nearest_top_copper, f"{b['name']}: metal head on top copper"
        if b["rests"]:
            assert d["rest_pad_d"] / 2 <= PARTS[b["key"]]["rest_nearest_pin"] - d["boss_pin_margin"], f"{b['name']}: rest pad on a pin"
        x0, x1, y0, y1 = b["rect"]
        (xi0, xi1), (yi0, yi1) = d["inner_x"], d["inner_y"]
        assert x0 - xi0 >= a - 1e-9 and xi1 - x1 >= a - 1e-9 and yi1 - y1 >= a - 1e-9, f"{b['name']} within {a} of a wall"
        assert y0 - yi0 >= d["cable_zone"] - 1e-9
        for col in d["columns"]:
            g = _rect_circle_gap(b["rect"], col, d["column_d"] / 2)
            assert g >= a - 1e-9, f"{b['name']} {g:.2f} from the lid column at ({col[0]:.1f}, {col[1]:.1f}); needs {a}"
    rects = [b["rect"] for b in d["boards"]]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            p, q = rects[i], rects[j]
            gap = max(q[0] - p[1], p[0] - q[1], q[2] - p[3], p[2] - q[3])
            assert gap >= a - 1e-9 or gap >= d["driver_gap"] - 1e-9, f"boards {i}, {j} {gap:.2f} apart"
    pts = [(b["at"], d["m2_boss_d"] / 2) for b in d["bosses"]] + [(r["at"], d["rest_pad_d"] / 2) for r in d["rest_pads"]]
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            gap = math.dist(pts[i][0], pts[j][0]) - pts[i][1] - pts[j][1]
            assert gap >= d["min_wall"], f"bosses/pads {pts[i][0]} and {pts[j][0]} leave {gap:.2f}"
    # every driver's JST PH plug has its plug + finger room before the carrier
    car = d["boards"][0]
    for b in d["boards"][1:]:
        for cn in b["conns"]:
            room = (cn["mouth"][0] - car["rect"][1]) if cn["facing"] == (-1, 0) else math.inf
            assert room >= cn["reach"] - 1e-9, f"{b['name']} {cn['kind']} has {room:.2f} to the carrier; plug needs {cn['reach']:.2f}"
    # the jack body fits under the boards, between the bottom columns
    jk = d["jack"]
    assert d["cable_zone"] >= jk["body_l"] + a - 1e-9, f"cable zone {d['cable_zone']} < jack body {jk['body_l']} + {a}"
    jr = (jk["x"] - jk["body_d"] / 2, jk["x"] + jk["body_d"] / 2, d["inner_y"][0], d["inner_y"][0] + jk["body_l"])
    for col in d["columns"]:
        assert _rect_circle_gap(jr, col, d["column_d"] / 2) >= a - 1e-9, "jack body at a lid column"
    assert jk["z"] + jk["body_d"] / 2 + a <= d["D"], "jack body above the rim"
    assert d["wall"] <= PARTS["dc_jack"]["panel_max"], "wall thicker than the jack's panel range"
    # bottom wall: notches, jack hole and columns apart by min_wall, all inside the cavity span
    spans = [(n["x"] - n["w"] / 2, n["x"] + n["w"] / 2, n["name"]) for n in d["notch_list"]]
    spans.append((jk["x"] - d["jack_hole"] / 2, jk["x"] + d["jack_hole"] / 2, "jack"))
    xi0, xi1 = d["inner_x"]
    spans.append((-math.inf, xi0 + d["column_d"] - d["column_sink"], "column"))
    spans.append((xi1 - d["column_d"] + d["column_sink"], math.inf, "column"))
    spans.sort()
    for (a0, a1, n0), (b0, b1, n1) in zip(spans, spans[1:]):
        assert b0 - a1 >= d["min_wall"], f"bottom wall: {n0} and {n1} leave {b0 - a1:.2f}"
    assert d["notch"][1] < d["D"] - d["back_t"], "notch deeper than the wall"
    # right strip: the drivers' WAGO ends clear the top-right column (checked above); the screws are stocked
    assert d["lid_screw_tip"] >= d["screw_tip_min"] - 1e-9 and d["lid_screw_tip"] <= d["m3_pocket"]["depth"] - SCREWS["M3"]["nut_m"] + 1e-9
    assert d["lid_screw_len"] in SCREWS["M3"]["lengths"]
    # the keyhole: the head passes the big hole, the slot holds the shank under the head, the ears clear the corners
    m4 = SCREWS["M4"]
    assert d["keyhole_big"] > m4["head_dk"] and d["keyhole_slot"] < m4["head_dk"] - 2 * 1.0, "keyhole does not hold the head"
    assert d["keyhole_slot"] > m4["d"], "keyhole slot does not pass the shank"
    lo, hi = sorted(e["y"] for e in d["ears"] if e["side"] > 0)
    assert hi[0] - lo[1] >= 0, "ears overlap"
    return d


def report() -> str:
    d = validate()
    m2, m3 = SCREWS["M2"], SCREWS["M3"]
    ew, eh = d["ear_size"]
    n_pa = sum(len(b["holes"]) for b in d["boards"] if b["pa"])
    n_m2 = sum(len(b["holes"]) for b in d["boards"] if not b["pa"])
    lines = [
        f"L1 logic box: {d['W']:.1f} x {d['H']:.1f} x {d['D']:.1f} (+ lid {d['lid_t']}), ears to {d['W'] + 2 * ew:.1f} wide; "
        f"depth governed by '{d['depth_governed_by']}' "
        + ", ".join(f"{k} {v:.2f}" for k, v in d["depth_needs"].items()),
        f"  back {d['back_t']:.2f}, standoff {d['standoff']:.2f} governed by '{d['standoff_governed_by']}', board underside z {d['z_board']:.2f}",
        "  boards: " + ", ".join(f"{b['name']} {b['board'].name} at ({b['centre'][0]:.1f}, {b['centre'][1]:.1f})" for b in d["boards"]),
        f"  jack at x {d['jack']['x']:.1f}, z {d['jack']['z']:.1f}, hole {d['jack_hole']:.2f}; notches "
        + ", ".join(f"{n['name']} x {n['x']:.1f}" for n in d["notch_list"]) + f", {d['notch'][0]} wide, {d['notch'][1]} deep",
        f"  keyholes: big {d['keyhole_big']:.2f}, slot {d['keyhole_slot']:.2f}, slide {d['keyhole_slide']}, ears {ew:.1f} x {eh:.1f} x {d['ear_t']}; "
        f"screw pitch {d['mount_pitch'][0]:.1f} x {d['mount_pitch'][1]:.1f} (drive the screws to stand {d['ear_t'] + 0.5:.1f} proud)",
        "  hardware: " + "; ".join([
            f"{n_m2} x M2 x {d['boards'][0]['m2_len']} {m2['std']} + nut (carrier)",
            f"{n_pa} x M2 x {d['boards'][1]['m2_len']} PA (nylon) + nut (drivers)",
            f"4 x M3 x {d['lid_screw_len']} {m3['std']} + nut (lid)",
            f"4 x M4 / #8 pan head (mount)", "Switchcraft 722A jack"]),
        "  pumps (later print): " + ", ".join(f"{k} {v}" for k, v in PUMPS.items()),
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
