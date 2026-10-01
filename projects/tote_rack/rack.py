"""Tote rack: one solid per leg, stringer, runner and tie, placed from
params.derive; the totes as check envelopes and the screws as shank
envelopes for the function checks. Every number is from params.derive.

    .venv/bin/python projects/tote_rack/rack.py [--show]     # builds params.ACTIVE_RACKS
"""
from __future__ import annotations

from build123d import Align, Box, Compound, Cylinder, Location, Part, Plane

from cacad import assert_bbox, assert_material, expect_solids, interference_volume
from projects.tote_rack.params import ACTIVE_RACKS, derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def _box(size, lo, label: str) -> Part:
    b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
    b.label = label
    return b


def build_rack(rack: str) -> dict[str, Part]:
    """name -> solid, each in its assembled position."""
    d = derive(rack)
    return {name: _box(size, lo, name) for name, (_, size, lo) in d["boards"].items()}


def build_totes(rack: str) -> dict[str, Part]:
    """Rim and body envelopes per level, hung on the rails. Check bodies, not exported."""
    d = derive(rack)
    return {name: _box(size, lo, name) for name, (size, lo) in d["totes"].items()}


def build_screws(rack: str) -> Compound:
    """Shank envelopes, head point to tip, in params' order. Heads sit flush; not modelled."""
    d = derive(rack)
    r = d["screw_spec"]["d"] / 2
    out = []
    for _, _, _, head, u, ln, _ in d["screws"]:
        out.append(Cylinder(r, ln, align=(Align.CENTER, Align.CENTER, Align.MIN))
                   .moved(Location(Plane(origin=head, z_dir=u))))
    return Compound(children=out)


def _bbox_touch(a: Part, b: Part, tol: float = 0.5) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


def check_rack(rack: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(rack)
    label = f"rack {rack}"
    asm = Compound(children=list(parts.values()))
    assert all(p.is_valid for p in parts.values()), f"{label}: invalid solid"
    expect_solids(asm, len(d["boards"]), label)
    assert_bbox(asm, (d["W"], d["D"], d["H"]), 0.0, d["bbox_tol"], label)
    vol = sum(p.volume for p in parts.values())
    assert abs(vol - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{label}: wood volume {vol:.0f} vs hand {d['wood_volume']:.0f}"

    # every solid is exactly its cut, in its place: bbox matches params' min corner and size
    for name, p in parts.items():
        _, size, lo = d["boards"][name]
        bb = p.bounding_box()
        got = (*tuple(bb.min), *tuple(bb.size))
        assert all(abs(a - b) < d["bbox_tol"] for a, b in zip(got, (*lo, *size))), f"{label}: {name} is {got}, params says {(*lo, *size)}"

    # function: no two pieces of wood overlap (touching faces give zero volume)
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if not _bbox_touch(parts[names[i]], parts[names[j]]):
                continue
            v = interference_volume(parts[names[i]], parts[names[j]])
            assert v < 1e-3, f"{label}: {names[i]} and {names[j]} overlap by {v:.3f} mm^3"

    # load path at every level, left and right: runner on stringer on the leg's inner face, air in the clear span
    lt, st, sh, rh = d["leg_t"], d["str_t"], d["str_h"], d["run_h"]
    ymid = d["D"] / 2
    for i, rt in enumerate(d["railtops"], start=1):
        for side, xin in (("L", lt), ("R", d["W"] - lt - st)):
            xc = xin + st / 2
            lx = lt / 2 if side == "L" else d["W"] - lt / 2
            assert_material(asm, {
                f"L{i}{side} runner": ((xc, ymid, rt - rh / 2), True),
                f"L{i}{side} air above the rail": ((xc, ymid, rt + 0.5), False),
                f"L{i}{side} stringer under the runner": ((xc, ymid, rt - rh - sh / 2), True),
                f"L{i}{side} air under the stringer": ((xc, ymid, rt - rh - sh - 0.5), False),
                f"L{i}{side} leg beside the stringer end": ((lx, d["leg_d"] / 2, rt - rh - sh / 2), True),
                f"L{i}{side} clear span past the runner": ((xin + (st + 0.5 if side == "L" else -0.5), ymid, rt - rh / 2), False),
            })
    # the front is open below the top tie: nothing at y = 0 between the legs below H - str_h
    assert_material(asm, {
        "open front, mid height": ((d["W"] / 2, st / 2, d["H"] / 2), False),
        "open front, just under the top tie": ((d["W"] / 2, st / 2, d["H"] - sh - 0.5), False),
        "front top tie": ((d["W"] / 2, st / 2, d["H"] - sh / 2), True),
        "back top tie": ((d["W"] / 2, d["D"] - st / 2, d["H"] - sh / 2), True),
        "back bottom tie": ((d["W"] / 2, d["D"] - d["leg_d"] / 2, lt / 2), True),
        "air above the back bottom tie": ((d["W"] / 2, d["D"] - d["leg_d"] / 2, lt + 0.5), False),
    })

    # totes: rim and body touch nothing, rim bears on both runners, body hangs through the clear span
    totes = build_totes(rack)
    for tn, t in totes.items():
        for bn, p in parts.items():
            if not _bbox_touch(t, p):
                continue
            v = interference_volume(t, p)
            assert v < 1e-3, f"{label}: {tn} hits {bn} by {v:.3f} mm^3"
    for i, rt in enumerate(d["railtops"], start=1):
        rim, body = totes[f"TOTE-{i}-RIM"], totes[f"TOTE-{i}-BODY"]
        for side, xin in (("L", lt + st), ("R", d["W"] - lt - st)):
            # the rim's plan footprint covers the runner top by params' bearing: probe the rim just above the rail
            x_bear = xin - d["rim_bearing"] / 2 if side == "L" else xin + d["rim_bearing"] / 2
            assert_material(rim, {f"tote {i}{side} rim over the runner": ((x_bear, ymid, rt + 0.1), True)})
            assert_material(asm, {f"tote {i}{side} runner under the rim": ((x_bear, ymid, rt - 0.1), True)})
            assert_material(body, {f"tote {i}{side} body clear of the runner": ((x_bear, ymid, rt - 0.1), False)})
        bb = body.bounding_box()
        assert abs(bb.min.Z - d["tote_base"][i - 1]) < 1e-6
        assert d["span_inner"][0] < bb.min.X and bb.max.X < d["span_inner"][1], f"{label}: tote {i} body does not hang through the span"

    # screws: each passes through exactly its own board, bites its target by params' penetration, and hits nothing else
    screws = build_screws(rack)
    sv = 3.14159265 * (d["screw_spec"]["d"] / 2) ** 2
    for s, (sn, through_nm, into_nm, _, _, ln, pen) in zip(screws.solids(), d["screws"]):
        in_through = interference_volume(s, parts[through_nm])
        in_into = interference_volume(s, parts[into_nm])
        assert abs(in_through - sv * (ln - pen)) < 0.02 * sv * (ln - pen), f"{label}: {sn} passes {in_through / sv:.1f} of {through_nm}, params says {ln - pen:.1f}"
        assert abs(in_into - sv * pen) < 0.02 * sv * pen, f"{label}: {sn} bites {in_into / sv:.1f} into {into_nm}, params says {pen:.1f}"
        for other, p in parts.items():
            if other in (through_nm, into_nm) or not _bbox_touch(s, p):
                continue
            assert interference_volume(s, p) < 1e-3, f"{label}: {sn} hits {other}"
    expect_solids(asm, len(d["boards"]), label)   # nothing above may have taken a solid out of the assembly
    return dict(volume=vol, bbox=asm.bounding_box().size, assembly=asm, totes=Compound(children=list(totes.values())), screws=screws)


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for rack in ACTIVE_RACKS:
        parts = build_rack(rack)
        rep = check_rack(rack, parts)
        bb = rep["bbox"]
        print(f"{rack}: bbox {bb.X:.2f} x {bb.Y:.2f} x {bb.Z:.2f} mm, wood {rep['volume'] / 1e6:.2f} L, "
              f"solids {len(rep['assembly'].solids())}, totes {len(rep['totes'].solids())}, screws {len(rep['screws'].solids())}")
        export(rep["assembly"], f"tote_rack_{rack}", OUT)
        export(rep["totes"], f"tote_rack_{rack}_totes", OUT)
        maybe_show(rep["assembly"], rep["totes"], rep["screws"], names=["rack", "totes", "screws"])
