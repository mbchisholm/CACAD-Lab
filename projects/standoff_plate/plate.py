"""Standoff plate: plate + bosses + through bores + hex nut pockets from the
bed face; with `tray` in params, walls to a derived rim and a U-opening per
connector. `build_hardware` makes the boards, screws, nuts and the plug and
reach envelopes the part must mate with, for the function-layer checks.
Every number is from params.derive.

    .venv/bin/python projects/standoff_plate/plate.py [--show]     # builds params.ACTIVE_PLATES
"""
from __future__ import annotations

import math

from build123d import (Axis, Box, BuildPart, BuildSketch, Compound, Cylinder, Hole, Location, Locations, Mode, Part,
                       Plane, RegularPolygon, extrude, fillet)

from cacad import (ALIGN_MIN_Z, assert_bbox, assert_material, circular_edges, interference_volume, is_inside,
                   single_solid, try_chamfer)
from projects.standoff_plate.params import ACTIVE_PLATES, derive


def build_plate(plate: str) -> Part:
    d = derive(plate)
    cx, cy = d["plate_centre"]
    outer_h = d["wall_top_z"] if d["tray"] else d["plate_t"]
    with BuildPart() as bp:
        with Locations((cx, cy, outer_h / 2)):
            Box(*d["plate_size"], outer_h)
        fillet(bp.edges().filter_by(Axis.Z), radius=d["corner_r"])
        if d["tray"]:
            with Locations((cx, cy, d["plate_t"] + d["wall_h"] / 2)):
                Box(*d["inner"], d["wall_h"], mode=Mode.SUBTRACT)
            inner_r = d["corner_r"] - d["wall"]
            if inner_r > 0:
                fillet(bp.edges().filter_by(Axis.Z).filter_by(
                    lambda e: abs(abs(e.center().X - cx) - d["inner"][0] / 2) < 1e-6), radius=inner_r)
            for o in d["openings"]:   # U-slot from the rim, through one wall
                sx, sy = o["centre"]
                wx = (d["plate_x1"] if o["side"] == "+X" else d["plate_x0"]) - (d["wall"] / 2 if o["side"] == "+X" else -d["wall"] / 2)
                wy = (d["plate_y1"] if o["side"] == "+Y" else d["plate_y0"]) - (d["wall"] / 2 if o["side"] == "+Y" else -d["wall"] / 2)
                h = d["wall_top_z"] - o["z0"] + 1.0
                if o["side"] in ("+X", "-X"):
                    with Locations((wx, sy, o["z0"])):
                        Box(d["wall"] + 0.2, o["width"], h, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
                else:
                    with Locations((sx, wy, o["z0"])):
                        Box(o["width"], d["wall"] + 0.2, h, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        with Locations(*[(x, y, d["plate_t"]) for x, y in d["holes"]]):
            Cylinder(d["boss_r"], d["standoff_h"], align=ALIGN_MIN_Z)
        # nut pockets, open to the bed face; flats perpendicular to X
        with BuildSketch(Plane.XY) as sk:
            with Locations(*d["holes"]):
                RegularPolygon(d["pocket_r"], 6, rotation=30)
        extrude(sk.sketch, amount=d["pocket_depth"], mode=Mode.SUBTRACT)
        with Locations(*[(x, y, d["z_board_bottom"]) for x, y in d["holes"]]):
            Hole(d["bore_d"] / 2)
        if d["mount_holes"]:   # plain through bores for the screws that hold the plate down
            with Locations(*[(x, y, d["plate_t"]) for x, y in d["mount_holes"]]):
                Hole(d["mount_bore_d"] / 2)
    part = bp.part
    # finish last: cosmetic lead-in on each bore at the boss top
    lead_in = circular_edges(part, d["bore_d"] / 2, d["z_board_bottom"])
    return try_chamfer(part, lead_in, d["chamfer_bore"], d["chamfer_fallbacks"], f"{plate} bore lead-in")


def build_hardware(plate: str) -> dict[str, Compound]:
    """Boards (with their own holes), screws (shank + head) and nuts at their
    assembled positions. Purchased-part envelopes, not models."""
    d = derive(plate)
    sc = d["screw_spec"]
    boards, screws, nuts = [], [], []
    for pb in d["boards"]:
        x, y = pb["xy"]
        slab = Box(*pb["size"], d["board_t"], align=ALIGN_MIN_Z).moved(Location((x, y, d["z_board_bottom"])))
        for hx, hy in pb["holes"]:
            slab -= Cylinder(pb["board"].hole_dia / 2, d["board_t"], align=ALIGN_MIN_Z).moved(Location((hx, hy, d["z_board_bottom"])))
        boards.append(slab)
    for x, y in d["holes"]:
        shank = Cylinder(sc["d"] / 2, d["screw_len"], align=ALIGN_MIN_Z).moved(Location((x, y, d["screw_tip_z"])))
        head = Cylinder(sc["head_dk"] / 2, sc["head_k"], align=ALIGN_MIN_Z).moved(Location((x, y, d["z_board_top"])))
        screws.append(shank + head)
        with BuildSketch(Plane.XY.offset(d["pocket_depth"] - sc["nut_m"])) as sk:
            with Locations((x, y)):
                RegularPolygon(sc["nut_s"] / (2 * math.cos(math.radians(30))), 6, rotation=30)
        nuts.append(extrude(sk.sketch, amount=sc["nut_m"]) - Cylinder(sc["d"] / 2, sc["nut_m"], align=ALIGN_MIN_Z)
                    .moved(Location((x, y, d["pocket_depth"] - sc["nut_m"]))))
    # mount screws: shank through the plate, head on the plate top, and the straight-down driver column above the head
    mount_screws, mount_access = [], []
    for x, y in d["mount_holes"]:
        ms = d["mount_spec"]
        shank = Cylinder(ms["d"] / 2, d["plate_t"], align=ALIGN_MIN_Z).moved(Location((x, y, 0)))
        head = Cylinder(d["mount_head_r"], ms["head_k"], align=ALIGN_MIN_Z).moved(Location((x, y, d["plate_t"])))
        mount_screws.append(shank + head)
        z0 = d["plate_t"] + ms["head_k"]
        mount_access.append(Cylinder(d["mount_head_r"], d["z_head_top"] + 5.0 - z0, align=ALIGN_MIN_Z).moved(Location((x, y, z0))))
    plugs, reach = [], []
    for cn in d["connectors"]:
        if cn["plug"] is None:
            continue
        (mx, my), L, w, h = cn["plug"]
        fx, fy = cn["facing"]
        for length, dest in ((L, plugs), (cn["reach"], reach)):
            size = (length, w, h) if fx else (w, length, h)
            centre = (mx + fx * length / 2, my + fy * length / 2, d["z_board_top"])
            dest.append(Box(*size, align=ALIGN_MIN_Z).moved(Location(centre)))
    return dict(boards=Compound(children=boards), screws=Compound(children=screws), nuts=Compound(children=nuts),
                plugs=Compound(children=plugs), reach=Compound(children=reach),
                mount_screws=Compound(children=mount_screws), mount_access=Compound(children=mount_access))


def expected_volume(d: dict) -> float:
    """Plate box minus corner fillets, plus bosses (and tray walls minus
    openings), minus pockets and bores."""
    w, l = d["plate_size"]
    r = d["corner_r"]
    plate = (w * l - 4 * (r * r - math.pi * r * r / 4)) * d["plate_t"]
    if d["tray"]:
        ri = max(d["corner_r"] - d["wall"], 0.0)
        ring = (w * l - (4 - math.pi) * r * r) - (d["inner"][0] * d["inner"][1] - (4 - math.pi) * ri * ri)
        plate += ring * d["wall_h"]
        plate -= sum(o["width"] * d["wall"] * (d["wall_top_z"] - o["z0"]) for o in d["openings"])
    n = len(d["holes"])
    bosses = n * math.pi * d["boss_r"] ** 2 * d["standoff_h"]
    pockets = n * (3 * math.sqrt(3) / 2) * d["pocket_r"] ** 2 * d["pocket_depth"]
    bores = n * math.pi * (d["bore_d"] / 2) ** 2 * (d["plate_t"] + d["standoff_h"] - d["pocket_depth"])
    mount = len(d["mount_holes"]) * math.pi * (d.get("mount_bore_d", 0.0) / 2) ** 2 * d["plate_t"]
    return plate + bosses - pockets - bores - mount


def check_plate(plate: str, part: Part) -> dict:
    """Geometry and function layers (printability is in tests/). Raises."""
    d = derive(plate)
    label = f"plate {plate}"
    assert part.is_valid, f"{label}: invalid"
    single_solid(part)
    top = d["wall_top_z"] if d["tray"] else d["plate_t"] + d["standoff_h"]
    assert_bbox(part, (*d["plate_size"], top), 0.0, d["bbox_tol"], label)
    vol = expected_volume(d)
    # the lead-in chamfer removes a little; allow it, but only downwards and only a chamfer's worth
    chamfer_max = len(d["holes"]) * math.pi * d["bore_d"] * d["chamfer_bore"] ** 2
    assert vol - chamfer_max - 1e-6 <= part.volume <= vol + 1e-6, f"{label}: volume {part.volume:.3f} vs hand {vol:.3f}"

    probes = {}
    s2 = d["pocket_s"] / 2
    for i, (x, y) in enumerate(d["holes"]):
        z_b = d["plate_t"] + d["standoff_h"] / 2
        probes.update({
            f"boss{i} wall": ((x + (d["bore_d"] / 2 + d["boss_r"]) / 2, y, z_b), True),
            f"boss{i} bore": ((x, y, z_b), False),
            f"boss{i} outside": ((x + d["boss_r"] + 0.1, y, z_b), False),
            f"pocket{i} air at flat": ((x + s2 - 0.1, y, d["pocket_depth"] / 2), False),
            f"pocket{i} wall past flat": ((x + s2 + 0.15, y, d["pocket_depth"] / 2), True),
            f"pocket{i} air at corner": ((x, y + d["pocket_r"] - 0.1, d["pocket_depth"] / 2), False),
            f"web{i} solid": ((x + d["bore_d"] / 2 + 0.3, y, d["pocket_depth"] + d["pocket_web"] / 2), True),
            f"web{i} bore": ((x, y, d["pocket_depth"] + d["pocket_web"] / 2), False),
        })
    for i, (x, y) in enumerate(d["mount_holes"]):   # through bore, material past it on the plate-edge side
        sx = 1.0 if x > d["plate_centre"][0] else -1.0
        for z in (0.2, d["plate_t"] / 2, d["plate_t"] - 0.2):
            probes[f"mount{i} bore z{z:.1f}"] = ((x, y, z), False)
        probes[f"mount{i} wall to edge"] = ((x + sx * (d["mount_bore_d"] / 2 + 0.3), y, d["plate_t"] / 2), True)
    assert_material(part, probes)

    # function: the purchased parts and the boards, placed, intersect nothing they should not
    hw = build_hardware(plate)
    for name, other in hw.items():
        if other.is_null or not other.solids():
            continue
        v = interference_volume(part, other)
        assert v < 1e-6, f"{label}: {name} interfere with the part by {v:.4f} mm^3"
    if hw["reach"].solids():   # unplugging room is clear of every board, including the connector's own neighbours
        v = interference_volume(hw["reach"], hw["boards"])
        assert v < 1e-6, f"{label}: plug reach hits a board by {v:.4f} mm^3"
    for o in d["openings"]:     # the opening is where params says: air at its centre just above its floor, wall beside it
        x, y = (d["plate_x1"] - d["wall"] / 2 if o["side"] == "+X" else d["plate_x0"] + d["wall"] / 2, o["centre"][1]) \
            if o["side"] in ("+X", "-X") else (o["centre"][0], d["plate_y1"] - d["wall"] / 2 if o["side"] == "+Y" else d["plate_y0"] + d["wall"] / 2)
        dx, dy = (0, o["width"] / 2 + 0.2) if o["side"] in ("+X", "-X") else (o["width"] / 2 + 0.2, 0)
        assert not is_inside(part, (x, y, o["z0"] + 0.2)), f"{label}: opening {o['side']} not cut"
        assert is_inside(part, (x, y, o["z0"] - 0.2)), f"{label}: opening {o['side']} floor missing"
        assert is_inside(part, (x + dx, y + dy, o["z0"] + 0.2)), f"{label}: no wall beside opening {o['side']}"
    if hw["mount_access"].solids():   # a driver reaches every mount head straight down, past the boards and their screws
        for other in ("boards", "screws"):
            v = interference_volume(hw["mount_access"], hw[other])
            assert v < 1e-6, f"{label}: mount screw driver column hits the {other} by {v:.4f} mm^3"
    assert interference_volume(hw["screws"], hw["boards"]) < 1e-6, f"{label}: screws hit the boards"
    assert interference_volume(hw["screws"], hw["nuts"]) < 1e-6, f"{label}: screw shank hits the nut (bore)"
    # the board rests on every boss: boss top touches the board underside inside its outline
    for pb in d["boards"]:
        b, (x, y) = pb["board"], pb["xy"]
        for hx, hy in pb["holes"]:
            # probe the seat towards the board centre, where boss and board certainly overlap
            r_seat = d["boss_r"] - 0.1
            dx = -r_seat if hx > x else (r_seat if hx < x else 0.0)
            dy = 0.0 if dx else (-r_seat if hy > y else r_seat)
            pt_boss = (hx + dx, hy + dy, d["z_board_bottom"] - 0.05)
            pt_board = (hx + dx, hy + dy, d["z_board_bottom"] + 0.05)
            assert is_inside(part, pt_boss) and is_inside(hw["boards"], pt_board), f"{label}: {b.name} not seated on boss at ({hx:.2f}, {hy:.2f})"
            # nothing of the part inside the pin ring under the board (nearest_pin - margin), any direction the
            # board extends to; a pin ring reaching past the board's own outline proves nothing there
            r_ring = b.nearest_pin - d["boss_pin_margin"] + 0.05
            for k in range(8):
                a = 2 * math.pi * k / 8
                px, py = hx + r_ring * math.cos(a), hy + r_ring * math.sin(a)
                if abs(px - x) > pb["size"][0] / 2 or abs(py - y) > pb["size"][1] / 2:
                    continue
                assert not is_inside(part, (px, py, d["z_board_bottom"] - 0.5)), \
                    f"{label}: material at {r_ring:.2f} from hole ({hx:.2f}, {hy:.2f}) where {b.name}'s pins are"
    assert hw["screws"].bounding_box().min.Z >= d["screw_tip_min"] - 1e-6, f"{label}: screw tip below its floor"
    return dict(volume=part.volume, expected_volume=vol, bbox=part.bounding_box().size, hardware=hw)


result = build_plate(ACTIVE_PLATES[0])

if __name__ == "__main__":
    from cacad import export, export_3mf, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for plate in ACTIVE_PLATES:
        part = build_plate(plate)
        rep = check_plate(plate, part)
        bb = rep["bbox"]
        print(f"{plate}: bbox {bb.X:.2f} x {bb.Y:.2f} x {bb.Z:.2f}, volume {rep['volume']:.1f} (hand {rep['expected_volume']:.1f}), "
              f"solids {len(part.solids())}, valid {part.is_valid}")
        export(part, f"standoff_plate_{plate}", OUT)
        export_3mf({f"standoff_plate_{plate}": part}, OUT + f"/standoff_plate_{plate}.3mf")
        hw = rep["hardware"]
        maybe_show(part, hw["boards"], hw["screws"], hw["nuts"], hw["plugs"], names=["plate", "boards", "screws", "nuts", "plugs"])
