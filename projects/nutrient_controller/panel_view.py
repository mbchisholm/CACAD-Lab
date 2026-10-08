"""Concept D in FreeCAD, coloured as it would print and light: black panel with legends in the second colour,
slate case, chrome-bezel lamps, red digits behind red filters. Every solid is a Part::Feature read from out/
(panel.py writes them); nothing is placed by hand. The printed parts' FreeCAD bounding boxes are compared with
panel_params.derive() first.

Needs FreeCAD open with the MCP Addon's RPC server started, and panel.py run first.

    .venv/bin/python projects/nutrient_controller/panel_view.py [--open]     # --open: the case translucent
"""
from __future__ import annotations

from cacad.freecad import FreeCADRPC
from projects.nutrient_controller.panel_params import derive

OUT = __file__.rsplit("/", 1)[0] + "/out"
DOC = "NutrientController_D"
COLOURS = dict(   # role -> (rgb, transparency): display only
    panel=((0.10, 0.10, 0.11), 0), inlays=((0.95, 0.94, 0.90), 0), case=((0.36, 0.40, 0.43), 0),
    knob=((0.07, 0.07, 0.08), 0), filters=((0.35, 0.02, 0.02), 55), displays=((0.04, 0.03, 0.03), 0),
    digits=((1.00, 0.20, 0.10), 0), lamp_bezels=((0.82, 0.83, 0.85), 0), lens_run=((1.00, 0.62, 0.10), 0),
    lens_power=((0.20, 0.95, 0.30), 0), lens_alert=((0.45, 0.05, 0.05), 0), toggles=((0.05, 0.05, 0.05), 0),
    nuts=((0.70, 0.71, 0.73), 0), encoder=((0.30, 0.32, 0.30), 0), pump_flange=((0.12, 0.12, 0.12), 0),
    pump_head=((0.88, 0.89, 0.86), 25), pump_motor=((0.70, 0.71, 0.72), 0), pump_tubes=((0.90, 0.80, 0.60), 0),
    boards=((0.08, 0.35, 0.18), 0), entries=((0.15, 0.15, 0.16), 0),
)

NEW_DOC = r'''
import FreeCAD as App, json
if %(doc)r in App.listDocuments():
    App.closeDocument(%(doc)r)
App.newDocument(%(doc)r)
print("JSON:" + json.dumps(dict(ok=True)))
'''

ADD = r'''
import FreeCAD as App, Part, json
doc = App.getDocument(%(doc)r)
sh = Part.read(%(step)r)
f = doc.addObject("Part::Feature", %(label)r)
f.Shape = sh
if App.GuiUp:
    f.ViewObject.ShapeColor = tuple(%(colour)r)
    f.ViewObject.Transparency = %(transparency)d
    if %(label)r in ("inlays", "digits", "lens_run", "lens_power", "lens_alert"):
        f.ViewObject.DisplayMode = "Shaded"   # no edge lines over small text
doc.recompute()
bb = sh.optimalBoundingBox(False, False)
print("JSON:" + json.dumps(dict(bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax], solids=len(sh.Solids),
                                valid=sh.isValid())))
'''

FIT = r'''
import FreeCADGui as Gui, json
Gui.getDocument(%(doc)r).activeView().viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(ok=True)))
'''


def expected(d: dict) -> dict:
    k = d["knob"]
    kx, kz = d["knob_xz"]
    return dict(panel=(d["x0"], 0.0, d["z0"], d["x1"], d["panel_t"] + d["lip_h"], d["z1"]),
                case=(d["x0"], d["panel_t"], d["z0"], d["x1"], d["depth"], d["z1"]),
                knob=(kx - k["skirt_d"] / 2, d["knob_front_y"], kz - k["skirt_d"] / 2,
                      kx + k["skirt_d"] / 2, d["knob_base_y"], kz + k["skirt_d"] / 2))


def main(open_case: bool = False, tol: float = 0.05):
    d = derive()
    fc = FreeCADRPC()
    fc.run(NEW_DOC % dict(doc=DOC), "new document")
    exp, bad = expected(d), []
    for role, (colour, tr) in COLOURS.items():
        if open_case and role == "case":
            tr = 70
        got = fc.run(ADD % dict(doc=DOC, step=f"{OUT}/D_{role}.step", label=role, colour=colour, transparency=tr), role)
        if not got["valid"] and role in exp:
            bad.append(f"{role}: invalid shape in FreeCAD")
        if role in exp:
            diff = max(abs(a - b) for a, b in zip(got["bbox"], exp[role]))
            print(f"  {role}: bbox off params by {diff:.3f}")
            if diff > tol:
                bad.append(f"{role}: bbox {[round(v, 3) for v in got['bbox']]} vs params {[round(v, 3) for v in exp[role]]}")
    fc.run(FIT % dict(doc=DOC), "view")
    if bad:
        raise SystemExit("FreeCAD cross-check FAILED:\n  " + "\n  ".join(bad))
    print("cross-check ok")


if __name__ == "__main__":
    import sys
    main(open_case="--open" in sys.argv[1:])
