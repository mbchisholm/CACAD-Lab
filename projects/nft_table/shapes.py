r"""Analytic solids for the NFT table: volume and world bounding box of a part from its description alone. No
numbers live here: params.py describes each solid as primitives in a local frame plus a placement, build.py turns
the same description into a build123d solid, and table.py compares the two (envelope and hand volume).

A description is dict(add=[...], sub=[...], label=None | dict). The volume is sum(add) - sum(sub), which holds
because params writes every part so that the additive primitives meet only on faces and every subtractive primitive
lies inside the additive union and away from the other subtractive ones. The test that the OCC volume matches is
what keeps params honest about that.

Primitives (local frame, mm):
    ("box", lo, hi)                                      axis-aligned
    ("cyl", c, axis, length, r)                          from c along a unit axis
    ("cone", c, axis, length, r0, r1)                    frustum, r0 at c
    ("prism", ax, poly, w0, w1)                          polygon in the plane normal to ax ('x','y','z'),
                                                         coordinates (u, v) = (y, z) | (x, z) | (x, y), extruded w0..w1
    ("ring", c, ax, w0, w1, ri, ro, a0, a1)              annular sector about an axis-parallel line through c, angle in
                                                         the (u, v) plane from +u, extruded w0..w1 along ax
    ("hex", c, axis, length, s[, phase])                 hexagonal prism, across flats s; phase 0 puts a pair of
                                                         flats normal to perp(axis), pi/6 puts a vertex there
    ("raw", prim, volume)                                prim built as is, its volume given (an overlap with air or
                                                         another primitive, integrated in params)
    ("rloft", (z0, cx0, cy0, L0, W0), (z1, cx1, cy1, L1, W1))   rectangle at z0 lofted to a rectangle at z1
    ("tee", c, run_axis, branch_axis, R, L_half, Rb, L_branch)  solid tee envelope (two equal-radius cylinders),
                                                         used only filled; the hollow tee is built from legs
A placement is (R, t): R a 3x3 rotation as three column vectors (local x, y, z in world), t the world origin.
"""
from __future__ import annotations

import math

from cacad import plumbing as P

AX = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
# (u, v, w) index order for a prism or ring along each axis
UVW = {"x": (1, 2, 0), "y": (0, 2, 1), "z": (0, 1, 2)}

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def rot_x(a: float):
    """Columns: local x, y, z in world after a rotation by a (rad) about X."""
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, s), (0.0, -s, c))


def rot_z(a: float):
    c, s = math.cos(a), math.sin(a)
    return ((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0))


def rot_y(a: float):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, -s), (0.0, 1.0, 0.0), (s, 0.0, c))


def compose(A, B):
    """Rotation A applied after B (columns)."""
    return tuple(apply_R(A, col) for col in B)


def apply_R(R, v):
    return tuple(R[0][i] * v[0] + R[1][i] * v[1] + R[2][i] * v[2] for i in range(3))


def to_world(pl, p):
    R, t = pl
    q = apply_R(R, p)
    return tuple(q[i] + t[i] for i in range(3))


def shoelace(poly) -> float:
    a = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2.0


# ---------------------------------------------------------------------------
# volumes
# ---------------------------------------------------------------------------
def _steinmetz_half(r: float) -> float:
    """Volume of the part of a cylinder of radius r, entering perpendicular to the axis of an equal cylinder,
    that lies inside it on one side of its axis plane: half the Steinmetz bicylinder, 8 r^3 / 3."""
    return 8.0 * r ** 3 / 3.0


def prim_volume(p) -> float:
    k = p[0]
    if k == "raw":
        return p[2]
    if k == "box":
        lo, hi = p[1], p[2]
        return (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])
    if k == "cyl":
        return math.pi * p[4] ** 2 * p[3]
    if k == "cone":
        _, _, _, L, r0, r1 = p
        return math.pi * L * (r0 * r0 + r0 * r1 + r1 * r1) / 3.0
    if k == "prism":
        _, _, poly, w0, w1 = p
        return abs(shoelace(list(poly))) * (w1 - w0)
    if k == "ring":
        _, _, _, w0, w1, ri, ro, a0, a1 = p
        return 0.5 * (a1 - a0) * (ro * ro - ri * ri) * (w1 - w0)
    if k == "hex":
        L, s = p[3], p[4]
        return (math.sqrt(3) / 2) * s * s * L
    if k == "rloft":
        (z0, _, _, L0, W0), (z1, _, _, L1, W1) = p[1], p[2]
        # prismoid: h/6 (A0 + 4 Am + A1)
        A0, A1, Am = L0 * W0, L1 * W1, (L0 + L1) / 2 * (W0 + W1) / 2
        return (z1 - z0) / 6.0 * (A0 + 4 * Am + A1)
    if k == "tee":
        _, _, _, _, R, Lh, Rb, Lb = p
        assert abs(R - Rb) < 1e-12, "tee: equal radii only"
        return math.pi * R * R * (2 * Lh) + math.pi * R * R * Lb - _steinmetz_half(R)
    raise ValueError(f"prim_volume: {k}")


def desc_volume(desc) -> float:
    """sum(add) - sum(sub) + sum(corr): corr carries the analytic overlaps params computed where two additive
    primitives share volume or a subtractive one reaches into air. Labels are measured separately."""
    return (sum(prim_volume(p) for p in desc["add"]) - sum(prim_volume(p) for p in desc.get("sub", []))
            + sum(desc.get("corr", [])))


# ---------------------------------------------------------------------------
# world bounding boxes (exact for each primitive under a rotation)
# ---------------------------------------------------------------------------
def _pts_box(pts):
    return (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))


def _disc_extent(c, a, r):
    """World bbox of a disc of radius r centred at c with unit normal a."""
    e = [r * math.sqrt(max(0.0, 1.0 - a[i] * a[i])) for i in range(3)]
    return tuple(c[i] - e[i] for i in range(3)), tuple(c[i] + e[i] for i in range(3))


def _merge(boxes):
    return (tuple(min(b[0][i] for b in boxes) for i in range(3)), tuple(max(b[1][i] for b in boxes) for i in range(3)))


def _uvw_point(ax, u, v, w):
    iu, iv, iw = UVW[ax]
    p = [0.0, 0.0, 0.0]
    p[iu], p[iv], p[iw] = u, v, w
    return tuple(p)


def prim_bbox(p, pl):
    R, _ = pl
    k = p[0]
    if k == "raw":
        return prim_bbox(p[1], pl)
    if k == "box":
        lo, hi = p[1], p[2]
        return _pts_box([to_world(pl, (x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    if k in ("cyl", "cone"):
        c, a, L = p[1], P.unit(p[2]), p[3]
        r0, r1 = (p[4], p[4]) if k == "cyl" else (p[4], p[5])
        c1 = tuple(c[i] + L * a[i] for i in range(3))
        aw = apply_R(R, a)
        return _merge([_disc_extent(to_world(pl, c), aw, r0), _disc_extent(to_world(pl, c1), aw, r1)])
    if k == "prism":
        _, ax, poly, w0, w1 = p
        return _pts_box([to_world(pl, _uvw_point(ax, u, v, w)) for u, v in poly for w in (w0, w1)])
    if k == "ring":
        _, c, ax, w0, w1, ri, ro, a0, a1 = p
        iu, iv, _ = UVW[ax]
        angs = [a0, a1] + [k_ * math.pi / 2 for k_ in range(-8, 9) if a0 < k_ * math.pi / 2 < a1]
        pts = []
        for a in angs:
            for r in (ri, ro):
                for w in (w0, w1):
                    q = list(_uvw_point(ax, c[iu] + r * math.cos(a), c[iv] + r * math.sin(a), w))
                    pts.append(to_world(pl, tuple(q)))
        # world extremes of an arc under a rotation need not sit at local cardinal angles: sample densely too
        n = 720
        for j in range(n + 1):
            a = a0 + (a1 - a0) * j / n
            for w in (w0, w1):
                pts.append(to_world(pl, _uvw_point(ax, c[iu] + ro * math.cos(a), c[iv] + ro * math.sin(a), w)))
        return _pts_box(pts)
    if k == "hex":
        c, a, L, s = p[1], P.unit(p[2]), p[3], p[4]
        phase = p[5] if len(p) > 5 else 0.0
        e1 = P.perp(a)
        e2 = P.cross(a, e1)
        rc = s / math.sqrt(3)
        pts = []
        for j in range(6):
            ang = math.pi / 6 + j * math.pi / 3 + phase
            for t in (0.0, L):
                pts.append(to_world(pl, tuple(c[i] + t * a[i] + rc * (math.cos(ang) * e1[i] + math.sin(ang) * e2[i])
                                              for i in range(3))))
        return _pts_box(pts)
    if k == "rloft":
        pts = []
        for z, cx, cy, Lx, Wy in (p[1], p[2]):
            for x in (cx - Lx / 2, cx + Lx / 2):
                for y in (cy - Wy / 2, cy + Wy / 2):
                    pts.append(to_world(pl, (x, y, z)))
        return _pts_box(pts)
    if k == "tee":
        _, c, ra, ba, Rr, Lh, Rb, Lb = p
        ra, ba = P.unit(ra), P.unit(ba)
        run = ("cyl", tuple(c[i] - Lh * ra[i] for i in range(3)), ra, 2 * Lh, Rr)
        br = ("cyl", c, ba, Lb, Rb)
        return _merge([prim_bbox(run, pl), prim_bbox(br, pl)])
    raise ValueError(f"prim_bbox: {k}")


def desc_bbox(desc, pl):
    return _merge([prim_bbox(p, pl) for p in desc["add"]])


def expect_prims(kind, desc, pl, **extra):
    lo, hi = desc_bbox(desc, pl)
    return dict(kind=kind, lo=lo, hi=hi, volume=desc_volume(desc), geom=("prims", desc, pl), **extra)


# ---------------------------------------------------------------------------
# hollow tee from legs: run (straight, stepped) plus branch (straight, stepped) whose bores meet
# ---------------------------------------------------------------------------
def tee_expect(kind, c, run_axis, branch_axis, R, run_secs, branch_secs, r_bore):
    """A moulded Sch 40 tee: hub OD 2R over the run and the branch, stepped bores. run_secs and branch_secs are
    (s0, s1, ri) along the run from one face to the other and along the branch from the run axis out, at outer
    radius R. The branch bore of radius r_bore (= the run's centre bore) meets the run's centre bore.
    Volume: outer union minus bore union, each by the half-Steinmetz overlap of equal cylinders."""
    ra, ba = P.unit(run_axis), P.unit(branch_axis)
    L_run = run_secs[-1][1] - run_secs[0][0]
    L_br = branch_secs[-1][1]
    v_outer = math.pi * R * R * (L_run + L_br) - _steinmetz_half(R)
    v_bore = sum(math.pi * ri * ri * (s1 - s0) for s0, s1, ri in run_secs) + \
        sum(math.pi * ri * ri * (s1 - s0) for s0, s1, ri in branch_secs) - _steinmetz_half(r_bore)
    p0 = tuple(c[i] + run_secs[0][0] * ra[i] for i in range(3))
    run = P.straight(p0, ra, [(s1 - s0, R, ri) for s0, s1, ri in run_secs])
    br = P.straight(c, ba, [(s1 - s0, R, ri) for s0, s1, ri in branch_secs])
    boxes = [P.leg_bbox(lg) for lg in run + br]
    lo = tuple(min(b[0][i] for b in boxes) for i in range(3))
    hi = tuple(max(b[1][i] for b in boxes) for i in range(3))
    return dict(kind=kind, lo=lo, hi=hi, volume=v_outer - v_bore,
                geom=("tee", run, br, R, L_run, L_br), filled_volume=v_outer)


# ---------------------------------------------------------------------------
# closed forms and quadrature for the overlaps params needs
# ---------------------------------------------------------------------------
_GL = None


def _gauss(n=48):
    """Gauss-Legendre nodes and weights on [-1, 1] (Newton on P_n)."""
    global _GL
    if _GL is not None and _GL[0] == n:
        return _GL[1]
    xs, ws = [], []
    for i in range(1, n + 1):
        x = math.cos(math.pi * (i - 0.25) / (n + 0.5))
        for _ in range(100):
            p0, p1 = 1.0, x
            for k in range(2, n + 1):
                p0, p1 = p1, ((2 * k - 1) * x * p1 - (k - 1) * p0) / k
            dp = n * (x * p1 - p0) / (x * x - 1)
            dx = p1 / dp
            x -= dx
            if abs(dx) < 1e-15:
                break
        xs.append(x)
        ws.append(2 / ((1 - x * x) * dp * dp))
    _GL = (n, list(zip(xs, ws)))
    return _GL[1]


def quad(f, a, b, n=48, panels=8):
    """Composite Gauss-Legendre."""
    tot = 0.0
    h = (b - a) / panels
    for j in range(panels):
        lo = a + j * h
        for x, w in _gauss(n):
            tot += w * f(lo + (x + 1) * h / 2) * h / 2
    return tot


def chord_integral(R: float, a: float) -> float:
    """Integral of sqrt(R^2 - x^2) dx over [-a, a], a <= R."""
    return a * math.sqrt(R * R - a * a) + R * R * math.asin(a / R)


def segment_area(R: float, a: float) -> float:
    """Area of the part of a disc of radius R with x >= a (|a| <= R)."""
    return R * R * math.acos(a / R) - a * math.sqrt(R * R - a * a)


def gland_volume(R: float, L: float, ri: float, ro: float) -> float:
    """O-ring groove cut into a cylindrical seat of radius R (axis z) to radial depth L: the annulus ri..ro about the
    x axis, between radii R and R + L about the z axis. Integral over the annulus in (y, z) of
    sqrt((R+L)^2 - y^2) - sqrt(R^2 - y^2)."""
    def ring(rho):
        return quad(lambda ph: (math.sqrt((R + L) ** 2 - (rho * math.cos(ph)) ** 2)
                                - math.sqrt(R * R - (rho * math.cos(ph)) ** 2)) * rho, 0.0, 2 * math.pi, 24, 8)
    return quad(ring, ri, ro, 16, 2)


def passage_volume(R: float, r: float, x_end: float) -> float:
    """Cylinder of radius r along +x from inside a seat of radius R (axis z) out to x_end: the part outside the
    seat, integral over |y| <= r of 2 sqrt(r^2 - y^2) (x_end - sqrt(R^2 - y^2))."""
    return quad(lambda y: 2 * math.sqrt(max(0.0, r * r - y * y)) * (x_end - math.sqrt(R * R - y * y)), -r, r, 48, 4)


def bore_passage_overlap(rb: float, rp: float) -> float:
    """A vertical bore (radius rb, from the passage axis up) fully over a horizontal passage (radius rp >= rb):
    the shared volume, integral over |y| <= rb of 2 sqrt(rb^2 - y^2) sqrt(rp^2 - y^2)."""
    return quad(lambda y: 2 * math.sqrt(max(0.0, rb * rb - y * y)) * math.sqrt(rp * rp - y * y), -rb, rb, 48, 4)


def poly_width(poly, x):
    """Total length of the polygon's cross-section at abscissa x (a convex or simple polygon in (x, z))."""
    zs = []
    n = len(poly)
    for i in range(n):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % n]
        if (x0 <= x < x1) or (x1 <= x < x0):
            zs.append(z0 + (z1 - z0) * (x - x0) / (x1 - x0))
    zs.sort()
    return sum(zs[k + 1] - zs[k] for k in range(0, len(zs) - 1, 2))


def prism_above_seat(poly, y_top: float, R: float, y0: float) -> float:
    """A prism of polygon poly (in (x, z)) along +y from below a seat cylinder (axis z, radius R, centre at y = y0)
    up to y_top: the part outside the seat, integral of width(x) (y_top - y0 - sqrt(R^2 - x^2))."""
    xs = sorted({p[0] for p in poly})
    tot = 0.0
    for a, b in zip(xs, xs[1:]):
        if b - a < 1e-12:
            continue
        tot += quad(lambda x: poly_width(poly, x) * (y_top - y0 - math.sqrt(R * R - x * x)), a, b, 24, 2)
    return tot


def circle_poly(r: float, n: int = 96, c=(0.0, 0.0), phase: float = 0.0):
    return [(c[0] + r * math.cos(phase + 2 * math.pi * k / n), c[1] + r * math.sin(phase + 2 * math.pi * k / n))
            for k in range(n)]


def teardrop_poly(r: float, n: int = 96, c=(0.0, 0.0)):
    """Circle with a 45 deg roof toward +v (print up): self-supporting horizontal hole. Vertices CCW."""
    pts = []
    a0, a1 = math.radians(135), math.radians(45) + 2 * math.pi
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    pts.append((c[0], c[1] + r * math.sqrt(2)))
    return pts


def bore_over_poly(rb: float, poly, z0: float) -> float:
    """A vertical bore (radius rb, axis at u = 0, from z0 up) through a horizontal prism of polygon poly (in (u, z)),
    fully across it: the shared volume, integral over |u| <= rb of 2 sqrt(rb^2 - u^2) (top(u) - z0)."""
    def top(u):
        zs = []
        n = len(poly)
        for i in range(n):
            (u0, z0_), (u1, z1_) = poly[i], poly[(i + 1) % n]
            if (u0 <= u <= u1) or (u1 <= u <= u0):
                if abs(u1 - u0) > 1e-15:
                    zs.append(z0_ + (z1_ - z0_) * (u - u0) / (u1 - u0))
        return max(zs)
    return quad(lambda u: 2 * math.sqrt(max(0.0, rb * rb - u * u)) * (top(u) - z0), -rb, rb, 48, 8)
