"""sen66_bench: the SEN66_BENCH standoff plate (Metro ESP32-S3 + SEN6x breakout on M2 bosses, nuts captured from the
bed face) plus a lip the SEN66 drops into and a groove under its socket for the cable. Every number is from
params.derive; the plate and its own checks are projects/standoff_plate's.

    .venv/bin/python projects/sen66_bench/sen66_bench.py [--show]     # ACTIVE_SIZES -> out/

A part file names no filesystem module (os, pathlib, sys): the build123d-mcp
sandbox refuses the file (FINDINGS F23). It imports params by package path (F24).
"""
from __future__ import annotations

import math

from build123d import (Box, BuildPart, BuildSketch, Compound, Location, Locations, Mode, Part, RectangleRounded, add,
                       extrude)

from cacad import ALIGN_MIN_Z, assert_bbox, assert_material, interference_volume, single_solid
from projects.sen66_bench.params import ACTIVE_SIZES, derive
from projects.standoff_plate.plate import build_hardware, build_plate, check_plate


def build_part(size: str) -> Part:
    d = derive(size)
    sx, sy = d["sensor_xy"]
    g = d["groove_rect"]
    plate = build_plate(d["plate"])   # outside the builder: its lead-in chamfer() would act on an open BuildPart
    with BuildPart() as bp:
        add(plate)
        with BuildSketch(Location((sx, sy, d["z_floor"]))) as lip:
            RectangleRounded(*d["lip_outer"], d["lip_outer_r"])
            RectangleRounded(*d["pocket"], d["pocket_r"], mode=Mode.SUBTRACT)
        extrude(lip.sketch, amount=d["lip_h"])
        # groove: floor at z_groove, open to the top, through the lip and out through the plate edge (1.0 past it)
        out = -1.0 if d["groove_side"] == "-Y" else 1.0
        with Locations(((g[0] + g[2]) / 2, (g[1] + g[3]) / 2 + out * 0.5, d["z_groove"])):
            Box(g[2] - g[0], g[3] - g[1] + 1.0, d["groove_depth"] + d["lip_h"] + 1.0, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    return bp.part


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


def expected_volume(size: str, plate: Part) -> float:
    """The standoff plate (checked against its own hand volume in check_plate) + the lip ring - the groove, which
    cuts the plate from its inboard end to the plate edge, and the lip wall once."""
    d = derive(size)

    def rr(w, h, r):
        return w * h - (4 - math.pi) * r * r
    ring = rr(*d["lip_outer"], d["lip_outer_r"]) - rr(*d["pocket"], d["pocket_r"])
    lip_cut = d["groove_w"] * d["lip_wall"] * d["lip_h"]
    groove = d["groove_w"] * d["groove_len"] * d["groove_depth"]
    return plate.volume + ring * d["lip_h"] - lip_cut - groove


def check_part(size: str, part: Part) -> dict:
    """Geometry and function layers. Raises. Printability is in tests/."""
    d = derive(size)
    p = d["p"]
    label = f"sen66_bench {size}"
    plate = build_plate(d["plate"])
    check_plate(d["plate"], plate)     # bosses, pockets, bores, boards seated, screws and plugs clear
    assert part.is_valid, f"{label}: invalid"
    single_solid(part)
    assert_bbox(part, (*p["plate_size"], p["plate_t"] + p["standoff_h"]), 0.0, d["bbox_tol"], label)
    vol = expected_volume(size, plate)
    assert abs(part.volume - vol) < 1e-3, f"{label}: volume {part.volume:.3f} vs hand {vol:.3f}"

    sx, sy = d["sensor_xy"]
    g = d["groove_rect"]
    gx = (g[0] + g[2]) / 2
    z_lip = d["z_floor"] + d["lip_h"] / 2
    in_x, in_y = d["pocket"][0] / 2 + d["lip_wall"] / 2, d["pocket"][1] / 2 + d["lip_wall"] / 2
    out = 1.0 if d["groove_side"] == "+Y" else -1.0          # towards the plate edge the groove leaves by
    lip_out_y, far_y = sy + out * in_y, sy - out * in_y
    inboard_y = (g[1] if out > 0 else g[3]) - out * 0.2       # just past the groove's inboard end
    edge_y = (p["plate_y1"] if out > 0 else p["plate_y0"]) - out * 0.2   # just inside the plate edge
    assert_material(part, {
        "lip +X": ((sx + in_x, sy, z_lip), True),
        "lip -X": ((sx - in_x, sy, z_lip), True),
        "lip far side": ((gx, far_y, z_lip), True),
        "lip beside groove": ((g[0] - 1.0, lip_out_y, z_lip), True),
        "groove through lip": ((gx, lip_out_y, z_lip), False),
        "pocket air": ((sx, sy, z_lip), False),
        "pocket floor": ((sx, sy, d["z_floor"] - 0.1), True),
        "lip top": ((sx + in_x, sy, d["z_lip_top"] + 0.1), False),
        "groove under plug": ((gx, d["socket_xy"][1], d["z_groove"] + 0.1), False),
        "groove floor": ((gx, d["socket_xy"][1], d["z_groove"] - 0.1), True),
        "past the groove's inboard end": ((gx, inboard_y, d["z_groove"] + 0.1), True),
        "groove open at the plate edge": ((gx, edge_y, d["z_groove"] + 0.1), False),
        "floor under the groove at the edge": ((gx, edge_y, d["z_groove"] - 0.1), True),
        "plate edge beside the groove": ((g[0] - 1.0, edge_y, d["z_groove"] + 0.1), True),
    })

    # function: the sensor at its maximum and its plug + wire bend clear the part; the boards, screws and plugs of
    # the plate clear the sensor
    env = build_envelopes(size)
    for name, other in env.items():
        v = interference_volume(part, other)
        assert v < 1e-6, f"{label}: {name} envelope hits the part by {v:.4f} mm^3"
    hw = build_hardware(d["plate"])
    for name in ("boards", "screws", "plugs", "reach"):
        if hw[name].solids():
            v = interference_volume(hw[name], env["sensor"])
            assert v < 1e-6, f"{label}: {name} hit the sensor by {v:.4f} mm^3"
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
        maybe_show(part, hw["boards"], hw["screws"], env["sensor"], env["plug"], names=["plate", "boards", "screws", "sensor", "plug"])
