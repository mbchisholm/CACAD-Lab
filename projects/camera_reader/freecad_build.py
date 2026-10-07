# Runs inside FreeCAD (GUI over RPC, or freecadcmd). Set MANIFEST to out/freecad_manifest.json first.
# Builds an Assembly (FreeCAD >= 1.0 Assembly workbench) of placed parts, stand grounded; falls back to App::Part
# groups. STEP flows into FreeCAD, never back: regenerate with the .py files, not here.
import json

import FreeCAD as App
import Mesh
import Part

m = json.load(open(MANIFEST))  # noqa: F821  (set by the caller)
if m["doc"] in App.listDocuments():
    App.closeDocument(m["doc"])
doc = App.newDocument(m["doc"])
try:
    asm = doc.addObject("Assembly::AssemblyObject", "Assembly")
    kind = "Assembly"
except Exception:
    asm = doc.addObject("App::Part", "Assembly")
    kind = "App::Part"
groups = {}
made = []
for r in m["parts"]:
    if r["file"].lower().endswith(".stl"):
        mesh = Mesh.Mesh(r["file"])
        shp = Part.Shape()
        shp.makeShapeFromMesh(mesh.Topology, 0.05)
        shp = Part.makeSolid(shp).removeSplitter() if shp.isClosed() else shp
    else:
        shp = Part.read(r["file"])
    obj = doc.addObject("Part::Feature", r["name"])
    obj.Shape = shp
    mat = App.Matrix(*[v for row in r["placement"] for v in row])
    obj.Placement = App.Placement(mat)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = tuple(r["color"])
        if r["name"].startswith(("cuvette", "lid")):
            obj.ViewObject.Transparency = 60
    if r["group"] not in groups:
        g = doc.addObject("App::DocumentObjectGroup", r["group"]) if kind == "App::Part" else None
        groups[r["group"]] = g
    asm.addObject(obj)
    made.append(obj)
grounded = None
if kind == "Assembly":
    try:
        import JointObject
        jg = asm.newObject("Assembly::JointGroup", "Joints")
        g = jg.newObject("App::FeaturePython", "GroundedJoint")
        JointObject.GroundedJoint(g, made[0])
        grounded = made[0].Name
    except Exception as e:
        grounded = f"not grounded: {e}"
doc.recompute()
bb = asm.Shape.BoundBox if hasattr(asm, "Shape") and not asm.Shape.isNull() else None
doc.saveAs(m["save"])
print("JSON:" + json.dumps(dict(kind=kind, parts=[o.Name for o in made], grounded=grounded, saved=m["save"],
                                bbox=[round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]
                                if bb else None)))
