"""Each version in its garage, in FreeCAD: wood coloured by size, feet,
translucent totes, slab, lip and wall. Imported positions are checked
against params (F11) with a shifted control. Renders per version a room view
and a front view; for the first version also a section through a tote column
and one ladder on its own (the build's repeated unit). Saves
out/tote_bench_<version>.FCStd.

Needs FreeCAD open with the MCP Addon's RPC server started, and bench.py run first.

    .venv/bin/python projects/tote_bench/freecad_view.py [version ...]     # default ACTIVE_VERSIONS
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.garage.params import derive as site_derive
from projects.tote_bench.params import ACTIVE_VERSIONS, derive
from projects.workbench.freecad_view import IMPORT, SAVE, SECTION, STYLE, check_positions

LOOK = dict(x2x4=((0.62, 0.42, 0.22), 0), x2x6=((0.85, 0.68, 0.45), 0), foot=((0.20, 0.20, 0.22), 0),
            tote=((0.30, 0.50, 0.75), 55), SLAB=((0.62, 0.62, 0.60), 0), LIP=((0.50, 0.50, 0.48), 0),
            WALL=((0.90, 0.89, 0.86), 0))

RENDER = r'''
import FreeCAD as App, FreeCADGui as Gui, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
Gui.setActiveDocument(doc.Name)
v = Gui.getDocument(doc.Name).activeView()
pref = App.ParamGet("User parameter:BaseApp/Preferences/View")      # F33: no animation while saving images
anim = pref.GetBool("UseNavigationAnimations", True)
pref.SetBool("UseNavigationAnimations", False)
sec = [o for o in doc.Objects if o.Label.startswith("cut ")]
full = [o for o in doc.Objects if o.TypeId == "Part::Feature" and o not in sec]
only = D["only"]
for o in full:
    o.ViewObject.Visibility = (not D["section"]) and (only is None or any(o.Label.startswith(p) for p in only))
for o in sec:
    o.ViewObject.Visibility = D["section"]
v.setCameraType("Orthographic")
if D["view"] == "room":
    v.viewIsometric()
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
print("JSON:" + json.dumps(dict(png=D["png"], shown=sum(1 for o in full if only is None or any(o.Label.startswith(p) for p in only)))))
'''


def expected(d: dict) -> dict:
    out = {nm: ("bench", lo, size) for nm, (_, size, lo) in d["boards"].items()}
    for nm, (base, r, h) in d["feet"].items():
        out[nm] = ("feet", (base[0] - r, base[1] - r, base[2]), (2 * r, 2 * r, h))
    for nm, (size, lo) in d["totes"].items():
        out[nm] = ("totes", lo, size)
    for nm, (size, lo) in site_derive(d["top_x0"], d["top_x0"] + d["W"])["boxes"].items():
        out[nm] = ("garage", lo, size)
    return out


def main(version: str, detail: bool):
    d = derive(version)
    out = __file__.rsplit("/", 1)[0] + "/out"
    doc = f"tote_bench_{version}"
    steps = {g: f"{out}/tote_bench_{version}{'' if g == 'bench' else '_' + g}.step" for g in ("bench", "feet", "totes", "garage")}
    fc = FreeCADRPC()
    got = fc.run(IMPORT % dict(d=json.dumps(dict(doc=doc, steps=steps))), f"import {version}")
    want = expected(d)
    bad = check_positions(want, got)
    assert not bad, f"{version}: FreeCAD disagrees with params:\n  " + "\n  ".join(bad)
    nm = next(iter(d["boards"]))
    grp, lo, size = want[nm]
    assert check_positions(dict(want, **{nm: (grp, (lo[0] + 1.0, lo[1], lo[2]), size)}), got), "control: 1 mm shift not detected"
    print(f"  {version}: {len(got)} solids agree with params to 0.01 mm; shifted control disagrees")
    look = {nm: LOOK[d["boards"][nm][0] if g == "bench" else {"feet": "foot", "totes": "tote"}.get(g, nm)] for nm, (g, _, _) in want.items()}
    st = fc.run(STYLE % dict(d=json.dumps(dict(doc=doc, look=look))), "style")
    assert st["styled"] == len(want), st
    renders = [("room", "room", False, None, 150), ("front", "viewRear", False, None, 0)]
    if detail:
        col = next(c for c in d["columns"] if c["kind"] == "T")
        sec = fc.run(SECTION % dict(d=json.dumps(dict(doc=doc, look=look, x=(col["x0"] + col["x1"]) / 2))), "section")
        print(f"  section through tote column {col['j']}: {sec['cut']} cut solids")
        renders += [("section", "viewLeft", True, None, 0), ("ladder", "room", False, ["L1-", "FOOT-L1-"], 75)]
    for tag, view, section, only, swing in renders:
        png = f"{out}/{version}_{tag}.png"
        r = fc.run(RENDER % dict(d=json.dumps(dict(doc=doc, view=view, swing=swing, section=section, only=only, png=png, w=1600, h=1000))),
                   f"render {tag}")
        if only:
            assert r["shown"] == sum(1 for n in want if any(n.startswith(p) for p in only)) > 0, r
        print(f"  render: {png}")
    s = fc.run(SAVE % dict(d=json.dumps(dict(doc=doc, fcstd=f"{out}/tote_bench_{version}.FCStd"))), "save")
    print(f"  saved {s['saved']}")


if __name__ == "__main__":
    import sys
    vs = sys.argv[1:] or list(ACTIVE_VERSIONS)
    for k, v in enumerate(vs):
        main(v, detail=(v == "desk"))
