"""Nutrient controller B2 rim clamp: a C-hook over the container's rim, an M6
thumbscrew knob and a pressure pad. Fits any container whose wall or lip at
the screw is rim_c thick; nothing is drilled.

The hook's leg bolts to the post plate's container side through two vertical
slots (box height under the rim adjustable). Its bridge sits on the rim top
with a groove for the probe cables and the dosing tube; its inner jaw bears on
the container's inside face. An ISO 4017 M6 screw through the leg (nut in a
pocket open to the throat, so clamping pushes it into the leg) presses the pad
against the container's outside. Box frame, every number from params.derive.
The hook prints upside down on its bridge; knob and pad print flat.

    .venv/bin/python projects/nutrient_controller/rim_hook.py
"""
from __future__ import annotations

import math

from build123d import Axis, Location, Part, Plane, Polygon, Pos, Rot, extrude

from cacad import export, single_solid
from projects.nutrient_controller.geom import box, cyl, hex_prism, slot_teardrop, teardrop
from projects.nutrient_controller.params import ACTIVE_SIZES, derive


def build_hook(size: str = "B2") -> Part:
    d = derive(size)
    (xl0, xl1), (xj0, xj1) = d["x_leg"], d["x_jaw"]
    zr, zt = d["z_bridge"]
    zl0, zj0 = d["z_leg"][0], d["z_jaw"][0]
    prof = Plane.XZ * Polygon((xl0, zl0), (xl1, zl0), (xl1, zt), (xj0, zt), (xj0, zj0), (xj1, zj0), (xj1, zr), (xl0, zr),
                              align=None)
    hook = Pos(0, d["hook_y"], 0) * extrude(prof, amount=d["hook_w"] / 2, both=True)
    hw, hy = d["hook_w"], d["hook_y"]
    gw, gd = d["groove"]
    cuts = [box(xj0 - 1, xl1 + 1, hy - gw / 2, hy + gw / 2, zt - gd, zt + 1)]
    for y in d["hook_bolts_y"]:
        cuts.append(slot_teardrop(d["hook_bolt_hole"], d["slot_half"], "x", ((xl0 + xl1) / 2, y, d["hook_bolts_z"]),
                                  d["leg_t"] + 0.02, apex="-z"))
    zs = d["screw_z"]
    cuts.append(teardrop(d["screw_hole"], "x", ((xl0 + xl1) / 2, hy, zs), d["leg_t"] + 0.02, apex="-z"))
    pk = d["screw_nut_pocket"]
    cuts.append(hex_prism(pk["s"], "x", (xl0 + pk["depth"] / 2 - 0.01, hy, zs), pk["depth"] + 0.02, "y", apex="-z"))
    for c in cuts:
        hook -= c
    return hook


def build_knob(size: str = "B2") -> Part:
    """Local frame: axis z, bed face z = 0, the screw head's pocket opens at the top (z = t)."""
    d = derive(size)
    kd, kt = d["knob"]
    m6 = d["screws"]["M6"]
    k = cyl(kd, "z", (0, 0, kt / 2), kt)
    for i in range(8):                                    # grip flutes
        a = math.radians(i * 45)
        k -= cyl(4.0, "z", (kd / 2 * math.cos(a), kd / 2 * math.sin(a), kt / 2), kt + 0.02)
    k -= hex_prism(m6["head_s"] + d["nut_pocket_clear"], "z", (0, 0, kt - (m6["head_k"] + 0.2) / 2 + 0.01), m6["head_k"] + 0.2 + 0.02, "y")
    k -= cyl(d["screw_hole"], "z", (0, 0, kt / 2), kt + 0.02)
    return k


def build_pad(size: str = "B2") -> Part:
    """Local frame: axis z, contact face z = 0 on the bed, blind hole for the screw tip from the top."""
    d = derive(size)
    pd, pt, ph = d["pad"]
    p = cyl(pd, "z", (0, 0, pt / 2), pt)
    p -= cyl(d["screw_hole"], "z", (0, 0, pt - ph / 2 + 0.01), ph + 0.02)
    return p


def clamp_locations(d, c: float) -> dict:
    """Placements (box frame) of the pad, screw and knob when clamping a container of thickness c."""
    m6 = d["screws"]["M6"]
    pd, pt, ph = d["pad"]
    kd, kt = d["knob"]
    face = d["x_jaw_face"] + c                            # container's outer face at the screw
    tip = face + pt - ph
    head_top = tip + d["screw_len"] + m6["head_k"]
    to_x = Rot(0, 90, 0)                                  # local +z -> +x
    y, z = d["hook_y"], d["screw_z"]
    return dict(pad=Location((face, y, z)) * to_x, knob=Location((head_top - kt, y, z)) * to_x,
                screw=(tip, head_top), face=face)


def check_rim_parts(hook: Part, knob: Part, pad: Part, size: str = "B2") -> dict:
    from cacad import assert_material
    from cacad.checks.orientation import check_declared_orientation
    from cacad.checks.overhang import check_overhang
    d = derive(size)
    reps = {}
    zt = d["z_bridge"][1]
    printed = {"hook": hook.rotate(Axis.X, 180).moved(Location((0, 0, zt))), "knob": knob, "pad": pad}
    for name, p in printed.items():
        single_solid(p)
        assert p.is_valid, f"{name}: invalid solid"
        o = dict(d["print_orientation"][name], up=(0, 0, 1), bed_z=0.0)
        check_declared_orientation(p, o)
        reps[name] = check_overhang(p, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"],
                                            exceptions=d["hook_overhang_exceptions"] if name == "hook" else []))
    (xl0, xl1), hy = d["x_leg"], d["hook_y"]
    zr = d["z_bridge"][0]
    assert_material(hook, {
        "bridge": (((d["x_jaw"][1] + xl0) / 2, hy + d["groove"][0] / 2 + 3.0, zr + 1.0), True),
        "groove": (((d["x_jaw"][1] + xl0) / 2, hy, d["z_bridge"][1] - 0.5), False),
        "throat": (((d["x_jaw"][1] + xl0) / 2, hy + 10.0, zr - 5.0), False),
        "screw hole": (((xl0 + xl1) / 2, hy, d["screw_z"]), False),
        "slot": (((xl0 + xl1) / 2, d["hook_bolts_y"][0], d["hook_bolts_z"] + d["slot_half"]), False),
    })
    return reps


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        h, k, p = build_hook(size), build_knob(size), build_pad(size)
        reps = check_rim_parts(h, k, p, size)
        for name, part in (("hook", h), ("knob", k), ("pad", p)):
            bb = part.bounding_box()
            print(f"{name} {size}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {part.volume / 1000:.1f} cm3, "
                  f"worst overhang {reps[name]['worst_ok']:.0f} deg")
            export(part, f"{size}_{name}", out)
    result = h
