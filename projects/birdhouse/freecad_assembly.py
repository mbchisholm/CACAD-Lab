"""FreeCAD assembly of the nest box with an exploded view: writes out/freecad_manifest.json (every part's STEP,
group, colour, and the explode steps), then builds out/birdhouse_V0.FCStd with camera_reader/freecad_build.py,
either in the running FreeCAD (RPC server started) or by printing the call for headless freecadcmd. Every part is
already in the assembly frame (assembly.py), so placements are identity and the body is grounded.

    .venv/bin/python projects/birdhouse/assembly.py          # STEP first
    .venv/bin/python projects/birdhouse/freecad_assembly.py  # manifest + build over RPC
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BUILD = HERE.parent / "camera_reader" / "freecad_build.py"   # manifest-driven, nothing camera-specific in it

IDENT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

# --- display only: tree labels, colours, see-through shells, exploded view. Nothing here is geometry. -------------
# (name, label, group, colour, transparency). The body comes first: it is the grounded part. The cap is see-through
# so the electronics show; the wiring room is a keep-out, not a part.
PARTS = [
    ("body", "Body (printed)", "Printed", (0.85, 0.78, 0.62), 0),
    ("floor", "Floor (printed)", "Printed", (0.62, 0.5, 0.36), 0),
    ("front", "Front panel with perch (printed)", "Printed", (0.75, 0.66, 0.5), 0),
    ("tray", "Tray: ceiling and electronics carrier (printed)", "Printed", (0.4, 0.45, 0.5), 0),
    ("cap", "Cap (printed)", "Printed", (0.35, 0.4, 0.35), 55),
    ("esp32cam", "ESP32-CAM, face down (bought)", "Bought", (0.1, 0.1, 0.12), 0),
    ("wiring_room", "Header wiring keep-out", "Bought", (1.0, 0.75, 0.0), 75),
    ("ir_leds", "IR LEDs 850 nm x2, TSHG6400 (bought)", "Bought", (0.75, 0.1, 0.1), 0),
    ("battery", "18650 in Keystone 1042 (bought)", "Bought", (0.2, 0.35, 0.75), 0),
    ("bq25185", "Charger + 5 V boost, Adafruit 6106 (bought)", "Bought", (0.1, 0.1, 0.1), 0),
    ("tpl5110", "Power timer, Adafruit 3435 (bought)", "Bought", (0.1, 0.3, 0.6), 0),
    ("solar_panel", "Solar panel 6 V 1 W, Adafruit 3809 (bought)", "Bought", (0.08, 0.1, 0.25), 0),
]

_ELEC = ["esp32cam", "wiring_room", "ir_leds", "battery", "bq25185", "tpl5110"]
# Moves add up per part, in mm. The order is the order you take it apart: the cap off, the tray unit off the body,
# the front panel up and out, the floor out the top, the electronics off the tray, the panel off the cap.
EXPLODE = [
    ("cap off the tray", ["cap", "solar_panel"], (0, 0, 200)),
    ("tray unit off the body", ["tray", *_ELEC], (0, 0, 70)),
    ("front panel out of its slots", ["front"], (0, -70, 25)),
    ("floor out the top", ["floor"], (0, 0, 150)),
    ("electronics off the tray", _ELEC, (0, 0, 30)),
    ("IR LEDs out of their bores", ["ir_leds"], (0, 0, 10)),
    ("panel off the cap", ["solar_panel"], (0, 0, 40)),
]


def manifest(size: str = "V0") -> dict:
    rows = []
    for name, label, group, color, transparency in PARTS:
        f = OUT / (f"hw_{name}.step" if group == "Bought" else f"{name}.step")
        assert f.exists(), f"missing {f}: run assembly.py first"
        rows.append(dict(name=name, file=str(f), group=group, color=color, placement=IDENT, label=label,
                         transparency=transparency))
    return dict(doc=f"birdhouse_{size}", save=str(OUT / f"birdhouse_{size}.FCStd"), parts=rows, explode=EXPLODE)


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
