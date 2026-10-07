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
    obj.Label = r.get("label", r["name"])
    mat = App.Matrix(*[v for row in r["placement"] for v in row])
    obj.Placement = App.Placement(mat)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = tuple(r["color"])
        obj.ViewObject.Transparency = r.get("transparency", 0)
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

# --- reading aids: light paths, part labels, exploded view. Display only; nothing here feeds back to geometry. ---
guides = doc.addObject("App::DocumentObjectGroup", "Guides")
guides.Label = "Guides (light paths, labels)"
COL = dict(ref=(0.2, 0.6, 1.0), c50=(1.0, 0.15, 0.15), c10=(0.1, 0.8, 0.3))
NAMES = dict(ref="Light path: REF window", c50="Light path: 50 mm cell (on axis)", c10="Light path: 10 mm cell")
G = m.get("guides")
if G:
    for key, (a, b) in list(G["paths"].items()) + [("axis", G["axis"])]:
        ln = doc.addObject("Part::Feature", "Path_" + key)
        ln.Shape = Part.makeLine(App.Vector(*a), App.Vector(*b))
        ln.Label = NAMES.get(key, "Optical axis: datum wall to LEDs")
        guides.addObject(ln)
        if App.GuiUp:
            ln.ViewObject.LineColor = COL.get(key, (1.0, 0.75, 0.0))
            ln.ViewObject.LineWidth = 4
    # one label per stage of the light path, out to the camera's right with a leader; parts inside the box are named
    # in the tree and seen in the exploded view (labels do not follow the explode)
    labels = doc.addObject("App::DocumentObjectGroup", "Labels")
    guides.addObject(labels)
    x_text = max(o.Shape.BoundBox.XMax for o in made) + 25
    for name, text, drop in G["labels"]:
        o = doc.getObject(name)
        c = o.Shape.BoundBox.Center
        a = doc.addObject("App::Annotation", "Label_" + name)
        a.LabelText = [text]
        a.Position = App.Vector(x_text, c.y, c.z - drop)
        lead = doc.addObject("Part::Feature", "Leader_" + name)
        lead.Shape = Part.makeLine(c, App.Vector(x_text - 3, c.y, c.z - drop))
        for x in (a, lead):
            labels.addObject(x)
        if App.GuiUp:
            a.ViewObject.FontSize = 15
            a.ViewObject.TextColor = (0.1, 0.1, 0.1)
            lead.ViewObject.LineColor = (0.45, 0.45, 0.45)
            lead.ViewObject.LineWidth = 1
exploded = None
if kind == "Assembly" and m.get("explode"):
    import CommandCreateView, UtilsAssembly
    by = {o.Name: o for o in made}
    view = UtilsAssembly.getViewGroup(asm).newObject("App::FeaturePython", "ExplodedView")
    view.Label = "Exploded view"
    CommandCreateView.ExplodedView(view)
    if App.GuiUp:
        CommandCreateView.ViewProviderExplodedView(view.ViewObject)
    steps = []
    for label, names, vec in m["explode"]:
        st = asm.newObject("App::FeaturePython", "Move")
        st.Label = label
        CommandCreateView.ExplodedViewStep(st, 0)
        if App.GuiUp:
            CommandCreateView.ViewProviderExplodedViewStep(st.ViewObject)
            st.ViewObject.Visibility = False   # its trail lines otherwise show on the assembled model
        st.MovementTransform = App.Placement(App.Vector(*vec), App.Rotation())
        st.References = [asm, [by[n].Name + "." for n in names]]
        steps.append(st)
    view.Group = steps
    doc.recompute()
    # exploded, every part must stand clear of every other it moved relative to; then put it back
    pos = lambda: {o.Name: [round(v, 3) for v in (o.Shape.BoundBox.XMin, o.Shape.BoundBox.YMin, o.Shape.BoundBox.ZMin)] for o in made}
    before = pos()
    view.Proxy.saveAssemblyAndExplode(view)
    during = pos()
    moved = [o for o in made if during[o.Name] != before[o.Name]]
    clash = []
    for i, a in enumerate(made):
        for b in made[i + 1:]:
            if a not in moved and b not in moved:
                continue
            if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                continue
            v = a.Shape.common(b.Shape).Volume
            if v > 0.5:
                clash.append([a.Name, b.Name, round(v, 2)])
    view.Proxy.restoreAssembly(view)
    after = pos()
    doc.recompute()
    exploded = dict(steps=len(steps), moved=sorted(o.Name for o in moved), clash=clash, restored=after == before)
if App.GuiUp:
    import FreeCADGui as Gui
    v = Gui.getDocument(doc.Name).activeView()
    v.setCameraType("Perspective")
    v.viewIsometric()
    v.fitAll()
bb = asm.Shape.BoundBox if hasattr(asm, "Shape") and not asm.Shape.isNull() else None
doc.saveAs(m["save"])
print("JSON:" + json.dumps(dict(kind=kind, parts=[o.Name for o in made], grounded=grounded, saved=m["save"], exploded=exploded,
                                bbox=[round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]
                                if bb else None)))
