"""Tote workbench: one solid per board, brace and the notched plywood top,
placed from params.derive; the totes as check envelopes and the screws as
shank envelopes for the function checks. Every number is from params.derive.

    .venv/bin/python projects/tote_bench/bench.py [--show]
"""
from __future__ import annotations

from build123d import Align, Box, Compound, Cylinder, Location, Part, Plane, Polyline, extrude, make_face

from cacad import assert_material, expect_solids, interference_volume
from projects.tote_bench.params import SCREW, derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def _box(size, lo, label: str) -> Part:
    b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
    b.label = label
    return b


def _prism(axis: str, lo: float, th: float, poly, label: str) -> Part:
    """Extrude a polygon given in the plane normal to `axis` ((y, z) for "x", (x, z) for "y") over [lo, lo + th]."""
    pts = [(lo, u, z) for u, z in poly] if axis == "x" else [(u, lo, z) for u, z in poly]
    p = extrude(make_face(Polyline(*pts, close=True)), amount=th, dir=(1, 0, 0) if axis == "x" else (0, 1, 0))
    p.label = label
    return p


def build_bench() -> dict[str, Part]:
    """name -> solid, each in its assembled position: boards, braces, then the top."""
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
    r = SCREW["d"][0] / 2
    return Compound(children=[Cylinder(r, ln, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Plane(origin=head, z_dir=u)))
                              for _, _, _, head, u, ln, _ in d["screws"]])


def _bbox_touch(a: Part, b: Part, tol: float = 0.5) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


def check_bench(parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive()
    t, w, s, D, W, H, ply = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"], d["ply"]
    tol = d["bbox_tol"]
    asm = Compound(children=list(parts.values()))
    n = len(d["boards"]) + len(d["prisms"]) + 1
    assert all(p.is_valid for p in parts.values()), "invalid solid"
    expect_solids(asm, n, "bench")
    bb = asm.bounding_box()
    want = ((0, W), (0, D), (0, H + ply))
    for i, (a, b) in enumerate(want):
        got = (tuple(bb.min)[i], tuple(bb.max)[i])
        assert abs(got[0] - a) < tol and abs(got[1] - b) < tol, f"bench extent {'XYZ'[i]} {got}, want {(a, b)}"
    for nm, (_, size, lo) in d["boards"].items():
        b = parts[nm].bounding_box()
        got = (*tuple(b.min), *tuple(b.size))
        assert all(abs(x - e) < tol for x, e in zip(got, (*lo, *size))), f"{nm} is {got}, params says {(*lo, *size)}"
    # nothing overlaps (touching faces give zero volume)
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if _bbox_touch(parts[names[i]], parts[names[j]]):
                v = interference_volume(parts[names[i]], parts[names[j]])
                assert v < 1e-3, f"{names[i]} and {names[j]} overlap by {v:.3f} mm^3"
    # load path: top on the front legs, aprons, side rails and joist; shelf on its rails; the hutch on the arms
    tf, ss = d["top_frame"], d["shelf_top"]
    xm = d["x_in"] + d["bay"] / 2
    probes = {
        "top over the front-left leg": ((t / 2, w / 2, tf + ply / 2), True),
        "front-left leg under the top": ((t / 2, w / 2, tf - 1), True),
        "front apron under the top": ((W / 4, t / 2, tf - 1), True),
        "top joist under the top": ((xm, D / 2, tf - 1), True),
        "top side rail under the top": ((1.5 * t, D / 2, tf - 1), True),
        "back leg through the top": ((t / 2, D - w / 2, tf + ply / 2), True),
        "shelf on its front rail": ((W / 4, w / 2, ss - 1), True),
        "shelf on its side rail": ((1.5 * t, D / 2, ss - 1), True),
        "shelf joist under the shelf": ((xm, D / 2, ss - 1), True),
        "hutch shelf on the arm": ((1.5 * t, D - d["hutch_shelf_d"] / 2, H - 1), True),
        "open front under the apron": ((W / 4, t / 2, d["apron"] - 10), False),
        "open front under the shelf rail": ((W / 4, t / 2, d["shelf_rail"] - 10), False),
        "open front of the hutch": ((W / 2, D - w - 20, (d["work_surface"] + H) / 2), False),
    }
    assert_material(asm, probes)
    # totes: touch nothing; the floor ones on the floor against the stretcher, the shelf ones on the shelf against the lip
    totes = build_totes()
    for tn, tote in totes.items():
        for bn, p in parts.items():
            if _bbox_touch(tote, p):
                v = interference_volume(tote, p)
                assert v < 1e-3, f"{tn} hits {bn} by {v:.3f} mm^3"
        size, lo = d["totes"][tn]
        xc, yc = lo[0] + size[0] / 2, lo[1] + size[1] / 2
        if tn.startswith("TOTE-2"):
            assert_material(parts["SHELF"], {f"{tn} on the shelf": ((xc, yc, lo[2] - 0.1), True)})
            assert abs(parts["LIP"].bounding_box().min.Y - (lo[1] + size[1])) < tol, f"{tn} not against the lip"
        else:
            assert abs(lo[2]) < tol, f"{tn} not on the floor"
            assert abs(parts["STRETCHER-B"].bounding_box().min.Y - (lo[1] + size[1])) < tol, f"{tn} not against the stretcher"
        # the tote's top clears the member above it at the front by the lid gap
        above = parts["APRON-F"] if tn.startswith("TOTE-2") else parts["SHELF-RAIL-F"]
        assert above.bounding_box().min.Z - (lo[2] + size[2]) >= d["clear_lid"] - tol, f"{tn} lid gap"
    # screws: each passes through its own member, bites its target by params' penetration, hits nothing else
    screws = build_screws()
    sv = 3.14159265 * (SCREW["d"][0] / 2) ** 2
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
          f"wood+sheet {rep['volume'] / 1e6:.1f} L, solids {len(rep['assembly'].solids())}, "
          f"totes {len(rep['totes'].solids())}, screws {len(rep['screws'].solids())}")
    export(rep["assembly"], "tote_bench", OUT)
    export(rep["totes"], "tote_bench_totes", OUT)
    maybe_show(rep["assembly"], rep["totes"], rep["screws"], names=["bench", "totes", "screws"])
