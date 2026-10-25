"""FreeCAD assembly of the Pi camera stand with an exploded view: writes out/freecad_manifest.json (every part's
STEP, group, colour, and the explode steps), then builds out/pi_cam_stand_V0.FCStd with camera_reader/freecad_build.py,
either in the running FreeCAD (RPC server started) or by printing the call for headless freecadcmd. Every part is
already in the stand frame at tilt 0 (assembly.py), so placements are identity and the stand is grounded.

    .venv/bin/python projects/pi_cam_stand/assembly.py          # STEP first
    .venv/bin/python projects/pi_cam_stand/freecad_assembly.py  # manifest + build over RPC
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BUILD = HERE.parent / "camera_reader" / "freecad_build.py"   # manifest-driven, nothing camera-specific in it

IDENT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

# --- display only: tree labels, colours, exploded view. Nothing here is geometry. -----------------------------------
# (name, file stem, label, group, colour). The stand comes first: it is the grounded part.
PARTS = [
    ("stand", "stand", "Stand (printed)", "Printed", (0.5, 0.55, 0.55)),
    ("carrier", "carrier_placed", "Camera carrier (printed)", "Printed", (0.95, 0.77, 0.06)),
    ("pi4b", "hw_pi4b", "Pi 4B (bought)", "Bought", (0.15, 0.55, 0.3)),
    ("camera", "hw_camera", "Camera Module 2 (bought)", "Bought", (0.1, 0.4, 0.25)),
    ("pi_screws", "hw_pi_screws", "M2.5x10 screws, Pi", "Bought", (0.7, 0.7, 0.72)),
    ("pi_nuts", "hw_pi_nuts", "M2.5 nuts, Pi", "Bought", (0.7, 0.7, 0.72)),
    ("cam_screws", "hw_cam_screws", "M2x10 screws, camera", "Bought", (0.7, 0.7, 0.72)),
    ("cam_nuts", "hw_cam_nuts", "M2 nuts, camera", "Bought", (0.7, 0.7, 0.72)),
    ("hinge_screw", "hw_hinge_screw", "M3x30 hinge bolt", "Bought", (0.7, 0.7, 0.72)),
    ("hinge_nut", "hw_hinge_nut", "M3 hinge nut", "Bought", (0.7, 0.7, 0.72)),
]

_HEAD = ["carrier", "camera", "cam_screws", "cam_nuts"]
# Moves add up per part, in mm (Y forward, the way the camera looks at tilt 0; Z up). The order is the order you take
# it apart: the hinge bolt and nut out sideways, the camera head forward off the column, the camera off its carrier,
# then the Pi up off its bosses.
EXPLODE = [
    ("hinge bolt out the -X side", ["hinge_screw"], (-45, 0, 0)),
    ("hinge nut out the +X side", ["hinge_nut"], (25, 0, 0)),
    ("camera head forward off the column", _HEAD, (0, 45, 0)),
    ("camera nuts out of the carrier back", ["cam_nuts"], (0, -12, 0)),
    ("camera off its bosses", ["camera", "cam_screws"], (0, 25, 0)),
    ("camera screws out the front", ["cam_screws"], (0, 20, 0)),
    ("Pi screws out", ["pi_screws"], (0, 0, 50)),
    ("Pi up off its bosses", ["pi4b", "pi_screws"], (0, 0, 30)),
    ("Pi nuts out the bottom", ["pi_nuts"], (0, 0, -15)),
]


def manifest(size: str = "V0") -> dict:
    rows = []
    for name, stem, label, group, color in PARTS:
        f = OUT / f"{stem}.step"
        assert f.exists(), f"missing {f}: run assembly.py first"
        rows.append(dict(name=name, file=str(f), group=group, color=color, placement=IDENT, label=label, transparency=0))
    return dict(doc=f"pi_cam_stand_{size}", save=str(OUT / f"pi_cam_stand_{size}.FCStd"), parts=rows, explode=EXPLODE)


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
