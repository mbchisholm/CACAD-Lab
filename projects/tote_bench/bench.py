"""Tote rack workbench: one solid per board, brace, diagonal and the plywood
top, placed from params.derive; the totes as check envelopes and the screws
as shank envelopes for the function checks. Every number is from params.derive.

    .venv/bin/python projects/tote_bench/bench.py [--show]
"""
from __future__ import annotations

from build123d import Align, Box, Compound, Cylinder, Location, Part, Plane, Polyline, extrude, make_face

from cacad import assert_bbox, assert_material, expect_solids, interference_volume
from projects.tote_bench.params import derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def _box(size, lo, label: str) -> Part:
    b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
    b.label = label
    return b


def _prism(axis: str, lo: float, th: float, poly, label: str) -> Part:
    """Extrude a polygon given in the plane normal to `axis` ((y, z) for "x", (x, z) for "y") over [lo, lo + th]."""
    if axis == "x":
        pts = [(lo, u, z) for u, z in poly]
        dirn = (1, 0, 0)
    else:
        pts = [(u, lo, z) for u, z in poly]
        dirn = (0, 1, 0)
    face = make_face(Polyline(*pts, close=True))
    p = extrude(face, amount=th, dir=dirn)
    p.label = label
    return p


def build_bench() -> dict[str, Part]:
    """name -> solid, each in its assembled position: boards, prisms, then the top."""
    d = derive()
    parts = {nm: _box(size, lo, nm) for nm, (_, size, lo) in d["boards"].items()}
    for nm, (_, axis, lo, th, poly) in d["prisms"].items():
        parts[nm] = _prism(axis, lo, th, poly, nm)
    tp = d["top"]
    top = Box(*tp["size"], align=ALIGN_MIN).moved(Location(tp["lo"]))
    for x, y, sx, sy in tp["notches"]:
        top = top - Box(sx, sy, tp["size"][2] + 2, align=ALIGN_MIN).moved(Location((x, y, tp["lo"][2] - 1)))
    top.label = "TOP"
    parts["TOP"] = top
    return parts


def build_totes() -> dict[str, Part]:
    d = derive()
    return {nm: _box(size, lo, nm) for nm, (size, lo) in d["totes"].items()}


def build_screws() -> Compound:
    """Shank envelopes, head point to tip, in params' order. Heads sit flush; not modelled."""
    d = derive()
    r = 0.164 * 25.4 / 2   # #8 shank, params.SCREW
    out = []
    for _, _, _, head, u, ln, _ in d["screws"]:
        out.append(Cylinder(r, ln, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Plane(origin=head, z_dir=u))))
    return Compound(children=out)


def _bbox_touch(a: Part, b: Part, tol: float = 0.5) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


def check_bench(parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive()
    t, w, s, D, W, H = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"]
    tol = d["bbox_tol"]
    asm = Compound(children=list(parts.values()))
    n = len(d["boards"]) + len(d["prisms"]) + 1
    assert all(p.is_valid for p in parts.values()), "invalid solid"
    expect_solids(asm, n, "bench")
    # overall: rails stick out t each side; the back stops t behind the back legs
    bb = asm.bounding_box()
    assert abs(bb.min.X + t) < tol and abs(bb.max.X - (W + t)) < tol, f"bench X {bb.min.X:.2f}..{bb.max.X:.2f}"
    assert abs(bb.min.Y) < tol and abs(bb.max.Y - (D + s)) < tol, f"bench Y {bb.min.Y:.2f}..{bb.max.Y:.2f}"
    assert abs(bb.min.Z) < tol and abs(bb.max.Z - H) < tol, f"bench Z {bb.min.Z:.2f}..{bb.max.Z:.2f}"
    # every board is its cut, in its place
    for nm, (_, size, lo) in d["boards"].items():
        b = parts[nm].bounding_box()
        got = (*tuple(b.min), *tuple(b.size))
        assert all(abs(a - e) < tol for a, e in zip(got, (*lo, *size))), f"{nm} is {got}, params says {(*lo, *size)}"
    # no two solids overlap (touching faces give zero volume)
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if _bbox_touch(parts[names[i]], parts[names[j]]):
                v = interference_volume(parts[names[i]], parts[names[j]])
                assert v < 1e-3, f"{names[i]} and {names[j]} overlap by {v:.3f} mm^3"
    # load path: the top sits on the work rungs, rails, posts and joist; each rung row sits against the uprights
    wt = d["work_top"]
    probes = {
        "top over the front work rung": ((W / 4, w + s / 2, wt + 0.5), True),
        "front work rung under the top": ((W / 4, w + s / 2, wt - 0.5), True),
        "top over the left work rail": ((-t / 2, D / 2, wt + 0.5), True),
        "left work rail under the top": ((-t / 2, D / 2, wt - 0.5), True),
        "joist under the top": ((d["boards"]["JOIST-1"][2][0] + s / 2, D / 2, wt - 0.5), True),
        "leg through the top notch": ((t / 2, w / 2, wt + d["ply"] / 2), True),
        "open front above the work top": ((W / 4, w / 2, (wt + H) / 2), False),
        "open front below the top tie": ((W / 4, w + s / 2, H - s - 1.0), False),
    }
    for r, z in enumerate(d["rows"]):
        probes[f"row {r} front rung at the left leg"] = ((t / 2, w + s / 2, z + s / 2), True)
        probes[f"row {r} back rung at the post"] = ((W / 2, D - w - s / 2, z + s / 2), True)
    assert_material(asm, probes)
    # totes: touch nothing, sit on both rungs, pass between leg and post
    totes = build_totes()
    for tn, tote in totes.items():
        for bn, p in parts.items():
            if _bbox_touch(tote, p):
                v = interference_volume(tote, p)
                assert v < 1e-3, f"{tn} hits {bn} by {v:.3f} mm^3"
    for tn, (size, lo) in d["totes"].items():
        lv = int(tn[5]) - 1
        z = d["tote_base"][lv]
        yb0, yb1 = d["tote_bottoms"][tn]
        xc = lo[0] + size[0] / 2
        for rung, y_in in ((f"RUNG-F{lv}", max(w, yb0) + 1.0), (f"RUNG-B{lv}", min(D - w, yb1) - 1.0)):
            assert_material(parts[rung], {f"{tn} bottom on {rung}": ((xc, y_in, z - 0.1), True)})
        # the back stop is behind the tote's back face at its top band
        stop = parts[f"STOP-{lv + 1}"]
        sb = stop.bounding_box()
        assert abs(sb.min.Y - (lo[1] + size[1])) < tol, f"{tn}: back stop not at the tote's back face"
        assert sb.max.Z <= lo[2] + size[2] + tol and sb.max.Z > lo[2] + size[2] - 25.4, f"{tn}: stop not at the rim band"
    # screws: each passes through its own member, bites its target by params' penetration, hits nothing else
    screws = build_screws()
    sv = 3.14159265 * (0.164 * 25.4 / 2) ** 2
    for sc, (sn, thr, into, _, _, ln, pen) in zip(screws.solids(), d["screws"]):
        a = interference_volume(sc, parts[thr])
        b = interference_volume(sc, parts[into])
        assert abs(a - sv * (ln - pen)) < 0.03 * sv * (ln - pen), f"{sn} passes {a / sv:.1f} of {thr}, params says {ln - pen:.1f}"
        assert abs(b - sv * pen) < 0.03 * sv * pen, f"{sn} bites {b / sv:.1f} into {into}, params says {pen:.1f}"
        for other, p in parts.items():
            if other in (thr, into) or not _bbox_touch(sc, p):
                continue
            assert interference_volume(sc, p) < 1e-3, f"{sn} hits {other}"
    expect_solids(asm, n, "bench")
    return dict(assembly=asm, totes=Compound(children=list(totes.values())), screws=screws,
                bbox=asm.bounding_box().size, volume=sum(p.volume for p in parts.values()))


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    parts = build_bench()
    rep = check_bench(parts)
    bb = rep["bbox"]
    print(f"tote_bench: bbox {bb.X / 25.4:.3f} x {bb.Y / 25.4:.3f} x {bb.Z / 25.4:.3f} in, "
          f"wood+ply {rep['volume'] / 1e6:.1f} L, solids {len(rep['assembly'].solids())}, "
          f"totes {len(rep['totes'].solids())}, screws {len(rep['screws'].solids())}")
    export(rep["assembly"], "tote_bench", OUT)
    export(rep["totes"], "tote_bench_totes", OUT)
    maybe_show(rep["assembly"], rep["totes"], rep["screws"], names=["bench", "totes", "screws"])
