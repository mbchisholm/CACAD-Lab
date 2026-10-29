"""out/desk_bench.step as a FreeCAD document, parts coloured by kind. Each part's world bounding box is checked
against params before the view is fitted. FreeCAD open with the MCP Addon's RPC server started; desk.py run first.

    .venv/bin/python projects/desk_bench/freecad_view.py
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.desk_bench.params import validate

COLOURS = dict(x2x4=(0.55, 0.36, 0.20), x2x2=(0.80, 0.60, 0.38), plywood=(0.90, 0.78, 0.55))

CODE = r'''
import FreeCAD as App, Import, json
D = json.loads(%(d)r)
if D["doc"] in App.listDocuments():
    App.closeDocument(D["doc"])
doc = App.newDocument(D["doc"])
Import.insert(D["step"], doc.Name)
doc.recompute()
out = {}
for o in doc.Objects:
    if not hasattr(o, "Shape") or o.InList or not o.Shape.Solids:
        continue
    for sub in [o] + o.OutListRecursive:
        if sub.Label in D["kinds"] and hasattr(sub, "Shape"):
            sh = sub.Shape.copy()
            sh.Placement = o.Placement.multiply(sh.Placement) if sub is not o else sh.Placement
            bb = sh.BoundBox
            out[sub.Label] = [bb.XMin, bb.YMin, bb.ZMin, bb.XLength, bb.YLength, bb.ZLength]
            if App.GuiUp:
                sub.ViewObject.ShapeColor = tuple(D["colours"][D["kinds"][sub.Label]])
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.getDocument(doc.Name).activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
doc.saveAs(D["fcstd"])
print("JSON:" + json.dumps(out))
'''


def expected(d):
    out = {n: (*lo, *size) for n, (_, size, lo) in d["boards"].items()}
    for n, (_, y0, th, poly) in d["prisms"].items():
        xs, zs = [p[0] for p in poly], [p[1] for p in poly]
        out[n] = (min(xs), y0, min(zs), max(xs) - min(xs), th, max(zs) - min(zs))
    out["TOP"] = (*d["top"]["lo"], *d["top"]["size"])
    return out


def main():
    d = validate()
    here = __file__.rsplit("/", 1)[0]
    kinds = {n: k for n, (k, *_) in {**d["boards"], **d["prisms"]}.items()}
    kinds["TOP"] = "plywood"
    fc = FreeCADRPC()
    got = fc.run(CODE % dict(d=json.dumps(dict(doc="desk_bench", step=f"{here}/out/desk_bench.step", fcstd=f"{here}/out/desk_bench.FCStd",
                                               kinds=kinds, colours=COLOURS))), "import")
    want = expected(d)
    bad = [f"{n}: FreeCAD {[round(x, 2) for x in got.get(n, [])]} params {[round(x, 2) for x in w]}"
           for n, w in want.items() if n not in got or any(abs(a - b) > 0.01 for a, b in zip(got[n], w))]
    assert not bad, "FreeCAD disagrees with params:\n" + "\n".join(bad)
    print(f"{len(got)} parts in FreeCAD, every bounding box matches params")


if __name__ == "__main__":
    main()
