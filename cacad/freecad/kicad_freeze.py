"""Freeze a KiCad board to STEP through KiCadStepUp, inside the FreeCAD GUI.

GUI-only: StepUp needs FreeCADGui. Paste into the FreeCAD Python console or
run through the RPC server with `execute_code_async` (a full board load and a
10+ MB STEP export exceed the 90 s synchronous budget, FINDINGS F17):

    exec(open("cacad/freecad/kicad_freeze.py").read())
    freeze("tentacle_t2", "/path/to/tentacle-mini.kicad_pcb", "/path/to/ref")

Re-run whenever the board changes; consumers read only the STEP. Community
STEP models are good for heights and collisions, not for holes or outlines
(FINDINGS F18); take those from the board registry.
"""
import os
import time


def freeze(name: str, pcb: str, out_dir: str) -> str:
    import FreeCAD, FreeCADGui, Import, Part  # noqa: E401  (FreeCAD-side modules)
    import kicadStepUptools as ksu
    FreeCADGui.activateWorkbench("KiCadStepUpWB")
    t0 = time.time()
    ksu.onLoadBoard(pcb, load_models=True)
    doc = FreeCAD.ActiveDocument
    doc.recompute()
    stem = os.path.splitext(os.path.basename(pcb))[0]
    root = [o for o in doc.Objects if o.TypeId == "App::Part" and o.Label == stem][0]
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name + ".step")
    Import.export([root], out)
    s = Part.read(out)
    b = s.BoundBox
    print(f"{name}: {len(s.Solids)} solids, bbox X {b.XMin:.2f}..{b.XMax:.2f} Y {b.YMin:.2f}..{b.YMax:.2f} "
          f"Z {b.ZMin:.2f}..{b.ZMax:.2f} -> {out} ({time.time() - t0:.0f}s)")
    FreeCAD.closeDocument(doc.Name)
    return out
