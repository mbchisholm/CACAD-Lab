"""build123d solids from the descriptions in params (shapes.py documents the primitives). No numbers live here.
Part files and table.py import this; the MCP sandbox accepts it (no os/pathlib/sys, F23)."""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, Cone, Cylinder, FontStyle, Location, Part, Plane, Polyline, Pos, Rectangle,
                       Text, extrude, loft, make_face, revolve)

from cacad import plumbing as P
from projects.nft_table import shapes as S

SINK = 0.02


def _plane(origin, z_dir, x_dir=None):
    z = P.unit(z_dir)
    x = P.unit(x_dir) if x_dir is not None else P.perp(z)
    return Plane(origin=tuple(origin), x_dir=x, z_dir=z)


def _poly_face(pts3):
    return make_face(Polyline(*pts3, close=True))


def prim_solid(p):
    k = p[0]
    if k == "raw":
        return prim_solid(p[1])
    if k == "box":
        lo, hi = p[1], p[2]
        return Box(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], align=(Align.MIN, Align.MIN, Align.MIN)).moved(Location(lo))
    if k == "cyl":
        _, c, a, L, r = p
        return Cylinder(r, L, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(_plane(c, a)))
    if k == "cone":
        _, c, a, L, r0, r1 = p
        return Cone(r0, r1, L, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(_plane(c, a)))
    if k == "prism":
        _, ax, poly, w0, w1 = p
        pts = [S._uvw_point(ax, u, v, w0) for u, v in poly]
        face = _poly_face(pts)
        return extrude(face, amount=w1 - w0, dir=S.AX[ax])
    if k == "ring":
        _, c, ax, w0, w1, ri, ro, a0, a1 = p
        iu, iv, iw = S.UVW[ax]
        pts = []
        for r, w in ((ri, w0), (ro, w0), (ro, w1), (ri, w1)):
            q = [0.0, 0.0, 0.0]
            q[iu], q[iv], q[iw] = c[iu] + r * math.cos(a0), c[iv] + r * math.sin(a0), w
            pts.append(tuple(q))
        axis_o = [0.0, 0.0, 0.0]
        axis_o[iu], axis_o[iv] = c[iu], c[iv]
        return revolve(_poly_face(pts), Axis(tuple(axis_o), S.AX[ax]), math.degrees(a1 - a0))
    if k == "hex":
        c, a, L, s = p[1], P.unit(p[2]), p[3], p[4]
        phase = p[5] if len(p) > 5 else 0.0
        e1 = P.perp(a)
        e2 = P.cross(a, e1)
        rc = s / math.sqrt(3)
        pts = [tuple(c[i] + rc * (math.cos(math.pi / 6 + j * math.pi / 3 + phase) * e1[i]
                                  + math.sin(math.pi / 6 + j * math.pi / 3 + phase) * e2[i]) for i in range(3)) for j in range(6)]
        return extrude(_poly_face(pts), amount=L, dir=a)
    if k == "rloft":
        (z0, cx0, cy0, L0, W0), (z1, cx1, cy1, L1, W1) = p[1], p[2]
        r0 = Plane.XY.offset(z0) * Pos(cx0, cy0) * Rectangle(L0, W0)
        r1 = Plane.XY.offset(z1) * Pos(cx1, cy1) * Rectangle(L1, W1)
        return loft([r0, r1])
    if k == "gland":
        # annulus about the x axis at height zc, between radii R and R + L about the z axis, x > 0
        _, (R, _, zc), L, ri, ro = p
        reach = R + L + 1.0
        tube = Cylinder(ro, reach, align=(Align.CENTER, Align.CENTER, Align.MIN)) - \
            Cylinder(ri, reach, align=(Align.CENTER, Align.CENTER, Align.MIN))
        tube = tube.moved(Location(Plane(origin=(0, 0, zc), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
        h = 2 * ro + 2.0
        shell = Cylinder(R + L, h, align=(Align.CENTER, Align.CENTER, Align.CENTER)) - \
            Cylinder(R, h, align=(Align.CENTER, Align.CENTER, Align.CENTER))
        return tube & shell.moved(Location((0, 0, zc)))
    raise ValueError(f"prim_solid: {k}")


def label_solid(lab):
    """Bold text embossed lab['t'] along the face normal, cap height about lab['h'] (font size h / 0.7). Its base is
    sunk SINK into the face so it fuses on a sloped face too (the sunk part is in its measured volume: < 1e-5)."""
    n, up = P.unit(lab["n"]), P.unit(lab["up"])
    x_dir = P.cross(up, n)
    pl = Plane(origin=P.add(lab["c"], n, -SINK), x_dir=x_dir, z_dir=n)
    txt = Text(lab["text"], font_size=lab["h"] / 0.7, font_style=FontStyle.BOLD, align=(Align.CENTER, Align.CENTER))
    return extrude(pl * txt, amount=lab["t"] + SINK, dir=n)


def _fuse(solids):
    out = solids[0]
    for s_ in solids[1:]:
        out = out + s_
    return out


def desc_solid(desc, filled=False, label=True):
    """Local-frame solid of a description: union of adds, minus subs (unless filled), plus the label."""
    out = _fuse([prim_solid(p) for p in desc["add"]])
    if not filled:
        for p in desc.get("sub", []):
            out = out - prim_solid(p)
    if label and desc.get("label"):
        out = out + label_solid(desc["label"])
    return out


def place(solid, pl):
    R, t = pl
    return solid.moved(Location(Plane(origin=tuple(t), x_dir=R[0], z_dir=R[2])))


def tee_solid(geom, filled=False):
    _, run, br, R, _, _ = geom
    run_o = _fuse([P.build_leg(lg, filled=True) for lg in run])
    br_o = _fuse([P.build_leg(lg, filled=True) for lg in br])
    solid = run_o + br_o
    if filled:
        return solid
    for lg in run + br:
        bore = dict(lg, sections=[(s0, s1, ri, 0.0) for s0, s1, ro, ri in lg["sections"]])
        solid = solid - P.build_leg(bore, filled=False)
    return solid


def build_expect(e, filled=False, label=True):
    """World solid for an expect entry."""
    g = e["geom"]
    if g[0] == "prims":
        return place(desc_solid(g[1], filled=filled, label=label), g[2])
    if g[0] in ("legs", "sweep"):
        return P.build_geom(e, filled=filled)
    if g[0] == "tee":
        return tee_solid(g, filled=filled)
    raise ValueError(f"build_expect: {g[0]}")


def label_volume(desc) -> float:
    lab = desc.get("label")
    return label_solid(lab).volume if lab else 0.0


def label_bbox(desc, pl):
    """World box of the placed label, or None."""
    lab = desc.get("label")
    if not lab:
        return None
    bb = place(label_solid(lab), pl).bounding_box()
    return tuple(bb.min), tuple(bb.max)
