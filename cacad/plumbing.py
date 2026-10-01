r"""Plumbing solids: analytic volume and bounding box from a part's description alone, and the build123d solid
built from the same description. No numbers live here: a project's params.py describes each part, its assembly
builds it with `build_geom`, and its checks compare the solid with `legs_expect` / `sweep_expect`. Promoted from
projects/nft_rack/legs.py (archive/nft_rack_v1).

A *leg* is a stepped hollow cylinder along a unit axis `o` from a point `c`: sections (s0, s1, ro, ri) in mm along
the axis. A straight part (pipe, cap, valve body, bushing, grommet) is one leg with t = 0 and s0 = 0 first. An
elbow is two legs leaving the corner `c` along o1 and o2, each cut by the bisector (mitre) plane through c; its
first section has s0 = None, meaning "from the mitre plane". In the leg's frame, w is the lateral coordinate
toward the other leg and the mitre plane is s = w t, t = tan of the angle between o and the plane normal. The two
legs share the mitre face, so the elbow's volume is the sum of its legs'. A real moulded elbow has a rounded
corner; the mitre is an envelope of it, exact in volume and box for what it draws.

    section volume = (s1 - s0) A - [F(s0) - F(s1)],   F(s) = integral over the annulus of (w t - s)+ dA

closed form below. The bbox is sampled on the outer boundary curves (end circles and mitre ellipse) at 2880
angles plus the exact angles where a section's circle meets the mitre plane: error < 2e-4 mm at r = 30.

A *sweep* is a circle (optionally annular) swept along an axis-aligned polyline with 90 degree corners filleted
at radius R: volume by Pappus, pi (ro^2 - ri^2) x path length; bbox from the points.
"""
from __future__ import annotations

import math

from build123d import Align, Axis, Box, Circle, FilletPolyline, Location, Plane, Polyline, make_face, revolve, sweep


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def add(a, b, k=1.0):
    return tuple(x + k * y for x, y in zip(a, b))


def perp(o):
    """A unit vector perpendicular to o (stable choice)."""
    ref = (0.0, 0.0, 1.0) if abs(o[2]) < 0.9 else (1.0, 0.0, 0.0)
    return unit(cross(cross(o, ref), o))


def _f_disk(R, s, t):
    """Integral over a disk of radius R of (w t - s)+ dA, for s >= 0."""
    if t == 0 or R <= 0:
        return 0.0
    w0 = s / t
    if w0 >= R:
        return 0.0
    q = math.sqrt(R * R - w0 * w0)
    return (2 * t / 3) * q ** 3 - s * (math.pi * R * R / 2 - w0 * q - R * R * math.asin(w0 / R))


def _F(ro, ri, s, t):
    A = math.pi * (ro * ro - ri * ri)
    if s >= 0:
        return _f_disk(ro, s, t) - _f_disk(ri, s, t)
    return -s * A + _f_disk(ro, -s, t) - _f_disk(ri, -s, t)


def leg(c, o, ew, sections, t=0.0):
    return dict(c=tuple(c), o=unit(o), ew=unit(ew), sections=[tuple(x) for x in sections], t=t)


def straight(p0, o, runs):
    """A straight stepped part from p0 along o: runs = [(length, ro, ri), ...] in order from p0."""
    secs, s = [], 0.0
    for ln, ro, ri in runs:
        secs.append((s, s + ln, ro, ri))
        s += ln
    o = unit(o)
    return [leg(p0, o, perp(o), secs, 0.0)]


def elbow(c, o1, secs1, o2, secs2):
    """Two mitred legs leaving corner c along o1 and o2; secs from the corner outward, first s0 None."""
    o1, o2 = unit(o1), unit(o2)
    cphi = dot(o1, o2)
    ca = math.sqrt((1 - cphi) / 2)
    t = math.sqrt(1 - ca * ca) / ca
    ew1 = unit(add(o2, o1, -cphi))
    ew2 = unit(add(o1, o2, -cphi))
    return [leg(c, o1, ew1, secs1, t), leg(c, o2, ew2, secs2, t)]


def leg_volume(lg) -> float:
    t, v = lg["t"], 0.0
    for s0, s1, ro, ri in lg["sections"]:
        A = math.pi * (ro * ro - ri * ri)
        if s0 is None:
            v += s1 * A + _F(ro, ri, s1, t)
        else:
            v += (s1 - s0) * A - (_F(ro, ri, s0, t) - _F(ro, ri, s1, t))
    return v


def leg_bbox(lg, n=2880):
    c, o, ew, t = lg["c"], lg["o"], lg["ew"], lg["t"]
    en = cross(o, ew)
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for s0, s1, ro, ri in lg["sections"]:
        ths = [2 * math.pi * k / n for k in range(n)]
        if t > 0:
            for s in (s0, s1):
                if s is not None and abs(s) < ro * t:
                    a = math.acos(s / (ro * t))
                    ths += [a, -a]
        for th in ths:
            w = ro * math.cos(th)
            slo = w * t if s0 is None else max(s0, w * t)
            if slo > s1:
                continue
            for s in (slo, s1):
                for i in range(3):
                    p = c[i] + s * o[i] + ro * (math.cos(th) * ew[i] + math.sin(th) * en[i])
                    lo[i], hi[i] = min(lo[i], p), max(hi[i], p)
    return tuple(lo), tuple(hi)


def legs_expect(kind, legs):
    """Envelope and hand volume of a part made of legs."""
    boxes = [leg_bbox(lg) for lg in legs]
    lo = tuple(min(b[0][i] for b in boxes) for i in range(3))
    hi = tuple(max(b[1][i] for b in boxes) for i in range(3))
    return dict(kind=kind, lo=lo, hi=hi, volume=sum(leg_volume(lg) for lg in legs), geom=("legs", legs))


def leg_point(lg, s):
    """Point on a leg's axis at distance s from c."""
    return add(lg["c"], lg["o"], s)


def sweep_length(pts, R):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    return sum(seg) - (len(pts) - 2) * (2 * R - math.pi * R / 2), seg


def sweep_expect(kind, pts, ro, ri, R):
    """Axis-aligned polyline, consecutive segments perpendicular, every corner filleted at R."""
    dirs = [unit(tuple(b - a for a, b in zip(p, q))) for p, q in zip(pts, pts[1:])]
    for u in dirs:
        assert sorted(abs(x) for x in u) == [0.0, 0.0, 1.0], f"sweep segment not axis-aligned: {u}"
    for u, v in zip(dirs, dirs[1:]):
        assert abs(dot(u, v)) < 1e-12, "sweep corner not 90 degrees"
    L, seg = sweep_length(pts, R)
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for k, p in enumerate(pts):
        axes = {0, 1, 2}
        if k == 0:
            axes -= {max(range(3), key=lambda i: abs(dirs[0][i]))}
        elif k == len(pts) - 1:
            axes -= {max(range(3), key=lambda i: abs(dirs[-1][i]))}
        for i in range(3):
            r = ro if i in axes else 0.0
            lo[i], hi[i] = min(lo[i], p[i] - r), max(hi[i], p[i] + r)
    return dict(kind=kind, lo=tuple(lo), hi=tuple(hi), volume=math.pi * (ro * ro - ri * ri) * L,
                geom=("sweep", [tuple(p) for p in pts], ro, ri, R), segs=seg, path_len=L)


def frame_place(F, x, s, z):
    """Local (across, along, up) -> world for a frame F = (origin, X, Y, Z)."""
    O, X, Y, Z = F
    return tuple(O[i] + x * X[i] + s * Y[i] + z * Z[i] for i in range(3))


def frame_box_bbox(F, x0, x1, s0, s1, z0, z1):
    pts = [frame_place(F, x, s, z) for x in (x0, x1) for s in (s0, s1) for z in (z0, z1)]
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


# ---------------------------------------------------------------------------
# build123d solids from the same description
# ---------------------------------------------------------------------------
def build_leg(lg: dict, filled: bool = False):
    """Revolve the stepped profile about local Z, cut by the mitre plane s = w t (local x = w), place.
    filled=True drops the bore (insertion depth is measured on filled solids)."""
    t = lg["t"]
    smin = -max(sec[2] for sec in lg["sections"]) * t - 1.0
    solid = None
    for s0, s1, ro, ri in lg["sections"]:
        s0 = smin if s0 is None else s0
        ri = 0.0 if filled else ri
        outline = [(ri, s0), (ro, s0), (ro, s1), (ri, s1)] if ri > 0 else [(0, s0), (ro, s0), (ro, s1), (0, s1)]
        sec = revolve(make_face(Polyline(*[(x, 0, z) for x, z in outline], close=True)), Axis.Z, 360)
        solid = sec if solid is None else solid + sec
    if t > 0:
        half = Box(1e4, 1e4, 1e4, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
            Location(Plane(origin=(0, 0, 0), x_dir=unit((1, 0, t)), z_dir=unit((-t, 0, 1)))))
        solid = solid & half
    return solid.moved(Location(Plane(origin=lg["c"], x_dir=lg["ew"], z_dir=lg["o"])))


def build_geom(e: dict, filled: bool = False):
    """Solid for an expectation made by legs_expect or sweep_expect. The legs of an elbow share their mitre face
    and fuse into one solid (F29)."""
    g = e["geom"]
    if g[0] == "legs":
        parts = [build_leg(lg, filled) for lg in g[1]]
        out = parts[0]
        for p in parts[1:]:
            out = out + p
        return out
    if g[0] == "sweep":
        _, pts, ro, ri, R = g
        path = FilletPolyline(*pts, radius=R)
        pl = Plane(origin=pts[0], z_dir=unit(tuple(b - a for a, b in zip(pts[0], pts[1]))))
        prof = pl * Circle(ro)
        if ri > 0 and not filled:
            prof = prof - pl * Circle(ri)
        return sweep(prof, path)
    raise ValueError(f"build_geom: unknown geom {g[0]}")
