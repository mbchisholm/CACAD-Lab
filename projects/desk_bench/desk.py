"""desk_bench model: one solid per board, brace and the plywood top, placed from params.derive, checked for
overlaps and extents, exported to out/desk_bench.step.

    .venv/bin/python projects/desk_bench/desk.py
"""
from __future__ import annotations

from build123d import Align, Box, Compound, Location, Part, Polyline, extrude, make_face

from cacad import interference_volume
from cacad.export import export
from projects.desk_bench.params import IN, validate

MIN = (Align.MIN, Align.MIN, Align.MIN)


def build() -> dict[str, Part]:
    d = validate()
    parts = {}
    for nm, (_, size, lo) in d["boards"].items():
        parts[nm] = Box(*size, align=MIN).moved(Location(lo))
    for nm, (_, y0, th, poly) in d["prisms"].items():
        parts[nm] = extrude(make_face(Polyline(*[(x, y0, z) for x, z in poly], close=True)), amount=th, dir=(0, 1, 0))
    parts["TOP"] = Box(*d["top"]["size"], align=MIN).moved(Location(d["top"]["lo"]))
    for nm, p in parts.items():
        p.label = nm
    return parts


def check(parts: dict[str, Part]) -> None:
    d = validate()
    assert all(p.is_valid for p in parts.values()), "invalid solid"
    bb = Compound(children=list(parts.values())).bounding_box()
    got = (*tuple(bb.size),)
    want = (d["L"], d["D"], d["surface"])
    assert all(abs(g - w) < 0.05 for g, w in zip(got, want)), f"extent {got}, want {want}"
    names = list(parts)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = interference_volume(parts[a], parts[b])
            assert v < 1.0, f"{a} overlaps {b}: {v:.1f} mm3"


if __name__ == "__main__":
    parts = build()
    check(parts)
    out = __file__.rsplit("/", 1)[0] + "/out"
    step, _ = export(Compound(children=list(parts.values())), "desk_bench", out)
    print(f"{len(parts)} solids, extent OK, no overlaps -> {step}")
