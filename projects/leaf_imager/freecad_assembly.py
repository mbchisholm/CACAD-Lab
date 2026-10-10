"""FreeCAD assembly of the leaf imager with an exploded view: writes out/freecad_manifest.json (every part's STEP,
group, colour, and the explode steps), then builds out/leaf_imager_V0.FCStd with camera_reader/freecad_build.py,
either in the running FreeCAD (RPC server started) or by printing the call for headless freecadcmd. Every part is
already in the assembly frame (assembly.py), so placements are identity and the base is grounded.

    .venv/bin/python projects/leaf_imager/assembly.py          # STEP first
    .venv/bin/python projects/leaf_imager/freecad_assembly.py  # manifest + build over RPC
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BUILD = HERE.parent / "camera_reader" / "freecad_build.py"   # manifest-driven, nothing camera-specific in it

IDENT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

# --- display only: tree labels, colours, see-through shells, exploded view. Nothing here is geometry. -------------
# (name, label, group, colour, transparency). The base comes first: it is the grounded part.
# The chamber and roof hide the LED ring and camera, so they are see-through.
PARTS = [
    ("base", "Base (printed)", "Printed", (0.5, 0.55, 0.55), 0),
    ("chamber", "Chamber (printed)", "Printed", (0.9, 0.5, 0.13), 70),
    ("hold_down", "Hold-down frame (printed)", "Printed", (0.56, 0.27, 0.68), 0),
    ("roof", "Roof (printed)", "Printed", (0.95, 0.77, 0.06), 60),
    ("carrier", "Camera carrier (printed)", "Printed", (0.75, 0.22, 0.17), 0),
    ("camera", "Camera Module 2 (bought)", "Bought", (0.1, 0.4, 0.25), 0),
    ("pi4b", "Pi 4B (bought)", "Bought", (0.15, 0.55, 0.3), 0),
    ("led_pcb", "LED ring PCB (bought)", "Bought", (0.2, 0.35, 0.7), 0),
    ("leds", "LEDs x20 (bought)", "Bought", (0.9, 0.2, 0.2), 0),
    ("ptfe_strip", "PTFE reference strip (bought, cut)", "Bought", (0.95, 0.95, 0.95), 0),
    ("flock", "Platen lining, flock (bought, cut)", "Bought", (0.12, 0.12, 0.12), 0),
    ("pcb_screws", "M3 screws, LED PCB", "Bought", (0.7, 0.7, 0.72), 0),
    ("cam_screws", "M2 screws, camera", "Bought", (0.7, 0.7, 0.72), 0),
    ("cam_nuts", "M2 nuts, camera", "Bought", (0.7, 0.7, 0.72), 0),
    ("roof_screws", "M3 screws, roof to carrier", "Bought", (0.7, 0.7, 0.72), 0),
    ("roof_nuts", "M3 nuts, roof to carrier", "Bought", (0.7, 0.7, 0.72), 0),
    ("pi_screws", "M2.5 screws, Pi", "Bought", (0.7, 0.7, 0.72), 0),
    ("pi_nuts", "M2.5 nuts, Pi", "Bought", (0.7, 0.7, 0.72), 0),
]

_PI = ["pi4b", "pi_screws", "pi_nuts"]
_ROOF_UNIT = ["roof", "roof_screws", "roof_nuts", "carrier", "camera", "cam_screws", "cam_nuts", *_PI]
_LED = ["led_pcb", "leds", "pcb_screws"]
# Moves add up per part, in mm along Z (the camera looks down -Z at the leaf on the platen at z = 0). The order is
# the order you take it apart: the chamber stack off the base, the platen layers up, the roof unit off the chamber,
# the LED ring out the top, then the roof unit apart.
EXPLODE = [
    ("chamber stack off the base", ["chamber", *_LED, *_ROOF_UNIT], (0, 0, 45)),
    ("hold-down off the platen", ["hold_down"], (0, 0, 25)),
    ("lining off the platen", ["flock"], (0, 0, 12)),
    ("PTFE strip out of its pocket", ["ptfe_strip"], (0, 0, 6)),
    ("roof unit off the chamber", _ROOF_UNIT, (0, 0, 75)),
    ("LED ring out the top of the chamber", _LED, (0, 0, 75)),
    ("PCB screws out of the inserts", ["pcb_screws"], (0, 0, 20)),
    ("Pi off the roof", ["pi4b", "pi_screws"], (0, 0, 95)),
    ("Pi screws out of the Pi", ["pi_screws"], (0, 0, 30)),
    ("Pi nuts out of the boss tops", ["pi_nuts"], (0, 0, 70)),
    ("roof screws out", ["roof_screws"], (0, 0, 80)),
    ("roof off the carrier", ["roof"], (0, 0, 55)),
    ("camera nuts out of the carrier top", ["cam_nuts"], (0, 0, 40)),
    ("carrier up off the camera", ["carrier"], (0, 0, 20)),
    ("roof nuts out of the carrier bottom", ["roof_nuts"], (0, 0, 5)),
    ("camera screws out the bottom", ["cam_screws"], (0, 0, -20)),
]


def manifest(size: str = "V0") -> dict:
    rows = []
    for name, label, group, color, transparency in PARTS:
        f = OUT / (f"hw_{name}.step" if group == "Bought" else f"{name}.step")
        assert f.exists(), f"missing {f}: run assembly.py first"
        rows.append(dict(name=name, file=str(f), group=group, color=color, placement=IDENT, label=label,
                         transparency=transparency))
    return dict(doc=f"leaf_imager_{size}", save=str(OUT / f"leaf_imager_{size}.FCStd"), parts=rows, explode=EXPLODE)


if __name__ == "__main__":
    m = manifest()
    mp = OUT / "freecad_manifest.json"
    mp.write_text(json.dumps(m, indent=1))
    call = f"MANIFEST = {str(mp)!r}\nexec(open({str(BUILD)!r}).read())"
    try:
        from cacad.freecad.rpc import FreeCADRPC
        print(FreeCADRPC().run(call, "build assembly"))
    except Exception as e:   # no GUI server: run headless instead
        print(f"FreeCAD RPC unavailable ({e}). Headless:\n  freecadcmd -c \"{call}\"")
