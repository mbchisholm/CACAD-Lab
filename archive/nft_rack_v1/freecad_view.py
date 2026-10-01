"""The exported rack as a FreeCAD assembly, for viewing: one Assembly with a part per frame member, channel body,
lid, cap, drain, feed tube, pipe, fitting, valve, hose, grommet, collector, tote and pump, one post grounded, parts coloured by kind, and a Spec
spreadsheet holding every value with its source tag. Nothing is placed or jointed by hand; the STEP carries every
position and rack.py checks them.

Before building, every imported part's world bounding box is compared with params' analytic envelope (computed
from the slope and placements, not read back from build123d) (F11: a STEP leaf can come in with its offset on a
wrapper), and one deliberately shifted expectation must disagree, so agreement is not vacuous. FreeCAD and
build123d are both OpenCascade: this check is independent in placement arithmetic, not in kernel.

Needs FreeCAD open with the MCP Addon's RPC server started, and rack.py run first.

    .venv/bin/python projects/nft_rack/freecad_view.py [rack]      # default ACTIVE_RACKS[0]
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.nft_rack.params import ACTIVE_RACKS, CHANNEL_KINDS, PLUMBING, PUMPS, RACK_SOURCES, RACKS, SPEC, derive

COLOURS = dict(frame=(0.62, 0.64, 0.68), channel=(0.95, 0.95, 0.95), lid=(0.85, 0.88, 0.85), cap=(0.30, 0.30, 0.32),
               drain=(0.30, 0.30, 0.32), tube=(0.55, 0.75, 0.95), manifold=(0.90, 0.90, 0.88),
               collector=(0.80, 0.82, 0.80), fitting=(0.55, 0.57, 0.60), pipe=(0.88, 0.88, 0.86),
               valve=(0.85, 0.25, 0.20), hose=(0.70, 0.85, 0.95), grommet=(0.12, 0.12, 0.12),
               tote=(0.15, 0.15, 0.17), pump=(0.10, 0.10, 0.10))   # display only

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
asm.Label = "nft_rack_" + D["rack"]
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


def check_positions(d: dict, got: dict, tol: float = 0.05) -> list[str]:
    """Compare FreeCAD's world bbox and volume per part with params. Empty list = agree."""
    exp = d["expect"]
    bad = []
    if set(got) != set(exp):
        bad.append(f"parts differ: missing {sorted(set(exp) - set(got))}, extra {sorted(set(got) - set(exp))}")
    for name, e in exp.items():
        if name not in got:
            continue
        g = got[name]
        want = (*e["lo"], *e["hi"])
        if g[6] != 1 or any(abs(a - b) > tol for a, b in zip(g[:6], want)) or abs(g[7] - e["volume"]) > 1e-3 * e["volume"]:
            bad.append(f"{name}: FreeCAD {[round(x, 2) for x in g[:6]]} vol {g[7]:.0f} ({g[6]} solids), "
                       f"params {[round(x, 2) for x in want]} vol {e['volume']:.0f}")
    return bad


def spec_rows(rack: str) -> list[list]:
    rows = [["Value", "mm / setting", "Tag", "Source"]]
    rows += [[k, round(v, 3), tag, src] for k, (v, tag, src) in SPEC.items()]
    rows.append([])
    rows += [[k, RACKS[rack][k] if not isinstance(RACKS[rack][k], float) else round(RACKS[rack][k], 3), tag, src]
             for k, (tag, src) in RACK_SOURCES[rack].items()]
    rows.append([])
    rows += [[f"channel {k} ({kv['label']})", f"{kv['sites']} sites @ {kv['pitch']:.1f}", *kv["src"]] for k, kv in CHANNEL_KINDS.items()]
    if "work_h" in RACKS[rack]:
        for row, r in list(PLUMBING.items()) + [(RACKS[rack]["pump"], PUMPS[RACKS[rack]["pump"]])]:
            rows.append([])
            rows.append([row, r["what"], "", r["ref"]])
            rows += [[f"{row}.{k}", v[0] if not isinstance(v[0], float) else round(v[0], 3), v[1], v[2]]
                     for k, v in r.items() if isinstance(v, tuple)]
    return rows


def main(rack: str):
    d = derive(rack)
    here = __file__.rsplit("/", 1)[0]
    step, fcstd = f"{here}/out/nft_rack_{rack}.step", f"{here}/out/nft_rack_{rack}.FCStd"
    doc = f"nft_rack_{rack}"
    fc = FreeCADRPC()

    imp = fc.run(IMPORT % dict(doc=doc, step=step), "import")
    bad = check_positions(d, imp["parts"])
    if bad:
        raise AssertionError(f"{rack}: FreeCAD positions disagree with params (root placement identity: {imp['root_identity']}):\n  "
                             + "\n  ".join(bad))
    # control: a 1 mm shift in one expectation must be caught
    name = sorted(n for n in d["expect"] if n.endswith("-lid") and n.startswith("L"))[-1]
    e = d["expect"][name]
    shifted = dict(d, expect=dict(d["expect"], **{name: dict(e, lo=(e["lo"][0] + 1.0, *e["lo"][1:]))}))
    assert check_positions(shifted, imp["parts"]), "control: a 1 mm shift was not detected; the position check is vacuous"
    print(f"  positions: {len(imp['parts'])} parts agree with params to 0.05 mm and 0.1 % volume; shifted control disagrees")

    kinds = {n: e["kind"] for n, e in d["expect"].items()}
    ground = "POST-FL"
    asm = fc.run(ASSEMBLE % dict(d=json.dumps(dict(doc=doc, rack=rack, kinds=kinds, colours=COLOURS, ground=ground))), "assemble")
    assert asm["parts"] == len(kinds), asm["parts"]
    assert asm["labels"] == sorted(kinds), f"{rack}: FreeCAD relabelled parts"
    assert asm["grounded"] == [ground], f"{rack}: grounded {asm['grounded']}, expected [{ground}]"
    want = sum(e["volume"] for e in d["expect"].values())
    assert abs(asm["volume"] - want) < 1e-3 * want, f"{rack}: assembly volume {asm['volume']:.0f} vs {want:.0f}"
    print(f"  assembly: {asm['parts']} parts, grounded {asm['grounded'][0]}, volume {asm['volume'] / 1e6:.2f} L of solid")

    s = fc.run(SHEET % dict(d=json.dumps(dict(doc=doc, rows=spec_rows(rack), fcstd=fcstd))), "spec sheet")
    print(f"  Spec sheet: {s['rows']} rows; saved {s['saved']}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ACTIVE_RACKS[0])
