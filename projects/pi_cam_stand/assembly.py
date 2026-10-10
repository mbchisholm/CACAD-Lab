"""Pi camera stand V0 assembly: stand, carrier, Pi 4B, Camera Module 2 and fasteners. Function checks:

- every pair of parts is clear (pairwise, F7); the designed contacts touch with zero volume;
- the carrier, with the camera and its screws, clears the stand and the Pi at every tilt in the range, 5 deg steps;
- the camera's view meets no part from straight ahead down to `view_clear_to`; the report gives the steepest clear
  tilt and the tilts where the stand enters the picture;
- each printed part stands on its declared bed face and has no overhang beyond 45 deg except its declared bridges.

Writes out/<part>.step/.stl, out/V0.3mf (printed parts, one mesh each, F15) and out/V0_assembly.step (tilt 0).

    .venv/bin/python projects/pi_cam_stand/assembly.py
"""
from __future__ import annotations

from build123d import Compound

from cacad import interference_volume
from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.registries.materials import NOZZLE
from projects.pi_cam_stand.carrier import build_carrier, carrier_location, check_carrier
from projects.pi_cam_stand.hardware import build_camera_unit, build_hardware
from projects.pi_cam_stand.params import validate
from projects.pi_cam_stand.stand import build_stand, check_stand

DESIGNED_CONTACT = (
    ("pi4b", "stand", "Pi on its four bosses"),
    ("camera", "carrier", "camera back on its four bosses"),
    ("pi_screws", "pi4b", "screw heads on the Pi"),
    ("cam_screws", "camera", "screw heads on the camera"),
    ("hinge_screw", "stand", "bolt head on the -X wall"),
    ("hinge_nut", "stand", "nut on its pocket floor"),
)
MOVING = ("carrier", "camera", "cam_screws", "cam_nuts")   # turn with the tilt


def build_printed(size: str = "V0") -> dict:
    parts = dict(stand=build_stand(size), carrier=build_carrier(size))
    check_stand(parts["stand"], size)
    check_carrier(parts["carrier"], size)
    return parts


def check_assembly(size: str = "V0", printed: dict | None = None) -> list[str]:
    d = validate(size)
    printed = printed or build_printed(size)
    hw = build_hardware(size)
    view = hw.pop("view")
    allp = dict(stand=printed["stand"], carrier=carrier_location(d) * printed["carrier"], **hw)
    report = []
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

    # tilt sweep: the moving unit against everything fixed; the view against the stand and the Pi
    unit = build_camera_unit(d)
    unit_parts = dict(carrier=printed["carrier"], camera=unit["camera"], cam_screws=unit["cam_screws"],
                      cam_nuts=unit["cam_nuts"])
    fixed = {k: v for k, v in allp.items() if k not in MOVING}
    seen = {k: fixed[k] for k in ("stand", "pi4b", "pi_screws", "hinge_screw", "hinge_nut")}
    lo, hi = d["tilt_range"]
    in_view = []
    for tilt in range(int(lo), int(hi) + 1, 5):
        loc = carrier_location(d, tilt)
        for mk, mp in unit_parts.items():
            for fk, fp in fixed.items():
                v = interference_volume(loc * mp, fp)
                assert v < 1e-3, f"at tilt {tilt}: {mk} hits {fk} ({v:.3f} mm3)"
        hits = [k for k, p in seen.items() if interference_volume(loc * unit["view"], p) > 1e-3]
        if hits:
            in_view.append((tilt, hits))
    report.append(f"tilt {lo:.0f} to {hi:.0f} deg: carrier, camera and screws clear the stand and Pi")
    blocked = [t for t, _ in in_view if t >= d["view_clear_to"]]
    assert not blocked, f"stand in the camera's view at tilt {blocked} (must be clear to {d['view_clear_to']:.0f})"
    steepest = max((t for t, _ in in_view), default=None)
    report.append(f"view clear from {hi:.0f} down to {steepest + 5 if steepest is not None else lo:.0f} deg"
                  + (f"; below that the picture's edge shows: "
                     + ", ".join(f"{t}: {'+'.join(h)}" for t, h in in_view[-1:] + in_view[:1]) if in_view else ""))

    for name, p in printed.items():
        o = d["print_orientation"][name]
        check_declared_orientation(p, o)
        rep = check_overhang(p, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"], nozzle_d=NOZZLE,
                                     exceptions=o["exceptions"]))
        report.append(f"{name}: bed face '{o['bed_face']}', worst overhang {rep['worst_ok']:.1f} deg, "
                      f"declared {len(rep['exceptions_found'])} faces ({'; '.join(o['known_overhangs'])})")
    return report


if __name__ == "__main__":
    from cacad import export, export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys (F23)
    d = validate()
    printed = build_printed()
    for line in check_assembly(printed=printed):
        print(line)
    for name, p in printed.items():
        export(p, name, OUT)
    export_3mf(printed, OUT + "/V0.3mf")
    hw = build_hardware()
    hw.pop("view")
    for name, p in hw.items():
        export(p, "hw_" + name, OUT)
    export(carrier_location(d) * printed["carrier"], "carrier_placed", OUT)
    export(Compound(children=[printed["stand"], carrier_location(d) * printed["carrier"], *hw.values()]), "V0_assembly", OUT)
    print("exported", ", ".join(printed), "and V0_assembly to", OUT)
