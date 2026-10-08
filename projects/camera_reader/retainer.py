"""LED retainer: a plate behind the cell box's back wall whose seven tubular
nubs clamp the LED flanges against the wall (led_preload), leads through the
nub bores. Two M3 screws into heat-set inserts in the box's pads. Prints on
its back face, nubs up.

    .venv/bin/python projects/camera_reader/retainer.py
"""
from __future__ import annotations

from build123d import Part

from projects.camera_reader.geom import box, cyl_y
from projects.camera_reader.params import PARTS, derive


def build_retainer(size: str = "V0") -> Part:
    d = derive(size)
    r = d["retainer"]
    ya, yb = r["y"]
    part = box(*r["x"], ya, yb, *r["z"])
    nub_od = PARTS["led"]["flange_d"] + 0.8
    for x, z in d["leds"]:
        part += cyl_y(nub_od, x, z, ya - r["nub_h"], ya)
        part -= cyl_y(d["lead_hole"], x, z, ya - r["nub_h"] - 1, yb + 1)
    for sx, sz in r["screws"]:
        part -= cyl_y(d["m3_bore"], sx, sz, ya - 1, yb + 1)
    return part


if __name__ == "__main__":
    from cacad import export
    p = build_retainer()
    assert p.is_valid and len(p.solids()) == 1
    print("retainer", [round(v, 2) for v in p.bounding_box().size])
    export(p, "retainer", __file__.rsplit("/", 1)[0] + "/out")
