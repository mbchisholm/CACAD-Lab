"""Print a `Board(...)` block for cacad/registries/boards.py from an Eagle .brd.

    .venv/bin/python tools/board_from_eagle.py path/to/board.brd NAME "source url or note"

Reads: the outline (layer 20 Dimension wires), every drilled hole >= 1.5 mm
(plain <hole>, package <hole>, package <pad> — so MOUNTINGHOLE_* packages are
found however the library drew them), and for each hole the distance to the
nearest component copper (smd/pad) on the top and the bottom side and to the
nearest through-hole pin centre: the head radius is bounded by the top copper,
the boss radius by the pin centre minus a solder fillet (pin tails are the
obstruction under a board). Traces are not considered. Coordinates
come out relative to the outline centre, +Y up, as boards.py expects.
Board thickness is not in an Eagle file: caliper it.
"""
from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MIN_DRILL = 1.5   # smaller drills are vias / component leads, not mounting holes
CONNECTOR_PACKAGES = {                                  # package-name regex -> cacad.registries.connectors key
    r"JST_SH(\d+).*": "JST_SH{0}",
    r"JSTPH(\d+).*": "JST_PH{0}",
    r"USB_C.*": "USB_C",
}
EDGE_ZONE = 4.0   # a multi-pad package this close to the outline is listed as a possible connector


@dataclass
class Hole:
    x: float
    y: float
    drill: float
    element: str
    plated: bool


def _rot(el):
    """Eagle rot attribute -> (mirror, angle_deg)."""
    r = el.get("rot", "R0")
    return r.startswith("M"), float(r.lstrip("MR") or 0)


def _place(ex, ey, mirror, ang, x, y):
    if mirror:
        x = -x
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return ex + x * c - y * s, ey + x * s + y * c


def parse(path: Path):
    board = ET.parse(path).getroot().find(".//board")
    plain = board.find("plain")

    pts = []
    for w in plain.findall("wire"):
        if w.get("layer") == "20":
            pts += [(float(w.get("x1")), float(w.get("y1"))), (float(w.get("x2")), float(w.get("y2")))]
    assert pts, "no layer-20 (Dimension) wires: outline not found"
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    outline = (min(xs), min(ys), max(xs), max(ys))

    pkgs = {(lib.get("name"), p.get("name")): p
            for lib in board.findall("libraries/library") for p in lib.findall("packages/package")}

    holes, copper, conns = [], [], []   # copper: (x, y, side, r_equiv); conns: (name, x, y, kind)
    for h in plain.findall("hole"):
        holes.append(Hole(float(h.get("x")), float(h.get("y")), float(h.get("drill")), "plain", False))
    for el in board.findall("elements/element"):
        pkg = pkgs[(el.get("library"), el.get("package"))]
        ex, ey = float(el.get("x")), float(el.get("y"))
        mirror, ang = _rot(el)
        name = f"{el.get('name')}:{el.get('package')}"
        for pat, kind in CONNECTOR_PACKAGES.items():
            m = re.fullmatch(pat, el.get("package"))
            if m:
                conns.append((name, ex, ey, kind.format(*m.groups()), pkg, mirror, ang))
        for h in pkg.findall("hole"):
            x, y = _place(ex, ey, mirror, ang, float(h.get("x")), float(h.get("y")))
            holes.append(Hole(x, y, float(h.get("drill")), name, False))
        for p in pkg.findall("pad"):
            x, y = _place(ex, ey, mirror, ang, float(p.get("x")), float(p.get("y")))
            drill = float(p.get("drill"))
            if drill >= MIN_DRILL:
                holes.append(Hole(x, y, drill, name, True))
            else:  # a through-hole lead: copper on both sides, and a pin tail below
                r = float(p.get("diameter", drill + 0.5)) / 2
                copper += [(x, y, "top", r), (x, y, "bottom", r), (x, y, "pin", 0.0)]
        for s in pkg.findall("smd"):
            x, y = _place(ex, ey, mirror, ang, float(s.get("x")), float(s.get("y")))
            side = "bottom" if (s.get("layer") == "16") != mirror else "top"
            r = math.hypot(float(s.get("dx")), float(s.get("dy"))) / 2
            copper.append((x, y, side, r))
    holes = [h for h in holes if h.drill >= MIN_DRILL]
    # multi-pad packages near an edge that matched no connector pattern: candidates to look at
    unknown = []
    for el in board.findall("elements/element"):
        pkg = pkgs[(el.get("library"), el.get("package"))]
        npads = len(pkg.findall("pad")) + len(pkg.findall("smd"))
        ex, ey = float(el.get("x")), float(el.get("y"))
        edge = min(ex - outline[0], outline[2] - ex, ey - outline[1], outline[3] - ey)
        if npads >= 2 and edge < EDGE_ZONE and "MOUNT" not in el.get("package").upper() \
                and not any(re.fullmatch(pat, el.get("package")) for pat in CONNECTOR_PACKAGES):
            unknown.append((el.get("name"), el.get("package"), ex, ey, edge))
    return outline, holes, copper, conns, unknown


def facing(pkg, mirror, ang, x, y, outline):
    """Outward direction of a connector's mouth. JST-style footprints (two
    large mechanical pads beside a row of smaller signal pads) give it from
    geometry: the mouth is on the mechanical-pad side. Anything else is
    snapped to the nearest outline edge, which is wrong for a mid-board
    connector; the printout says which rule was used."""
    smds = sorted(((float(s.get("x")), float(s.get("y")), float(s.get("dx")) * float(s.get("dy"))) for s in pkg.findall("smd")),
                  key=lambda t: t[2])
    if len(smds) >= 4 and smds[-1][2] > 1.5 * smds[-3][2] and abs(smds[-1][2] - smds[-2][2]) < 1e-6:
        small, big = smds[:-2], smds[-2:]
        vx = sum(p[0] for p in big) / 2 - sum(p[0] for p in small) / len(small)
        vy = sum(p[1] for p in big) / 2 - sum(p[1] for p in small) / len(small)
        if mirror:
            vx = -vx
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        wx, wy = vx * c - vy * s, vx * s + vy * c
        return ((1 if wx > 0 else -1, 0) if abs(wx) >= abs(wy) else (0, 1 if wy > 0 else -1)), "pad geometry"
    d = {(-1, 0): x - outline[0], (1, 0): outline[2] - x, (0, -1): y - outline[1], (0, 1): outline[3] - y}
    return min(d, key=d.get), "nearest edge"


def nearest_copper(h: Hole, copper, side) -> float | None:
    ds = [math.hypot(h.x - x, h.y - y) - r for x, y, s, r in copper if s == side and math.hypot(h.x - x, h.y - y) > h.drill]
    return min(ds) if ds else None


def main(path: str, name: str, source: str):
    outline, holes, copper, conns, unknown = parse(Path(path))
    cx, cy = (outline[0] + outline[2]) / 2, (outline[1] + outline[3]) / 2
    sx, sy = outline[2] - outline[0], outline[3] - outline[1]
    drills = sorted({h.drill for h in holes})
    print(f"# {name}: outline {sx:.3f} x {sy:.3f} mm ({sx / 25.4:.3f} x {sy / 25.4:.3f} in), {len(holes)} holes, drill {drills}")
    print("# hole   rel-centre (x, y)        drill  plated  nearest copper top / bottom / pin centre  [package]")
    for h in sorted(holes, key=lambda h: (h.y, h.x)):
        top, bot, pin = (nearest_copper(h, copper, side) for side in ("top", "bottom", "pin"))
        fmt = lambda v: f"{v:5.2f}" if v is not None else "  -  "
        print(f"#        ({h.x - cx:7.3f}, {h.y - cy:7.3f})   {h.drill:.2f}   {str(h.plated):5s}   {fmt(top)} / {fmt(bot)} / {fmt(pin)}   [{h.element}]")
    if len(drills) != 1:
        print("# WARNING: mixed drill sizes; hole_dia below is the smallest. Check which are mounting holes.")
    for el_name, pkg, x, y, edge in unknown:
        print(f"# edge package with no connector rule: {el_name} {pkg} at ({x - cx:.2f}, {y - cy:.2f}), {edge:.2f} from the edge")
    print()
    print(f"{name} = Board(")
    print(f'    name="{name}",')
    print(f"    size=({sx:.3f}, {sy:.3f}),")
    print("    holes=(" + ", ".join(f"({h.x - cx:.3f}, {h.y - cy:.3f})" for h in sorted(holes, key=lambda h: (h.y, h.x))) + "),")
    print(f"    hole_dia={min(drills):.2f},   # Eagle drill; a plated hole finishes smaller than the drill")
    print(f'    source="{source}; {Path(path).name} parsed by tools/board_from_eagle.py, {date.today().isoformat()}",')
    print("    thickness=None,   # not in an Eagle file: caliper")
    pins = [nearest_copper(h, copper, "pin") for h in holes]
    tops = [nearest_copper(h, copper, "top") for h in holes]
    fmt = lambda vs: f"{min(v for v in vs if v is not None):.2f}" if any(v is not None for v in vs) else "None"
    print(f"    nearest_pin={fmt(pins)},")
    print(f"    nearest_top_copper={fmt(tops)},")
    if conns:
        print("    connectors=(")
        for name, x, y, kind, pkg, mirror, ang in conns:
            (fx, fy), how = facing(pkg, mirror, ang, x, y, outline)
            print(f'        Connector({x - cx:.2f}, {y - cy:.2f}, ({fx}, {fy}), "{kind}"),   # {name}, facing by {how}')
        print("    ),")
    print(")")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
