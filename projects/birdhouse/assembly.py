"""Nest box V0 assembly: the five printed parts with the ESP32-CAM, IR LEDs, battery, charger, timer and solar
panel, in the assembly frame. Function checks:

- every pair of parts is clear (pairwise, F7); the designed contacts touch with zero volume;
- the camera's view pyramid, lens to floor, meets nothing but the walls, and takes in the whole floor (stock-lens
  FOV, UNVERIFIED);
- each printed part stands on its declared bed face in its print pose, has no overhang beyond 45 deg except its
  declared bridges, and fits the bed (params.validate).

Writes out/<part>.step/.stl, out/hw_<part>.step, out/V0.3mf (printed parts, one mesh each, F15) and
out/V0_assembly.step.

    .venv/bin/python projects/birdhouse/assembly.py
"""
from __future__ import annotations

from build123d import Compound

from cacad import interference_volume
from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.registries.materials import NOZZLE
from projects.birdhouse.body import build_body, check_body
from projects.birdhouse.cap import build_cap, check_cap
from projects.birdhouse.floor import build_floor, check_floor
from projects.birdhouse.front import build_front, check_front
from projects.birdhouse.geom import print_pose
from projects.birdhouse.hardware import build_hardware, view_cone
from projects.birdhouse.params import PARTS, validate
from projects.birdhouse.tray import build_tray, check_tray

BUILD = dict(body=(build_body, check_body), floor=(build_floor, check_floor), front=(build_front, check_front),
             tray=(build_tray, check_tray), cap=(build_cap, check_cap))

# Pairs that must touch with zero volume, and why.
DESIGNED_CONTACT = (
    ("floor", "body", "floor on the ledge"),
    ("front", "body", "panel on the sill"),
    ("tray", "body", "tray on the wall tops"),
    ("tray", "front", "tray holds the panel down"),
    ("cap", "tray", "cap shoulder on the tray rim"),
    ("esp32cam", "tray", "board on the end ledges"),
    ("wiring_room", "esp32cam", "wiring on the board's back"),
    ("ir_leds", "tray", "LED flanges on the tray top"),
    ("battery", "tray", "holder on the tray"),
    ("bq25185", "tray", "charger on the tray"),
    ("tpl5110", "tray", "timer on the tray"),
    ("solar_panel", "cap", "panel bonded to the cap top"),
)

VIEW_EXEMPT = {"esp32cam": "the pyramid's apex", "floor": "the pyramid's base",
               "body": "the walls: the field at the floor is wider than the floor, so all of it is seen",
               "front": "the front wall, same reason"}


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
    fl = printed["floor"]
    seen = interference_volume(view_cone(d, d["floor_z"][0] - 1.0), fl) / fl.volume
    assert seen > 0.95, f"camera sees only {seen:.0%} of the floor"
    report.append(f"view pyramid clear of the tray, LEDs and electronics; sees {seen:.0%} of the floor "
                  f"(stock-lens FOV, UNVERIFIED)")

    for name, p in printed.items():
        o = d["print_orientation"][name]
        posed, bed_z = print_pose(p, o["rot_x"])
        o = dict(o, bed_z=bed_z) if o["rot_x"] else o
        check_declared_orientation(posed, o)
        rep = check_overhang(posed, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"], nozzle_d=NOZZLE,
                                         exceptions=o["exceptions"]))
        report.append(f"{name}: bed face '{o['bed_face']}', worst overhang {rep['worst_ok']:.1f} deg"
                      + (f", bridges {len(rep['exceptions_found'])} ({', '.join(o['known_overhangs'])})"
                         if rep["exceptions_found"] else ""))
    return report


if __name__ == "__main__":
    from cacad import export, export_3mf
    from build123d import export_step
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys (F23)
    printed = build_printed()
    hw = build_hardware()
    for line in check_assembly(printed=printed, hw=hw):
        print(line)
    for name, p in printed.items():
        export(p, name, OUT)
    for name, p in hw.items():
        export_step(p, f"{OUT}/hw_{name}.step")
    export_3mf(printed, OUT + "/V0.3mf")
    export(Compound(children=[*printed.values(), *hw.values()]), "V0_assembly", OUT)
    print("exported", ", ".join(printed), "and V0_assembly to", OUT)
