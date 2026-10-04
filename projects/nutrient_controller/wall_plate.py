"""Nutrient controller B1 wall plate and backing plate. The wall plate bolts
flat to the outside of the tote's end wall (4 x M5 through the wall into the
backing plate inside the tote) and carries three mushroom posts the box hangs
on, a window for the probe cables and a slot for the pump tubes. The backing
plate spreads the bolt load on the HDPE wall. Box frame (params docstring);
every number from params.derive. Both print flat on their tote-side face.

    .venv/bin/python projects/nutrient_controller/wall_plate.py
"""
from __future__ import annotations

from build123d import Axis, Cone, Location, Part, Pos, Rot, fillet

from projects.nutrient_controller.geom import box, cyl
from projects.nutrient_controller.params import ACTIVE_SIZES, derive

from cacad import export, single_solid


def _outline(d, x0, x1):
    (y0, y1), (z0, z1) = d["plate_y"], d["plate_z"]
    p = box(x0, x1, y0, y1, z0, z1)
    try:
        return fillet(p.edges().filter_by(Axis.X), d["corner_r"])
    except Exception:
        return p


def plate_x(d):
    """(tote-side face, front face) of the wall plate."""
    return -d["gap"] - d["plate_t"], -d["gap"]


def build_plate(size: str = "B1") -> Part:
    d = derive(size)
    x0, x1 = plate_x(d)
    plate = _outline(d, x0, x1)
    nl = d["post_neck_l"]
    rn, rh = d["post_neck_d"] / 2, d["post_head_d"] / 2
    for y, z in d["keyholes"]:
        plate += cyl(d["post_neck_d"], "x", (x1 + nl / 2, y, z), nl + 0.02)
        cone_h = rh - rn
        plate += Pos(x1 + nl, y, z) * Rot(0, 90, 0) * Pos(0, 0, cone_h / 2) * Cone(rn, rh, cone_h)
        plate += cyl(d["post_head_d"], "x", (x1 + nl + cone_h + d["post_head_t"] / 2, y, z), d["post_head_t"])
    cuts = [cyl(d["plate_bolt_hole"], "x", ((x0 + x1) / 2, y, z), d["plate_t"] + 0.02) for y, z in d["plate_bolts"]]
    cy, cz = d["cable_hole"]
    cuts.append(cyl(d["plate_window_d"], "x", ((x0 + x1) / 2, cy, cz), d["plate_t"] + 0.02))
    ty = d["tote_holes"]["tube"][0]
    lo, hi = d["tube_z"]
    sw = d["tube_hole_d"] + 4.0                                  # DESIGN: slot width around both tube ends
    cuts.append(box(x0 - 0.01, x1 + 0.01, ty - sw / 2, ty + sw / 2, lo - sw / 2, hi + sw / 2))
    for c in cuts:
        plate -= c
    return plate


def build_backing(size: str = "B1") -> Part:
    d = derive(size)
    x0 = plate_x(d)[0] - max(d["tote_wall_t"]) - d["backing_t"]   # drawn at the thickest wall
    back = _outline(d, x0, x0 + d["backing_t"])
    cuts = [cyl(d["plate_bolt_hole"], "x", (x0 + d["backing_t"] / 2, y, z), d["backing_t"] + 0.02) for y, z in d["plate_bolts"]]
    cy, cz = d["cable_hole"]
    cuts.append(cyl(d["cable_hole_d"] + 4.0, "x", (x0 + d["backing_t"] / 2, cy, cz), d["backing_t"] + 0.02))
    ty, tz = d["tote_holes"]["tube"]
    cuts.append(cyl(d["tube_hole_d"] + 4.0, "x", (x0 + d["backing_t"] / 2, ty, tz), d["backing_t"] + 0.02))
    for c in cuts:
        back -= c
    return back


def check_plates(plate: Part, backing: Part, size: str = "B1") -> dict:
    from cacad import assert_material
    from cacad.checks.orientation import check_declared_orientation
    from cacad.checks.overhang import check_overhang
    d = derive(size)
    reps = {}
    for name, p, bed_x in (("plate", plate, plate_x(d)[0]),
                           ("backing", backing, plate_x(d)[0] - max(d["tote_wall_t"]) - d["backing_t"])):
        single_solid(p)
        assert p.is_valid, f"{name}: invalid solid"
        printed = p.rotate(Axis.Y, -90).moved(Location((0, 0, -bed_x)))
        o = dict(d["print_orientation"][name], up=(0, 0, 1), bed_z=0.0)
        check_declared_orientation(printed, o)
        reps[name] = check_overhang(printed, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"]))
    x0, x1 = plate_x(d)
    cy, cz = d["cable_hole"]
    ky, kz = d["keyholes"][0]
    assert_material(plate, {
        "cable window": (((x0 + x1) / 2, cy, cz), False),
        "post neck": ((x1 + 2.0, ky, kz), True),
        "plate body": (((x0 + x1) / 2, 0.0, 30.0), True),
    })
    return reps


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        p, b = build_plate(size), build_backing(size)
        reps = check_plates(p, b, size)
        for name, part in (("plate", p), ("backing", b)):
            bb = part.bounding_box()
            print(f"{name} {size}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {part.volume / 1000:.1f} cm3, "
                  f"worst overhang {reps[name]['worst_ok']:.0f} deg")
            export(part, f"{size}_{name}", out)
    result = p
