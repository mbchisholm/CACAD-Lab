"""sen66_bench: an open PETG bench plate for a first test of a Sensirion SEN66 air-quality sensor. It carries an
Adafruit Metro ESP32-S3 and the Adafruit SEN6x breakout on M2 bosses with captured nuts, and the SEN66 itself,
which has no mounting holes, in a low lip.

The boards are a standoff_plate row (`SEN66_BENCH` in projects/standoff_plate/params.py: placements, screw, the
sensor's keep-in). This file adds what a standoff plate does not have, and every number for it:

  - the lip: the sensor drops into it with materials.FIT_CLEAR all round and sits flat on the plate, which closes
    the sensor's open bottom duct as the datasheet asks. The lip stops under the lowest edge of the outlet arches,
    so it never shades the exhaust.
  - the groove: the SEN66's GH socket is in the duct roof and its plug hangs to 0.74 above the sensor bottom, so the
    wires need a channel under it to turn in. Depth, width and plug numbers are projects/sen6x_enclosure's (Sensirion
    datasheet, Sensirion STEP, JST eGH). The groove runs out under the +Y arch, towards the breakout's GH socket.

The sensor is turned 180 deg (fan at -X) so its socket is on the side facing the breakout.

    plan (Y up)
    +-----------------------------------------------------------+
    |  +----------------+                    +--------+          |
    |  |                |=QT=====QT cable====| SEN6x  |          |
    |  |  Metro         |                    +---GH---+          |
    |  |  ESP32-S3      |                        |  GH cable      |
    |  |                |   [==lip=========| groove |=========]   |
    |  |                |   [  fan    SEN66  (plug) |         ]   |
    |  +-----USB--------+   [=========================== =====]   |
    +-----------------------------------------------------------+

    .venv/bin/python projects/sen66_bench/params.py      # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import FIT_CLEAR, FLOOR, LAYER, NOZZLE, WALL
from projects.sen6x_enclosure.params import derive as sen6x_derive
from projects.sen6x_enclosure.params import validate as sen6x_validate
from projects.standoff_plate.params import derive as plate_derive
from projects.standoff_plate.params import validate as plate_validate

STATUS = "passes"   # concept | passes | printed | parked

COMMON = MappingProxyType(dict(
    # --- named clearances (mm): which two surfaces each one separates ---
    fit_clear=FIT_CLEAR,         # radial, sensor side at its datasheet maximum to the lip's inner face: materials.FIT_CLEAR
                                 # (Prusa >= 0.3, Hubs 0.5). The sensor is free in the lip, never pressed
    arch_margin=0.1,             # lip top below the lowest point of the sensor's outlet arch. DESIGN
    groove_past_lip=1.0,         # groove runs this far past the lip's outer face, so the wires leave it level. DESIGN
    gh_mouth_out=1.0,            # UNVERIFIED: the breakout's GH mouth may stand this far past its board edge (the
                                 # header depth is not in the connector registry; the Eagle origin is 3.18 inside the edge)
    finger_room=10.0,            # clear space beyond an unplugged plug, to grab it: as standoff_plate. DESIGN, UNVERIFIED
    gh_align_tol=1.0,            # the breakout's GH within this of the sensor socket in X: the GH cable runs straight. DESIGN
    metro_side_room=8.0,         # Metro outline to the sensor: fingers on jumpers in the Metro's +X headers. DESIGN
    # --- geometry rules ---
    lip_wall=WALL,               # 4 perimeters
    floor_web=FLOOR,             # plate left under the groove, 6 layers
    # --- manufacturing rules ---
    nozzle_d=NOZZLE,
    layer=LAYER,
    min_wall=1.2,
    max_overhang_deg=60.0,
    bbox_tol=0.05,
))

SIZES = {
    "SEN66_BENCH": dict(
        plate="SEN66_BENCH",     # projects/standoff_plate PLATES row: boards, screw, sensor keep-in
        sensor="SEN66",          # the keep-in in that row the sensor sits on
        sensor_rot=180,          # DESIGN: fan at -X, socket on the +Y side, towards the breakout
        # the breakout's JST GH 6 (X1, SM06B-GHS-TB), board frame: Adafruit SEN6x Breakout.brd via
        # tools/board_from_eagle.py, 2026-10-23; mouth to +Y (nearest edge and Adafruit's product photo)
        gh_board="SEN6X_BREAKOUT",
        gh_xy=(0.0, 5.71),
        gh_facing=(0, 1),
    ),
}

ACTIVE_SIZES = ("SEN66_BENCH",)


def _rot(v, rot):
    x, y = v
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[rot % 360]


def _rect_to_point(rect, p):
    """Plan distance from a point to an axis-aligned rectangle (x0, y0, x1, y1); 0 inside."""
    x0, y0, x1, y1 = rect
    return math.hypot(max(x0 - p[0], 0.0, p[0] - x1), max(y0 - p[1], 0.0, p[1] - y1))


def _rect(cx, cy, sx, sy):
    return (cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)


def derive(size: str, **overrides) -> dict:
    """Every dimension sen66_bench.py and the tests need. Overrides are for what-if tables only."""
    s = dict(SIZES[size])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(size=size, **s, **c)
    p = d["p"] = plate_derive(s["plate"])          # the standoff plate under everything
    e = d["e"] = sen6x_derive()                     # the sensor, its plug and its groove, sensor frame
    keep = next(k for k in p["keep_in"] if k["name"] == s["sensor"])
    d["sensor_xy"], d["keep_size"] = keep["xy"], keep["size"]
    d["sensor_max"] = (e["sensor_l"] + e["sensor_l_tol"], e["sensor_w"] + e["sensor_w_tol"])
    rot = s["sensor_rot"]
    assert rot % 180 == 0, "the lip and groove are drawn for the sensor's long axis along X"

    def to_plate(x, y):   # sensor frame -> plate
        rx, ry = _rot((x, y), rot)
        return d["sensor_xy"][0] + rx, d["sensor_xy"][1] + ry

    def rect_to_plate(x0, y0, x1, y1):
        (ax, ay), (bx, by) = to_plate(x0, y0), to_plate(x1, y1)
        return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))

    # z levels: the plate top is the sensor's floor
    d["z_floor"] = p["plate_t"]
    # lip: pocket = the enclosure's (sensor maximum + fit_clear all round, corner r 3.0); top under the arch
    d["pocket"] = (e["pocket_l"], e["pocket_w"])
    d["pocket_r"] = e["pocket_corner_r"]
    d["lip_outer"] = (e["pocket_l"] + 2 * c["lip_wall"], e["pocket_w"] + 2 * c["lip_wall"])
    d["lip_outer_r"] = d["pocket_r"] + c["lip_wall"]
    d["arch_low"] = min(z for _, z in e["arch"])
    d["lip_h"] = math.floor((d["arch_low"] - c["arch_margin"]) / c["layer"] + 1e-9) * c["layer"]
    d["z_lip_top"] = d["z_floor"] + d["lip_h"]
    d["lip_rect"] = _rect(*d["sensor_xy"], *d["lip_outer"])
    # groove: the enclosure's plan (plug width + groove_side, from inboard of the plug to the side), out past the lip
    gx0, gx1 = e["groove_x"]
    y_in = e["groove_y"][1]                                                   # inboard end, sensor frame
    y_out = -(d["lip_outer"][1] / 2 + c["groove_past_lip"])                   # past the lip on the socket side
    d["groove_depth"] = e["groove_depth"]
    d["z_groove"] = round(d["z_floor"] - d["groove_depth"], 6)
    d["groove_rect"] = rect_to_plate(gx0, y_out, gx1, y_in)
    d["groove_w"] = gx1 - gx0
    d["groove_len"] = y_in - y_out
    d["groove_lip_side"] = "+Y" if to_plate(0, y_out)[1] > d["sensor_xy"][1] else "-Y"
    d["socket_xy"] = to_plate(e["socket_x"], e["socket_y"])
    d["plug_bottom_z"] = d["z_floor"] + e["plug_bottom_z"]

    # the breakout's GH: mouth on the plate, and its plug's room towards the sensor
    pb = next(b for b in p["boards"] if b["name"] == s["gh_board"])
    gx, gy = _rot(s["gh_xy"], pb["rot"])
    fx, fy = _rot(s["gh_facing"], pb["rot"])
    edge = (pb["size"][0] / 2 if fx else pb["size"][1] / 2) - abs(gx * fx + gy * fy)   # origin to board edge, along facing
    d["gh_xy"] = (pb["xy"][0] + gx, pb["xy"][1] + gy)
    d["gh_facing"] = (fx, fy)
    d["gh_mouth"] = (d["gh_xy"][0] + fx * (edge + c["gh_mouth_out"]), d["gh_xy"][1] + fy * (edge + c["gh_mouth_out"]))
    k0x, k0y, k1x, k1y = _rect(*d["sensor_xy"], *d["keep_size"])
    # mouth to the sensor's near side, along a +-Y facing (None: the GH does not face the sensor's long side)
    d["gh_to_sensor"] = ((d["gh_mouth"][1] - k1y) if fy < 0 else (k0y - d["gh_mouth"][1])) if fy else None
    d["gh_reach"] = e["plug_len"] + c["finger_room"]
    metro = next(b for b in p["boards"] if b["name"] == "METRO_ESP32S3")
    d["metro_to_sensor"] = k0x - (metro["xy"][0] + metro["size"][0] / 2)

    d["walls"] = {
        "lip wall": c["lip_wall"],
        "floor under groove": d["z_groove"],
        "groove to nut pocket (pocket corner)": min(_rect_to_point(d["groove_rect"], h) for h in p["holes"]) - p["pocket_r"],
        "lip to boss root flare": min(_rect_to_point(d["lip_rect"], h) for h in p["holes"]) - p["flare_r"],
    }
    d["print_orientation"] = p["print_orientation"]
    return d


def validate(size: str, **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings. Overrides plant defects in tests."""
    d = derive(size, **overrides)
    p, e = d["p"], d["e"]
    plate_validate(d["plate"])
    sen6x_validate()           # the plug, the wire bend and the groove depth hold there; this plate copies them
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"{size}: wall {name} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"{size}: wall {name} = {w:.2f} < 2 x nozzle"
    # the keep-in the plate was sized from holds the sensor at its datasheet maximum
    ks = d["keep_size"] if d["sensor_rot"] % 180 == 0 else d["keep_size"][::-1]
    assert ks[0] >= d["sensor_max"][0] - 1e-9 and ks[1] >= d["sensor_max"][1] - 1e-9, (
        f"{size}: keep-in {ks} smaller than the sensor {d['sensor_max']}")
    # lip and groove stay on the plate
    x0, y0, x1, y1 = d["lip_rect"]
    assert p["plate_x0"] <= x0 and x1 <= p["plate_x1"] and p["plate_y0"] <= y0 and y1 <= p["plate_y1"], f"{size}: lip off the plate"
    g = d["groove_rect"]
    assert p["plate_x0"] < g[0] and g[2] < p["plate_x1"] and p["plate_y0"] < g[1] and g[3] < p["plate_y1"], f"{size}: groove off the plate"
    # the lip never shades the outlet; the pocket corner clears the sensor corner
    assert d["lip_h"] < d["arch_low"], f"{size}: lip {d['lip_h']:.2f} reaches the outlet arch at {d['arch_low']}"
    assert d["lip_h"] >= 4 * d["layer"], f"{size}: lip {d['lip_h']:.2f} too low to hold the sensor"
    assert d["pocket_r"] <= e["sensor_corner_r"] + d["fit_clear"], f"{size}: pocket corner bears on the sensor corner"
    # the groove: deep enough for the wire bend (as the enclosure), a floor under it, out through the arch
    assert d["plug_bottom_z"] - e["bend_room"] >= d["z_groove"] - 1e-9, f"{size}: groove too shallow for the wire bend"
    assert d["z_groove"] >= d["floor_web"] - 1e-9, f"{size}: groove leaves {d['z_groove']:.2f} under it"
    assert e["window_x"][0] <= e["groove_x"][0] and e["groove_x"][1] <= e["window_x"][1], f"{size}: groove misses the outlet arch"
    # plugs: the breakout's GH sits over the socket and has room to be plugged; nothing but the cable is between
    assert abs(d["gh_xy"][0] - d["socket_xy"][0]) <= d["gh_align_tol"], (
        f"{size}: breakout GH at x {d['gh_xy'][0]:.2f}, sensor socket at {d['socket_xy'][0]:.2f}")
    assert d["gh_to_sensor"] is not None and d["gh_to_sensor"] >= d["gh_reach"], (
        f"{size}: GH mouth {d['gh_to_sensor']} from the sensor; plug needs {d['gh_reach']:.1f}")
    lip_side_y = g[3] if d["groove_lip_side"] == "+Y" else g[1]
    assert (d["gh_facing"][1] < 0) == (d["groove_lip_side"] == "+Y") and (lip_side_y - d["gh_mouth"][1]) * d["gh_facing"][1] > 0, (
        f"{size}: the groove leaves the lip on {d['groove_lip_side']}, away from the breakout's GH")
    assert d["metro_to_sensor"] >= d["metro_side_room"] - 1e-9, f"{size}: sensor {d['metro_to_sensor']:.2f} from the Metro"
    return d


def report(size: str) -> str:
    d = derive(size)
    p = d["p"]
    return "\n".join([
        f"{size}: plate {p['plate_size'][0]:.2f} x {p['plate_size'][1]:.2f} x {p['plate_t']:.2f}, "
        f"bosses to z {p['z_board_bottom']:.2f}, {len(p['holes'])} x {p['screw']} x {p['screw_len']} ISO 4762 + ISO 4032 nuts",
        f"  boards: " + ", ".join(f"{b['name']} at ({b['xy'][0]:.2f}, {b['xy'][1]:.2f}) rot {b['rot']}" for b in p["boards"]),
        f"  SEN66 at ({d['sensor_xy'][0]:.2f}, {d['sensor_xy'][1]:.2f}) rot {d['sensor_rot']}, max {d['sensor_max'][0]:.1f} x "
        f"{d['sensor_max'][1]:.1f}; lip pocket {d['pocket'][0]:.2f} x {d['pocket'][1]:.2f}, wall {d['lip_wall']:.2f}, "
        f"{d['lip_h']:.2f} tall (outlet arch from {d['arch_low']:.2f})",
        f"  groove {d['groove_w']:.2f} x {d['groove_len']:.2f} x {d['groove_depth']:.2f} deep, out the {d['groove_lip_side']} lip, "
        f"floor {d['z_groove']:.2f}; plug end z {d['plug_bottom_z']:.2f}",
        f"  breakout GH at ({d['gh_xy'][0]:.2f}, {d['gh_xy'][1]:.2f}), socket at ({d['socket_xy'][0]:.2f}, {d['socket_xy'][1]:.2f}), "
        f"{d['gh_to_sensor']:.2f} from the sensor (plug + fingers {d['gh_reach']:.1f}); Metro {d['metro_to_sensor']:.2f} away",
        "  walls " + ", ".join(f"{k} {v:.2f}" for k, v in d["walls"].items()),
    ])


if __name__ == "__main__":
    for size in SIZES:
        try:
            validate(size)
            print(report(size), "\n  ok" + ("" if size in ACTIVE_SIZES else " (inactive)"))
        except AssertionError as e:
            print(f"{size}: FAIL: {e}")
