"""SEN6x enclosure: base (floor, pocket, long-wall windows on the outlet arches, cable groove, four insert holes in
the end walls) and lid (plate with a hole over each top opening and four screw bores). `build_hardware` places the
vendor STEP, the GHR-06V-S plug, the wire-bend room, the six wires and the screws for the function checks. Every number is from
params.derive.

    .venv/bin/python projects/sen6x_enclosure/enclosure.py [--show]
"""
from __future__ import annotations

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Circle, Compound, Cylinder, Line, Location, Locations,
                       Mode, Part, Plane, Polygon, Rectangle, RectangleRounded, ThreePointArc, Transition, Wire, extrude,
                       fillet, import_step, sweep)

from cacad import (ALIGN_MIN_Z, assert_bbox, assert_material, circular_edges, export, export_3mf, interference_volume,
                   maybe_show, single_solid, try_chamfer)
from projects.sen6x_enclosure.params import derive

HERE = __file__.rsplit("/", 1)[0]
SENSOR_STEP = HERE + "/ref/SEN6x.step"
OUT = HERE + "/out"


def build_base() -> Part:
    d = derive()
    with BuildPart() as bp:
        Box(d["outer_l"], d["outer_w"], d["z_lid"], align=ALIGN_MIN_Z)
        fillet(bp.edges().filter_by(Axis.Z), radius=d["outer_corner_r"])
        with BuildSketch(Plane.XY.offset(d["z_floor"])):
            RectangleRounded(d["pocket_l"], d["pocket_w"], d["pocket_corner_r"])
        extrude(amount=d["z_lid"], mode=Mode.SUBTRACT)
        # outlet windows: the arch profile, both long walls in one cut (the pocket between them is already empty)
        prof = [(x, d["z_floor"] + z) for x, z in d["window_profile"]]
        with BuildSketch(Plane.XZ):
            Polygon(*prof, align=None)
        extrude(amount=d["outer_w"] / 2 + 1, both=True, mode=Mode.SUBTRACT)
        # cable groove: under the plug, out under the -Y wall into the window
        (gx0, gx1), (gy0, gy1) = d["groove_x"], d["groove_y"]
        with Locations(((gx0 + gx1) / 2, (gy0 + gy1) / 2, d["z_groove"])):
            Box(gx1 - gx0, gy1 - gy0, d["z_floor"] - d["z_groove"] + 0.01, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
        # heat-set insert holes from the wall top
        with Locations(*[(x, y, d["z_lid"] - d["insert_hole_depth"]) for x, y in d["inserts"]]):
            Cylinder(d["insert_bore"] / 2, d["insert_hole_depth"] + 0.01, align=ALIGN_MIN_Z, mode=Mode.SUBTRACT)
    part = single_solid(bp.part)
    # finish last: cosmetic lead-in on each insert hole
    return try_chamfer(part, circular_edges(part, d["insert_bore"] / 2, d["z_lid"]), d["chamfer_top"], (0.3, 0.2),
                       "insert lead-in")


def build_lid() -> Part:
    d = derive()
    with BuildPart() as bp:
        with Locations((0, 0, d["z_lid"])):
            Box(d["outer_l"], d["outer_w"], d["lid_t"], align=ALIGN_MIN_Z)
        fillet(bp.edges().filter_by(Axis.Z), radius=d["outer_corner_r"])
        with BuildSketch(Plane.XY.offset(d["z_lid"])):
            for h in d["lid_holes"].values():
                with Locations(h["c"]):
                    Circle(h["d"] / 2) if h["kind"] == "circle" else Rectangle(*h["size"])
            with Locations(*d["inserts"]):
                Circle(d["screw_bore"] / 2)
        extrude(amount=d["lid_t"], mode=Mode.SUBTRACT)
    return single_solid(bp.part)


def build_sensor() -> Part:
    """The vendor STEP is Y-up (SolidWorks): turn it Z-up and stand it on the floor."""
    d = derive()
    s = import_step(SENSOR_STEP)
    s.parent = None   # import_step leaves it a child of the file's root Compound; export_step then fails (F32)
    s = s.rotate(Axis.X, 90)
    bb = s.bounding_box(optimal=True)
    return s.moved(Location((0, 0, d["z_floor"] - bb.min.Z)))


def build_cable() -> list[Part]:
    """One swept wire per pin, pin 1 first: down out of the plug's end, a 90 deg turn toward -Y, along the groove
    floor, out under the -Y wall."""
    d = derive()
    sy, z0, zc, r = d["socket_y"], d["wire_z0"], d["wire_zc"], d["wire_bend_r"]
    wires = []
    for x in d["wire_x"]:
        c = (x, sy - r, zc + r)                                        # centre of the turn
        path = Wire([
            ThreePointArc((x, sy, z0), (x, c[1] + r * 0.70710678, c[2] - r * 0.70710678), (x, sy - r, zc)),
            Line((x, sy - r, zc), (x, d["wire_y_end"], zc)),
        ])
        profile = Plane(origin=(x, sy, z0), z_dir=(0, 0, -1)) * Circle(d["wire_od"] / 2)
        wires.append(single_solid(sweep(profile, path=path, transition=Transition.ROUND)))
    return wires


def build_hardware() -> dict:
    """Sensor, plug, the wire-bend room under it, and the four screws at their assembled positions."""
    d = derive()
    sx, sy = d["socket_x"], d["socket_y"]
    plug = Box(d["plug_w"], d["plug_t"], d["plug_len"], align=ALIGN_MIN_Z).moved(Location((sx, sy, d["z_floor"] + d["plug_bottom_z"])))
    bend = Box(d["plug_w"], d["plug_t"], d["bend_room"], align=(Align.CENTER, Align.CENTER, Align.MAX)).moved(
        Location((sx, sy, d["z_floor"] + d["plug_bottom_z"])))
    screws = [Cylinder(d["screw_d"] / 2, d["screw_len"], align=ALIGN_MIN_Z).moved(Location((x, y, d["screw_tip_z"])))
              + Cylinder(d["screw_head_dk"] / 2, d["screw_head_k"], align=ALIGN_MIN_Z).moved(Location((x, y, d["z_top"])))
              for x, y in d["inserts"]]
    return dict(sensor=build_sensor(), plug=plug, bend=bend, screws=Compound(screws), cable=Compound(build_cable()))


def build_keepouts() -> dict:
    """Air the sensor must have: a column over each top opening (sensor opening at its tolerance, no margin), from the
    sensor top through the lid."""
    d = derive()
    z0 = d["z_floor"] + d["sensor_h"] - d["sensor_h_tol"]
    h = d["z_top"] + 1 - z0
    tol = d["top_open_tol"] + d["fit_clear"]
    sq = ((d["sq_x0"] + d["sq_x1"]) / 2, (d["sq_y0"] + d["sq_y1"]) / 2)
    return dict(
        fan=Cylinder(d["fan_d"] / 2 + tol, h, align=ALIGN_MIN_Z).moved(Location((d["fan_x"], d["fan_y"], z0))),
        round=Cylinder(d["rd_d"] / 2 + tol, h, align=ALIGN_MIN_Z).moved(Location((d["rd_x"], d["rd_y"], z0))),
        square=Box(d["sq_x1"] - d["sq_x0"] + 2 * tol, d["sq_y1"] - d["sq_y0"] + 2 * tol, h, align=ALIGN_MIN_Z).moved(
            Location((*sq, z0))),
    )


def check(base: Part, lid: Part, hw: dict, keep: dict) -> dict:
    """Function layer: nothing the sensor needs is printed over. Returns the measured numbers."""
    d = derive()
    tol = 0.05
    assert_bbox(base, (d["outer_l"], d["outer_w"], d["z_lid"]), 0.0, tol, "base")
    assert_bbox(lid, (d["outer_l"], d["outer_w"], d["lid_t"]), d["z_lid"], tol, "lid")
    got = {}
    for a, b in [("sensor", "base"), ("sensor", "lid"), ("plug", "base"), ("bend", "base"), ("plug", "sensor"),
                 ("screws", "lid"), ("screws", "base"), ("cable", "base"), ("cable", "sensor"), ("cable", "plug")]:
        sa = hw[a]
        sb = dict(base=base, lid=lid, sensor=hw["sensor"], plug=hw["plug"])[b]
        got[f"{a} x {b}"] = v = interference_volume(sa, sb)
        assert v < 1e-3, f"{a} intersects {b}: {v:.4f} mm3"
    for k, ko in keep.items():
        got[f"inlet {k} x lid"] = v = interference_volume(ko, lid)
        assert v < 1e-3, f"lid covers the {k} opening: {v:.4f} mm3"
    # the sensor stands on the floor and stays under the lid at its tallest
    sb = hw["sensor"].bounding_box(optimal=True)
    assert abs(sb.min.Z - d["z_floor"]) < 1e-3, f"sensor bottom at {sb.min.Z:.3f}, floor at {d['z_floor']:.3f}"
    got["lid gap at +tol"] = d["z_lid"] - (sb.max.Z + d["sensor_h_tol"])
    assert got["lid gap at +tol"] >= d["lid_gap"] - 1e-6, f"lid gap {got['lid gap at +tol']:.3f}"
    # outlet: probe pairs on each long wall, in the window just under its top, and in the wall just above it
    zw, yw = d["z_floor"] + d["window_top"], d["outer_w"] / 2 - d["wall"] / 2
    pts = {}
    for side in (-1, 1):
        pts[f"window {side:+d} open"] = ((-4.0, side * yw, zw - 0.3), False)
        pts[f"wall {side:+d} above window"] = ((-4.0, side * yw, zw + 0.3), True)
        pts[f"wall {side:+d} beside window"] = ((d["window_x"][1] + 1.0, side * yw, d["z_floor"] + 1.0), True)
    gy = -yw   # mid -Y wall, where the groove passes under it
    pts["groove under -Y wall open"] = ((d["socket_x"], gy, d["z_groove"] + 0.3), False)
    pts["floor under groove solid"] = ((d["socket_x"], gy, d["z_groove"] - 0.3), True)
    assert_material(base, pts)
    return got


def build_all():
    base, lid = build_base(), build_lid()
    hw, keep = build_hardware(), build_keepouts()
    return base, lid, hw, keep


if __name__ == "__main__":
    base, lid, hw, keep = build_all()
    for k, v in check(base, lid, hw, keep).items():
        print(f"  {k}: {v:.4f}")
    for name, part in (("base", base), ("lid", lid)):
        bb = part.bounding_box()
        print(f"{name}: valid={part.is_valid} volume={part.volume:.0f} mm3 bbox {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f}")
        export(part, f"sen6x_{name}", OUT)
    # print orientation: base floor down as built; lid flipped, top face on the bed
    export_3mf(dict(base=base, lid=lid.rotate(Axis.X, 180)), OUT + "/sen6x_enclosure.3mf")
    for name in ("sensor", "plug", "screws"):   # placed, for freecad_view.py
        export(hw[name], f"sen6x_{name}_placed", OUT)
    for i, w in enumerate(build_cable()):   # one STEP per wire, pin 1 first, so FreeCAD can colour by pin
        export(w, f"sen6x_wire{i + 1}_placed", OUT)
    export(Compound([base, lid, hw["sensor"], hw["plug"], hw["screws"], hw["cable"]]), "sen6x_assembly", OUT)
    print("exported to", OUT)
    maybe_show(base, lid, hw["sensor"], hw["plug"], names=["base", "lid", "sensor", "plug"])
