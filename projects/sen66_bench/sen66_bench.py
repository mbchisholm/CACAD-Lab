"""sen66_bench: one bench plate, two ways to hold the boards (params.SIZES):

  SEN66_BENCH      the SEN66_BENCH standoff plate (projects/standoff_plate: M2 bosses, nuts captured from the bed face)
  SEN66_BENCH_PEG  no screws: a plain plate whose bosses carry locating pegs through the boards' holes

Both add a lip the SEN66 drops into and a groove under its socket for the cable. Every number is from params.derive.

    .venv/bin/python projects/sen66_bench/sen66_bench.py [--show]     # ACTIVE_SIZES -> out/

A part file names no filesystem module (os, pathlib, sys): the build123d-mcp
sandbox refuses the file (FINDINGS F23). It imports params by package path (F24).
"""
from __future__ import annotations

import math

from build123d import (Axis, Box, BuildPart, BuildSketch, Compound, Cone, Cylinder, Location, Locations, Mode, Part,
                       Rectangle, RectangleRounded, add, extrude, fillet)

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, interference_volume, is_inside, single_solid
from projects.sen66_bench.params import ACTIVE_SIZES, derive
from projects.standoff_plate.plate import build_hardware, build_plate, check_plate


def _peg_plate(d: dict) -> Part:
    """Plate, flared bosses, and a peg with a 45 deg lead-in tip on each: no bores, no pockets."""
    p = d["p"]
    with BuildPart() as bp:
        with Locations((*p["plate_centre"], d["plate_t"] / 2)):
            Box(*p["plate_size"], d["plate_t"])
        fillet(bp.edges().filter_by(Axis.Z), radius=p["corner_r"])
        with Locations(*[(x, y, d["plate_t"]) for x, y in p["holes"]]):
            Cylinder(d["boss_r"], d["standoff_h"], align=ALIGN_MIN_Z)
            Cone(d["flare_r"], d["boss_r"], d["boss_root_flare"], align=ALIGN_MIN_Z)   # root flare, 45 deg
        for pg in d["pegs"]:
            r, h = pg["d"] / 2, d["z_top"] - d["peg_tip"] - d["z_board_bottom"]
            with Locations((*pg["xy"], d["z_board_bottom"])):
                Cylinder(r, h, align=ALIGN_MIN_Z)
            with Locations((*pg["xy"], d["z_top"] - d["peg_tip"])):
                Cone(r, r - d["peg_tip"], d["peg_tip"], align=ALIGN_MIN_Z)
    return bp.part


def build_base(size: str) -> Part:
    """The plate under the lip and groove: standoff_plate's for screws, _peg_plate otherwise."""
    d = derive(size)
    return build_plate(d["plate"]) if d["fixing"] == "screw" else _peg_plate(d)


def build_part(size: str) -> Part:
    d = derive(size)
    sx, sy = d["sensor_xy"]
    g = d["groove_rect"]
    base = build_base(size)   # outside the builder: standoff_plate's lead-in chamfer() would act on an open BuildPart
    with BuildPart() as bp:
        add(base)
        with BuildSketch(Location((sx, sy, d["z_floor"]))) as lip:
            RectangleRounded(*d["lip_outer"], d["lip_outer_r"])
            RectangleRounded(*d["pocket"], d["pocket_r"], mode=Mode.SUBTRACT)
        extrude(lip.sketch, amount=d["lip_h"])
        # tall end lip: the same ring, beyond the outlet arches, up to z_end_top
        with BuildSketch(Location((0, 0, d["z_lip_top"]))) as ends:
            with Locations((sx, sy)):
                RectangleRounded(*d["lip_outer"], d["lip_outer_r"])
                RectangleRounded(*d["pocket"], d["pocket_r"], mode=Mode.SUBTRACT)
            with BuildSketch(mode=Mode.PRIVATE) as slabs:
                for x0, x1 in d["end_slabs"]:
                    with Locations(((x0 + x1) / 2, sy)):
                        Rectangle(x1 - x0, d["lip_outer"][1] + 2.0)
            add(slabs.sketch, mode=Mode.INTERSECT)
        extrude(ends.sketch, amount=d["z_end_top"] - d["z_lip_top"])
        # groove: floor at z_groove, open to the top, from inboard of the plug out through the lip
        with Locations(((g[0] + g[2]) / 2, (g[1] + g[3]) / 2, d["z_groove"])):
            Box(g[2] - g[0], g[3] - g[1], d["groove_depth"] + d["lip_h"] + 1.0, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    return bp.part


def build_hardware_for(size: str) -> dict[str, Compound]:
    """Bought parts as placed: standoff_plate's boards, screws, nuts and plugs for the screw plate; for the peg plate
    the boards (with their drilled holes) at the peg plate's height."""
    d = derive(size)
    if d["fixing"] == "screw":
        return build_hardware(d["plate"])
    p = d["p"]
    boards = []
    for pb in p["boards"]:
        slab = Box(*pb["size"], p["board_t"], align=ALIGN_MIN_Z).moved(Location((*pb["xy"], d["z_board_bottom"])))
        for hx, hy in pb["holes"]:
            slab -= Cylinder(pb["board"].hole_dia / 2, p["board_t"], align=ALIGN_MIN_Z).moved(Location((hx, hy, d["z_board_bottom"])))
        boards.append(slab)
    return dict(boards=Compound(children=boards))


def build_envelopes(size: str) -> dict[str, Compound]:
    """The sensor at its datasheet maximum on the plate top, and its plug hanging from the socket with the wire-bend
    room below it (the enclosure's numbers). Purchased-part envelopes, not models."""
    d = derive(size)
    e = d["e"]
    sx, sy = d["sensor_xy"]
    with BuildPart() as sensor:
        with BuildSketch(Location((sx, sy, d["z_floor"]))):
            RectangleRounded(*d["sensor_max"], e["sensor_corner_r"])
        extrude(amount=e["sensor_h"] + e["sensor_h_tol"])
    px, py = d["socket_xy"]
    plug_w, plug_t = (e["plug_w"], e["plug_t"]) if d["sensor_rot"] % 180 == 0 else (e["plug_t"], e["plug_w"])
    plug = Box(plug_w, plug_t, e["plug_len"] + e["bend_room"], align=ALIGN_MIN_Z).moved(
        Location((px, py, d["plug_bottom_z"] - e["bend_room"])))
    return dict(sensor=Compound(children=[sensor.part]), plug=Compound(children=[plug]))


def _frustum(r0: float, r1: float, h: float) -> float:
    return math.pi * h * (r0 * r0 + r0 * r1 + r1 * r1) / 3


def expected_volume(size: str, base: Part) -> float:
    """The base (the screw plate is checked against its own hand volume in check_plate; the peg plate is computed
    here) + the lip ring - the groove, which cuts the plate over its plan and the lip wall once."""
    d = derive(size)
    p = d["p"]

    def rr(w, h, r):
        return w * h - (4 - math.pi) * r * r
    if d["fixing"] == "screw":
        vol = base.volume
    else:
        n, R, f = len(p["holes"]), d["boss_r"], d["boss_root_flare"]
        vol = rr(*p["plate_size"], p["corner_r"]) * d["plate_t"]
        vol += n * (math.pi * R * R * d["standoff_h"] + _frustum(d["flare_r"], R, f) - math.pi * R * R * f)
        for pg in d["pegs"]:
            r = pg["d"] / 2
            vol += math.pi * r * r * (d["z_top"] - d["peg_tip"] - d["z_board_bottom"]) + _frustum(r, r - d["peg_tip"], d["peg_tip"])
    ring = rr(*d["lip_outer"], d["lip_outer_r"]) - rr(*d["pocket"], d["pocket_r"])

    def beyond(w, h, r, a):   # area of a rounded rectangle (w along the sensor) beyond a line a from its centre
        assert a <= w / 2 - r, "the cut line runs through a corner arc"
        return (w / 2 - a) * h - 2 * (1 - math.pi / 4) * r * r
    ends = sum(beyond(*d["lip_outer"], d["lip_outer_r"], a) - beyond(*d["pocket"], d["pocket_r"], a) for a in d["end_a"])
    vol += ends * (d["z_end_top"] - d["z_lip_top"])
    lip_cut = d["groove_w"] * d["lip_wall"] * d["lip_h"]
    groove = d["groove_w"] * d["groove_len"] * d["groove_depth"]
    return vol + ring * d["lip_h"] - lip_cut - groove


def check_part(size: str, part: Part) -> dict:
    """Geometry and function layers. Raises. Printability is in tests/."""
    d = derive(size)
    p = d["p"]
    label = f"sen66_bench {size}"
    base = build_base(size)
    if d["fixing"] == "screw":
        check_plate(d["plate"], base)   # bosses, pockets, bores, boards seated, screws and plugs clear
    assert part.is_valid, f"{label}: invalid"
    single_solid(part)
    assert_bbox(part, (*p["plate_size"], d["z_top"]), 0.0, d["bbox_tol"], label)
    vol = expected_volume(size, base)
    assert abs(part.volume - vol) < 1e-3, f"{label}: volume {part.volume:.3f} vs hand {vol:.3f}"

    sx, sy = d["sensor_xy"]
    g = d["groove_rect"]
    gx = (g[0] + g[2]) / 2
    z_lip = d["z_floor"] + d["lip_h"] / 2
    in_x, in_y = d["pocket"][0] / 2 + d["lip_wall"] / 2, d["pocket"][1] / 2 + d["lip_wall"] / 2
    out = 1.0 if d["groove_side"] == "+Y" else -1.0          # the side the groove leaves by
    lip_out_y, far_y = sy + out * in_y, sy - out * in_y
    inboard_y = (g[1] if out > 0 else g[3]) - out * 0.2       # just past the groove's inboard end
    outer_y = (g[3] if out > 0 else g[1]) + out * 0.2         # just past its outer end
    probes = {
        "lip +X": ((sx + in_x, sy, z_lip), True),
        "lip -X": ((sx - in_x, sy, z_lip), True),
        "lip far side": ((gx, far_y, z_lip), True),
        "lip beside groove": ((g[0] - 1.0, lip_out_y, z_lip), True),
        "groove through lip": ((gx, lip_out_y, z_lip), False),
        "pocket air": ((sx, sy, z_lip), False),
        "pocket floor": ((sx, sy, d["z_floor"] - 0.1), True),
        "groove under plug": ((gx, d["socket_xy"][1], d["z_groove"] + 0.1), False),
        "groove floor": ((gx, d["socket_xy"][1], d["z_groove"] - 0.1), True),
        "past the groove's inboard end": ((gx, inboard_y, d["z_groove"] + 0.1), True),
        "past the groove's outer end": ((gx, outer_y, d["z_groove"] + 0.1), True),
        "tall end lip, both ends": ((sx + in_x, sy, d["z_end_top"] - 0.2), True),
        "tall end lip, -X end": ((sx - in_x, sy, d["z_end_top"] - 0.2), True),
        "above the tall end lip": ((sx + in_x, sy, d["z_end_top"] + 0.1), False),
        "side lip stays low at mid length": ((sx, far_y, d["z_lip_top"] + 0.1), False),
        "tall lip wraps the corner": ((sx + d["pocket"][0] / 2 - d["pocket_r"] - 0.5, far_y, d["z_end_top"] - 0.2), True),
    }
    if d["fixing"] == "peg":
        zb = d["z_board_bottom"]
        for i, pg in enumerate(d["pegs"]):
            (x, y), r = pg["xy"], pg["d"] / 2
            probes.update({
                f"peg{i} in the board": ((x, y, zb + p["board_t"] / 2), True),
                f"peg{i} clear of the hole wall": ((x + (r + pg["hole"] / 2) / 2, y, zb + p["board_t"] / 2), False),
                f"peg{i} tip": ((x, y, d["z_top"] - 0.05), True),
                f"above peg{i}": ((x, y, d["z_top"] + 0.1), False),
                f"boss{i}": ((x + (r + d["boss_r"]) / 2, y, d["plate_t"] + d["standoff_h"] / 2), True),
                f"outside boss{i}": ((x + d["boss_r"] + 0.1, y, d["plate_t"] + d["standoff_h"] / 2), False),
                f"plate under boss{i}": ((x, y, d["plate_t"] / 2), True),
            })
    assert_material(part, probes)

    # function: the sensor at its maximum and its plug + wire bend clear the part; the boards, screws and plugs of
    # the plate clear the part and the sensor
    env = build_envelopes(size)
    for name, other in env.items():
        v = interference_volume(part, other)
        assert v < 1e-6, f"{label}: {name} envelope hits the part by {v:.4f} mm^3"
    hw = build_hardware_for(size)
    for name, other in hw.items():
        if not other.solids():
            continue
        v = interference_volume(other, env["sensor"])
        assert v < 1e-6, f"{label}: {name} hit the sensor by {v:.4f} mm^3"
    if d["fixing"] == "peg":
        v = interference_volume(part, hw["boards"])
        assert v < 1e-6, f"{label}: a peg or boss hits a board by {v:.4f} mm^3"
        for pb in p["boards"]:   # each board sits on every boss, and nothing of the part is inside its pin ring
            b, (bx, by) = pb["board"], pb["xy"]
            for hx, hy in pb["holes"]:
                r_seat = d["boss_r"] - 0.1
                dx = -r_seat if hx > bx else (r_seat if hx < bx else 0.0)
                dy = 0.0 if dx else (-r_seat if hy > by else r_seat)
                assert is_inside(part, (hx + dx, hy + dy, d["z_board_bottom"] - 0.05)) and \
                    is_inside(hw["boards"], (hx + dx, hy + dy, d["z_board_bottom"] + 0.05)), f"{label}: {b.name} not seated at ({hx:.2f}, {hy:.2f})"
                r_ring = b.nearest_pin - p["boss_pin_margin"] + 0.05
                for k in range(8):
                    a = 2 * math.pi * k / 8
                    px, py = hx + r_ring * math.cos(a), hy + r_ring * math.sin(a)
                    if abs(px - bx) > pb["size"][0] / 2 or abs(py - by) > pb["size"][1] / 2:
                        continue
                    assert not is_inside(part, (px, py, d["z_board_bottom"] - 0.5)), \
                        f"{label}: material at {r_ring:.2f} from hole ({hx:.2f}, {hy:.2f}) where {b.name}'s pins are"
    return dict(volume=part.volume, expected_volume=vol, bbox=part.bounding_box().size, hardware=hw, envelopes=env)


if __name__ == "__main__":
    from cacad import export, export_3mf, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects pathlib/os anywhere in this file
    for size in ACTIVE_SIZES:
        part = build_part(size)
        rep = check_part(size, part)
        bb = rep["bbox"]
        print(f"{size}: bbox {bb.X:.2f} x {bb.Y:.2f} x {bb.Z:.2f}, volume {rep['volume']:.1f} (hand {rep['expected_volume']:.1f}), "
              f"solids {len(part.solids())}, valid {part.is_valid}")
        export(part, f"sen66_bench_{size}", OUT)
        export_3mf({f"sen66_bench_{size}": part}, OUT + f"/sen66_bench_{size}.3mf")
    hw, env = rep["hardware"], rep["envelopes"]
    maybe_show(part, hw["boards"], env["sensor"], env["plug"], names=["plate", "boards", "sensor", "plug"])
