"""Standoff plate family: a flat plate with printed bosses that carries one or
more boards from cacad.registries.boards on M-screws with a hex nut captured
in a pocket under the plate. With `tray=True` the plate grows walls, and each
board-edge connector in the registry gets a wall opening sized from its plug.

Axis convention: Z up, Z=0 is the plate's bottom (bed) face. Bosses rise from
the plate top; the board sits on the boss tops at z = plate_t + standoff_h.
Screws go in from the board top; the nut sits in a hex pocket open to the
bed face, so the plate stands flat and nothing needs support.

    z = wall_top_z                                tray rim (tray only)
    z = plate_t + standoff_h + board_t + head_k   screw head top
    z = plate_t + standoff_h                      board underside on boss tops
    z = plate_t                                   plate top
    z = pocket_depth                              nut pocket ceiling (declared ceiling)
    z = 0                                         bed face

Everything downstream (plate.py, tests) reads `derive(plate)`.
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.boards import BOARDS
from cacad.registries.connectors import MATINGS
from cacad.registries.materials import CLEAR_LOOSE, LAYER, NOZZLE, WALL

# ---------------------------------------------------------------------------
# Bought hardware. ISO 4032 hex nuts (s = across flats, m = height) and
# ISO 4762 socket-head cap screws (dk = head dia, k = head height, lengths =
# the stocked ladder). A pan head (ISO 7045) is lower and wider; if that is
# what is on hand, change the row, not the derive().
# ---------------------------------------------------------------------------
SCREWS = MappingProxyType(dict(
    M2=dict(d=2.0, pitch=0.40, nut_s=4.0, nut_m=1.6, head_dk=3.8, head_k=2.0, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
    M2_5=dict(d=2.5, pitch=0.45, nut_s=5.0, nut_m=2.0, head_dk=4.5, head_k=2.5, lengths=(4, 5, 6, 8, 10, 12, 16, 20)),
    M3=dict(d=3.0, pitch=0.50, nut_s=5.5, nut_m=2.4, head_dk=5.5, head_k=3.0, lengths=(5, 6, 8, 10, 12, 16, 20, 25)),
))

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    screw_clearance=CLEAR_LOOSE,      # diametral: plate/boss bore - screw nominal (ISO 273 medium M3)
    nut_pocket_clearance=0.30,        # across flats: pocket - nut s. UNVERIFIED: hex-pocket coupon
    nut_pocket_extra_depth=0.80,      # pocket depth - nut m: room for the screw tip window (>= screw_tip_min + a layer step)
    board_air_gap=1.0,                # lowest underside feature (pin tail) to plate top
    boss_pin_margin=1.0,              # boss outer radius stays this far from a pin centre: pin half 0.32 + solder fillet. UNVERIFIED
    screw_tip_min=0.40,               # screw tip stays this far above the bed face: one pitch of length tolerance, plate stands flat
    finger_room=10.0,                 # clear space beyond an unplugged plug, to grab it. Design choice, UNVERIFIED
    opening_clearance=1.0,            # each side of the plug width, wall opening
    opening_below=0.5,                # wall opening floor below the board top, so the plug slides in level
    board_wall_gap=1.0,               # board edge to inner wall face (tray)
    lid_clearance=3.0,                # rim above the tallest top-side thing (tray). Design choice, UNVERIFIED
    hole_line_centre_tol=1.0,         # two-hole boards: the hole line passes within this of the outline centre
    mount_screw_clearance=CLEAR_LOOSE,  # diametral: plate mount bore - mount screw nominal (ISO 273 medium M3)
    mount_access_clearance=0.5,       # plan: mount screw head edge to the nearest board outline, so a driver goes straight down. DESIGN
    mount_head_seat=0.5,              # plan: mount screw head edge to the plate edge, the head bears fully on the plate. DESIGN
    # --- geometry rules ---
    boss_wall=WALL,                   # 1.6 = 4 perimeters around the bore
    pocket_web_min=1.2,               # plate material above the nut pocket (bridged ceiling) = min_wall, 6 layers
    plate_min_t=2.0,                  # stiffness floor for the plate itself
    plate_margin=3.0,                 # flat plate: edge beyond every board outline
    wall=WALL,                        # tray wall, 4 perimeters
    corner_r=2.0,                     # plate vertical corner radius
    chamfer_bore=0.4,                 # cosmetic lead-in at the boss top
    chamfer_fallbacks=(0.3, 0.2),
    # --- manufacturing rules ---
    nozzle_d=NOZZLE,
    layer=LAYER,
    min_wall=1.2,
    max_overhang_deg=60.0,
    bbox_tol=0.05,
))

PRINT_ORIENTATION = MappingProxyType(dict(
    plate=dict(up=(0, 0, 1), bed_face="plate bottom", bed_z="0",
               known_overhangs=["nut_pocket_ceiling"],       # annulus bore..hex over each pocket, bridged
               overhang_exceptions=[("nut_pocket_ceiling", "pocket_depth")]),
    # a tray's openings are U-slots from the rim: no ceilings beyond the pockets
))

# ---------------------------------------------------------------------------
# Family axis: one entry per plate. Inputs only. `placements` are board
# outline centres on the plate; `board_t` and `underside_protrusion` are
# caliper values for the boards as soldered (a header tail is ~3 mm).
# ---------------------------------------------------------------------------
_ADS = dict(screw="M2",
            board_t=1.6,               # UNVERIFIED: caliper the board
            underside_protrusion=3.5,  # UNVERIFIED: caliper the soldered header tails
            top_protrusion=2.5)        # UNVERIFIED: caliper; header insulator if pins are down, pin tips if up

PLATES = {
    "ADS1115": dict(_ADS, placements=(("ADS1115", (0.0, 0.0)),), tray=False),
    # two boards end to end, 6 mm apart, as projects/mount_plate/enclosure.py had them:
    # the inner STEMMA QT connectors face each other across the gap. Kept to show validate() refusing it.
    "ADS1115x2": dict(_ADS, placements=(("ADS1115", (-15.7, 0.0)), ("ADS1115", (15.7, 0.0))), tray=False),
    # two boards side by side along their long edges, 4 mm apart; every connector faces an end wall
    "ADS1115x2_tray": dict(_ADS, placements=(("ADS1115", (0.0, -10.89)), ("ADS1115", (0.0, 10.89))), tray=True),
    "ADS1115_V1": dict(_ADS, placements=(("ADS1115_V1", (0.0, 0.0)),), tray=False),   # two-hole revision, see validate()
    "UNO_R3": dict(_ADS, placements=(("UNO_R3", (0.0, 0.0)),), screw="M3", tray=False),
    # --- boards added 2026-09-21 ---
    "INA219": dict(_ADS, placements=(("INA219", (0.0, 0.0)),), tray=False),
    "TCA9548A": dict(_ADS, placements=(("TCA9548A", (0.0, 0.0)),), tray=False),
    "BME280": dict(_ADS, placements=(("BME280", (0.0, 0.0)),), tray=False),             # holes on one edge, see validate()
    "FEATHER": dict(_ADS, placements=(("FEATHER_ESP32S3", (0.0, 0.0)),), tray=False),
    "FEATHER_tray": dict(_ADS, placements=(("FEATHER_ESP32S3", (0.0, 0.0)),), tray=True),   # blocked: USB-C plug envelope
    # sensor hub: power monitor, two ADCs and the I2C mux in one column, every STEMMA QT mouth to a side wall,
    # 4 mm between boards. The Feather joins it when the USB-C plug envelope is in the connector registry.
    "SENSOR_HUB_tray": dict(_ADS, placements=(
        ("INA219", (0.0, 0.0), 0),
        ("ADS1115", (0.0, 23.05), 0),
        ("ADS1115", (0.0, 44.83), 0),
        ("TCA9548A", (0.0, 66.61), 90),
    ), tray=True),
    # --- 2026-10-07: DFRobot Gravity analog TDS board on M3 + ISO 4032 nuts. The board thickness is
    # not published; the layout shows SMD parts only and no underside, so underside_protrusion is a
    # DESIGN allowance that also clears through-hole tails if the board has any.
    "SEN0244": dict(screw="M3",
                    board_t=1.6,                # UNVERIFIED: not published, standard FR-4
                    underside_protrusion=3.5,   # DESIGN allowance, UNVERIFIED: underside not drawn
                    top_protrusion=6.0,         # UNVERIFIED: XH header height; tray only
                    placements=(("SEN0244", (0.0, 0.0)),), tray=False,
                    mount=dict(screw="M3", sides="Y")),   # connectors face ±X: mount strips on ±Y
    # Two Atlas isolated EZO carriers (pH + EC) side by side, 4 mm apart (DESIGN), SMAs to -Y, headers to +Y.
    # The board hole is 3.0, so M3 is refused; M2 is on hand (enclosure_atlas/NOTES.md) and M2.5 also passes.
    "EZO_ISO_x2": dict(screw="M2",
                       board_t=1.6,                 # Atlas STEP 1.59
                       underside_protrusion=3.5,    # DESIGN allowance: STEP max 2.51 (4-pin part), SMA 2.0; header tails UNVERIFIED
                       top_protrusion=10.0,         # Atlas STEP 4-pin part; EZO on its 8.7 sockets UNVERIFIED. Tray only
                       placements=(("EZO_CARRIER_ISO", (-18.0, 0.0)), ("EZO_CARRIER_ISO", (18.0, 0.0))), tray=False,
                       mount=dict(screw="M3", sides="X")),   # SMA and header face ±Y: mount strips on ±X
}

ACTIVE_PLATES = ("ADS1115", "ADS1115x2_tray", "INA219", "TCA9548A", "FEATHER", "SENSOR_HUB_tray", "SEN0244", "EZO_ISO_x2")


def _round_up(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 6)


_SIDES = {(1, 0): "+X", (-1, 0): "-X", (0, 1): "+Y", (0, -1): "-Y"}


def _rot(v, rot):
    """Rotate a board-frame vector by a multiple of 90 degrees."""
    x, y = v
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[rot % 360]


def _placed(board, xy, rot):
    """A board on the plate: (registry Board, centre, rotation) plus its
    world-frame size, holes and connector origins, so nothing downstream
    rotates anything itself."""
    assert rot % 90 == 0, f"{board.name}: rotation {rot} is not a multiple of 90"
    sx, sy = board.size
    size = (sx, sy) if rot % 180 == 0 else (sy, sx)
    holes = [(xy[0] + hx, xy[1] + hy) for hx, hy in (_rot(h, rot) for h in board.holes)]
    conns = [(xy[0] + cx, xy[1] + cy, _rot(cn.facing, rot), cn) for (cx, cy), cn in ((_rot((cn.x, cn.y), rot), cn) for cn in board.connectors)]
    return dict(board=board, name=board.name, xy=tuple(xy), rot=rot, size=size, holes=holes, connectors=conns)


def _connector(d: dict, pb: dict, x: float, y: float, facing, cn) -> dict:
    """World-frame envelopes for one connector. The mouth is header_depth/2
    from the connector origin along its facing; the plug sits on the board
    top from the mouth outward; the reach adds finger_room. `faces` is the
    wall side it looks at, or the name of the board in the way, with the
    distance from the mouth to it along the facing."""
    m = MATINGS[cn.kind]
    fx, fy = facing
    mouth = (x + fx * m.header_depth / 2, y + fy * m.header_depth / 2)
    half_w = (m.plug_w if m.plug_known else m.header_len) / 2
    # distance along the facing from the mouth to the nearest other board whose outline overlaps the plug width
    blockers = []
    for ob in d["boards"]:
        if ob is pb:
            continue
        (bx, by), bsize = ob["xy"], ob["size"]
        along = (bx - mouth[0]) * fx + (by - mouth[1]) * fy - (bsize[0] / 2 if fx else bsize[1] / 2)
        across = abs((by - mouth[1]) * fx - (bx - mouth[0]) * fy)   # perpendicular offset of the board centre
        half_b = bsize[1] / 2 if fx else bsize[0] / 2
        if along > 0 and across - half_b < half_w:
            blockers.append((along, ob["name"]))
    to_wall = ((d["plate_x1"] if fx > 0 else d["plate_x0"]) - mouth[0]) * fx if fx else ((d["plate_y1"] if fy > 0 else d["plate_y0"]) - mouth[1]) * fy
    to_wall -= d["margin"] - d["board_wall_gap"] if d["tray"] else 0.0   # inner wall face, if there is a wall
    faces, dist = (_SIDES[(fx, fy)], to_wall)
    if blockers and min(blockers)[0] < to_wall:
        dist, faces = min(blockers)
    return dict(kind=cn.kind, mating=m, board=pb["name"], xy=(x, y), facing=(fx, fy), mouth=mouth, faces=faces, distance=dist,
                plug=(mouth, m.plug_len, m.plug_w, m.plug_h) if m.plug_known else None,
                reach=m.plug_len + d["finger_room"] if m.plug_known else None)


def _opening_span(d: dict, o: dict) -> tuple[float, float]:
    """(lo, hi) of an opening along its wall."""
    c = o["centre"][1] if o["side"] in ("+X", "-X") else o["centre"][0]
    return c - o["width"] / 2, c + o["width"] / 2


def derive(plate: str, **overrides) -> dict:
    """Every dimension plate.py and the tests need. Overrides are for what-if tables only."""
    s = dict(PLATES[plate])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(plate=plate, **s, **c)
    sc = dict(SCREWS[s["screw"]])
    d["screw_spec"] = sc
    d["boards"] = [_placed(BOARDS[pl[0]], pl[1], pl[2] if len(pl) > 2 else 0) for pl in s["placements"]]

    # bore, boss, pocket
    d["bore_d"] = sc["d"] + c["screw_clearance"]
    d["boss_r"] = d["bore_d"] / 2 + c["boss_wall"]
    d["boss_d"] = 2 * d["boss_r"]
    d["pocket_s"] = sc["nut_s"] + c["nut_pocket_clearance"]          # across flats
    d["pocket_r"] = d["pocket_s"] / (2 * math.cos(math.radians(30)))  # circumscribed radius
    d["pocket_depth"] = sc["nut_m"] + c["nut_pocket_extra_depth"]
    d["plate_t"] = _round_up(max(c["plate_min_t"], d["pocket_depth"] + c["pocket_web_min"]), c["layer"])
    d["pocket_web"] = round(d["plate_t"] - d["pocket_depth"], 6)

    # standoff height: max() of the competing needs, winner recorded
    needs = {"underside clearance": s["underside_protrusion"] + c["board_air_gap"]}
    # a stock screw must reach through the nut (tip >= nut bottom) without
    # passing the bed face: L in [stack - pocket_depth + nut_m, stack], where
    # stack = board_t + standoff_h + plate_t. Raise the standoff, in layer
    # steps, until a stocked length lands in that window.
    h = _round_up(needs["underside clearance"], c["layer"])
    for _ in range(400):
        stack = s["board_t"] + h + d["plate_t"]
        lo, hi = stack - d["pocket_depth"] + sc["nut_m"], stack - c["screw_tip_min"]
        fit = [L for L in sc["lengths"] if lo - 1e-9 <= L <= hi + 1e-9]
        if fit:
            break
        h += c["layer"]
    else:
        raise AssertionError(f"{plate}: no stocked {s['screw']} length fits any standoff")
    needs["stock screw length"] = h
    d["standoff_governed_by"], d["standoff_h"] = max(needs.items(), key=lambda kv: kv[1])
    d["standoff_needs"] = needs
    d["screw_len"] = fit[0]
    d["stack"] = s["board_t"] + d["standoff_h"] + d["plate_t"]
    d["screw_tip_z"] = d["stack"] - d["screw_len"]                    # above bed face
    d["screw_beyond_nut"] = (d["pocket_depth"] - sc["nut_m"]) - d["screw_tip_z"]  # thread past the nut's bottom face

    # z levels
    d["z_plate_top"] = d["plate_t"]
    d["z_board_bottom"] = d["plate_t"] + d["standoff_h"]
    d["z_board_top"] = d["z_board_bottom"] + s["board_t"]
    d["z_head_top"] = d["z_board_top"] + sc["head_k"]

    # plate outline from the boards, holes in plate coordinates
    d["margin"] = c["wall"] + c["board_wall_gap"] if s["tray"] else c["plate_margin"]
    xs = [pb["xy"][0] + sx * pb["size"][0] / 2 for pb in d["boards"] for sx in (-1, 1)]
    ys = [pb["xy"][1] + sy * pb["size"][1] / 2 for pb in d["boards"] for sy in (-1, 1)]
    # mount holes: a strip on two opposite sides (the ones no connector faces), wide enough that the
    # mount screw head sits wholly outside every board outline (driver access) and wholly on the plate
    mx = my = d["margin"]
    d["mount"] = mount = s.get("mount")
    if mount:
        ms = d["mount_spec"] = dict(SCREWS[mount["screw"]])
        d["mount_bore_d"] = ms["d"] + c["mount_screw_clearance"]
        d["mount_head_r"] = ms["head_dk"] / 2
        d["mount_inset"] = d["mount_head_r"] + c["mount_head_seat"]                    # hole centre to plate edge
        d["mount_strip"] = d["mount_head_r"] + c["mount_access_clearance"] + d["mount_inset"]   # board outline to plate edge
        if mount["sides"] == "X":
            mx = max(mx, d["mount_strip"])
        else:
            my = max(my, d["mount_strip"])
    d["margin_x"], d["margin_y"] = mx, my
    d["plate_x0"], d["plate_x1"] = min(xs) - mx, max(xs) + mx
    d["plate_y0"], d["plate_y1"] = min(ys) - my, max(ys) + my
    # one hole in each plate corner, inset from both edges; the strip puts it beyond the boards on the mount sides
    e = d.get("mount_inset", 0.0)
    d["mount_holes"] = [(x, y) for x in (d["plate_x0"] + e, d["plate_x1"] - e)
                        for y in (d["plate_y0"] + e, d["plate_y1"] - e)] if mount else []
    d["plate_size"] = (d["plate_x1"] - d["plate_x0"], d["plate_y1"] - d["plate_y0"])
    d["plate_centre"] = ((d["plate_x0"] + d["plate_x1"]) / 2, (d["plate_y0"] + d["plate_y1"]) / 2)
    d["holes"] = [h for pb in d["boards"] for h in pb["holes"]]
    # how far a boss reaches past its board's edge (ADS1115: holes 2.54 from the edge, boss r 2.8 -> 0.26)
    d["boss_beyond_board"] = max(max(abs(hx - pb["xy"][0]) + d["boss_r"] - pb["size"][0] / 2,
                                     abs(hy - pb["xy"][1]) + d["boss_r"] - pb["size"][1] / 2, 0.0)
                                 for pb in d["boards"] for hx, hy in pb["holes"])

    # connectors: world position, mouth, plug and reach envelopes, and what each one faces
    d["connectors"] = [_connector(d, pb, x, y, facing, cn) for pb in d["boards"] for x, y, facing, cn in pb["connectors"]]
    # tray: walls to a derived height, one opening per connector that faces a wall
    if s["tray"]:
        top_h = max([s["top_protrusion"]] + [max(cn["mating"].header_h, cn["mating"].plug_h or 0.0) for cn in d["connectors"]])
        d["wall_top_z"] = _round_up(d["z_board_top"] + top_h + c["lid_clearance"], c["layer"])
        d["wall_h"] = round(d["wall_top_z"] - d["plate_t"], 6)
        d["inner"] = (d["plate_size"][0] - 2 * c["wall"], d["plate_size"][1] - 2 * c["wall"])
        # an opening where a plug's reach crosses the wall; a connector whose reach stops inside needs no hole in the wall
        d["openings"] = [dict(connector=cn, side=cn["faces"], centre=cn["mouth"], width=cn["mating"].plug_w + 2 * c["opening_clearance"],
                              z0=d["z_board_top"] - c["opening_below"])
                         for cn in d["connectors"] if cn["faces"] in _SIDES.values() and cn["reach"] is not None and cn["distance"] < cn["reach"]]
    else:
        d["wall_top_z"], d["wall_h"], d["inner"], d["openings"] = None, 0.0, None, []

    # walls the printability check reads (analytic; tests also measure the geometry)
    d["walls"] = {
        "boss wall (bore to boss OD)": c["boss_wall"],
        "pocket web (pocket ceiling to plate top)": d["pocket_web"],
        "plate edge (pocket corner to plate edge)": min(
            min(d["plate_x1"] - x, x - d["plate_x0"], d["plate_y1"] - y, y - d["plate_y0"]) for x, y in d["holes"]) - d["pocket_r"],
    }
    if mount:
        d["walls"]["mount hole to plate edge"] = d["mount_inset"] - d["mount_bore_d"] / 2
        d["walls"]["mount hole to nut pocket (pocket corner)"] = min(
            math.dist(m, h) for m in d["mount_holes"] for h in d["holes"]) - d["mount_bore_d"] / 2 - d["pocket_r"]
    if s["tray"]:
        d["walls"]["tray wall"] = c["wall"]
        for o in d["openings"]:   # material between an opening and the nearest plate corner, past the corner radius
            lo, hi = _opening_span(d, o)
            axis_lo, axis_hi = (d["plate_y0"], d["plate_y1"]) if o["side"] in ("+X", "-X") else (d["plate_x0"], d["plate_x1"])
            d["walls"][f"wall beside opening {o['side']}@{o['centre'][0]:.1f},{o['centre'][1]:.1f}"] = min(lo - axis_lo, axis_hi - hi) - c["corner_r"]
    d["min_printable_wall"] = 2 * c["nozzle_d"]
    d["print_orientation"] = {
        k: dict(v, bed_z=float(v["bed_z"]) if v["bed_z"].replace(".", "").isdigit() else d[v["bed_z"]],
                overhang_exceptions=[(n, d[z] if isinstance(z, str) else z) for n, z in v["overhang_exceptions"]])
        for k, v in PRINT_ORIENTATION.items()
    }
    return d


def validate(plate: str) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(plate)
    sc = d["screw_spec"]
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"{plate}: wall {name} = {w:.2f} < {d['min_wall']}"
        assert w >= d["min_printable_wall"], f"{plate}: wall {name} = {w:.2f} < 2 x nozzle"
    for pb in d["boards"]:
        b = pb["board"]
        # rule: unbuyable or unmeasurable = failing test; None never passes
        assert b.hole_dia is not None, f"{plate}: {b.name}.hole_dia unknown; parse the board file or caliper it"
        assert sc["d"] < b.hole_dia, f"{plate}: {b.name} hole {b.hole_dia} does not pass an {d['screw']} screw"
        assert b.nearest_pin is not None, f"{plate}: {b.name}.nearest_pin unknown; the boss radius cannot be bounded"
        assert d["boss_r"] <= b.nearest_pin - d["boss_pin_margin"], (
            f"{plate}: {b.name} boss r {d['boss_r']:.2f} reaches within {d['boss_pin_margin']} of a pin at {b.nearest_pin}")
        if b.nearest_top_copper is not None:
            assert sc["head_dk"] / 2 <= b.nearest_top_copper, (
                f"{plate}: {b.name} head r {sc['head_dk'] / 2:.2f} overlaps top copper at {b.nearest_top_copper}")
        # the holes must surround the board's centre: two holes on the centreline hold a board (TCA9548A);
        # two holes on one edge cantilever the rest of it (ADS1115_V1, BME280) and this family has no rest feature
        assert len(b.holes) >= 2, f"{plate}: {b.name} has {len(b.holes)} holes"
        if len(b.holes) == 2:
            (ax, ay), (bx, by) = b.holes
            off = abs((bx - ax) * ay - (by - ay) * ax) / math.hypot(bx - ax, by - ay)   # centre (0, 0) to the hole line
            assert off <= d["hole_line_centre_tol"], (
                f"{plate}: {b.name}'s two holes lie {off:.2f} off the board centre; needs a rest under the free edge (not designed)")
        else:
            hx, hy = [x for x, _ in b.holes], [y for _, y in b.holes]
            assert min(hx) < 0 < max(hx) and min(hy) < 0 < max(hy), f"{plate}: {b.name}'s holes do not surround its centre"
    # every connector can be plugged and unplugged: a wall gets an opening, another board must be a reach away
    for cn in d["connectors"]:
        if cn["faces"] in _SIDES.values():
            # flat plate: nothing in the way. Tray: a wall the plug reaches needs an opening, so its size must be known
            assert not d["tray"] or cn["reach"] is not None or cn["distance"] > d["finger_room"], (
                f"{plate}: {cn['kind']} on {cn['board']} faces the {cn['faces']} wall {cn['distance']:.2f} away and its plug envelope is unknown")
        else:
            assert cn["reach"] is not None, f"{plate}: {cn['kind']} on {cn['board']} faces {cn['faces']} and its plug envelope is unknown"
            assert cn["distance"] >= cn["reach"], (
                f"{plate}: {cn['kind']} at ({cn['xy'][0]:.2f}, {cn['xy'][1]:.2f}) faces {cn['faces']} {cn['distance']:.2f} away; "
                f"plug needs {cn['reach']:.1f} (plug {cn['mating'].plug_len} + finger room {d['finger_room']})")
    if d["mount"]:
        assert not d["tray"], f"{plate}: mount holes in a tray floor: not designed"
        assert d["mount"]["sides"] in ("X", "Y"), f"{plate}: mount sides {d['mount']['sides']!r} is not 'X' or 'Y'"
        # the mount head sits on the plate top beside the bosses: it may not overlap one
        gap = min(math.dist(m, h) for m in d["mount_holes"] for h in d["holes"]) - d["mount_head_r"] - d["boss_r"]
        assert gap >= 0, f"{plate}: mount screw head overlaps a boss by {-gap:.2f}"
        # a connector facing a mount side would put its plug and cable over the mount heads
        for cn in d["connectors"]:
            faces_mount_side = (cn["facing"][0] != 0) == (d["mount"]["sides"] == "X")
            assert not faces_mount_side, (
                f"{plate}: {cn['kind']} on {cn['board']} faces the {cn['faces']} mount side")
    if d["tray"]:
        for side in _SIDES.values():   # openings on one wall may not overlap or merge through their clearance
            spans = sorted(_opening_span(d, o) for o in d["openings"] if o["side"] == side)
            for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
                assert b0 - a1 >= d["min_wall"], f"{plate}: openings on {side} wall {a1:.2f}..{b0:.2f} leave {b0 - a1:.2f} between them"
        assert d["inner"][0] > 0 and d["inner"][1] > 0
    assert d["screw_len"] in sc["lengths"], f"{plate}: screw length {d['screw_len']} not stocked"
    assert d["screw_tip_z"] >= d["screw_tip_min"] - 1e-9, f"{plate}: screw tip {d['screw_tip_z']:.2f} passes the bed face"
    assert d["screw_beyond_nut"] >= 0, f"{plate}: screw {d['screw_len']} does not reach through the nut"
    assert d["pocket_r"] < d["boss_r"] + d["margin"], f"{plate}: nut pocket wider than the material around it"
    # a boss may reach past the board edge by part of its wall, never by the bore: at least one extrusion width of
    # seat stays under the board on the edge side. Feather holes are 1.84 from the long edge (boss reaches 0.96);
    # a commercial 4.5 OD standoff overhangs that edge by 0.41 and is what those boards ship on.
    assert d["boss_beyond_board"] <= d["boss_wall"] - d["nozzle_d"], (
        f"{plate}: boss reaches {d['boss_beyond_board']:.2f} past the board edge; less than a nozzle width of seat on that side")
    # bosses of different boards may not merge
    hs = d["holes"]
    for i in range(len(hs)):
        for j in range(i + 1, len(hs)):
            gap = math.dist(hs[i], hs[j]) - d["boss_d"]
            assert gap >= d["min_wall"] or gap < -1e-9, f"{plate}: bosses {i},{j} nearly touch (gap {gap:.2f})"
    return d


def report(plate: str) -> str:
    d = derive(plate)
    lines = [f"{plate}: {d['screw']} x {d['screw_len']}, {len(d['holes'])} bosses",
             f"  plate {d['plate_size'][0]:.2f} x {d['plate_size'][1]:.2f} x {d['plate_t']:.2f}, bore {d['bore_d']:.2f}, boss OD {d['boss_d']:.2f}",
             f"  standoff {d['standoff_h']:.2f} governed by '{d['standoff_governed_by']}' "
             + ", ".join(f"{k} {v:.2f}" for k, v in d["standoff_needs"].items()),
             f"  boss reaches {d['boss_beyond_board']:.2f} past the board edge",
             f"  nut pocket s {d['pocket_s']:.2f} depth {d['pocket_depth']:.2f}, web {d['pocket_web']:.2f}; "
             f"screw tip {d['screw_tip_z']:.2f} above bed, {d['screw_beyond_nut']:.2f} past the nut",
             "  walls " + ", ".join(f"{k} {v:.2f}" for k, v in d["walls"].items())]
    if d["mount"]:
        lines.append(f"  mount: {len(d['mount_holes'])} x {d['mount']['screw']} on the {d['mount']['sides']} sides, bore {d['mount_bore_d']:.2f}, "
                     f"{d['mount_inset']:.2f} from the plate edges, strip {d['mount_strip']:.2f} beyond the boards, clamp {d['plate_t']:.2f}")
    for cn in d["connectors"]:
        lines.append(f"  {cn['kind']} on {cn['board']} at ({cn['xy'][0]:.2f}, {cn['xy'][1]:.2f}) faces {cn['faces']} at {cn['distance']:.2f}, "
                     + (f"reach {cn['reach']:.1f}" if cn["reach"] is not None else "plug envelope unknown"))
    if d["tray"]:
        lines.append(f"  tray: rim z {d['wall_top_z']:.2f} (wall {d['wall_h']:.2f} above plate), inner {d['inner'][0]:.2f} x {d['inner'][1]:.2f}, "
                     + ", ".join(f"{o['side']} opening w {o['width']:.1f} from z {o['z0']:.2f}" for o in d["openings"]))
    return "\n".join(lines)


if __name__ == "__main__":
    for plate in PLATES:
        try:
            validate(plate)
            print(report(plate), "\n  ok" + ("" if plate in ACTIVE_PLATES else " (inactive)"))
        except AssertionError as e:
            print(f"{plate}: FAIL: {e}")
