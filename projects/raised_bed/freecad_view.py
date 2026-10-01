"""The exported bed as a FreeCAD assembly, for viewing: one Assembly with a
part per picket and post, one post grounded, pickets and posts coloured by
kind, and a BOM spreadsheet written from params.derive. Nothing is placed or
jointed by hand; the STEP carries every position and bed.py checks them.

Before building, every imported part's world bounding box is compared with
params (F11: a STEP leaf can come in with its offset on a wrapper), and one
deliberately shifted expectation must disagree, so agreement is not vacuous.

Needs FreeCAD open with the MCP Addon's RPC server started, and bed.py run first.

    .venv/bin/python projects/raised_bed/freecad_view.py [bed]      # default ACTIVE_BEDS[0]
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.raised_bed.params import ACTIVE_BEDS, IN, LUMBER, derive

COLOURS = dict(picket=(0.78, 0.53, 0.35), post=(0.42, 0.29, 0.18))   # display only

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
ident = root.Placement.isIdentity()
out = {}
for o in doc.Objects:
    if o is root or not hasattr(o, "Shape"):
        continue
    sh = o.Shape.copy()
    sh.Placement = root.Placement.multiply(sh.Placement)
    bb = sh.BoundBox
    out[o.Label] = [bb.XMin, bb.YMin, bb.ZMin, bb.XLength, bb.YLength, bb.ZLength, len(sh.Solids)]
print("JSON:" + json.dumps(dict(root=root.Label, root_identity=ident, parts=out)))
'''

ASSEMBLE = r'''
import FreeCAD as App, json, JointObject, UtilsAssembly
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
src = {o.Label: o for o in doc.Objects if o.InList}
root = [o for o in doc.Objects if not o.InList][0]
asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
asm.Label = "raised_bed_" + D["bed"]
shapes = {}
for label in D["kinds"]:
    sh = src[label].Shape.copy()
    sh.Placement = root.Placement.multiply(sh.Placement)
    shapes[label] = sh
for o in [root] + list(src.values()):   # remove first: a live duplicate label would get a 001 suffix
    doc.removeObject(o.Name)
made = {}
for label, kind in D["kinds"].items():
    f = asm.newObject("Part::Feature", label.replace("+", "p").replace("-", "m"))
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
# UtilsAssembly.isAssemblyGrounded() reads the GUI's active assembly, not this one: read the joint group
print("JSON:" + json.dumps(dict(parts=len(made), labels=sorted(f.Label for f in made.values()),
                                grounded=[j.ObjectToGround.Label for j in jg.Group if hasattr(j, "ObjectToGround")],
                                volume=sum(f.Shape.Volume for f in made.values()))))
'''

EXPLODE = r'''
import FreeCAD as App, json, CommandCreateView, UtilsAssembly
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
asm = doc.getObject("Assembly")
by_label = {o.Label: o for o in asm.Group if o.TypeId == "Part::Feature"}
view = UtilsAssembly.getViewGroup(asm).newObject("App::FeaturePython", "ExplodedView")
view.Label = "Exploded view"
CommandCreateView.ExplodedView(view)
if App.GuiUp:
    CommandCreateView.ViewProviderExplodedView(view.ViewObject)
moves = []
for name, parts, vec in D["moves"]:
    m = asm.newObject("App::FeaturePython", "Move")
    m.Label = name
    CommandCreateView.ExplodedViewStep(m, 0)
    if App.GuiUp:
        CommandCreateView.ViewProviderExplodedViewStep(m.ViewObject)
    m.MovementTransform = App.Placement(App.Vector(*vec), App.Rotation())
    m.References = [asm, [by_label[p].Name + "." for p in parts]]
    moves.append(m)
view.Group = moves
doc.recompute()
def mins():
    return {l: [o.Shape.BoundBox.XMin, o.Shape.BoundBox.YMin, o.Shape.BoundBox.ZMin] for l, o in by_label.items()}
before = mins()
view.Proxy.saveAssemblyAndExplode(view)
exploded = mins()
shapes = [o.Shape for o in by_label.values()]
overlap = max(shapes[i].common(shapes[j]).Volume for i in range(len(shapes)) for j in range(i + 1, len(shapes)))
view.Proxy.restoreAssembly(view)
after = mins()
doc.recompute()
print("JSON:" + json.dumps(dict(moves=len(view.Group), before=before, exploded=exploded, after=after, overlap=overlap)))
'''

BOM = r'''
import FreeCAD as App, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
sheet = doc.addObject("Spreadsheet::Sheet", "BOM")
for r, row in enumerate(D["rows"], start=1):
    for c, v in enumerate(row):
        cell = "ABCDEFG"[c] + str(r)
        sheet.set(cell, str(v))
doc.recompute()
doc.saveAs(D["fcstd"])
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.getDocument(doc.Name).activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(rows=len(D["rows"]), saved=D["fcstd"])))
'''


def check_positions(d: dict, got: dict, tol: float = 0.01) -> list[str]:
    """Compare FreeCAD's world bbox per part with params. Empty list = agree."""
    bad = []
    if set(got) != set(d["boards"]):
        bad.append(f"parts differ: missing {sorted(set(d['boards']) - set(got))}, extra {sorted(set(got) - set(d['boards']))}")
    for name, (_, size, lo) in d["boards"].items():
        if name not in got:
            continue
        g = got[name]
        want = (*lo, *size)
        if g[6] != 1 or any(abs(a - b) > tol for a, b in zip(g[:6], want)):
            bad.append(f"{name}: FreeCAD {[round(x, 2) for x in g[:6]]} ({g[6]} solids), params {[round(x, 2) for x in want]}")
    return bad


def check_exploded(d: dict, ex: dict, tol: float = 0.01):
    """Exploded = assembled + params' offset per part; restored = assembled; the moves really moved the pickets."""
    assert ex["moves"] == len(d["explode_moves"]), ex["moves"]
    for name, (_, _, lo) in d["boards"].items():
        off = d["explode_offset"][name]
        want = [lo[a] + off[a] for a in range(3)]
        for key, exp in (("before", lo), ("exploded", want), ("after", lo)):
            got = ex[key][name]
            assert all(abs(g - e) < tol for g, e in zip(got, exp)), f"{name} {key}: FreeCAD {got}, params {exp}"
        moved = any(abs(o) > tol for o in off)
        assert moved == (d["boards"][name][0] == "picket"), f"{name}: moved {moved}"
    assert ex["overlap"] < 1e-3, f"exploded parts overlap by {ex['overlap']:.3f} mm^3"


def bom_rows(d: dict) -> list[list]:
    long_n = sum(1 for n in d["boards"] if n.startswith("long"))
    short_n = sum(1 for n in d["boards"] if n.startswith("short"))
    post_n = sum(1 for n in d["boards"] if n.startswith("post"))
    mm_in = lambda x: [round(x, 1), round(x / IN, 2)]
    return [
        ["Item", "Qty", "Cut mm", "Cut in", "From", "Source"],
        ["Long side picket", long_n, *mm_in(d["long_len"]), "1x6 cedar picket, 6 ft", LUMBER["picket"]["source"]],
        ["Short side picket", short_n, *mm_in(d["short_len"]), "1x6 cedar picket, 6 ft", LUMBER["picket"]["source"]],
        ["Corner post", post_n, *mm_in(d["post_len"]), "4x4 cedar, 8 ft", LUMBER["post"]["source"]],
        ["Screw", len(d["screws"]), *mm_in(d["screw_len"]), d["screw_spec"]["label"], "6D min penetration (AWC NDS)"],
        [],
        ["Buy", "Qty", "", "", "", ""],
        ["1x6 cedar picket, 6 ft", d["pickets_needed"], "", "", f"yield {100 * d['picket_yield']:.0f} %", ""],
        ["4x4 cedar, 8 ft", d["posts_needed"], "", "", "", ""],
        [d["screw_spec"]["label"] + f" {d['screw_len'] / IN:g} in", len(d["screws"]), "", "", "", ""],
        [],
        ["Soil to rim, L", round(d["soil_volume_l"]), "", "", f"{d['soil_volume_cuft']:.1f} cu ft", ""],
    ]


def main(bed: str):
    d = derive(bed)
    here = __file__.rsplit("/", 1)[0]
    step, fcstd = f"{here}/out/raised_bed_{bed}.step", f"{here}/out/raised_bed_{bed}.FCStd"
    doc = f"raised_bed_{bed}"
    fc = FreeCADRPC()

    imp = fc.run(IMPORT % dict(doc=doc, step=step), "import")
    bad = check_positions(d, imp["parts"])
    if bad:
        raise AssertionError(f"{bed}: FreeCAD positions disagree with params (root placement identity: {imp['root_identity']}):\n  "
                             + "\n  ".join(bad))
    # control: a 1 mm shift in one expectation must be caught
    name = next(iter(d["boards"]))
    kind, size, lo = d["boards"][name]
    shifted = dict(d, boards=dict(d["boards"], **{name: (kind, size, (lo[0] + 1.0, lo[1], lo[2]))}))
    assert check_positions(shifted, imp["parts"]), "control: a 1 mm shift was not detected; the position check is vacuous"
    print(f"  positions: {len(imp['parts'])} parts agree with params to 0.01 mm; shifted control disagrees")

    kinds = {n: k for n, (k, _, _) in d["boards"].items()}
    ground = next(n for n, k in kinds.items() if k == "post")
    asm = fc.run(ASSEMBLE % dict(d=json.dumps(dict(doc=doc, bed=bed, kinds=kinds, colours=COLOURS, ground=ground))), "assemble")
    assert asm["parts"] == len(d["boards"]), asm
    assert asm["labels"] == sorted(d["boards"]), f"{bed}: FreeCAD relabelled parts: {asm['labels']}"
    assert asm["grounded"] == [ground], f"{bed}: grounded {asm['grounded']}, expected [{ground}]"
    assert abs(asm["volume"] - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{bed}: assembly volume {asm['volume']:.0f} vs {d['wood_volume']:.0f}"
    print(f"  assembly: {asm['parts']} parts, grounded {asm['grounded'][0]}, wood {asm['volume'] / 1e6:.2f} L")

    ex = fc.run(EXPLODE % dict(d=json.dumps(dict(doc=doc, moves=d["explode_moves"]))), "exploded view")
    check_exploded(d, ex)
    print(f"  exploded view: {ex['moves']} moves; every part lands on params' offset, none overlap "
          f"(max {ex['overlap']:.3g} mm^3), and all return to the assembled position")

    b = fc.run(BOM % dict(d=json.dumps(dict(doc=doc, rows=bom_rows(d), fcstd=fcstd))), "bom")
    print(f"  BOM: {b['rows']} rows; saved {b['saved']}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ACTIVE_BEDS[0])
