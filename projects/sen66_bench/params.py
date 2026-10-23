"""sen66_bench: an open PETG bench plate for a first test of a Sensirion SEN66 air-quality sensor. It carries an
Adafruit Metro ESP32-S3, the Adafruit SEN6x breakout and the SEN66 itself, which has no mounting holes, in a low lip.
Two ways to hold the boards, one layout:

  SEN66_BENCH      M2 screws through printed bosses, nuts captured from the bed face (projects/standoff_plate).
  SEN66_BENCH_PEG  no screws: each boss carries a plain locating peg through the board's hole, as thick as the screw
                   it replaces less nothing it needs (a slip fit). The boards drop on, cannot slide or turn, and lift
                   straight off. A snap pin is not offered: in the breakout's 2.5 hole its two prongs would be 0.6
                   to 1.0 thick, under min_wall.

The layout is a standoff_plate row (`SEN66_BENCH` in projects/standoff_plate/params.py: placements, the sensor's
keep-in). Front row: breakout | Metro; the SEN66 behind the Metro. The STEMMA QT pair faces the front edge
(`cable_edge`), as on the owner's working bench (photo, 2026-10-23): a cable of any length from `qt_cable_min` up
hangs off the plate in a U and puts no side load on either plug.

  - the lip: the sensor drops into it with materials.FIT_CLEAR all round and sits flat on the plate, which closes
    the sensor's open bottom duct as the datasheet asks. The lip stops under the lowest edge of the outlet arches.
  - the groove: the SEN66's GH socket is in the duct roof and its plug hangs to 0.74 above the sensor bottom, so the
    wires need a channel under it to turn in. Depth, width and plug numbers are projects/sen6x_enclosure's (Sensirion
    datasheet, Sensirion STEP, JST eGH). It runs out under the front arch, past the lip, onto open plate; the GH cable
    then goes behind the breakout to its GH, which faces the -X edge.
  - the Metro: USB-C and DC jack on one end, battery JST and microSD on the other, jumper headers along both sides;
    each end has `end_room` of open plate or a plate edge, the rear headers `header_room`.

    plan (Y up, front = -Y)
    +----------------------------------------------+
    |                 [=========lip==========]     |
    |                 [ SEN66             fan]     |
    |                 [==| groove |==========]     |
    |                      GH cable               |
    |  +--------+         |     +-----------------+|
    | <GH       |   <-----+     |                 ||> USB-C, DC jack
    |  |breakout|               |  Metro ESP32-S3 ||
    |  +---QT---+               +--------------QT-+|
    +------|----------------------------------|----+
           +-------- STEMMA QT U -------------+

    .venv/bin/python projects/sen66_bench/params.py      # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import CLEAR_SLIP, FDM_HOLE_ALLOWANCE, FIT_CLEAR, FLOOR, LAYER, NOZZLE, WALL
from projects.sen6x_enclosure.params import derive as sen6x_derive
from projects.sen6x_enclosure.params import validate as sen6x_validate
from projects.standoff_plate.params import derive as plate_derive
from projects.standoff_plate.params import validate as plate_validate

STATUS = "passes"   # concept | passes | printed | parked

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    fit_clear=FIT_CLEAR,         # radial, sensor side at its datasheet maximum to the lip's inner face: materials.FIT_CLEAR
                                 # (Prusa >= 0.3, Hubs 0.5). The sensor is free in the lip, never pressed
    peg_clear=CLEAR_SLIP + FDM_HOLE_ALLOWANCE,   # diametral, finished board hole - peg: ISO 273 fine (a slip fit, 0.2)
                                 # + the DESIGN FDM allowance (0.2; a printed pin comes out as oversize as a hole undersize)
    plating=0.10,                # UNVERIFIED: a plated hole finishes this much under its Eagle drill (copper both walls)
    arch_margin=0.1,             # lip top below the lowest point of the sensor's outlet arch. DESIGN
    groove_past_lip=1.0,         # groove runs this far past the lip's outer face, so the wires leave it level. DESIGN
    cable_room=4.0,              # open plate past the groove's end: the GH wires (OD 1.0) turn at 2 x OD. DESIGN
    gh_mouth_out=1.0,            # UNVERIFIED: the breakout's GH mouth may stand this far past its board edge (the
                                 # header depth is not in the connector registry; the Eagle origin is 3.18 inside the edge)
    finger_room=10.0,            # clear space beyond an unplugged plug, to grab it: as standoff_plate. DESIGN, UNVERIFIED
    end_room=15.0,               # open plate beyond each Metro end: a microSD card is 15 long (SD Association physical
                                 # spec), pushed by its end; the DC and battery plugs are checked on their own. DESIGN
    header_room=8.0,             # open plate beside each Metro long side: fingers on jumpers in its headers. DESIGN
    straight_out=10.0,           # cable straight out of a plug before it bends: no side load on the latch. DESIGN
    # --- geometry rules ---
    lip_wall=WALL,               # 4 perimeters
    floor_web=FLOOR,             # plate left under the groove, 6 layers
    plate_min_t=2.0,             # peg plate stiffness floor, as standoff_plate
    board_air_gap=1.0,           # peg plate: lowest underside feature (pin tail) to plate top, as standoff_plate
    peg_proud=1.0,               # peg above the board top, so a board cannot slip off it. DESIGN
    peg_tip=0.4,                 # 45 deg lead-in on the peg tip, radial. DESIGN
    peg_min_d=4 * NOZZLE,        # thinnest peg: two perimeters each side, solid. DESIGN
    # --- manufacturing rules ---
    nozzle_d=NOZZLE,
    layer=LAYER,
    min_wall=1.2,
    max_overhang_deg=60.0,
    bbox_tol=0.05,
))

_BENCH = dict(
    plate="SEN66_BENCH",     # projects/standoff_plate PLATES row: boards, screw, sensor keep-in
    sensor="SEN66",          # the keep-in in that row the sensor sits on
    sensor_rot=0,            # DESIGN: fan at +X, socket on the -Y side, towards the front row
    cable_edge="-Y",         # DESIGN: the STEMMA QT cable leaves by this plate edge
    qt_boards=("METRO_ESP32S3", "SEN6X_BREAKOUT"),   # the STEMMA QT link
    # the breakout's JST GH 6 (X1, SM06B-GHS-TB), board frame: Adafruit SEN6x Breakout.brd via
    # tools/board_from_eagle.py, 2026-10-23; mouth to +Y (nearest edge and Adafruit's product photo)
    gh_board="SEN6X_BREAKOUT",
    gh_xy=(0.0, 5.71),
    gh_facing=(0, 1),
    metro="METRO_ESP32S3",   # its ends (board frame +-Y) carry the plug-in parts, its sides the headers (boards.py)
    plated={"METRO_ESP32S3": False, "SEN6X_BREAKOUT": True},   # Eagle: plain 3.2 drills / MOUNTINGHOLE_2.5_PLATED
)

SIZES = {
    "SEN66_BENCH": dict(_BENCH, fixing="screw"),
    "SEN66_BENCH_PEG": dict(_BENCH, fixing="peg"),
}

ACTIVE_SIZES = ("SEN66_BENCH", "SEN66_BENCH_PEG")

_SIDES = {"+X": (1, 0), "-X": (-1, 0), "+Y": (0, 1), "-Y": (0, -1)}


def _round_up(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 6)


def _rot(v, rot):
    x, y = v
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[rot % 360]


def _rect_to_point(rect, p):
    """Plan distance from a point to an axis-aligned rectangle (x0, y0, x1, y1); 0 inside."""
    x0, y0, x1, y1 = rect
    return math.hypot(max(x0 - p[0], 0.0, p[0] - x1), max(y0 - p[1], 0.0, p[1] - y1))


def _rect(cx, cy, sx, sy):
    return (cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)


def _ahead(rect, origin, facing, half_w, others):
    """Distance along `facing` from `origin` to the nearest rectangle in `others` that overlaps the band half_w either
    side of the facing line; None if nothing is ahead (the plate edge is)."""
    fx, fy = facing
    hits = []
    for o in others:
        if o is rect:
            continue
        x0, y0, x1, y1 = o
        lo, hi = (y0, y1) if fx else (x0, x1)
        c = origin[1] if fx else origin[0]
        if hi <= c - half_w or lo >= c + half_w:
            continue
        near = (x0 if fx > 0 else -x1) if fx else (y0 if fy > 0 else -y1)
        along = near - (origin[0] * fx if fx else origin[1] * fy)
        if along > -1e-9:
            hits.append(along)
    return min(hits) if hits else None


def derive(size: str, **overrides) -> dict:
    """Every dimension sen66_bench.py and the tests need. Overrides are for what-if tables only."""
    s = dict(SIZES[size])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(size=size, **s, **c)
    p = d["p"] = plate_derive(s["plate"])          # the standoff plate: outline, boards, bosses (screw version: all of it)
    e = d["e"] = sen6x_derive()                     # the sensor, its plug and its groove, sensor frame
    keep = next(k for k in p["keep_in"] if k["name"] == s["sensor"])
    d["sensor_xy"], d["keep_size"] = keep["xy"], keep["size"]
    d["sensor_max"] = (e["sensor_l"] + e["sensor_l_tol"], e["sensor_w"] + e["sensor_w_tol"])
    rot = s["sensor_rot"]
    assert rot % 180 == 0, "the lip and groove are drawn for the sensor's long axis along X"
    edge_xy = _SIDES[s["cable_edge"]]
    plate_rect = (p["plate_x0"], p["plate_y0"], p["plate_x1"], p["plate_y1"])

    def to_plate(x, y):   # sensor frame -> plate
        rx, ry = _rot((x, y), rot)
        return d["sensor_xy"][0] + rx, d["sensor_xy"][1] + ry

    # --- the plate and how the boards sit on it
    groove_floor_need = e["groove_depth"] + c["floor_web"]
    if s["fixing"] == "screw":
        d["plate_t"], d["standoff_h"] = p["plate_t"], p["standoff_h"]
        d["plate_governed_by"] = "nut pocket + web (standoff_plate)"   # validate() holds the groove's floor_web under it
    else:
        needs = {"plate_min_t": c["plate_min_t"], "groove + floor_web": groove_floor_need}
        d["plate_governed_by"], t = max(needs.items(), key=lambda kv: kv[1])
        d["plate_t"] = _round_up(t, c["layer"])
        d["standoff_h"] = _round_up(p["underside_protrusion"] + c["board_air_gap"], c["layer"])
        # a peg per hole: the finished hole less the slip clearance, 0.01 steps down
        d["pegs"] = []
        for pb in p["boards"]:
            b = pb["board"]
            finished = b.hole_dia - (c["plating"] if s["plated"][b.name] else 0.0)
            peg_d = math.floor((finished - c["peg_clear"]) * 100 + 1e-6) / 100
            d["pegs"] += [dict(board=b.name, xy=h, d=peg_d, hole=finished) for h in pb["holes"]]
    d["z_board_bottom"] = d["plate_t"] + d["standoff_h"]
    d["z_board_top"] = d["z_board_bottom"] + p["board_t"]
    d["z_top"] = d["z_board_top"] + c["peg_proud"] if s["fixing"] == "peg" else d["z_board_bottom"]
    d["boss_r"], d["flare_r"], d["boss_root_flare"] = p["boss_r"], p["flare_r"], p["boss_root_flare"]

    # --- lip: pocket = the enclosure's (sensor maximum + fit_clear all round, corner r 3.0); top under the arch
    d["z_floor"] = d["plate_t"]
    d["pocket"] = (e["pocket_l"], e["pocket_w"])
    d["pocket_r"] = e["pocket_corner_r"]
    d["lip_outer"] = (e["pocket_l"] + 2 * c["lip_wall"], e["pocket_w"] + 2 * c["lip_wall"])
    d["lip_outer_r"] = d["pocket_r"] + c["lip_wall"]
    d["arch_low"] = min(z for _, z in e["arch"])
    d["lip_h"] = math.floor((d["arch_low"] - c["arch_margin"]) / c["layer"] + 1e-9) * c["layer"]
    d["z_lip_top"] = d["z_floor"] + d["lip_h"]
    d["lip_rect"] = _rect(*d["sensor_xy"], *d["lip_outer"])

    # --- groove: the enclosure's plan (plug width + groove_side, from inboard of the plug), out past the lip
    gx0, gx1 = e["groove_x"]
    y_out = -(d["lip_outer"][1] / 2 + c["groove_past_lip"])
    (ax, ay), (bx, by) = to_plate(gx0, e["groove_y"][1]), to_plate(gx1, y_out)
    d["groove_rect"] = (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))
    d["groove_w"] = abs(bx - ax)
    d["groove_len"] = abs(by - ay)
    d["groove_side"] = "-Y" if by < ay else "+Y"
    d["groove_depth"] = e["groove_depth"]
    d["z_groove"] = round(d["z_floor"] - d["groove_depth"], 6)
    d["socket_xy"] = to_plate(e["socket_x"], e["socket_y"])
    d["plug_bottom_z"] = d["z_floor"] + e["plug_bottom_z"]
    gdir = _SIDES[d["groove_side"]]
    d["groove_end"] = ((ax + bx) / 2, by)

    rects = {b["name"]: _rect(*b["xy"], *b["size"]) for b in p["boards"]}
    rects[s["sensor"]] = _rect(*d["sensor_xy"], *d["keep_size"])
    others = list(rects.values())
    d["groove_ahead"] = _ahead(None, d["groove_end"], gdir, d["groove_w"] / 2, others)

    # --- the breakout's GH: mouth on the plate, and its plug's room
    pb = next(b for b in p["boards"] if b["name"] == s["gh_board"])
    gx, gy = _rot(s["gh_xy"], pb["rot"])
    fx, fy = _rot(s["gh_facing"], pb["rot"])
    edge = (pb["size"][0] / 2 if fx else pb["size"][1] / 2) - abs(gx * fx + gy * fy)   # origin to board edge, along facing
    d["gh_xy"] = (pb["xy"][0] + gx, pb["xy"][1] + gy)
    d["gh_facing"] = (fx, fy)
    d["gh_mouth"] = (d["gh_xy"][0] + fx * (edge + c["gh_mouth_out"]), d["gh_xy"][1] + fy * (edge + c["gh_mouth_out"]))
    d["gh_ahead"] = _ahead(rects[s["gh_board"]], d["gh_mouth"], (fx, fy), e["plug_w"] / 2, others)   # None: plate edge
    d["gh_reach"] = e["plug_len"] + c["finger_room"]

    # --- the STEMMA QT link: one connector on each board faces the cable edge
    d["qt"] = {name: [cn for cn in p["connectors"] if cn["board"] == name and cn["kind"] == "JST_SH4" and cn["faces"] == s["cable_edge"]]
               for name in s["qt_boards"]}
    m0, m1 = (d["qt"][n][0]["mouth"] if d["qt"][n] else None for n in s["qt_boards"])
    if m0 and m1:
        span = abs((m1[0] - m0[0]) * edge_xy[1]) + abs((m1[1] - m0[1]) * edge_xy[0])   # along the edge
        to_edge = max(abs((plate_rect[0 if edge_xy[0] < 0 else 2] - m[0]) if edge_xy[0] else (plate_rect[1 if edge_xy[1] < 0 else 3] - m[1]))
                      for m in (m0, m1))
        plug = d["qt"][s["qt_boards"][0]][0]["mating"].plug_len
        # each end: plug + straight run (or to the plate edge, if farther), then a half circle across the span
        d["qt_span"] = span
        d["qt_cable_min"] = 2 * (plug + max(c["straight_out"], to_edge)) + math.pi * span / 2
    else:
        d["qt_span"] = d["qt_cable_min"] = None
    # the GH cable: socket, groove, then around the breakout to its GH mouth (Manhattan, an estimate)
    gm, ge = d["gh_mouth"], d["groove_end"]
    d["gh_cable_min"] = (e["plug_len"] + d["groove_len"] + abs(gm[0] - ge[0]) + abs(gm[1] - ge[1]) + 2 * c["straight_out"])

    # --- the Metro: ends (board frame +-Y) need end_room, sides (+-X) header_room, or a plate edge
    mb = next(b for b in p["boards"] if b["name"] == s["metro"])
    d["metro_room"] = {}
    for local, need in (((0, 1), c["end_room"]), ((0, -1), c["end_room"]), ((1, 0), c["header_room"]), ((-1, 0), c["header_room"])):
        f = _rot(local, mb["rot"])
        half = mb["board"].size[1] / 2 if local[1] else mb["board"].size[0] / 2
        mid = (mb["xy"][0] + f[0] * half, mb["xy"][1] + f[1] * half)
        across = mb["size"][1] / 2 if f[0] else mb["size"][0] / 2
        name = {(0, 1): "USB-C/DC end", (0, -1): "battery/microSD end", (1, 0): "IOH/IOL header side", (-1, 0): "POWER/AD header side"}[local]
        d["metro_room"][name] = dict(facing=f, need=need, ahead=_ahead(rects[s["metro"]], mid, f, across, others))

    d["walls"] = {
        "lip wall": c["lip_wall"],
        "floor under groove": d["z_groove"],
        "groove to boss root flare": min(_rect_to_point(d["groove_rect"], h) for h in p["holes"]) - d["flare_r"],
        "lip to boss root flare": min(_rect_to_point(d["lip_rect"], h) for h in p["holes"]) - d["flare_r"],
    }
    if s["fixing"] == "screw":
        d["walls"]["groove to nut pocket (pocket corner)"] = min(_rect_to_point(d["groove_rect"], h) for h in p["holes"]) - p["pocket_r"]
        d["print_orientation"] = p["print_orientation"]
    else:
        d["walls"]["peg"] = min(pg["d"] for pg in d["pegs"])
        d["print_orientation"] = dict(plate=dict(up=(0, 0, 1), bed_face="plate bottom", bed_z=0.0,
                                                 known_overhangs=[], overhang_exceptions=[]))
    return d


def validate(size: str, **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings. Overrides plant defects in tests."""
    d = derive(size, **overrides)
    p, e = d["p"], d["e"]
    plate_validate(d["plate"])   # bosses against the boards' pins, every board connector's plug room
    sen6x_validate()             # the plug, the wire bend and the groove depth hold there; this plate copies them
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"{size}: wall {name} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"{size}: wall {name} = {w:.2f} < 2 x nozzle"
    if d["fixing"] == "peg":
        for pg in d["pegs"]:
            assert pg["d"] >= d["peg_min_d"], f"{size}: {pg['board']} peg {pg['d']:.2f} < {d['peg_min_d']:.2f}"
            assert pg["d"] + d["peg_clear"] <= pg["hole"] + 1e-9, f"{size}: {pg['board']} peg {pg['d']:.2f} in a {pg['hole']:.2f} hole"
            assert pg["d"] / 2 < d["boss_r"] - d["nozzle_d"], f"{size}: {pg['board']} peg leaves no seat on its boss"
        assert d["standoff_h"] >= p["underside_protrusion"] + d["board_air_gap"] - 1e-9, f"{size}: pin tails reach the plate"
        assert d["boss_root_flare"] <= d["board_air_gap"], f"{size}: boss root flare reaches the pin tails"
    # the keep-in the plate was sized from holds the sensor at its datasheet maximum
    ks = d["keep_size"] if d["sensor_rot"] % 180 == 0 else d["keep_size"][::-1]
    assert ks[0] >= d["sensor_max"][0] - 1e-9 and ks[1] >= d["sensor_max"][1] - 1e-9, (
        f"{size}: keep-in {ks} smaller than the sensor {d['sensor_max']}")
    # lip and groove on the plate
    for name, (x0, y0, x1, y1) in (("lip", d["lip_rect"]), ("groove", d["groove_rect"])):
        assert p["plate_x0"] <= x0 and x1 <= p["plate_x1"] and p["plate_y0"] <= y0 and y1 <= p["plate_y1"], f"{size}: {name} off the plate"
    # the lip never shades the outlet; the pocket corner clears the sensor corner
    assert d["lip_h"] < d["arch_low"], f"{size}: lip {d['lip_h']:.2f} reaches the outlet arch at {d['arch_low']}"
    assert d["lip_h"] >= 4 * d["layer"], f"{size}: lip {d['lip_h']:.2f} too low to hold the sensor"
    assert d["pocket_r"] <= e["sensor_corner_r"] + d["fit_clear"], f"{size}: pocket corner bears on the sensor corner"
    # the groove: deep enough for the wire bend (as the enclosure), a floor under it, out through the arch, open ahead
    assert d["plug_bottom_z"] - e["bend_room"] >= d["z_groove"] - 1e-9, f"{size}: groove too shallow for the wire bend"
    assert d["z_groove"] >= d["floor_web"] - 1e-9, f"{size}: groove leaves {d['z_groove']:.2f} under it"
    assert e["window_x"][0] <= e["groove_x"][0] and e["groove_x"][1] <= e["window_x"][1], f"{size}: groove misses the outlet arch"
    assert d["groove_ahead"] is None or d["groove_ahead"] >= d["cable_room"], (
        f"{size}: groove ends {d['groove_ahead']:.2f} from the next part; the wires need {d['cable_room']}")
    # cables: the STEMMA QT pair faces the cable edge; the GH has room to be plugged
    for name, cns in d["qt"].items():
        assert cns, f"{size}: no STEMMA QT on {name} faces the cable edge {d['cable_edge']}; the cable would bunch between the boards"
    assert d["gh_ahead"] is None or d["gh_ahead"] >= d["gh_reach"], (
        f"{size}: GH mouth {d['gh_ahead']:.2f} from the next part; plug needs {d['gh_reach']:.1f}")
    for name, r in d["metro_room"].items():
        assert r["ahead"] is None or r["ahead"] >= r["need"] - 1e-9, (
            f"{size}: Metro {name} {r['ahead']:.2f} from the next part; needs {r['need']}")
    assert d["z_top"] + 1 <= 256 and p["plate_size"][0] + 1 <= 256 and p["plate_size"][1] + 1 <= 256, f"{size}: does not fit the bed"
    return d


def report(size: str) -> str:
    d = derive(size)
    p = d["p"]
    room = ", ".join(f"{k} " + ("to the plate edge" if v["ahead"] is None else f"{v['ahead']:.2f} open") for k, v in d["metro_room"].items())
    fix = (f"{len(p['holes'])} x {p['screw']} x {p['screw_len']} ISO 4762 + ISO 4032 nuts" if d["fixing"] == "screw" else
           f"no screws: {len(d['pegs'])} locating pegs, " + ", ".join(sorted({f"{pg['board']} d {pg['d']:.2f} in {pg['hole']:.2f}" for pg in d["pegs"]}))
           + f", {d['peg_proud']:.1f} proud")
    return "\n".join([
        f"{size}: plate {p['plate_size'][0]:.2f} x {p['plate_size'][1]:.2f} x {d['plate_t']:.2f} ({d['plate_governed_by']}), "
        f"boards on bosses at z {d['z_board_bottom']:.2f}, top z {d['z_top']:.2f}",
        f"  {fix}",
        f"  boards: " + ", ".join(f"{b['name']} at ({b['xy'][0]:.2f}, {b['xy'][1]:.2f}) rot {b['rot']}" for b in p["boards"]),
        f"  SEN66 at ({d['sensor_xy'][0]:.2f}, {d['sensor_xy'][1]:.2f}) rot {d['sensor_rot']}, max {d['sensor_max'][0]:.1f} x "
        f"{d['sensor_max'][1]:.1f}; lip pocket {d['pocket'][0]:.2f} x {d['pocket'][1]:.2f}, wall {d['lip_wall']:.2f}, "
        f"{d['lip_h']:.2f} tall (outlet arch from {d['arch_low']:.2f})",
        f"  groove {d['groove_w']:.2f} x {d['groove_len']:.2f} x {d['groove_depth']:.2f} deep, out the {d['groove_side']} side, "
        f"floor {d['z_groove']:.2f}, " + ("to the plate edge" if d["groove_ahead"] is None else f"{d['groove_ahead']:.2f} open") + " ahead",
        f"  STEMMA QT leaves by {d['cable_edge']}: mouths {d['qt_span']:.1f} apart, cable >= {d['qt_cable_min']:.0f} mm; "
        f"GH cable >= {d['gh_cable_min']:.0f} mm (estimate)",
        f"  breakout GH at ({d['gh_xy'][0]:.2f}, {d['gh_xy'][1]:.2f}) facing {d['gh_facing']}, "
        + ("to the plate edge" if d["gh_ahead"] is None else f"{d['gh_ahead']:.2f} to the next part") + f" (plug + fingers {d['gh_reach']:.1f})",
        f"  Metro: {room}",
        "  walls " + ", ".join(f"{k} {v:.2f}" for k, v in d["walls"].items()),
    ])


if __name__ == "__main__":
    for size in SIZES:
        try:
            validate(size)
            print(report(size), "\n  ok" + ("" if size in ACTIVE_SIZES else " (inactive)"))
        except AssertionError as e:
            print(f"{size}: FAIL: {e}")
