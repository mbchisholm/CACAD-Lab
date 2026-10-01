"""Raised bed: one solid per picket and post, placed from params.derive, and
the screws as envelopes for the function checks. Every number is from
params.derive.

    .venv/bin/python projects/raised_bed/bed.py [--show]     # builds params.ACTIVE_BEDS
"""
from __future__ import annotations

from build123d import Align, Axis, Box, Compound, Cylinder, Location, Part, Plane

from cacad import assert_bbox, assert_material, expect_solids, interference_volume
from projects.raised_bed.params import ACTIVE_BEDS, derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def build_bed(bed: str) -> dict[str, Part]:
    """name -> solid, each in its assembled position."""
    d = derive(bed)
    parts = {}
    for name, (_, size, lo) in d["boards"].items():
        b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
        b.label = name
        parts[name] = b
    return parts


def build_screws(bed: str) -> Compound:
    """Shank envelopes, head point to tip. Heads sit flush on the picket face; not modelled."""
    d = derive(bed)
    r = d["screw_spec"]["d"] / 2
    out = []
    for _, head, tip in d["screws"]:
        axis = tuple(t - h for h, t in zip(head, tip))
        z_dir = tuple(a / d["screw_len"] for a in axis)
        out.append(Cylinder(r, d["screw_len"], align=(Align.CENTER, Align.CENTER, Align.MIN))
                   .moved(Location(Plane(origin=head, z_dir=z_dir))))
    return Compound(children=out)


def check_bed(bed: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(bed)
    label = f"bed {bed}"
    asm = Compound(children=list(parts.values()))
    assert all(p.is_valid for p in parts.values()), f"{label}: invalid solid"
    expect_solids(asm, len(d["boards"]), label)
    assert_bbox(asm, (d["outer_l"], d["outer_w"], d["height"]), 0.0, d["bbox_tol"], label)
    vol = sum(p.volume for p in parts.values())
    assert abs(vol - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{label}: wood volume {vol:.0f} vs hand {d['wood_volume']:.0f}"

    # every solid is exactly its cut: longest bbox side matches the cut list
    for name, p in parts.items():
        kind, size, _ = d["boards"][name]
        got = sorted(tuple(p.bounding_box().size))
        assert all(abs(a - b) < d["bbox_tol"] for a, b in zip(got, sorted(size))), f"{label}: {name} is {got}, cut list says {size}"

    # function: no two pieces of wood overlap (touching faces give zero volume)
    names = list(parts)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            v = interference_volume(parts[names[i]], parts[names[j]])
            assert v < 1e-3, f"{label}: {names[i]} and {names[j]} overlap by {v:.3f} mm^3"

    # every post sits against a long and a short picket, and in the corner, not outside it
    t, p, L, W = d["t"], d["p"], d["outer_l"], d["outer_w"]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (L / 2 - t - p / 2), sy * (W / 2 - t - p / 2)
            z = d["w"] / 2
            assert_material(asm, {
                f"post {sx:+}{sy:+} centre": ((cx, cy, z), True),
                f"long picket behind post {sx:+}{sy:+}": ((cx, sy * (W / 2 - t / 2), z), True),
                f"short picket beside post {sx:+}{sy:+}": ((sx * (L / 2 - t / 2), cy, z), True),
                f"air inside past post {sx:+}{sy:+}": ((cx - sx * (p / 2 + 1), cy - sy * (p / 2 + 1), z), False),
            })
    # the soil cavity is open top and bottom
    assert_material(asm, {"soil cavity": ((0, 0, d["height"] / 2), False),
                          "open bottom": ((0, 0, 0.5), False)})

    # screws: each goes through exactly its own picket and one post, never another picket or out of the post
    screws = build_screws(bed)
    posts = [parts[n] for n, (k, _, _) in d["boards"].items() if k == "post"]   # a list: Compound(children=) would re-parent them out of asm
    pickets = {n: parts[n] for n, (k, _, _) in d["boards"].items() if k == "picket"}
    sv = 3.14159265 * (d["screw_spec"]["d"] / 2) ** 2
    for s, (board, _, _) in zip(screws.solids(), d["screws"]):
        in_own = interference_volume(s, pickets[board])
        in_post = sum(interference_volume(s, po) for po in posts)
        assert abs(in_own - sv * d["t"]) < 0.02 * sv * d["t"], f"{label}: screw in {board} passes {in_own / sv:.1f} of picket"
        assert abs(in_post - sv * d["screw_penetration"]) < 0.02 * sv * d["screw_penetration"], \
            f"{label}: screw in {board} bites {in_post / sv:.1f} into a post, params says {d['screw_penetration']:.1f}"
        for other, pk in pickets.items():
            if other != board:
                assert interference_volume(s, pk) < 1e-3, f"{label}: screw from {board} hits {other}"
    expect_solids(asm, len(d["boards"]), label)   # again: nothing above may have taken a solid out of the assembly
    return dict(volume=vol, bbox=asm.bounding_box().size, assembly=asm, screws=screws)


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for bed in ACTIVE_BEDS:
        parts = build_bed(bed)
        rep = check_bed(bed, parts)
        bb = rep["bbox"]
        print(f"{bed}: bbox {bb.X:.2f} x {bb.Y:.2f} x {bb.Z:.2f}, wood {rep['volume'] / 1e6:.2f} L, "
              f"solids {len(rep['assembly'].solids())}, screws {len(rep['screws'].solids())}")
        export(rep["assembly"], f"raised_bed_{bed}", OUT)
        maybe_show(rep["assembly"], rep["screws"], names=["bed", "screws"])
