"""Seedling wheel assembly: frame, rotor, two gravity-hung gondolas with trays, light; checked through the turn.

    .venv/bin/python projects/seedling_wheel/assembly.py [phi_deg]   # checks; out/seedling_wheel_<phi>.step + .3mf

Bought parts are envelopes: 2020 extrusion as a 20 x 20 bar with a 6 x 6 groove in each face (HFS5 slot opening and
depth), the gearmotor as its 42.3 square, the tray as a straight-walled shell, the plants as the headroom box.
P7 light hangers, P8 nacelles, P10 leg shoes and the Misumi brackets are envelopes until they are drawn.
`check_assembly(phi)` fails on any overlap between parts that are not designed to touch.

A part file names no filesystem module (F23) and imports params by package path (F24).
"""
from __future__ import annotations

import math

from build123d import Box, Compound, Cone, Cylinder, Location, Part, Plane, RegularPolygon, extrude, Pos

from cacad import interference_volume
from projects.seedling_wheel.params import derive
from projects.seedling_wheel.p1_hub import build_part as build_p1
from projects.seedling_wheel.p2_pivot import build_part as build_p2
from projects.seedling_wheel.p3_hanger import build_part as build_p3
from projects.seedling_wheel.p4_corner import build_part as build_p4
from projects.seedling_wheel.p5_head import build_part as build_p5


def _bar(length: float, d: dict) -> Part:
    """2020 along local Z, centred, with the slot grooves."""
    a, so, sd = d["ext"]["a"], d["ext"]["slot_open"], d["ext"]["slot_depth"]
    b = Box(a, a, length)
    for ang in (0, 90, 180, 270):
        b -= Pos(0, 0, 0) * Location((0, 0, 0), (0, 0, ang)) * Pos(a / 2 - sd / 2 + 0.001, 0, 0) * Box(sd, so, length)
    return b


def bar(p0, p1, d: dict) -> Part:
    """2020 from p0 to p1 (axis-aligned or not), slots on its four faces."""
    v = [b - a for a, b in zip(p0, p1)]
    L = math.sqrt(sum(c * c for c in v))
    z = tuple(c / L for c in v)
    x = (1, 0, 0) if abs(z[0]) < 0.9 else (0, 1, 0)
    mid = tuple((a + b) / 2 for a, b in zip(p0, p1))
    return Plane(origin=mid, x_dir=x, z_dir=z).location * _bar(L, d)


def box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def cyl_x(x0, x1, r, y, z) -> Part:
    return Plane(origin=((x0 + x1) / 2, y, z), x_dir=(0, 1, 0), z_dir=(1, 0, 0)).location * Cylinder(r, x1 - x0)


def gondola(d: dict, label: str) -> dict:
    """Gondola parts in the gondola-local frame (pivot axis at y = z = 0)."""
    t, c, a = d["tray"], d["c"], d["ext"]["a"]
    zf = d["z_floor"]
    p = {}
    for s in (-1, 1):
        p[f"{label} rail {s:+d}"] = bar((-d["x_post1"], s * c["rail_y"], zf - a / 2), (d["x_post1"], s * c["rail_y"], zf - a / 2), d)
        xm = s * (d["x_end0"] + a / 2)
        p[f"{label} crossbar {s:+d}"] = bar((xm, -d["xbar_len"] / 2, zf - 1.5 * a), (xm, d["xbar_len"] / 2, zf - 1.5 * a), d)
        p[f"{label} post {s:+d}"] = bar((xm, 0, d["post_z"][0]), (xm, 0, d["post_z"][1]), d)
        # P3 on the post's outboard face: local z -> outboard, local y -> up
        p[f"{label} P3 {s:+d}"] = Plane(origin=(s * d["x_post1"], 0, 0), x_dir=(0, s, 0), z_dir=(s, 0, 0)).location * build_p3(d["size"])
    # P4 corner guides: one part, mirrored to each corner; local origin on the crossbar's inner top corner, at its end
    p4 = build_p4(d["size"])
    for s in (-1, 1):
        for sy in (-1, 1):
            q = p4
            if s < 0:
                q = q.mirror(Plane.YZ)
            if sy < 0:
                q = q.mirror(Plane.XZ)
            p[f"{label} P4 {s:+d}{sy:+d}"] = Pos(s * d["x_end0"], sy * d["xbar_len"] / 2, zf - a) * q
    w = 2.0
    p[f"{label} tray"] = box(-t["L"] / 2, t["L"] / 2, -t["W"] / 2, t["W"] / 2, zf, zf + t["D"]) - \
        box(-t["L"] / 2 + w, t["L"] / 2 - w, -t["W"] / 2 + w, t["W"] / 2 - w, zf + w, zf + t["D"] + 1)
    p[f"{label} plants"] = box(-t["L"] / 2 + 10, t["L"] / 2 - 10, -t["W"] / 2 + 10, t["W"] / 2 - 10,
                               zf + t["D"], zf + d["h_plants"])
    return p


def rotor(d: dict, phi: float) -> dict:
    """Arms, hubs, P1, P2 and the pivot hardware, in the world frame, rotor at phi (deg; 0 = gondola A on top)."""
    c, f, a, za = d["c"], d["fas"], d["ext"]["a"], d["z_axis"]
    e = (0.0, math.sin(math.radians(phi)), math.cos(math.radians(phi)))
    R = d["R"]
    wd, wD, wt = f["washer8"]
    p = {}
    for s in (-1, 1):
        xa = s * (d["x_arm"][0] + a / 2)
        L = d["arm_len"] / 2
        p[f"arm {s:+d}"] = bar((xa, -L * e[1], za - L * e[2]), (xa, L * e[1], za + L * e[2]), d)
        p[f"P1 {s:+d}"] = Plane(origin=(s * d["x_p1"][1], 0, za), x_dir=e, z_dir=(-s, 0, 0)).location * build_p1(d["size"])
        x0, x1 = sorted((s * d["x_hub"][0], s * d["x_hub"][1]))
        p[f"Pololu hub {s:+d}"] = cyl_x(x0, x1, d["hub"]["od"] / 2, 0, za) - cyl_x(x0, x1, d["hub"]["bore"] / 2, 0, za)
        x0, x1 = sorted((s * d["x_tower"][0], s * (d["x_tower"][0] - d["motor"]["shaft"][1])))
        p[f"gearbox shaft {s:+d}"] = cyl_x(x0, x1, d["motor"]["shaft"][0] / 2, 0, za)
        for lab, sg in (("A", 1), ("B", -1)):
            py, pz = sg * R * e[1], za + sg * R * e[2]
            p[f"P2 {lab}{s:+d}"] = Plane(origin=(s * d["x_p2"][1], py, pz), x_dir=(0, sg * e[1], sg * e[2]),
                                         z_dir=(-s, 0, 0)).location * build_p2(d["size"])
            xh = d["x_post1"] - wt                       # head underside / shoulder start
            pieces = [
                (xh - f["sh_head"][1], xh, f["sh_head"][0] / 2),           # head
                (xh, xh + d["sh_len"], f["sh_d"] / 2),                     # shoulder
                (xh + d["sh_len"], xh + d["sh_len"] + f["sh_thread_len"], 3.0),   # M6 thread
            ]
            scr = None
            for u0, u1, r in pieces:
                x0, x1 = sorted((s * u0, s * u1))
                scr = cyl_x(x0, x1, r, py, pz) if scr is None else scr + cyl_x(x0, x1, r, py, pz)
            p[f"shoulder screw {lab}{s:+d}"] = scr
            for k, u0 in enumerate((xh, d["x_p3"][1])):
                x0, x1 = sorted((s * u0, s * (u0 + wt)))
                p[f"washer {lab}{s:+d}.{k}"] = cyl_x(x0, x1, wD / 2, py, pz) - cyl_x(x0, x1, wd / 2, py, pz)
            un = d["x_p2"][0] + c["p2_web"]
            x0, x1 = sorted((s * un, s * (un + f["nut_M6"][1])))
            hexn = extrude(RegularPolygon(f["nut_M6"][0] / 2, 6, major_radius=False), x1 - x0)
            hexn = Plane(origin=(x0, py, pz), x_dir=(0, sg * e[1], sg * e[2]), z_dir=(1, 0, 0)).location * hexn
            p[f"M6 nut {lab}{s:+d}"] = hexn - cyl_x(x0, x1, 3.0, py, pz)
    return p


def frame(d: dict) -> dict:
    """Static parts: two A towers (legs, mast, foot), the P5 heads, gearmotors under P8 nacelles, ridge, spine, light."""
    c, a, m = d["c"], d["ext"]["a"], d["motor"]
    za, zr = d["z_axis"], d["z_ridge"]
    fy, fo, r0 = c["foot_y"], c["foot_over"], c["spoke_r0"]
    bl, bw, bt = c["bracket"]
    p = {}
    x0, x1 = d["x_tower"]
    for s in (-1, 1):
        xt = s * (x0 + a / 2)
        xi, xo = sorted((s * x0, s * x1))
        p[f"foot {s:+d}"] = bar((xt, -fy - fo, a / 2), (xt, fy + fo, a / 2), d)
        p[f"mast {s:+d}"] = bar((xt, 0, d["mast"][0]), (xt, 0, d["mast"][1]), d)
        for sy in (-1, 1):
            u = (sy * fy, a - za)
            n = math.hypot(*u)
            u = (u[0] / n, u[1] / n)
            far = n + a                                        # past the foot, then cut on the crossbar's top
            leg = bar((xt, u[0] * r0, za + u[1] * r0), (xt, u[0] * far, za + u[1] * far), d)
            p[f"leg {s:+d}{sy:+d}"] = leg & box(xi - 1, xo + 1, -fy - 2 * fo, fy + 2 * fo, a, za)
            # P10 leg shoe (envelope): a plate on the outboard faces of leg and foot
            xs0, xs1 = sorted((s * x1, s * (x1 + 6.0)))
            p[f"P10 {s:+d}{sy:+d}"] = box(xs0, xs1, *sorted((sy * (fy - 45), sy * (fy + fo))), 0, 60)
        p[f"P5 {s:+d}"] = Plane(origin=(s * x0, 0, za), x_dir=(0, -s, 0), z_dir=(-s, 0, 0)).location * build_p5(d["size"])
        gx0, gx1 = sorted((s * x0, s * d["motor_end"]))
        g = m["flange"] / 2
        p[f"gearmotor {s:+d}"] = box(gx0, gx1, -g, g, za - g, za + g)
        # P8 nacelle (envelope): a closed cone shell from the spokes' outboard faces over the gearmotor
        pr, pe, pw, pg = c["pod"]
        L = d["pod_x"][1] - d["pod_x"][0]
        loc = Plane(origin=(s * (d["pod_x"][0] + L / 2), 0, za), x_dir=(0, 1, 0), z_dir=(s, 0, 0)).location
        inner = Pos(0, 0, -pw / 2) * Cone(pr - pw, pe - pw + pw * (pr - pe) / L, L - pw)
        p[f"P8 {s:+d}"] = loc * (Cone(pr, pe, L) - inner)
        # Misumi HBLFSN5 brackets (envelopes): mast to ridge, foot to spine, on the inboard corners
        xb0, xb1 = sorted((s * x0, s * (x0 - bl)))
        xv0, xv1 = sorted((s * x0, s * (x0 - bt)))
        p[f"bracket ridge {s:+d}"] = box(xb0, xb1, -bw / 2, bw / 2, zr - bt, zr) + box(xv0, xv1, -bw / 2, bw / 2, zr - bl, zr)
        p[f"bracket spine {s:+d}"] = box(xb0, xb1, -bw / 2, bw / 2, a, a + bt)
        xh = s * c["hanger_x"]
        p[f"P7 {s:+d}"] = box(xh - a / 2, xh + a / 2, -110, 110, d["z_light"] + d["light"]["section"], zr)
    p["ridge"] = bar((-x1, 0, zr + a / 2), (x1, 0, zr + a / 2), d)
    p["spine"] = bar((-x0, 0, a / 2), (x0, 0, a / 2), d)
    L, sec = d["light"]["L"], d["light"]["section"]
    n, pitch = d["light"]["count"], d["light"]["pitch"]
    for i in range(n):
        y = (i - (n - 1) / 2) * pitch
        p[f"T5 bar {i}"] = box(-L / 2, L / 2, y - sec / 2, y + sec / 2, d["z_light"], d["z_light"] + sec)
    return p


def assemble(phi: float = 0.0, size: str = "T1020") -> dict:
    """{name: (group, shape)} in the world frame. Groups: frame, rotor, A, B."""
    d = derive(size)
    out = {k: ("frame", v) for k, v in frame(d).items()}
    out.update({k: ("rotor", v) for k, v in rotor(d, phi).items()})
    e = (math.sin(math.radians(phi)), math.cos(math.radians(phi)))
    for lab, sg in (("A", 1), ("B", -1)):
        loc = Location((0, sg * d["R"] * e[0], d["z_axis"] + sg * d["R"] * e[1]))
        out.update({k: (lab, loc * v) for k, v in gondola(d, lab).items()})
    return out


def _overlap(b1, b2, tol=1e-6) -> bool:
    return all(tuple(b1.min)[i] < tuple(b2.max)[i] - tol and tuple(b2.min)[i] < tuple(b1.max)[i] - tol
               for i in range(3))


def interferences(parts: dict, tol: float = 1e-3) -> list:
    """Every pair of parts whose solids overlap by more than tol mm^3."""
    names = list(parts)
    bbs = {n: parts[n][1].bounding_box() for n in names}
    hits = []
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            if not _overlap(bbs[n1], bbs[n2]):
                continue
            v = interference_volume(parts[n1][1], parts[n2][1])
            if v > tol:
                hits.append((n1, n2, round(v, 3)))
    return hits


def check_assembly(phi: float = 0.0, size: str = "T1020") -> dict:
    parts = assemble(phi, size)
    for n, (_, s) in parts.items():
        assert s.is_valid, f"{n} invalid"
    hits = interferences(parts)
    assert not hits, f"phi {phi}: overlaps {hits}"
    return parts


if __name__ == "__main__":
    import sys
    from build123d import export_step
    from cacad import export_3mf
    OUT = __file__.rsplit("/", 1)[0] + "/out"
    phis = [float(a) for a in sys.argv[1:] if not a.startswith("-")] or [0.0, 45.0, 90.0, 135.0]
    for phi in phis:
        parts = check_assembly(phi)
        print(f"phi {phi:5.1f}: {len(parts)} parts, no overlaps")
    parts = assemble(phis[0])
    export_step(Compound([s for _, s in parts.values()]), f"{OUT}/seedling_wheel_{int(phis[0])}.step")
    export_3mf({n: s for n, (_, s) in parts.items() if "plants" not in n}, f"{OUT}/seedling_wheel_{int(phis[0])}.3mf")
    bb = Compound([s for _, s in parts.values()]).bounding_box()
    print(f"bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}")
