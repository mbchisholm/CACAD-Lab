"""The exported table as a FreeCAD assembly, for viewing and as a cross-check: one Assembly with a part per frame
member, bracket, channel body and lid, printed part, pipe, fitting, feed line, tote part and the pump; one leg
grounded; parts coloured by kind; a Spec sheet holding every value with its source tag. Nothing is placed or jointed
by hand: the STEP carries every position and table.py checks them.

Before building, every imported part's world bounding box (optimalBoundingBox, F26) and volume are compared with
params' analytic envelope and hand volume, and one deliberately shifted expectation must disagree, so agreement is
not vacuous. FreeCAD and build123d are both OpenCascade: this check is independent in placement arithmetic and in
the analytic description, not in kernel (design review rule 7).

Needs FreeCAD open with the MCP Addon's RPC server started, and table.py run first (out/nft_table.step).

    .venv/bin/python projects/nft_table/freecad_view.py
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.nft_table.params import BOUGHT, HYD, LAYOUT, SPEC, derive
from projects.nft_table.table import expected_box, expected_volume

COLOURS = dict(frame=(0.62, 0.64, 0.68), bracket=(0.45, 0.47, 0.50), channel=(0.95, 0.95, 0.95), lid=(0.85, 0.88, 0.85),
               printed=(0.95, 0.55, 0.15), pipe=(0.88, 0.88, 0.86), fitting=(0.55, 0.57, 0.60), sweep=(0.85, 0.25, 0.20),
               tube=(0.55, 0.75, 0.95), tote=(0.15, 0.15, 0.17), pump=(0.10, 0.10, 0.10))   # display only

IMPORT = r'''
import FreeCAD as App, Import, json
name = %(doc)r
if name in App.listDocuments():
    App.closeDocument(name)
doc = App.newDocument(name)
Import.insert(%(step)r, doc.Name)
doc.recompute()
roots = [o for o in doc.Objects if not o.InList]
assert len(roots) == 1, [o.Label for o in roots]
root = roots[0]
out = {}
for o in doc.Objects:
    if o is root or not hasattr(o, "Shape"):
        continue
    sh = o.Shape.copy()
    sh.Placement = root.Placement.multiply(sh.Placement)
    bb = sh.optimalBoundingBox(False, False)   # BoundBox is loose on torus and cut-cylinder faces (F26)
    out[o.Label] = [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax, len(sh.Solids), sh.Volume]
print("JSON:" + json.dumps(dict(root=root.Label, root_identity=root.Placement.isIdentity(), parts=out)))
'''

ASSEMBLE = r'''
import FreeCAD as App, json, JointObject, UtilsAssembly
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
src = {o.Label: o for o in doc.Objects if o.InList}
root = [o for o in doc.Objects if not o.InList][0]
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Label = "nft_table"
shapes = {}
for label in D["kinds"]:
    sh = src[label].Shape.copy()
    sh.Placement = root.Placement.multiply(sh.Placement)
    shapes[label] = sh
for o in [root] + list(src.values()):   # remove first: a live duplicate label would get a 001 suffix
    doc.removeObject(o.Name)
made = {}
for label, kind in D["kinds"].items():
    f = asm.newObject("Part::Feature", label.replace("-", "_"))
    f.Label = label
    f.Shape = shapes[label]
    if App.GuiUp:
        f.ViewObject.ShapeColor = tuple(D["colours"][kind])
    made[label] = f
jg = UtilsAssembly.getJointGroup(asm)
g = jg.newObject("App::FeaturePython", "GroundedJoint")
JointObject.GroundedJoint(g, made[D["ground"]])
if App.GuiUp:
    JointObject.ViewProviderGroundedJoint(g.ViewObject)
doc.recompute()
print("JSON:" + json.dumps(dict(parts=len(made), labels=sorted(f.Label for f in made.values()),
                                grounded=[j.ObjectToGround.Label for j in jg.Group if hasattr(j, "ObjectToGround")],
                                volume=sum(f.Shape.Volume for f in made.values()))))
'''

SHEET = r'''
import FreeCAD as App, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
sheet = doc.addObject("Spreadsheet::Sheet", "Spec")
for r, row in enumerate(D["rows"], start=1):
    for c, v in enumerate(row):
        sheet.set("ABCD"[c] + str(r), "'" + str(v))
doc.recompute()
doc.saveAs(D["fcstd"])
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.getDocument(doc.Name).activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(rows=len(D["rows"]), saved=D["fcstd"])))
'''


def check_positions(d: dict, got: dict, tol: float = 0.05, override: dict | None = None) -> list[str]:
    """Compare FreeCAD's world bbox and volume per part with params (labels included). Empty list = agree."""
    exp = d["expect"]
    override = override or {}
    bad = []
    if set(got) != set(exp):
        bad.append(f"parts differ: missing {sorted(set(exp) - set(got))}, extra {sorted(set(got) - set(exp))}")
    for name, e in exp.items():
        if name not in got:
            continue
        g = got[name]
        lo, hi = override.get(name, expected_box(e))
        want = (*lo, *hi)
        vw = expected_volume(e)
        if g[6] != 1 or any(abs(a - b) > tol for a, b in zip(g[:6], want)) or abs(g[7] - vw) > 1e-3 * vw:
            bad.append(f"{name}: FreeCAD {[round(x, 2) for x in g[:6]]} vol {g[7]:.0f} ({g[6]} solids), "
                       f"params {[round(x, 2) for x in want]} vol {vw:.0f}")
    return bad


def spec_rows() -> list[list]:
    rows = [["Value", "mm / setting", "Tag", "Source"]]
    for title, table in (("SPEC", SPEC), ("HYD", HYD), ("LAYOUT", LAYOUT)):
        rows.append([title, "", "", ""])
        rows += [[k, v if not isinstance(v, float) else round(v, 4), tag, src] for k, (v, tag, src) in table.items()]
    for row, r in BOUGHT.items():
        rows.append([])
        rows.append([row, r["what"], "", r["ref"]])
        rows += [[f"{row}.{k}", v[0] if not isinstance(v[0], float) else round(v[0], 4), v[1], v[2]]
                 for k, v in r.items() if isinstance(v, tuple)]
    return rows


def main():
    d = derive()
    here = __file__.rsplit("/", 1)[0]
    step, fcstd = f"{here}/out/nft_table.step", f"{here}/out/nft_table.FCStd"
    doc = "nft_table"
    fc = FreeCADRPC()

    imp = fc.run(IMPORT % dict(doc=doc, step=step), "import")
    bad = check_positions(d, imp["parts"])
    if bad:
        raise AssertionError("FreeCAD positions disagree with params (root placement identity: "
                             f"{imp['root_identity']}):\n  " + "\n  ".join(bad))
    # control: a 1 mm shift in one expectation must be caught
    name = "C3-lid"
    lo, hi = expected_box(d["expect"][name])
    assert check_positions(d, imp["parts"], override={name: ((lo[0] + 1.0, *lo[1:]), hi)}), \
        "control: a 1 mm shift was not detected; the position check is vacuous"
    print(f"  positions: {len(imp['parts'])} parts agree with params to 0.05 mm and 0.1 % volume; shifted control disagrees")

    kinds = {n: e["kind"] for n, e in d["expect"].items()}
    ground = "LEG-FL"
    asm = fc.run(ASSEMBLE % dict(d=json.dumps(dict(doc=doc, rack="table", kinds=kinds, colours=COLOURS, ground=ground))), "assemble")
    assert asm["parts"] == len(kinds), asm["parts"]
    assert asm["labels"] == sorted(kinds), "FreeCAD relabelled parts"
    assert asm["grounded"] == [ground], f"grounded {asm['grounded']}, expected [{ground}]"
    want = sum(expected_volume(e) for e in d["expect"].values())
    assert abs(asm["volume"] - want) < 1e-3 * want, f"assembly volume {asm['volume']:.0f} vs {want:.0f}"
    print(f"  assembly: {asm['parts']} parts, grounded {asm['grounded'][0]}, volume {asm['volume'] / 1e6:.2f} L of solid")

    s = fc.run(SHEET % dict(d=json.dumps(dict(doc=doc, rows=spec_rows(), fcstd=fcstd))), "spec sheet")
    print(f"  Spec sheet: {s['rows']} rows; saved {s['saved']}")


if __name__ == "__main__":
    main()
