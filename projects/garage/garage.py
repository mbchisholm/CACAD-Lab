"""The garage site as solids, for a build to check against and to render in:
slab, lip and wall along a stretch of the lip wall. Every number is from
params.derive.

    .venv/bin/python projects/garage/garage.py      # prints the site facts and exports a 2 m stretch
"""
from __future__ import annotations

from build123d import Align, Box, Location, Part

from projects.garage.params import derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def build_site(x0: float, x1: float, wall: str = "lip_wall") -> dict[str, Part]:
    """name -> solid along [x0, x1] of the wall, drawn DISPLAY margin past each end."""
    d = derive(x0, x1, wall)
    out = {}
    for name, (size, lo) in d["boxes"].items():
        b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
        b.label = name
        out[name] = b
    return out


if __name__ == "__main__":
    from build123d import Compound

    from cacad import export
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys (F23)
    site = build_site(0.0, 2000.0)
    for n, p in site.items():
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm at {tuple(round(v, 1) for v in bb.min)}")
    export(Compound(children=list(site.values())), "garage_lip_wall", OUT)
