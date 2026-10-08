"""Leaf imager V0 assembly: the five printed parts with the camera, Pi, LED ring PCB, PTFE strip, platen lining and
fasteners, in the assembly frame. Function checks:

- every pair of parts is clear (pairwise, F7); the designed contacts touch with zero volume;
- the camera's view pyramid, lens to leaf plane, meets nothing but the hold-down frame, which lies on the leaf's
  edges by design;
- a ray from every LED reaches the centre, the corners of the uniformity area and the corners of the PTFE strip
  past every part (so the frame's shadow misses the strip);
- each printed part stands on its declared bed face, has no overhang beyond 45 deg except its declared bridges, and
  fits the bed (params.validate).

Writes out/<part>.step/.stl, out/V0.3mf (printed parts, one mesh each, F15) and out/V0_assembly.step.

    .venv/bin/python projects/leaf_imager/assembly.py
"""
from __future__ import annotations

from build123d import Compound

from cacad import interference_volume
from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.registries.materials import NOZZLE
from projects.leaf_imager.base import build_base, check_base
from projects.leaf_imager.carrier import build_carrier, check_carrier
from projects.leaf_imager.chamber import build_chamber, check_chamber
from projects.leaf_imager.hardware import build_hardware, rays, view_cone
from projects.leaf_imager.hold_down import build_hold_down, check_hold_down
from projects.leaf_imager.params import PARTS, validate
from projects.leaf_imager.roof import build_roof, check_roof

BUILD = dict(base=(build_base, check_base), chamber=(build_chamber, check_chamber), hold_down=(build_hold_down, check_hold_down), roof=(build_roof, check_roof),
             carrier=(build_carrier, check_carrier))

# Pairs that must touch with zero volume, and why.
DESIGNED_CONTACT = (
    ("chamber", "base", "lowered onto the base top, inside the rim"),
    ("flock", "base", "lining on the platen"),
    ("ptfe_strip", "base", "strip on its pocket floor"),
    ("hold_down", "flock", "frame on the platen"),
    ("led_pcb", "chamber", "PCB on the ledge and corner bosses"),
    ("roof", "chamber", "roof on the wall tops"),
    ("carrier", "roof", "carrier under the roof"),
    ("camera", "carrier", "camera back on the bosses"),
    ("pi4b", "roof", "Pi on the boss tops"),
)

# Fasteners sit in their holes and on their nuts: contact, never overlap. A screw passes through the PCB, camera,
# Pi, roof and carrier bores with clearance; these pairs only have to be clear.
VIEW_EXEMPT = {"hold_down": "lies on the leaf's edges inside the field by design (its window is the leaf area)",
               "camera": "the pyramid's apex", "flock": "the leaf plane", "ptfe_strip": "the leaf plane"}


def build_printed(size: str = "V0") -> dict:
    parts = {}
    for name in PARTS:
        build, check = BUILD[name]
        parts[name] = build(size)
        check(parts[name], size)
    return parts


def check_assembly(size: str = "V0", printed: dict | None = None, hw: dict | None = None) -> list[str]:
    d = validate(size)
    printed = printed or build_printed(size)
    hw = hw or build_hardware(size)
    report = []
    allp = {**printed, **hw}
    names = list(allp)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = interference_volume(allp[a], allp[b])
            assert v < 1e-3, f"{a} and {b} interfere: {v:.3f} mm3"
    report.append(f"pairwise clear: {len(names)} parts, {len(names) * (len(names) - 1) // 2} pairs")
    for a, b, why in DESIGNED_CONTACT:
        gap = allp[a].distance_to(allp[b])
        assert gap < 1e-3, f"{a} should touch {b} ({why}), gap {gap:.3f}"
    report.append(f"designed contacts touch: {len(DESIGNED_CONTACT)}")

    cone = view_cone(d)
    for name, p in allp.items():
        if name in VIEW_EXEMPT:
            continue
        v = interference_volume(cone, p)
        assert v < 1e-3, f"{name} is in the camera's view: {v:.3f} mm3"
    report.append(f"view pyramid clear of everything but {', '.join(VIEW_EXEMPT)}")

    blockers = {k: v for k, v in allp.items() if k not in ("leds", "flock", "ptfe_strip")}
    rs = rays(d)
    for rname, ray in rs.items():
        for pname, p in blockers.items():
            v = interference_volume(ray, p)
            assert v < 1e-4, f"ray {rname} is blocked by the {pname}: {v:.4f} mm3"
    report.append(f"LED rays clear: {len(rs)} rays (20 LEDs x centre, uniformity corners, strip corners)")

    for name, p in printed.items():
        o = d["print_orientation"][name]
        check_declared_orientation(p, o)
        rep = check_overhang(p, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"], nozzle_d=NOZZLE,
                                     exceptions=o["exceptions"]))
        report.append(f"{name}: bed face '{o['bed_face']}', worst overhang {rep['worst_ok']:.1f} deg"
                      + (f", bridges {len(rep['exceptions_found'])} ({', '.join(o['known_overhangs'])})"
                         if rep["exceptions_found"] else ""))
    return report


if __name__ == "__main__":
    from cacad import export, export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys (F23)
    printed = build_printed()
    hw = build_hardware()
    for line in check_assembly(printed=printed, hw=hw):
        print(line)
    for name, p in printed.items():
        export(p, name, OUT)
    export_3mf(printed, OUT + "/V0.3mf")
    export(Compound(children=[*printed.values(), *hw.values()]), "V0_assembly", OUT)
    print("exported", ", ".join(printed), "and V0_assembly to", OUT)
