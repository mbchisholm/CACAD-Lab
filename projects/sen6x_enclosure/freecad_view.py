"""The exported enclosure in FreeCAD, for viewing and as a cross-check: base, lid (translucent), the Sensirion STEP
the GHR plug and its six wires (coloured by pin), each a Part::Feature from its STEP, one document. Nothing is placed by hand: the STEPs carry every
position. Before building the view, each part's FreeCAD bounding box (optimalBoundingBox, F26) is compared with the
envelope params.derive() states, so the view shows what params says.

Needs FreeCAD open with the MCP Addon's RPC server started, and enclosure.py run first (out/*.step).

    .venv/bin/python projects/sen6x_enclosure/freecad_view.py [--explode]

--explode lifts each part straight up after the cross-check, so the check still runs on the assembled positions.
"""
from __future__ import annotations

import json

from cacad.freecad import FreeCADRPC
from projects.sen6x_enclosure.params import derive, spec

OUT = __file__.rsplit("/", 1)[0] + "/out"
DOC = "SEN6x_enclosure"
PARTS = dict(   # label -> (step, colour, transparency): display only
    base=("sen6x_base", (0.91, 0.53, 0.23), 0),
    lid=("sen6x_lid", (0.95, 0.70, 0.48), 55),
    sensor=("sen6x_sensor_placed", (0.20, 0.20, 0.22), 0),
    plug=("sen6x_plug_placed", (0.95, 0.95, 0.90), 0),
    screws=("sen6x_screws_placed", (0.60, 0.62, 0.66), 0),
)
# one wire per pin, labelled "wire1_VDD" ...; display colours by function, not Sensirion's cable colours
PIN_COLOURS = {"VDD": (0.85, 0.10, 0.10), "GND": (0.08, 0.08, 0.08), "SDA": (0.15, 0.40, 0.90), "SCL": (0.95, 0.80, 0.10),
               "GND/NC": (0.35, 0.35, 0.35), "VDD/NC": (0.55, 0.20, 0.20)}
for _i, _pin in enumerate(spec("pins")):
    _n, _name = _pin.split(" ", 1)
    PARTS[f"wire{_n}_{_name.replace('/', '_')}"] = (f"sen6x_wire{_i + 1}_placed", PIN_COLOURS[_name], 0)

NEW_DOC = r'''
import FreeCAD as App, json
if %(doc)r in App.listDocuments():
    App.closeDocument(%(doc)r)
App.newDocument(%(doc)r)
print("JSON:" + json.dumps(dict(ok=True)))
'''

ADD = r'''
import FreeCAD as App, Part, json
doc = App.getDocument(%(doc)r)
sh = Part.read(%(step)r)
f = doc.addObject("Part::Feature", %(label)r)
f.Shape = sh
if App.GuiUp:
    f.ViewObject.ShapeColor = tuple(%(colour)r)
    f.ViewObject.Transparency = %(transparency)d
doc.recompute()
bb = sh.optimalBoundingBox(False, False)
print("JSON:" + json.dumps(dict(bbox=[bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax], solids=len(sh.Solids),
                                volume=sh.Volume, valid=sh.isValid())))
'''

FIT = r'''
import FreeCADGui as Gui, json
Gui.getDocument(%(doc)r).activeView().viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(dict(ok=True)))
'''


EXPLODE = r'''
import FreeCAD as App, FreeCADGui as Gui, json
doc = App.getDocument(%(doc)r)
lift = json.loads(%(lift)r)
for label, dz in lift.items():
    o = doc.getObjectsByLabel(label)[0]
    o.Placement.Base = App.Vector(0, 0, dz)
doc.recompute()
Gui.getDocument(%(doc)r).activeView().viewIsometric()
Gui.SendMsgToActiveView("ViewFit")
print("JSON:" + json.dumps(lift))
'''


def explode_lifts(gap: float = 10.0) -> dict:
    """Display only: z lift per part so each clears the one below by `gap` mm. Heights from params."""
    d = derive()
    sensor = d["z_lid"] - d["z_floor"] - d["plug_bottom_z"] + gap   # plug end clears the base rim
    lid = sensor + d["z_floor"] + d["sensor_h"] - d["z_lid"] + gap  # lid clears the lifted sensor top
    screws = lid + d["z_top"] - d["screw_tip_z"] + gap              # screw tips clear the lifted lid
    return dict(base=0.0, sensor=sensor, plug=sensor, lid=lid, screws=screws,
                **{k: sensor for k in PARTS if k.startswith("wire")})   # the cable stays on the plug


def expected() -> dict:
    """Envelope per part from params: (xmin, ymin, zmin, xmax, ymax, zmax)."""
    d = derive()
    L, W = d["outer_l"] / 2, d["outer_w"] / 2
    sx, sy, pz = d["socket_x"], d["socket_y"], d["z_floor"] + d["plug_bottom_z"]
    r, sy = d["wire_od"] / 2, d["socket_y"]
    wires = {k: (x - r, d["wire_y_end"], d["wire_zc"] - r, x + r, sy + r, d["wire_z0"])
             for k, x in zip([k for k in PARTS if k.startswith("wire")], d["wire_x"])}
    return dict(
        **wires,
        base=(-L, -W, 0.0, L, W, d["z_lid"]),
        lid=(-L, -W, d["z_lid"], L, W, d["z_top"]),
        sensor=(-d["sensor_l"] / 2, -d["sensor_w"] / 2, d["z_floor"], d["sensor_l"] / 2, d["sensor_w"] / 2, d["z_floor"] + d["sensor_h"]),
        plug=(sx - d["plug_w"] / 2, sy - d["plug_t"] / 2, pz, sx + d["plug_w"] / 2, sy + d["plug_t"] / 2, pz + d["plug_len"]),
    )


def main(tol: float = 0.05, explode: bool = False):
    fc = FreeCADRPC()
    print("FreeCAD", fc.version())
    fc.run(NEW_DOC % dict(doc=DOC), "new document")
    exp, bad = expected(), []
    for label, (step, colour, tr) in PARTS.items():
        got = fc.run(ADD % dict(doc=DOC, step=f"{OUT}/{step}.step", label=label, colour=colour, transparency=tr), label)
        if not got["valid"]:
            bad.append(f"{label}: invalid shape in FreeCAD")
        if label in exp:
            diff = max(abs(a - b) for a, b in zip(got["bbox"], exp[label]))
            print(f"  {label}: {got['solids']} solid(s), {got['volume']:.0f} mm3, bbox off params by {diff:.3f}")
            if diff > tol:
                bad.append(f"{label}: bbox {[round(v, 3) for v in got['bbox']]} vs params {[round(v, 3) for v in exp[label]]}")
    fc.run(FIT % dict(doc=DOC), "view")
    if bad:
        raise SystemExit("FreeCAD cross-check FAILED:\n  " + "\n  ".join(bad))
    print("cross-check ok")
    if explode:
        lift = fc.run(EXPLODE % dict(doc=DOC, lift=json.dumps(explode_lifts())), "explode")
        print("  exploded: " + ", ".join(f"{k} +{v:.1f}" for k, v in lift.items()))


if __name__ == "__main__":
    import sys
    main(explode="--explode" in sys.argv[1:])
