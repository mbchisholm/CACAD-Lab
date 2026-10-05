"""Nutrient controller post plate (and, for the wall mount, its backing plate).
The plate carries three mushroom posts the box hangs on and a slot for the
pump tubes. Wall mount (B1): it bolts flat to the outside of the tote's end
wall (4 x M5 into the backing plate inside the tote, which spreads the load)
and has a window for the probe cables. Rim mount (B2): it bolts to the rim
hook through two M5 holes whose nuts sit in bosses on its box side. Box frame (params docstring);
every number from params.derive. Both print flat on their tote-side face.

    .venv/bin/python projects/nutrient_controller/wall_plate.py
"""
from __future__ import annotations

from build123d import Axis, Cone, Location, Part, Pos, Rot, fillet

from projects.nutrient_controller.geom import box, cyl, hex_prism
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
    if d["mount"] == "wall":
        cuts = [cyl(d["plate_bolt_hole"], "x", ((x0 + x1) / 2, y, z), d["plate_t"] + 0.02) for y, z in d["plate_bolts"]]
        cy, cz = d["cable_hole"]
        cuts.append(cyl(d["plate_window_d"], "x", ((x0 + x1) / 2, cy, cz), d["plate_t"] + 0.02))
    else:
        # rim clamp: two M5 holes for the hook, each nut in a boss on the box side (pocket opens up in print)
        nb_d, nb_h = d["plate_nut_boss"]
        pk = d["plate_nut_pocket"]
        z = d["hook_bolts_z"]
        cuts = []
        for y in d["hook_bolts_y"]:
            plate += cyl(nb_d, "x", (x1 + nb_h / 2, y, z), nb_h)
            cuts.append(cyl(d["hook_bolt_hole"], "x", ((x0 + x1 + nb_h) / 2, y, z), d["plate_t"] + nb_h + 0.02))
            cuts.append(hex_prism(pk["s"], "x", (x1 + nb_h - pk["depth"] / 2 + 0.01, y, z), pk["depth"] + 0.02, "z"))
    ty = -d["W"] / 2 - d["parts"]["pump"]["head_depth"] / 2
    lo, hi = d["tube_z"]
    sw = d["tube_slot_w"]
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


def check_plates(plate: Part, backing: Part | None, size: str = "B1") -> dict:
    from cacad import assert_material
    from cacad.checks.orientation import check_declared_orientation
    from cacad.checks.overhang import check_overhang
    d = derive(size)
    reps = {}
    parts = [("plate", plate, plate_x(d)[0])]
    if backing is not None:
        parts.append(("backing", backing, plate_x(d)[0] - max(d["tote_wall_t"]) - d["backing_t"]))
    for name, p, bed_x in parts:
        single_solid(p)
        assert p.is_valid, f"{name}: invalid solid"
        printed = p.rotate(Axis.Y, -90).moved(Location((0, 0, -bed_x)))
        o = dict(d["print_orientation"][name], up=(0, 0, 1), bed_z=0.0)
        check_declared_orientation(printed, o)
        reps[name] = check_overhang(printed, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"]))
    x0, x1 = plate_x(d)
    ky, kz = d["keyholes"][0]
    probes = {"post neck": ((x1 + 2.0, ky, kz), True), "plate body": (((x0 + x1) / 2, 0.0, 30.0), True)}
    if d["mount"] == "wall":
        cy, cz = d["cable_hole"]
        probes["cable window"] = (((x0 + x1) / 2, cy, cz), False)
    else:
        y, z = d["hook_bolts_y"][0], d["hook_bolts_z"]
        probes["hook bolt hole"] = (((x0 + x1) / 2, y, z), False)
        probes["nut boss wall"] = ((x1 + 1.0, y + d["plate_nut_boss"][0] / 2 - 0.5, z), True)
    assert_material(plate, probes)
    return reps


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        p = build_plate(size)
        b = build_backing(size) if derive(size)["mount"] == "wall" else None
        reps = check_plates(p, b, size)
        for name, part in (("plate", p), ("backing", b)):
            if part is None:
                continue
            bb = part.bounding_box()
            print(f"{name} {size}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {part.volume / 1000:.1f} cm3, "
                  f"worst overhang {reps[name]['worst_ok']:.0f} deg")
            export(part, f"{size}_{name}", out)
    result = p
