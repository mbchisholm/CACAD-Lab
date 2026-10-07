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
    return dict(doc=f"camera_reader_{size}", save=str(OUT / f"camera_reader_{size}.FCStd"), parts=rows)


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
