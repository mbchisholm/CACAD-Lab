"""NFT rack: one solid per frame member, channel body, lid, end cap, drain, feed tube, pipe, fitting, valve, hose,
grommet, collector part, tote part and pump, placed from params.derive. Every number is from params.

    .venv/bin/python projects/nft_rack/rack.py [--show]     # builds params.ACTIVE_RACKS -> out/nft_rack_<rack>.step
"""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, Circle, Compound, Cylinder, FilletPolyline, Location, Part, Plane, Polyline,
                       Pos, Rectangle, loft, make_face, revolve, sweep)

from cacad import assert_material, expect_solids, interference_volume
from projects.nft_rack import legs as L_
from projects.nft_rack.params import ACTIVE_RACKS, derive, spec

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def _label(p: Part, name: str) -> Part:
    p.label = name
    return p


def _channel_loc(d: dict, c: dict) -> Location:
    """Channel-local frame (x across, y along the channel downhill, z up from the floor) -> world."""
    return Location((c["xc"], c["y_hi"], c["z_hi"]), (-math.degrees(d["theta"]), 0, 0))


def _frame_loc(F) -> Location:
    O, X, Y, Z = F
    return Location(Plane(origin=O, x_dir=X, z_dir=Z))


def build_frame(d: dict) -> dict[str, Part]:
    out = {}
    for name, e in d["expect"].items():
        if e["kind"] == "frame":
            lo, size = e["box"]
            out[name] = _label(Box(*size, align=ALIGN_MIN).moved(Location(lo)), name)
    return out


def build_channel(d: dict, c: dict) -> dict[str, Part]:
    """Body (U), lid with site holes and the feed hole, two end caps; growing_up_pro adds its drain stub cut by the
    floor plane (the table's drain cap spigot is a leg part, built by build_geom)."""
    cw, ch, ct, lt, capt = (spec(k) for k in ("channel_w", "channel_h", "channel_t", "lid_t", "cap_t"))
    L = d["channel_len"]
    loc = _channel_loc(d, c)
    n = c["name"]
    outer = Box(cw, L, ch, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, capt, 0))
    inner = Box(cw - 2 * ct, L, ch, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, capt, ct))
    body = outer - inner
    lid = Box(cw, L, lt, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, capt, ch))
    for s_ in c["sites"]:
        lid -= Cylinder(spec("site_hole_d") / 2, 3 * lt).moved(Pos(0, s_, ch + lt / 2))
    lid -= Cylinder(spec("feed_tube_od") / 2, 3 * lt).moved(Pos(0, c["s_feed"], ch + lt / 2))
    caps = {end: Box(cw, capt, ch + lt, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, s0, 0))
            for end, s0 in (("hi", 0.0), ("lo", capt + L))}
    out = {f"{n}-body": body.moved(loc), f"{n}-lid": lid.moved(loc)}
    out.update({f"{n}-cap-{end}": cap.moved(loc) for end, cap in caps.items()})
    e = d["expect"][f"{n}-drain"]
    if "geom" not in e:
        # drain: a vertical cylinder from the collector top up past the floor, trimmed to the half-space below the floor
        r = spec("drain_od") / 2
        stub = Cylinder(r, 4 * spec("drain_stub_len"), align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(
            Pos(c["xc"], d["y_drain"], e["lo"][2]))
        below = Box(cw * 4, d["Lo"] + 400, 400, align=(Align.CENTER, Align.MIN, Align.MAX)).moved(Pos(0, -200, 0)).moved(loc)
        out[f"{n}-drain"] = stub & below
    return {k: _label(v if isinstance(v, Part) else Part(v.wrapped), k) for k, v in out.items()}


def build_tube(t: dict) -> Part:
    path = FilletPolyline(*t["pts"], radius=t["bend_r"])
    prof = Plane(origin=t["pts"][0], z_dir=(0, 0, 1)) * Circle(t["r"])
    return _label(sweep(prof, path), t["name"])


def build_pipe(p: dict) -> Part:
    pipe = Cylinder(p["r"], p["length"], align=(Align.CENTER, Align.CENTER, Align.MIN), rotation=(0, 90, 0))
    if p["r_in"] > 0:
        pipe -= Cylinder(p["r_in"], p["length"], align=(Align.CENTER, Align.CENTER, Align.MIN), rotation=(0, 90, 0))
    return _label(pipe.moved(Pos(p["x0"], p["y"], p["z"])), p["name"])


# ---------------------------------------------------------------------------
# generic parts described by params' "geom"
# ---------------------------------------------------------------------------
def build_leg(lg: dict, filled: bool = False) -> Part:
    """Revolve the stepped profile about local Z, cut by the mitre plane s = w t (local x = w), place."""
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
            Location(Plane(origin=(0, 0, 0), x_dir=L_.unit((1, 0, t)), z_dir=L_.unit((-t, 0, 1)))))
        solid = solid & half
    return solid.moved(Location(Plane(origin=lg["c"], x_dir=lg["ew"], z_dir=lg["o"])))


def build_geom(e: dict, filled: bool = False) -> Part:
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
        z_dir = L_.unit(tuple(b - a for a, b in zip(pts[0], pts[1])))
        pl = Plane(origin=pts[0], z_dir=z_dir)
        prof = pl * Circle(ro)
        if ri > 0 and not filled:
            prof = prof - pl * Circle(ri)
        return sweep(prof, path)
    if g[0] == "box":
        _, lo, size = g
        return Box(*size, align=ALIGN_MIN).moved(Location(lo))
    if g[0] == "ubody":
        _, F, cw, ch, ct, s0, s1 = g
        outer = Box(cw, s1 - s0, ch, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, s0, 0))
        inner = Box(cw - 2 * ct, s1 - s0, ch, align=(Align.CENTER, Align.MIN, Align.MIN)).moved(Pos(0, s0, ct))
        return (outer - inner).moved(_frame_loc(F))
    if g[0] == "plate":
        _, F, (x0, x1, s0, s1, z0, z1), holes = g
        plate = Box(x1 - x0, s1 - s0, z1 - z0, align=ALIGN_MIN).moved(Pos(x0, s0, z0)).moved(_frame_loc(F))
        for p, o, r in holes:
            cyl = Cylinder(r, 400, align=(Align.CENTER, Align.CENTER, Align.CENTER))
            plate = plate - cyl.moved(Location(Plane(origin=p, x_dir=L_.perp(o), z_dir=o)))
        return plate
    if g[0] == "tub":
        _, lo, size, z_floor, (b_lo, b_size), (t_lo, t_size) = g
        outer = Box(*size, align=ALIGN_MIN).moved(Location(lo))
        z1 = lo[2] + size[2]
        # cavity: linear loft from the bottom rectangle at z_floor to the top rectangle at z1, carried 1 mm past z1
        k = (z1 + 1.0 - z_floor) / (z1 - z_floor)
        bc = (b_lo[0] + b_size[0] / 2, b_lo[1] + b_size[1] / 2)
        tc = (t_lo[0] + t_size[0] / 2, t_lo[1] + t_size[1] / 2)
        ex = tuple(b + (t - b) * k for b, t in zip(b_size, t_size))
        exc = tuple(b + (t - b) * k for b, t in zip(bc, tc))
        r0 = Plane.XY.offset(z_floor) * Pos(*bc) * Rectangle(*b_size)
        r1 = Plane.XY.offset(z1 + 1.0) * Pos(*exc) * Rectangle(*ex)
        return outer - loft([r0, r1])
    raise ValueError(f"unknown geom {g[0]}")


def build_rack(rack: str) -> dict[str, Part]:
    """name -> solid, each in its assembled position."""
    d = derive(rack)
    parts = build_frame(d)
    for c in d["channels"]:
        parts.update(build_channel(d, c))
    for t in d["tubes"]:
        parts[t["name"]] = build_tube(t)
    for p in d["pipes"]:
        parts[p["name"]] = build_pipe(p)
    for name, e in d["expect"].items():
        if "geom" in e and name not in parts:
            p = build_geom(e)
            parts[name] = _label(p if isinstance(p, Part) else Part(p.wrapped), name)
    return parts


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def _bbox_touch(a: Part, b: Part, tol: float = 0.5) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


def measure_insertion(d: dict, male: str, female: str, r: float) -> float:
    """Length of the male inside the female, on the geometry: volume of (male filled) n (female filled) over the
    male's entering cross-section, radius r."""
    me, fe = d["expect"][male], d["expect"][female]
    v = interference_volume(build_geom(me, filled=True), build_geom(fe, filled=True))
    return v / (math.pi * r * r)


def check_fall(paths: dict) -> None:
    for name, pts in paths.items():
        zs = [p[2] for p in pts]
        assert all(b < a for a, b in zip(zs, zs[1:])), f"return path from {name} does not fall all the way: {[round(z, 1) for z in zs]}"


def check_rack(rack: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(rack)
    label = f"nft_rack {rack}"
    exp = d["expect"]
    assert set(parts) == set(exp), f"{label}: built {sorted(set(parts) - set(exp))} not in params, missing {sorted(set(exp) - set(parts))}"
    for name, p in parts.items():
        assert p.is_valid, f"{label}: {name} invalid"
        assert len(p.solids()) == 1, f"{label}: {name} has {len(p.solids())} solids"
    asm = Compound(children=list(parts.values()))
    expect_solids(asm, len(exp), label)

    # every solid sits in params' analytic envelope and has params' hand volume
    tol = d["bbox_tol"]
    for name, p in parts.items():
        bb = p.bounding_box()
        got = (*tuple(bb.min), *tuple(bb.max))
        want = (*exp[name]["lo"], *exp[name]["hi"])
        bad = [round(g - w, 3) for g, w in zip(got, want) if abs(g - w) > tol]
        assert not bad, f"{label}: {name} bbox {[round(x, 2) for x in got]} vs params {[round(x, 2) for x in want]}"
        v, vw = p.volume, exp[name]["volume"]
        assert abs(v - vw) <= 1e-3 * vw, f"{label}: {name} volume {v:.1f} vs hand {vw:.1f}"
    lo, hi = d["bbox"]
    bb = asm.bounding_box()
    assert all(abs(a - b) < tol for a, b in zip((*tuple(bb.min), *tuple(bb.max)), (*lo, *hi))), f"{label}: assembly bbox {bb}"

    # function: no two solids overlap (touching faces and lines give zero volume)
    names = list(parts)
    overlaps, checked = [], 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if _bbox_touch(parts[names[i]], parts[names[j]]):
                checked += 1
                v = interference_volume(parts[names[i]], parts[names[j]])
                if v > 1e-3:
                    overlaps.append(f"{names[i]} x {names[j]}: {v:.3f} mm^3")
    assert not overlaps, f"{label}: overlaps:\n  " + "\n  ".join(overlaps)

    # function probes per channel, in channel-local coordinates mapped to world
    a = spec("frame_a")
    ch, ct, lt = spec("channel_h"), spec("channel_t"), spec("lid_t")
    for c in d["channels"]:
        loc = _channel_loc(d, c)
        w = lambda x, s_, z: tuple((loc * Pos(x, s_, z)).position)
        n = c["name"]
        body, lid = parts[f"{n}-body"], parts[f"{n}-lid"]
        mid_web = (c["sites"][0] + c["sites"][1]) / 2
        probes_lid = {f"{n} site {k + 1} open": (w(0, s_, ch + lt / 2), False) for k, s_ in enumerate(c["sites"])}
        probes_lid[f"{n} lid between sites 1-2"] = (w(0, mid_web, ch + lt / 2), True)
        probes_lid[f"{n} feed hole open"] = (w(0, c["s_feed"], ch + lt / 2), False)
        assert_material(lid, probes_lid)
        assert_material(body, {
            f"{n} floor": (w(0, mid_web, ct / 2), True),
            f"{n} channel open above the floor": (w(0, mid_web, ct + 1), False),
            f"{n} side wall": (w(spec("channel_w") / 2 - ct / 2, mid_web, ch / 2), True),
        })
        # rests on both rails: rail material just below the floor at each contact line, floor just above
        lv = c["level"]
        front, back = parts[f"L{lv}-RAIL-F"], parts[f"L{lv}-RAIL-B"]
        zf = next(x["z_f"] for x in d["levels_derived"] if x["i"] == lv)
        zb = zf - d["drop"]
        assert_material(front, {f"{n} front rail under the floor": ((c["xc"], a - 0.5, zf - 0.1), True)})
        assert_material(back, {f"{n} back rail under the floor": ((c["xc"], d["D"] - 0.5, zb - 0.1), True)})
        assert_material(body, {f"{n} floor over the front rail": ((c["xc"], a - 0.5, zf + d["slope"] * 0.5 + 0.1), True),
                               f"{n} floor over the back rail": ((c["xc"], d["D"] - 0.5, zb + d["slope"] * 0.5 + 0.1), True)})
        if "work_h" not in d:
            e = d["expect"][f"{n}-drain"]
            drain = parts[f"{n}-drain"]
            assert_material(drain, {f"{n} drain stub, mid": ((c["xc"], d["y_drain"], (e["lo"][2] + e["hi"][2]) / 2), True)})
            coll = parts[f"L{lv}-collector"]
            assert_material(coll, {f"{n} collector under the stub": ((c["xc"], d["y_drain"], e["lo"][2] - 0.1), True)})
            assert_material(drain, {f"{n} stub bottom on the collector": ((c["xc"], d["y_drain"], e["lo"][2] + 0.1), True)})
    rep = dict(assembly=asm, bbox=bb.size, volume=sum(p.volume for p in parts.values()), overlaps_checked=checked)
    if "work_h" in d:
        rep.update(check_plumbing(d, parts))
    expect_solids(asm, len(exp), label)
    return rep


def check_plumbing(d: dict, parts: dict) -> dict:
    """Table function layer: supply continuous, every socket's insertion measured, drop tips inside the collector,
    return falls and ends inside the tote. Raises."""
    label = f"nft_rack {d['rack']}"
    out = {}
    # supply chain: consecutive parts touch
    chain = d["supply_chain"]
    for a_, b_ in zip(chain, chain[1:]):
        dist = parts[a_].distance_to(parts[b_])
        assert dist < 1e-6, f"{label}: supply break between {a_} and {b_}: {dist:.3f} mm"
    for t in d["tubes"]:
        dist = parts[t["name"]].distance_to(parts["SUP-manifold"])
        assert dist < 1e-6, f"{label}: {t['name']} not on the manifold ({dist:.3f} mm)"
    # insertion depths on the geometry
    ins = {}
    for male, female, r, want, mn, what in d["joints"]:
        dist = parts[male].distance_to(parts[female])
        assert dist < 1e-6, f"{label}: {what}: {male} and {female} do not touch ({dist:.3f} mm)"
        if want is None:
            continue
        got = measure_insertion(d, male, female, r)
        ins[what] = got
        assert abs(got - want) < 0.05, f"{label}: {what}: inserted {got:.2f} mm, expected {want:.2f}"
        if mn is not None:
            assert got >= mn - 1e-6, f"{label}: {what}: inserted {got:.2f} mm, below the ASTM D2466 minimum {mn:.2f}"
    out["insertion"] = ins
    # drop tips: 1 mm past each tip is air inside the collector, between its floor and lid
    O, X, Y, Z = d["collector_frame"]
    cw, ch, ct = spec("channel_w"), spec("channel_h"), spec("channel_t")
    for c in d["channels"]:
        p = L_.add(c["tip"], c["o_drop"], 1.0)
        rel = tuple(p[i] - O[i] for i in range(3))
        x, z = L_.dot(rel, X), L_.dot(rel, Z)
        assert abs(x) < cw / 2 - ct and ct < z < ch, f"{label}: {c['name']} drop tip lands outside the collector (x {x:.1f}, z {z:.1f})"
        for nm in ("COLL-body", "COLL-lid"):
            assert_material(parts[nm], {f"{c['name']} tip in air ({nm})": (p, False)})
    # return end inside the tote cavity, below the lid, above the floor, clear of the pump
    pe = L_.add(d["return_end"], (0, 0, -1), 1.0)
    assert d["tote_floor_top"] < pe[2] < d["tote_lid_under"], f"{label}: return end z {pe[2]:.1f} not inside the tote"
    for nm in ("TOTE-body", "PUMP", "TOTE-lid"):
        assert_material(parts[nm], {f"return end in air ({nm})": (pe, False)})
    cav = d["tote_cavity"]
    k = (pe[2] - cav["z0"]) / (cav["z1"] - cav["z0"])
    (bx, by), (bL, bW) = cav["bot"]
    (tx, ty), (tL, tW) = cav["top"]
    x0, y0 = bx + (tx - bx) * k, by + (ty - by) * k
    x1, y1 = x0 + bL + (tL - bL) * k, y0 + bW + (tW - bW) * k
    assert x0 < pe[0] < x1 and y0 < pe[1] < y1, f"{label}: return end ({pe[0]:.1f}, {pe[1]:.1f}) outside the tote cavity at z {pe[2]:.1f}"
    check_fall(d["return_paths"])
    # nothing in the plumbing touches the frame or the channels (interference already zero); report the nearest
    plumbing = [n for n, e in d["expect"].items() if n.startswith(("SUP-", "RET-", "COLL-", "PUMP")) or n.endswith(("-drain", "-elbow"))]
    hard = [n for n, e in d["expect"].items() if e["kind"] in ("frame", "channel", "lid", "cap") and not n.startswith("COLL")]
    near = {}
    for p_ in ("SUP-valve", "SUP-valve-handle", "SUP-hose", "SUP-riser", "SUP-elbow", "RET-pipe", "COLL-body", "COLL-elbow"):
        best = min(((parts[p_].distance_to(parts[h]), h) for h in hard if _bbox_touch(parts[p_], parts[h], tol=200.0)),
                   default=(math.inf, None))
        near[p_] = best
    out["nearest_hard"] = near
    out["plumbing_parts"] = len(plumbing)
    return out


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for rack in ACTIVE_RACKS:
        parts = build_rack(rack)
        rep = check_rack(rack, parts)
        bb = rep["bbox"]
        print(f"{rack}: bbox {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm, solids {len(rep['assembly'].solids())}, "
              f"pairs checked {rep['overlaps_checked']}")
        for k, v in rep.get("insertion", {}).items():
            print(f"  inserted {v:6.2f} mm  {k}")
        for k, (dist, h) in rep.get("nearest_hard", {}).items():
            print(f"  nearest frame/channel to {k}: {dist:.1f} mm ({h})")
        export(rep["assembly"], f"nft_rack_{rack}", OUT)
        maybe_show(rep["assembly"], names=["rack"])
