"""The exported bench in its garage, in FreeCAD, for viewing: wood coloured
by stock, feet, translucent tote envelopes, and the slab, lip and wall it
stands on. A section group cuts everything through the middle of bay 0, so
the lip, the back legs on it and the two totes read in one picture. Saves
out/workbench_<bench>.FCStd and three PNG renders.

Before building, every imported solid's world bounding box is compared with
params (F11), and a deliberately shifted expectation must disagree, so the
agreement is not vacuous. Nothing is placed by hand: the STEPs carry every
position and bench.py checks them.

Needs FreeCAD open with the MCP Addon's RPC server started, and bench.py run first.

    .venv/bin/python projects/workbench/freecad_view.py [bench]      # default ACTIVE_BENCHES[0]
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.garage.params import derive as site_derive
from projects.workbench.params import ACTIVE_BENCHES, derive

# display only: (rgb, transparency %)
LOOK = dict(x2x4=((0.62, 0.42, 0.22), 0), ply=((0.86, 0.72, 0.50), 0), foot=((0.20, 0.20, 0.22), 0),
            tote=((0.30, 0.50, 0.75), 55), SLAB=((0.62, 0.62, 0.60), 0), LIP=((0.50, 0.50, 0.48), 0),
            WALL=((0.90, 0.89, 0.86), 0))

IMPORT = r'''
import FreeCAD as App, Import, json
D = json.loads(%(d)r)
if D["doc"] in App.listDocuments():
    App.closeDocument(D["doc"])
doc = App.newDocument(D["doc"])
out = {}
for grp_name, step in D["steps"].items():
    before = set(doc.Objects)
    Import.insert(step, doc.Name)
    new = [o for o in doc.Objects if o not in before]
    roots = [o for o in new if not o.InList]
    assert len(roots) == 1, (grp_name, [o.Label for o in roots])
    root = roots[0]
    grp = doc.addObject("App::DocumentObjectGroup", grp_name)
    shapes = {}
    for o in new:
        if o is root or not hasattr(o, "Shape") or o.Shape.isNull() or len(o.Shape.Solids) != 1:
            continue
        sh = o.Shape.copy()
        sh.Placement = root.Placement.multiply(sh.Placement)
        shapes[o.Label] = sh
    for o in sorted(new, key=lambda o: -len(o.OutList)):
        doc.removeObject(o.Name)
    for label, sh in shapes.items():
        f = doc.addObject("Part::Feature", label.replace("-", "_"))
        f.Label = label
        f.Shape = sh
        grp.addObject(f)
        bb = sh.BoundBox
        out[label] = [grp_name, bb.XMin, bb.YMin, bb.ZMin, bb.XLength, bb.YLength, bb.ZLength]
doc.recompute()
print("JSON:" + json.dumps(out))
'''

STYLE = r'''
import FreeCAD as App, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
n = 0
for label, (rgb, tr) in D["look"].items():
    o = doc.getObjectsByLabel(label)[0]
    if App.GuiUp:
        o.ViewObject.ShapeColor = tuple(rgb)
        o.ViewObject.Transparency = tr
        o.ViewObject.LineColor = (0.15, 0.12, 0.10)
    n += 1
print("JSON:" + json.dumps(dict(styled=n)))
'''

SECTION = r'''
import FreeCAD as App, Part, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
grp = doc.addObject("App::DocumentObjectGroup", "Section")
grp.Label = "Section through bay 0"
x = D["x"]
keep = Part.makeBox(1e5, 1e5, 1e5, App.Vector(x, -5e4, -5e4))   # everything at +X of the cut
made = 0
for label, (rgb, tr) in D["look"].items():
    o = doc.getObjectsByLabel(label)[0]
    sh = o.Shape.common(keep)
    if sh.isNull() or sh.Volume < 1e-6:
        continue
    f = doc.addObject("Part::Feature", "cut")
    f.Label = "cut " + label
    f.Shape = sh
    grp.addObject(f)
    if App.GuiUp:
        f.ViewObject.ShapeColor = tuple(rgb)
        f.ViewObject.Transparency = min(tr, 40)
        f.ViewObject.Visibility = False
    made += 1
doc.recompute()
print("JSON:" + json.dumps(dict(cut=made)))
'''

RENDER = r'''
import FreeCAD as App, FreeCADGui as Gui, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
Gui.setActiveDocument(doc.Name)
v = Gui.getDocument(doc.Name).activeView()
# saveImage right after a view change captures the camera mid-animation (FINDINGS F33): animation off, restored after
pref = App.ParamGet("User parameter:BaseApp/Preferences/View")
anim = pref.GetBool("UseNavigationAnimations", True)
pref.SetBool("UseNavigationAnimations", False)
sec = [o for o in doc.Objects if o.Label.startswith("cut ")]
full = [o for o in doc.Objects if o.TypeId == "Part::Feature" and o not in sec]
for o in full:
    o.ViewObject.Visibility = not D["section"]
for o in sec:
    o.ViewObject.Visibility = D["section"]
v.setCameraType("Orthographic")
if D["view"] == "room":
    v.viewIsometric()   # looks at the wall's back; swing the camera round Z into the room
    v.setCameraOrientation(App.Rotation(App.Vector(0, 0, 1), D["swing"]).multiply(v.getCameraOrientation()))
else:
    getattr(v, D["view"])()
v.fitAll()
v.saveImage(D["png"], D["w"], D["h"], "White")
for o in full:
    o.ViewObject.Visibility = True
for o in sec:
    o.ViewObject.Visibility = False
pref.SetBool("UseNavigationAnimations", anim)
print("JSON:" + json.dumps(dict(png=D["png"], camera=list(v.getCameraOrientation().Q))))
'''

SAVE = r'''
import FreeCAD as App, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
doc.saveAs(D["fcstd"])
print("JSON:" + json.dumps(dict(saved=D["fcstd"], objects=len(doc.Objects))))
'''


def expected(d: dict) -> dict:
    """label -> (group, min corner xyz, size xyz), from params, for every solid FreeCAD should hold."""
    out = {nm: ("bench", lo, size) for nm, (_, size, lo) in d["boards"].items()}
    for nm, (base, r, h) in d["feet"].items():
        out[nm] = ("feet", (base[0] - r, base[1] - r, base[2]), (2 * r, 2 * r, h))
    for nm, (size, lo) in d["totes"].items():
        out[nm] = ("totes", lo, size)
    s = site_derive(d["top_x0"], d["top_x0"] + d["W"], d["wall"])
    for nm, (size, lo) in s["boxes"].items():
        out[nm] = ("garage", lo, size)
    return out


def check_positions(want: dict, got: dict, tol: float = 0.01) -> list[str]:
    bad = []
    if set(got) != set(want):
        bad.append(f"labels differ: missing {sorted(set(want) - set(got))}, extra {sorted(set(got) - set(want))}")
    for nm, (grp, lo, size) in want.items():
        if nm not in got:
            continue
        g = got[nm]
        if g[0] != grp or any(abs(a - b) > tol for a, b in zip(g[1:], (*lo, *size))):
            bad.append(f"{nm}: FreeCAD {g[0]} {[round(x, 2) for x in g[1:]]}, params {grp} {[round(x, 2) for x in (*lo, *size)]}")
    return bad


def main(bench: str):
    d = derive(bench)
    here = __file__.rsplit("/", 1)[0]
    out = f"{here}/out"
    doc = f"workbench_{bench}"
    steps = {g: f"{out}/workbench_{bench}{'' if g == 'bench' else '_' + g}.step" for g in ("bench", "feet", "totes", "garage")}
    fc = FreeCADRPC()

    got = fc.run(IMPORT % dict(d=json.dumps(dict(doc=doc, steps=steps))), "import")
    want = expected(d)
    bad = check_positions(want, got)
    if bad:
        raise AssertionError(f"{bench}: FreeCAD positions disagree with params:\n  " + "\n  ".join(bad))
    nm = next(iter(d["boards"]))
    grp, lo, size = want[nm]
    shifted = dict(want, **{nm: (grp, (lo[0] + 1.0, lo[1], lo[2]), size)})
    assert check_positions(shifted, got), "control: a 1 mm shift was not detected; the position check is vacuous"
    print(f"  positions: {len(got)} solids agree with params to 0.01 mm; shifted control disagrees")

    look = {}
    for nm, (grp, _, _) in want.items():
        key = d["boards"][nm][0] if grp == "bench" else {"feet": "foot", "totes": "tote"}.get(grp, nm)
        look[nm] = LOOK[key]
    st = fc.run(STYLE % dict(d=json.dumps(dict(doc=doc, look=look))), "style")
    assert st["styled"] == len(want), st

    x_cut = sum(d["bays_x"][0]) / 2
    sec = fc.run(SECTION % dict(d=json.dumps(dict(doc=doc, look=look, x=x_cut))), "section")
    print(f"  section at x = {x_cut:.0f} mm (bay 0 centre): {sec['cut']} cut solids")

    # (tag, view, section): "room" is the isometric swung round into the room; viewRear looks at the wall from the
    # room; viewLeft looks along +X at the section's cut face
    renders = [("iso", "room", False), ("front", "viewRear", False), ("section", "viewLeft", True)]
    for tag, view, section in renders:
        png = f"{out}/render_{tag}.png"
        fc.run(RENDER % dict(d=json.dumps(dict(doc=doc, view=view, swing=150, section=section, png=png, w=1600, h=1100))),
               f"render {tag}")
        print(f"  render: {png}")
    s = fc.run(SAVE % dict(d=json.dumps(dict(doc=doc, fcstd=f"{out}/workbench_{bench}.FCStd"))), "save")
    print(f"  saved {s['saved']} ({s['objects']} objects)")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ACTIVE_BENCHES[0])
