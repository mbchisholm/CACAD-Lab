"""Assembly tutorial in FreeCAD: eight steps, each shows what is built so far, the new pieces slide in in orange.
Steps 1-5 are built UPSIDE DOWN on the garage floor, away from the wall: the frame lies flat on its edges, so
everything squares up against the floor and the legs just stand up out of it. Step 6 flips it over, 7 pushes
it back against the wall, 8 drops the plywood on. The back rail is the wall side.

Needs freecad_view.py run first (it builds the document), RPC server started. Does not save.

    .venv/bin/python projects/desk_bench/freecad_stages.py          # play all steps, 3 s hold each
    .venv/bin/python projects/desk_bench/freecad_stages.py 4        # stay on step 4
    .venv/bin/python projects/desk_bench/freecad_stages.py --list
"""
from __future__ import annotations

import json
import sys
import time

from cacad.freecad import FreeCADRPC
from projects.desk_bench.params import IN, validate

LEGS = ["LEG-FL", "LEG-FR", "LEG-BL", "LEG-BR"]
BRACES = ["BRACE-FL", "BRACE-FR", "BRACE-BL", "BRACE-BR"]
FRAME = ["RAIL-F", "RAIL-B", "END-L", "END-R"]
JOISTS = ["JOIST-1", "JOIST-2"]
FOOT = ["FOOT-L", "FOOT-R"]
# (title, new parts, flipped 0 = upside down 1 = upright, shift toward wall 0 = in the open 1 = at the wall)
STEPS = [
    ("1. Upside down on the floor: the two 72 in rails and two 31 in end rails on edge, tops down. Back rail toward the wall.", FRAME, 0, 0),
    ("2. Two 31 in joists between the rails, 22 in apart. Screw through the rails into the ends.", JOISTS, 0, 0),
    ("3. Legs in the four corners, standing up. Screw through the rail and the end rail.", LEGS, 0, 0),
    ("4. 45 deg braces beside each leg, long edge up under the rail.", BRACES, 0, 0),
    ("5. 2x2 foot rails between the legs at each end, 8 in up (from the floor once flipped).", FOOT, 0, 0),
    ("6. Two people: roll it over onto its legs.", [], "flip", 0),
    ("7. Slide it back against the wall.", [], 1, "push"),
    ("8. Plywood top, flush all round, screwed down into the rails and joists every 8 in.", ["TOP"], 1, 1),
]
BUILT = ["RAIL-F", "RAIL-B", "END-L", "END-R", "JOIST-1", "JOIST-2", *LEGS, *BRACES, *FOOT, "TOP"]
OLD, NEW = (0.55, 0.36, 0.20), (1.0, 0.45, 0.0)
PLY = (0.90, 0.78, 0.55)
FRAMES, FRAME_S, SLIDE = 8, 0.12, 300.0
BACK_OFF = -40 * IN          # build position: this far in front of the wall

APPLY = r'''
import FreeCAD as App, json
from FreeCAD import Vector, Rotation, Placement
D = json.loads(%(d)r)
doc = App.getDocument(D["doc"])
names = set(D["all"])
parts = {o.Label: o for o in doc.Objects if o.Label in names and hasattr(o, "Shape") and o.Shape.Solids}
root = None
for o in doc.Objects:
    if o.Label not in names and o.Label not in ("Floor", "Wall", "Step") and hasattr(o, "Placement") and any(p in o.OutListRecursive for p in parts.values()):
        root = o
        break
if not hasattr(App, "_desk_base"):
    App._desk_base = {k: Placement(v.Placement) for k, v in parts.items()}
    App._desk_root = Placement(root.Placement) if root else None
    # garage: floor and a wall behind the desk's final back
    for lab, size, lo in (("Floor", (D["fx"], D["fy"], 50.8), (D["fx0"], D["fy0"], -50.8)),
                          ("Wall", (D["fx"], 76.2, 1500), (D["fx0"], D["wall_y"], 0))):
        import Part
        f = doc.addObject("Part::Feature", lab)
        f.Label = lab
        f.Shape = Part.makeBox(*size, Vector(*lo))
        if App.GuiUp:
            f.ViewObject.ShapeColor = (0.78, 0.78, 0.80) if lab == "Floor" else (0.88, 0.86, 0.80)
            if lab == "Wall":
                f.ViewObject.Transparency = 35
c = Vector(0, D["D"] / 2, D["ztop"] / 2)
ang = D["angle"]
import math
lift = math.sin(math.radians(ang)) * D["lift"]
pl = Placement(Vector(0, D["shift"], lift), Rotation(Vector(1, 0, 0), ang), c)
if root is not None:
    root.Placement = pl.multiply(App._desk_root)
    rinv = root.Placement.Rotation.inverted()
else:
    rinv = Rotation()
off = rinv.multVec(Vector(*D["slide"]))
for lab, o in parts.items():
    vis = lab in D["visible"]
    o.Visibility = vis
    if App.GuiUp:
        o.ViewObject.Visibility = vis
    base = App._desk_base[lab]
    o.Placement = Placement(base.Base + (off if lab in D["new"] else Vector()), base.Rotation)
    if App.GuiUp and vis:
        o.ViewObject.ShapeColor = tuple(D["new_col"] if lab in D["new"] else (D["ply_col"] if lab == "TOP" else D["old_col"]))
if root is not None:
    for o in root.ElementList:
        root.setElementVisible(o.Name, o.Label in D["visible"])
if App.GuiUp:
    import FreeCADGui as Gui
    import textwrap
    lines = textwrap.wrap(D["title"], 28)
    ts = doc.getObjectsByLabel("Step")
    t = ts[0] if ts else None
    if t is None:
        try:
            import Draft
            t = Draft.make_text(lines, placement=Placement(Vector(D["fx0"] + 100, D["wall_y"] - 5, 1350), Rotation(Vector(1, 0, 0), 90)))
            t.Label = "Step"
            t.ViewObject.FontSize = 160
            t.ViewObject.TextColor = (0.1, 0.1, 0.1)
            t.ViewObject.LineSpacing = 1.2
        except Exception as e:
            print("no Draft text:", e)
    if t is not None:
        t.Text = lines
    if D.get("fit"):
        v = Gui.getDocument(doc.Name).activeView()
        v.viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
doc.recompute()
print("JSON:" + json.dumps(dict(visible=len(D["visible"]))))
'''


def main():
    d0 = validate()
    args = sys.argv[1:]
    if "--list" in args:
        for t, *_ in STEPS:
            print(t)
        return
    fc = FreeCADRPC()
    Dp, ztop = d0["D"], d0["leg"]
    fx0, fy0 = -20 * IN, -90 * IN
    base = dict(doc="desk_bench", all=BUILT, D=Dp, ztop=ztop, lift=8 * IN, fx0=fx0, fy0=fy0, fx=112 * IN, fy=-fy0 + Dp,
                wall_y=Dp, new_col=NEW, old_col=OLD, ply_col=PLY)

    def show(i, angle, shift, t, fit=False):
        title, new, _, _ = STEPS[i]
        vis = [p for _, ns, _, _ in STEPS[: i + 1] for p in ns]
        fc.run(APPLY % dict(d=json.dumps(dict(base, visible=vis, new=new, angle=angle, shift=shift, title=title, fit=fit,
                                              slide=(0, 0, SLIDE * t)))), "stage")

    def stage(i, hold):
        title, new, flip, push = STEPS[i]
        print(title)
        if flip == "flip":
            for k in range(FRAMES + 1):
                show(i, 180 - 180 * k / FRAMES, BACK_OFF, 0)
                time.sleep(FRAME_S)
        elif push == "push":
            for k in range(FRAMES + 1):
                show(i, 0, BACK_OFF * (1 - k / FRAMES), 0)
                time.sleep(FRAME_S)
        else:
            angle = 180 if i < 5 else 0
            shift = BACK_OFF if i < 6 else 0
            for k in range(FRAMES + 1):
                show(i, angle, shift, 1 - k / FRAMES, fit=(i == 0 and k == 0))
                time.sleep(FRAME_S)
        time.sleep(hold)

    nums = [int(a) for a in args if a.isdigit()]
    if nums:
        stage(nums[0] - 1, 0)
        return
    for i in range(len(STEPS)):
        stage(i, 3.0)


if __name__ == "__main__":
    main()
