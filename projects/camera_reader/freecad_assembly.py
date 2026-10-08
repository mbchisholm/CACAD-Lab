"""FreeCAD assembly of the camera reader: writes out/freecad_manifest.json
(every part's file, placement and group, placements from params/hardware),
then builds out/camera_reader_V0.FCStd with freecad_build.py, either in the
running FreeCAD (RPC server started) or by printing the call for headless
freecadcmd.

    .venv/bin/python projects/camera_reader/assembly.py          # STEP/STL first
    .venv/bin/python projects/camera_reader/freecad_assembly.py  # manifest + build over RPC
"""
from __future__ import annotations

import json
from pathlib import Path

from projects.camera_reader.hardware import BASE_STL, UPRIGHT_STL, cam_location, flat_location, pi_location
from projects.camera_reader.params import derive

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def _matrix(loc) -> list:
    """build123d Location -> row-major 4x4."""
    t = loc.wrapped.Transformation()
    return [[t.Value(r, c) for c in range(1, 5)] for r in range(1, 4)] + [[0, 0, 0, 1]]


IDENT = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def manifest(size: str = "V0") -> dict:
    d = derive(size)
    rows = [
        # bought: the stand as the designer's meshes, the boards from their vendor-drawing STEPs (local frames)
        dict(name="Stand_Upright", file=str(HERE / UPRIGHT_STL), group="Bought", color=(0.2, 0.2, 0.2),
             placement=_matrix(flat_location("upright")), ground=True),
        dict(name="Stand_Base", file=str(HERE / BASE_STL), group="Bought", color=(0.2, 0.2, 0.2),
             placement=_matrix(flat_location("base"))),
        dict(name="Pi4B", file=str(OUT / "pi4b_local.step"), group="Bought", color=(0.15, 0.55, 0.3),
             placement=_matrix(pi_location(d))),
        dict(name="CameraV2_NoIR", file=str(OUT / "cam_v2_local.step"), group="Bought", color=(0.1, 0.4, 0.25),
             placement=_matrix(cam_location(d))),
    ]
    for n, c in (("cuvette_c50", (0.6, 0.8, 1.0)), ("cuvette_c10", (0.6, 0.8, 1.0)), ("diffuser", (0.95, 0.95, 0.95)),
                 ("leds", (0.9, 0.2, 0.2))):
        rows.append(dict(name=n, file=str(OUT / f"{n}.step"), group="Bought", color=c, placement=IDENT))
    for n, c in (("snout", (0.75, 0.22, 0.17)), ("cell_box", (0.9, 0.5, 0.13)), ("retainer", (0.56, 0.27, 0.68)),
                 ("lid", (0.95, 0.77, 0.06)), ("riser", (0.5, 0.55, 0.55))):
        rows.append(dict(name=n, file=str(OUT / f"{n}.step"), group="Printed", color=c, placement=IDENT))
    for r in rows:
        assert Path(r["file"]).exists(), f"missing {r['file']}: run assembly.py first"
        r["label"], r["transparency"] = SHOW[r["name"]]
    return dict(doc=f"camera_reader_{size}", save=str(OUT / f"camera_reader_{size}.FCStd"), parts=rows,
                guides=guides(d), explode=EXPLODE)


# --- display only: tree labels, see-through shells, exploded view. Nothing here is geometry. ---------------------
# The shells that hide the light path (stand, snout, box, lid, riser) are see-through; what the light meets is solid.
SHOW = {
    "Stand_Upright": ("Stand upright (bought)", 75), "Stand_Base": ("Stand base (bought)", 75),
    "Pi4B": ("Pi 4B (bought)", 0), "CameraV2_NoIR": ("Camera Module 2 NoIR (bought)", 0),
    "cuvette_c50": ("50 mm cuvette (bought)", 45), "cuvette_c10": ("10 mm cuvette (bought)", 45),
    "diffuser": ("Diffuser, 3 mm opal (bought, cut)", 35), "leds": ("LEDs x7 (bought)", 0),
    "snout": ("Snout (printed)", 70), "cell_box": ("Cell box (printed)", 65), "retainer": ("LED retainer (printed)", 30),
    "lid": ("Lid (printed)", 70), "riser": ("Riser (printed)", 70),
}
_BOX = ["riser", "cell_box", "lid", "cuvette_c50", "cuvette_c10", "diffuser", "leds", "retainer"]
# Moves add up per part, in mm along ASM (Y = optical axis, Z up). The order is the order you take it apart.
EXPLODE = [
    ("box assembly away from the camera", _BOX, (0, 90, 0)),
    ("snout off the camera rim", ["snout"], (0, 40, 0)),
    ("lid up", ["lid"], (0, 0, 130)),
    ("cuvettes up out of their pockets", ["cuvette_c50", "cuvette_c10"], (0, 0, 70)),
    ("diffuser up out of its slot", ["diffuser"], (0, 0, 90)),
    ("retainer off the back", ["retainer"], (0, 90, 0)),
    ("LEDs out of the back wall", ["leds"], (0, 40, 0)),
]


def guides(d) -> dict:
    """The lens-to-window light paths and the axis on from the datum wall to the LEDs, from params: lines only."""
    lx, ly, lz = d["lens"]
    y_back = d["retainer"]["y"][0]
    paths = {}
    for name, (x0, x1, z0, z1) in d["windows"].items():
        paths[name] = [(lx, ly, lz), ((x0 + x1) / 2, d["y_datum"], (z0 + z1) / 2)]
    # (part, text, text drop in mm: the retainer's centre sits at the box's height, one below the other)
    labels = [("CameraV2_NoIR", "Camera", 0), ("Pi4B", "Pi 4B", 0), ("snout", "Snout", 0), ("cell_box", "Cell box + cuvettes", 0),
              ("retainer", "LEDs + retainer", 25), ("riser", "Riser", 0)]
    return dict(axis=[(lx, d["y_datum"], lz), (lx, y_back, lz)], paths=paths, labels=labels)


if __name__ == "__main__":
    m = manifest()
    mp = OUT / "freecad_manifest.json"
    mp.write_text(json.dumps(m, indent=1))
    build = HERE / "freecad_build.py"
    call = f"MANIFEST = {str(mp)!r}\nexec(open({str(build)!r}).read())"
    try:
        from cacad.freecad.rpc import FreeCADRPC
        print(FreeCADRPC().run(call, "build assembly"))
    except Exception as e:   # no GUI server: run headless instead
        print(f"FreeCAD RPC unavailable ({e}). Headless:\n  freecadcmd -c \"{call}\"")
