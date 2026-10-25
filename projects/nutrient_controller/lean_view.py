"""L1 in FreeCAD, one document: the logic box with its boards, drivers, jack and screws, the lid lifted off in
front of it, and the ANALOG_NODE plate with its boards beside it on the same wall. The wall frame (X across, Y up,
Z out of the wall) is turned +90 deg about X, so FreeCAD's Front view looks at the wall. The lid lift and the
plate's offset are display only. Each printed part's FreeCAD bounding box (optimalBoundingBox, F26) is compared
with lean_params.derive() before the view is fitted.

Needs FreeCAD open with the MCP Addon's RPC server started, and lean_box.py run first.

    .venv/bin/python projects/nutrient_controller/lean_view.py
"""
from __future__ import annotations

from cacad.freecad import FreeCADRPC
from projects.nutrient_controller.lean_params import derive
from projects.standoff_plate.params import derive as plate_derive

OUT = __file__.rsplit("/", 1)[0] + "/out"
PLATE_OUT = __file__.rsplit("/", 2)[0] + "/standoff_plate/out"
DOC = "NutrientController_L1"
LID_LIFT = 45.0     # display: lid in front of the box, mm
PLATE_GAP = 20.0    # display: plate beside the box's ears, mm
PETG, LID = ((0.91, 0.53, 0.23), 0), ((0.91, 0.53, 0.23), 55)
BOARD, PART, METAL, PLUG = ((0.10, 0.36, 0.18), 0), ((0.55, 0.60, 0.58), 50), ((0.62, 0.64, 0.68), 0), ((0.85, 0.85, 0.80), 30)

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
f.Placement = App.Placement(App.Vector(%(dx)r, -%(dz)r, 0), App.Rotation(App.Vector(1, 0, 0), 90))
if App.GuiUp:
    f.ViewObject.ShapeColor = tuple(%(colour)r)
    f.ViewObject.Transparency = %(transparency)d
doc.recompute()
bb = sh.optimalBoundingBox(False, False)
print("JSON:" + json.dumps(dict(bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax], solids=len(sh.Solids),
                                valid=sh.isValid())))
'''

FIT = r'''
import FreeCADGui as Gui, json
v = Gui.getDocument(%(doc)r).activeView()
v.viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(ok=True)))
'''


def main(tol: float = 0.05):
    d, pd = derive(), plate_derive("ANALOG_NODE")
    ew, _ = d["ear_size"]
    W, H, D = d["W"], d["H"], d["D"]
    # (label, step, dx, dz (display lift out of the wall), colour, expected bbox in the part's own frame or None)
    pdx = W / 2 + ew + PLATE_GAP - pd["plate_x0"]
    rows = [("L1_body", f"{OUT}/L1_body.step", 0.0, 0.0, PETG, (-W / 2 - ew, 0.0, 0.0, W / 2 + ew, H, D)),
            ("L1_lid", f"{OUT}/L1_lid.step", 0.0, LID_LIFT, LID, (-W / 2, 0.0, D, W / 2, H, d["lid_top"]))]
    rows += [(f"L1_{k}", f"{OUT}/L1_hw_{k}.step", 0.0, LID_LIFT if k == "lid_screws" else 0.0, c, None)
             for k, c in (("boards", BOARD), ("tops", PART), ("plugs", PLUG), ("screws", METAL), ("nuts", METAL),
                          ("lid_screws", METAL), ("lid_nuts", METAL), ("jack", METAL), ("mounts", METAL))]
    rows += [("ANALOG_NODE_plate", f"{OUT}/ANALOG_NODE_plate.step", pdx, 0.0, PETG,
              (pd["plate_x0"], pd["plate_y0"], 0.0, pd["plate_x1"], pd["plate_y1"], pd["plate_t"] + pd["standoff_h"]))]
    rows += [(f"ANALOG_NODE_{k}", f"{OUT}/ANALOG_NODE_{k}.step", pdx, 0.0, c, None)
             for k, c in (("boards", BOARD), ("screws", METAL), ("nuts", METAL), ("mount_screws", METAL))]
    fc = FreeCADRPC()
    print("FreeCAD", fc.version())
    fc.run(NEW_DOC % dict(doc=DOC), "new document")
    bad = []
    for label, step, dx, dz, (colour, tr), exp in rows:
        got = fc.run(ADD % dict(doc=DOC, step=step, label=label, dx=dx, dz=dz, colour=colour, transparency=tr), label)
        if not got["valid"]:
            bad.append(f"{label}: invalid shape in FreeCAD")
        if exp is not None:
            diff = max(abs(a - b) for a, b in zip(got["bbox"], exp))
            print(f"  {label}: {got['solids']} solid(s), bbox off params by {diff:.3f}")
            if diff > tol:
                bad.append(f"{label}: bbox {[round(v, 3) for v in got['bbox']]} vs params {[round(v, 3) for v in exp]}")
    fc.run(FIT % dict(doc=DOC), "view")
    if bad:
        raise SystemExit("FreeCAD cross-check FAILED:\n  " + "\n  ".join(bad))
    print("cross-check ok")


if __name__ == "__main__":
    main()
