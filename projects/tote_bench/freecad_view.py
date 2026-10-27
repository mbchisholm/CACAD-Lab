"""The exported bench as a FreeCAD assembly, for viewing: one Assembly with a
part per board (2x4, 2x2, plywood shelf and hutch shelf, pegboard), brace and
the notched plywood top, LEG-FL grounded, parts coloured by kind, the tote
envelopes as translucent parts, the screws as shank envelopes, an exploded
view from params, and a BOM spreadsheet from params.derive. Nothing is placed or jointed by hand; the STEP carries every
position and bench.py checks them.

Before building, every imported part's world bounding box is compared with
params (F11: a STEP leaf can come in with its offset on a wrapper), and one
deliberately shifted expectation must disagree, so agreement is not vacuous.
Boards compare as (min corner, size); braces as their polygon's extents plus
[lo, lo + thickness] on their axis; the top as lo / size (the back-leg notches
do not change its box).

Needs FreeCAD open with the MCP Addon's RPC server started, and bench.py run first.

    .venv/bin/python projects/tote_bench/freecad_view.py
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.tote_bench.params import LUMBER, SCREW, derive, tape

COLOURS = dict(x2x4=(0.55, 0.36, 0.20), x2x2=(0.80, 0.60, 0.38), plywood=(0.90, 0.78, 0.55),
               pegboard=(0.42, 0.30, 0.20), tote=(0.35, 0.55, 0.80))   # display only
GROUND = "LEG-FL"
# Parts the exploded view leaves in place: the frame across the bay. params' moves lift the top, the shelf + lip and
# the hutch group, and move the legs + side rails out to either side.
REFERENCE = frozenset(("APRON-F", "APRON-B", "SHELF-RAIL-F", "SHELF-RAIL-B", "STRETCHER-B", "JOIST-TOP", "JOIST-SHELF"))
SHEETS = dict(plywood="23/32 plywood", pegboard="1/4 pegboard")   # BOM labels for the sheet kinds

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
asm.Label = D["doc"]
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

TOTES = r'''
import FreeCAD as App, Part, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
grp = doc.addObject("App::DocumentObjectGroup", "Totes")
grp.Label = "Totes (check envelopes)"
out = {}
for label, (size, lo) in D["totes"].items():
    f = doc.addObject("Part::Feature", label.replace("-", "_"))
    f.Label = label
    f.Shape = Part.makeBox(*size, App.Vector(*lo))
    grp.addObject(f)
    if App.GuiUp:
        f.ViewObject.ShapeColor = tuple(D["colour"])
        f.ViewObject.Transparency = 70
    bb = f.Shape.BoundBox
    out[label] = [bb.XMin, bb.YMin, bb.ZMin, bb.XLength, bb.YLength, bb.ZLength]
doc.recompute()
print("JSON:" + json.dumps(dict(totes=out)))
'''

SCREWS = r'''
import FreeCAD as App, Part, json
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
grp = doc.addObject("App::DocumentObjectGroup", "Screws")
grp.Label = "Screws (shank envelopes)"
vol = 0.0
for name, head, u, ln in D["screws"]:
    f = doc.addObject("Part::Feature", "screw")
    f.Label = name
    f.Shape = Part.makeCylinder(D["r"], ln, App.Vector(*head), App.Vector(*u))
    grp.addObject(f)
    if App.GuiUp:
        f.ViewObject.ShapeColor = (0.45, 0.45, 0.48)
    vol += f.Shape.Volume
doc.recompute()
print("JSON:" + json.dumps(dict(n=len(grp.Group), volume=vol)))
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
def touch(a, b, tol=0.5):   # bounding boxes within tol on every axis: only these pairs can share volume
    return (a.XMin <= b.XMax + tol and b.XMin <= a.XMax + tol and a.YMin <= b.YMax + tol and b.YMin <= a.YMax + tol
            and a.ZMin <= b.ZMax + tol and b.ZMin <= a.ZMax + tol)
labels = list(by_label)
shapes = {l: by_label[l].Shape for l in labels}
bbs = {l: sh.BoundBox for l, sh in shapes.items()}
overlap, worst, pairs = 0.0, None, 0
for i in range(len(labels)):
    for j in range(i + 1, len(labels)):
        a, b = labels[i], labels[j]
        if not touch(bbs[a], bbs[b]):
            continue
        pairs += 1
        v = shapes[a].common(shapes[b]).Volume
        if v > overlap:
            overlap, worst = v, [a, b]
view.Proxy.restoreAssembly(view)
after = mins()
doc.recompute()
print("JSON:" + json.dumps(dict(moves=len(view.Group), before=before, exploded=exploded, after=after, overlap=overlap,
                                worst=worst, pairs=pairs, of=len(labels) * (len(labels) - 1) // 2)))
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


def kinds(d: dict) -> dict[str, str]:
    """Part name -> colour kind, for every solid in the STEP: boards, prisms, then the top."""
    k = {n: kind for n, (kind, _, _) in d["boards"].items()}
    k.update({n: kind for n, (kind, *_) in d["prisms"].items()})
    k["TOP"] = "plywood"
    return k


def expected_bboxes(d: dict) -> dict[str, tuple]:
    """Part name -> (xmin, ymin, zmin, xlen, ylen, zlen) from params alone."""
    out = {n: (*lo, *size) for n, (_, size, lo) in d["boards"].items()}
    for n, (_, axis, lo, th, poly) in d["prisms"].items():
        us, zs = [p[0] for p in poly], [p[1] for p in poly]
        u0, z0, ul, zl = min(us), min(zs), max(us) - min(us), max(zs) - min(zs)
        out[n] = (lo, u0, z0, th, ul, zl) if axis == "x" else (u0, lo, z0, ul, th, zl)
    out["TOP"] = (*d["top"]["lo"], *d["top"]["size"])
    return out


def _poly_area(poly) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def expected_volume(d: dict) -> float:
    """Wood and plywood volume from params: boxes, prism area x thickness, the top less its notches."""
    v = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in d["boards"].values())
    v += sum(_poly_area(list(poly)) * th for _, _, _, th, poly in d["prisms"].values())
    tp = d["top"]
    (x0, y0, _), (sx, sy, sz) = tp["lo"], tp["size"]
    cut = 0.0
    for nx, ny, nsx, nsy in tp["notches"]:   # notch area inside the panel
        cut += max(0.0, min(nx + nsx, x0 + sx) - max(nx, x0)) * max(0.0, min(ny + nsy, y0 + sy) - max(ny, y0))
    return v + (sx * sy - cut) * sz


def check_positions(d: dict, got: dict, tol: float = 0.01) -> list[str]:
    """Compare FreeCAD's world bbox per part with params. Empty list = agree."""
    want_all = expected_bboxes(d)
    bad = []
    if set(got) != set(want_all):
        bad.append(f"parts differ: missing {sorted(set(want_all) - set(got))}, extra {sorted(set(got) - set(want_all))}")
    for name, want in want_all.items():
        if name not in got:
            continue
        g = got[name]
        if g[6] != 1 or any(abs(a - b) > tol for a, b in zip(g[:6], want)):
            bad.append(f"{name}: FreeCAD {[round(x, 2) for x in g[:6]]} ({g[6]} solids), params {[round(x, 2) for x in want]}")
    return bad


def check_exploded(d: dict, ex: dict, tol: float = 0.01):
    """Exploded = assembled + params' offset per part; restored = assembled; the moves really moved the parts."""
    assert ex["moves"] == len(d["explode_moves"]), ex["moves"]
    want_all = expected_bboxes(d)
    assert set(d["explode_offset"]) == set(want_all), "explode_offset does not cover every part"
    for name, bb in want_all.items():
        lo = bb[:3]
        off = d["explode_offset"][name]
        want = [lo[a] + off[a] for a in range(3)]
        for key, exp in (("before", lo), ("exploded", want), ("after", lo)):
            got = ex[key][name]
            assert all(abs(g - e) < tol for g, e in zip(got, exp)), f"{name} {key}: FreeCAD {got}, params {exp}"
        moved = any(abs(o) > tol for o in off)
        assert moved == (name not in REFERENCE), f"{name}: moved {moved}"   # the aprons, shelf rails, stretcher, joists stay
    assert ex["overlap"] < 1e-3, f"exploded parts {ex.get('worst')} overlap by {ex['overlap']:.3f} mm^3"


def _sides(size) -> tuple[float, float]:
    """A sheet part's two faces' sides, in params' axis order: its size without the thickness (the smallest)."""
    k = size.index(min(size))
    return tuple(v for i, v in enumerate(size) if i != k)


def bom_rows(d: dict) -> list[list]:
    """Cut list (every part, its kind and cut size), then the shopping list."""
    label = lambda kind: LUMBER[kind]["label"] if kind in LUMBER else SHEETS[kind]
    rows = [["Part", "Kind", "Cut", "Cut mm", "Note"]]
    for n, (kind, size, _) in d["boards"].items():
        if kind in SHEETS:
            a, b = _sides(size)
            note = "from the 4 x 8 ft sheet" if kind == "plywood" else "from the 2 x 4 ft panel"
            rows.append([n, label(kind), f"{tape(a)} x {tape(b)}", f"{a:.1f} x {b:.1f}", note])
        else:
            rows.append([n, label(kind), tape(max(size)), round(max(size), 1), "square ends"])
    L = d["brace_long_point"]
    for n, (kind, *_) in d["prisms"].items():
        rows.append([n, label(kind), tape(L), round(L, 1), f"recut to a {tape(L)} long point, 45° both ends"])
    tp = d["top"]
    sx, sy, _ = tp["size"]
    nsx, nsy = tp["notches"][0][2:]          # params cuts every notch the same size
    rows.append(["TOP", label("plywood"), f"{tape(sx)} x {tape(sy)}", f"{sx:.1f} x {sy:.1f}",
                 f"from the 4 x 8 ft sheet; notched {tape(nsx)} x {tape(nsy)} at the {len(tp['notches'])} back legs"])
    rows += [[], ["Buy", "Qty", "Note", "", ""]]
    for item, n, note in d["shopping"]:
        rows.append([item, n, note, "", ""])
    return rows


def main():
    d = derive()
    here = __file__.rsplit("/", 1)[0]
    step, fcstd = f"{here}/out/tote_bench.step", f"{here}/out/tote_bench.FCStd"
    doc = "tote_bench"
    fc = FreeCADRPC()

    imp = fc.run(IMPORT % dict(doc=doc, step=step), "import")
    bad = check_positions(d, imp["parts"])
    if bad:
        raise AssertionError(f"FreeCAD positions disagree with params (root placement identity: {imp['root_identity']}):\n  "
                             + "\n  ".join(bad))
    # control: a 1 mm shift in one expectation must be caught
    name = next(iter(d["boards"]))
    kind, size, lo = d["boards"][name]
    shifted = dict(d, boards=dict(d["boards"], **{name: (kind, size, (lo[0] + 1.0, lo[1], lo[2]))}))
    assert check_positions(shifted, imp["parts"]), "control: a 1 mm shift was not detected; the position check is vacuous"
    print(f"  positions: {len(imp['parts'])} parts agree with params to 0.01 mm; shifted control disagrees")

    k = kinds(d)
    asm = fc.run(ASSEMBLE % dict(d=json.dumps(dict(doc=doc, kinds=k, colours=COLOURS, ground=GROUND))), "assemble")
    assert asm["parts"] == len(k), asm
    assert asm["labels"] == sorted(k), f"FreeCAD relabelled parts: {asm['labels']}"
    assert asm["grounded"] == [GROUND], f"grounded {asm['grounded']}, expected [{GROUND}]"
    vol = expected_volume(d)
    assert abs(asm["volume"] - vol) < 1e-3 * vol, f"assembly volume {asm['volume']:.0f} vs params {vol:.0f}"
    print(f"  assembly: {asm['parts']} parts, grounded {asm['grounded'][0]}, wood + ply {asm['volume'] / 1e6:.2f} L")

    t = fc.run(TOTES % dict(d=json.dumps(dict(doc=doc, totes=d["totes"], colour=COLOURS["tote"]))), "totes")
    for tn, (size, lo) in d["totes"].items():
        assert all(abs(a - b) < 0.01 for a, b in zip(t["totes"][tn], (*lo, *size))), f"{tn}: FreeCAD {t['totes'][tn]}"
    print(f"  totes: {len(t['totes'])} translucent envelopes at params' positions")

    sc = [(sn, head, u, ln) for sn, _, _, head, u, ln, _ in d["screws"]]
    r = SCREW["d"][0] / 2
    scr = fc.run(SCREWS % dict(d=json.dumps(dict(doc=doc, screws=sc, r=r))), "screws")
    want = sum(3.14159265 * r * r * ln for _, _, _, ln in sc)
    assert scr["n"] == len(sc) and abs(scr["volume"] - want) < 1e-3 * want, f"screws {scr}, params {len(sc)} / {want:.0f}"
    print(f"  screws: {scr['n']} shank envelopes at params' heads")

    ex = fc.run(EXPLODE % dict(d=json.dumps(dict(doc=doc, moves=d["explode_moves"]))), "exploded view")
    check_exploded(d, ex)
    print(f"  exploded view: {ex['moves']} moves; every part lands on params' offset, none overlap "
          f"(max {ex['overlap']:.3g} mm^3 over the {ex['pairs']} of {ex['of']} pairs whose boxes touch), "
          f"and all return to the assembled position")

    b = fc.run(BOM % dict(d=json.dumps(dict(doc=doc, rows=bom_rows(d), fcstd=fcstd))), "bom")
    print(f"  BOM: {b['rows']} rows; saved {b['saved']}")


if __name__ == "__main__":
    main()
