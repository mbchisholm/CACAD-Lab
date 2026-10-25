"""The analog nutrient node's plates in FreeCAD, one document: each NUTRIENT_ANALOG plate with its boards (vendor
STEP where there is one, the registry envelope otherwise, translucent) and its screws and nuts, the plates laid out
side by side along X. Every solid is a Part::Feature read from out/ (vendor.py writes them); the side-by-side offset
is display only. Before showing anything, each plate's and each screw set's FreeCAD bounding box
(optimalBoundingBox, F26) is compared with params.derive().

Needs FreeCAD open with the MCP Addon's RPC server started, and vendor.py run first.

    .venv/bin/python projects/standoff_plate/freecad_view.py
"""
from __future__ import annotations

from cacad.freecad import FreeCADRPC
from projects.standoff_plate.params import NUTRIENT_ANALOG, VENDOR_STEPS, derive

OUT = __file__.rsplit("/", 1)[0] + "/out"
DOC = "NutrientAnalog_plates"
GAP = 15.0   # display: space between plates, mm
COLOURS = dict(plate=((0.91, 0.53, 0.23), 0), vendor=((0.10, 0.36, 0.18), 0), envelope=((0.55, 0.60, 0.58), 60),
               screws=((0.62, 0.64, 0.68), 0))

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
f.Placement.Base = App.Vector(%(dx)r, 0, 0)
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
Gui.getDocument(%(doc)r).activeView().viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(ok=True)))
'''


def expected(d: dict) -> dict:
    """(xmin, ymin, zmin, xmax, ymax, zmax) per checked object, from params, in the plate's own frame."""
    top = d["wall_top_z"] if d["tray"] else d["plate_t"] + d["standoff_h"]
    hx = [x for x, _ in d["holes"]]
    hy = [y for _, y in d["holes"]]
    sc = d["screw_spec"]
    rx = max(sc["head_dk"], sc["nut_s"]) / 2               # nut flats face X
    ry = max(sc["head_dk"], sc["nut_s"] / 0.8660254) / 2   # nut corners point along Y
    return dict(plate=(d["plate_x0"], d["plate_y0"], 0.0, d["plate_x1"], d["plate_y1"], top),
                screws=(min(hx) - rx, min(hy) - ry, d["screw_tip_z"], max(hx) + rx, max(hy) + ry, d["z_head_top"]))


def main(tol: float = 0.05):
    fc = FreeCADRPC()
    print("FreeCAD", fc.version())
    fc.run(NEW_DOC % dict(doc=DOC), "new document")
    bad, cursor = [], 0.0
    for plate in NUTRIENT_ANALOG:
        d = derive(plate)
        dx = cursor - d["plate_x0"]
        cursor += d["plate_size"][0] + GAP
        vendor = all(pl[0] in VENDOR_STEPS for pl in d["placements"])
        exp = expected(d)
        for kind, colour_key in (("plate", "plate"), ("boards", "vendor" if vendor else "envelope"), ("screws", "screws")):
            step = f"{OUT}/standoff_plate_{plate}" + ("" if kind == "plate" else f"_{kind}") + ".step"
            colour, tr = COLOURS[colour_key]
            got = fc.run(ADD % dict(doc=DOC, step=step, label=f"{plate}_{kind}", dx=dx, colour=colour, transparency=tr), f"{plate} {kind}")
            if not got["valid"]:
                bad.append(f"{plate} {kind}: invalid shape in FreeCAD")
            if kind in exp:
                diff = max(abs(a - b) for a, b in zip(got["bbox"], exp[kind]))
                print(f"  {plate} {kind}: {got['solids']} solid(s), bbox off params by {diff:.3f}")
                if diff > tol:
                    bad.append(f"{plate} {kind}: bbox {[round(v, 3) for v in got['bbox']]} vs params {[round(v, 3) for v in exp[kind]]}")
            else:
                print(f"  {plate} {kind}: {got['solids']} solid(s), {'vendor STEP' if vendor else 'registry envelope'}")
    fc.run(FIT % dict(doc=DOC), "view")
    if bad:
        raise SystemExit("FreeCAD cross-check FAILED:\n  " + "\n  ".join(bad))
    print("cross-check ok")


if __name__ == "__main__":
    main()
