"""Camera reader V0 assembly: the bought stand (envelope), Pi 4B and Camera
Module 2 placed as the stand holds them, and the five printed additions with
the cuvettes, diffuser and LEDs, in the ASM frame. Function checks:

- every pair of parts is clear (pairwise, F7); the designed contacts touch
  with zero volume (collar stop on the camera rim, flange on the front wall,
  cuvettes on the pocket floors and the datum mask, box on the riser, lid on
  the walls and the mask top); the one designed overlap is the retainer's
  preload on the LED flanges;
- the light from each window reaches the lens past every printed part, and
  through no cuvette but its own;
- the collar surrounds the camera rim on three sides and the ribbon notch
  sits over the rim's open side;
- the Pi's tallest parts stay clear of the snout.

Writes out/V0.3mf (printed parts, one mesh each, F15), out/V0_assembly.step
(everything modelled; the stand as its envelope) and out/<part>.step/.stl.

    .venv/bin/python projects/camera_reader/assembly.py
"""
from __future__ import annotations

from build123d import Compound

from cacad import export, export_3mf, interference_volume, is_inside
from projects.camera_reader.cell_box import build_cell_box, check_cell_box
from projects.camera_reader.hardware import build_hardware, ray_solids
from projects.camera_reader.lid import build_lid
from projects.camera_reader.params import ACTIVE_SIZES, derive, validate
from projects.camera_reader.retainer import build_retainer
from projects.camera_reader.riser import build_riser
from projects.camera_reader.snout import build_snout, check_snout

# Pairs allowed to overlap, and why. Everything else must be clear or touch with zero volume.
DESIGNED_OVERLAP = {
    frozenset(("retainer", f"led{i}")): "nubs clamp each LED flange by led_preload" for i in range(7)
}


# Pairs that must touch (zero gap): the collar's stop face on the camera rim, the flange on the front wall, the
# cuvettes on their pockets and the datum mask, the box on the riser, the lid on the walls, the Pi on its ledges.
DESIGNED_CONTACT = (("snout", "stand_upright"), ("snout", "cell_box"), ("cuvette_c50", "cell_box"),
                    ("cuvette_c10", "cell_box"), ("cell_box", "riser"), ("lid", "cell_box"),
                    ("pi4b", "stand_upright"))


def build_printed(size: str = "V0") -> dict:
    parts = dict(snout=build_snout(size), cell_box=build_cell_box(size), retainer=build_retainer(size),
                 lid=build_lid(size), riser=build_riser(size))
    check_snout(parts["snout"], size)
    check_cell_box(parts["cell_box"], size)
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
            key = frozenset((a, b))
            if key in DESIGNED_OVERLAP:
                assert v > 0, f"{a}/{b}: designed overlap ({DESIGNED_OVERLAP[key]}) is missing"
                continue
            assert v < 1e-3, f"{a} and {b} interfere: {v:.3f} mm3"
    report.append(f"pairwise clear: {len(names)} parts, {len(names) * (len(names) - 1) // 2} pairs")
    for a, b in DESIGNED_CONTACT:
        gap = allp[a].distance_to(allp[b])
        assert gap < 1e-3, f"{a} should touch {b}, gap {gap:.3f}"
    report.append(f"designed contacts touch: {', '.join('/'.join(p) for p in DESIGNED_CONTACT)}")
    # Light paths
    for k, ray in ray_solids(d).items():
        for pname, p in printed.items():
            v = interference_volume(ray, p)
            assert v < 1e-3, f"{k} is clipped by the {pname}: {v:.3f} mm3"
        for cname in ("cuvette_c50", "cuvette_c10"):
            own = cname.endswith(k.split("_")[1])
            v = interference_volume(ray, hw[cname])
            if not own:
                assert v < 1e-3, f"{k} passes through {cname}: {v:.3f} mm3"
    report.append("light paths: every window sees the lens, past every printed part")
    # Collar: material above, beside and below the rim, but not under its open side (the ribbon notch)
    s, rim = d["snout"], d["cam_rim"]
    yc = (s["y_collar"] + s["y_stop"]) / 2
    zt = rim["z"][1] + d["fit"] + d["collar_wall"] / 2
    zb = rim["z"][0] - d["fit"] - d["collar_wall"] / 2
    xs = rim["x"][0] - d["fit"] - d["collar_wall"] / 2
    sn = printed["snout"]
    assert is_inside(sn, (sum(rim["x"]) / 2, yc, zt)), "collar roof missing"
    assert is_inside(sn, (xs, yc, sum(rim["z"]) / 2)), "collar side missing"
    assert not is_inside(sn, (sum(rim["gap_x"]) / 2, s["y_collar"] + 1, zb)), "ribbon notch missing"
    assert is_inside(sn, (rim["x"][0] + 1, yc + 3, zb)), "collar floor missing beside the notch"
    report.append("collar wraps the camera rim; ribbon notch under its open side")
    return report


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        printed, hw = build_printed(size), build_hardware(size)
        for line in check_assembly(size, printed, hw):
            print(" ", line)
        for name, p in printed.items():
            export(p, name, out)
        for name in ("pi4b", "cam_v2", "cuvette_c50", "cuvette_c10", "diffuser"):
            export(hw[name], f"{name}_asm" if name in ("pi4b", "cam_v2") else name, out)
        export(Compound(children=[v for k, v in hw.items() if k.startswith("led")]), "leds", out)
        export_3mf(printed, out + f"/{size}.3mf")
        everything = Compound(children=[p for p in {**printed, **hw}.values()])
        export(everything, f"{size}_assembly", out)
        d = derive(size)
        print(f"{size}: optical axis Z {d['lens'][2]:.1f}; wrote {out}/{size}.3mf and {size}_assembly.step")
