"""desk_bench: a 72 x 34 in work desk, no hutch, no tote storage. The desktop frame is the four 72 in and
four 31 in 2x4s on hand: two 72s are the front and back rails, the other two are cut in half for the legs,
the four 31s are the two end rails and two joists. The 45 deg braces stiffen the legs along the bench.

Coordinates: origin = floor at the front-left outer corner; +X right, +Y back, +Z up. Boards are boxes:
name -> (kind, size, min corner), mm. Braces are prisms in the XZ plane: name -> (y0, thickness, polygon (x, z)).

Every number is a (value, TAG, source) triple (docs/PARAMS_CONVENTION.md).

    .venv/bin/python projects/desk_bench/params.py      # prints the design and cut list
"""
from __future__ import annotations

import math

STATUS = "concept"   # concept | passes | printed | parked

IN = 25.4

LUMBER = {
    "t": (1.5 * IN, "STANDARD", "ALSC PS 20: 2 in nominal -> 1-1/2 in"),
    "w4": (3.5 * IN, "STANDARD", "ALSC PS 20: 4 in nominal -> 3-1/2 in"),
}
PLY_T = (23 / 32 * IN, "STANDARD", "US DOC PS 1: 23/32 Performance Category, sold as 3/4 in")
SHEET = ((48 * IN, 96 * IN), "VENDOR", "plywood sheet, 4 x 8 ft, any home centre")

# On hand, 2x4 unless noted. The 72s are taken as UNCUT; if the front legs were already cut to 37-11/16 in,
# this design cannot use them.
ON_HAND = {
    "stick72": (4, 72 * IN, "on hand: 72 in 2x4s, taken as uncut, square ends"),
    "stick31": (4, 31 * IN, "on hand: 31 in 2x4s"),
    "brace": (4, 18 * IN, "on hand: 45 deg both ends, long point 18-24 in. UNVERIFIED: shortest taken as 18 in"),
    "x2x2": (8, 96 * IN, "on hand: 2x2s, UNVERIFIED length taken as 96 in; the design uses one"),
}

DESIGN = {
    "leg": (35.5 * IN, "DESIGN", "leg length: two per 72 in stick with a kerf, desktop surface lands at 36-1/4 in"),
    "work_height": ((34 * IN, 38 * IN), "DESIGN", "standing work height window"),
    "joists": (2, "DESIGN", "joists between the rails: ply spans <= 24 in"),
    "ply_span_max": (24 * IN, "DESIGN", "plywood unsupported span"),
    "brace_long": (17.5 * IN, "DESIGN", "brace long point after recut: the shortest on hand (18 in) less 1/2 in"),
    "stretcher_z": (8 * IN, "DESIGN", "end stretcher centre above the floor: a foot rail, stiffens the ends"),
    "kerf": (IN / 8, "DESIGN", "1/8 in per cut"),
    "screw_bite_min": (0.984 * IN, "STANDARD", "AWC NDS 2018: #8 wood screw 6D = 0.984 in penetration"),
    "screw_len": (2.5 * IN, "VENDOR", "#8 x 2-1/2 in wood screw, stocked length"),
}


def brace_polygon(x0: float, z0: float, sx: int, L: float, w: float):
    """45 deg brace in the corner of a vertical face (x = x0) and a horizontal line (z = z0, below it), long point L.
    sx = +1 away from the leg to the right, -1 to the left. Points (x, z)."""
    e = w * math.sqrt(2)
    a = L / math.sqrt(2) - e
    assert a > 0, f"brace long point {L / IN:.2f} in too short for a {w / IN} in board"
    return ((x0, z0 - a), (x0 + sx * a, z0), (x0 + sx * (a + e), z0), (x0, z0 - (a + e)))


def derive() -> dict:
    d = {k: v[0] for k, v in DESIGN.items()}
    t, w = LUMBER["t"][0], LUMBER["w4"][0]
    L, ply = ON_HAND["stick72"][1], PLY_T[0]
    S = ON_HAND["stick31"][1]
    D = S + 2 * t                       # depth: the 31s between the two 72s
    leg, ztop = d["leg"], d["leg"]
    zf = ztop - w                       # bottom of the frame
    b, p = {}, {}
    b["RAIL-F"] = ("x2x4", (L, t, w), (0, 0, zf))
    b["RAIL-B"] = ("x2x4", (L, t, w), (0, D - t, zf))
    b["END-L"] = ("x2x4", (t, S, w), (0, t, zf))
    b["END-R"] = ("x2x4", (t, S, w), (L - t, t, zf))
    n = d["joists"]
    gap = (L - 2 * t - n * t) / (n + 1)
    for i in range(n):
        b[f"JOIST-{i + 1}"] = ("x2x4", (t, S, w), (t + gap * (i + 1) + t * i, t, zf))
    # legs: inside the corner, 3-1/2 in along X, against the rail and the end rail
    for nm, x, y in (("LEG-FL", t, t), ("LEG-FR", L - t - w, t), ("LEG-BL", t, D - 2 * t), ("LEG-BR", L - t - w, D - 2 * t)):
        b[nm] = ("x2x4", (w, t, leg), (x, y, 0))
    # foot rails: 2x2 between the legs at each end, on the legs' inner faces
    lenS = D - 4 * t
    for nm, x in (("FOOT-L", t + 0.5 * IN), ("FOOT-R", L - t - w + 0.5 * IN)):
        b[nm] = ("x2x2", (t, lenS, t), (x, 2 * t, d["stretcher_z"] - t / 2))
    # braces: in each leg's plane, on the leg's inboard side, long edge up under the rail
    Lb = d["brace_long"]
    for nm, x0, sx, y in (("BRACE-FL", t + w, 1, t), ("BRACE-FR", L - t - w, -1, t),
                          ("BRACE-BL", t + w, 1, D - 2 * t), ("BRACE-BR", L - t - w, -1, D - 2 * t)):
        p[nm] = ("x2x4", y, t, brace_polygon(x0, zf, sx, Lb, w))
    d["top"] = dict(size=(L, D, ply), lo=(0, 0, ztop))
    d.update(boards=b, prisms=p, L=L, D=D, ply=ply, t=t, w=w, surface=ztop + ply, joist_gap=gap)
    # cut plan: legs from the 72s, the rest as is
    d["cuts"] = {
        "72 in": [("RAIL-F", L), ("RAIL-B", L), ("LEG-FL + LEG-FR", 2 * leg + d["kerf"]), ("LEG-BL + LEG-BR", 2 * leg + d["kerf"])],
        "31 in": [("END-L", S), ("END-R", S), ("JOIST-1", S), ("JOIST-2", S)],
        "2x2": [("FOOT-L", lenS), ("FOOT-R", lenS)],
        "brace": [(f"BRACE-{c}", Lb) for c in ("FL", "FR", "BL", "BR")],
    }
    d["buy"] = f"1 plywood sheet 4 x 8 ft: top {L / IN:.0f} x {D / IN:.0f} in; #8 screws 2-1/2 in (and 1-1/4 in for the top)"
    return d


def validate() -> dict:
    d = derive()
    for table in (LUMBER, DESIGN):
        for k, (_, tag, src) in table.items():
            assert tag and src, f"{k}: every number needs a tag and a source"
    lo, hi = d["work_height"]
    assert lo <= d["surface"] <= hi, f"surface {d['surface'] / IN:.2f} in outside {lo / IN:.0f}-{hi / IN:.0f} in"
    for name, stock in (("72 in", ON_HAND["stick72"][1]), ("31 in", ON_HAND["stick31"][1])):
        for nm, ln in d["cuts"][name]:
            assert ln <= stock + 1e-9, f"{nm} {ln / IN:.2f} in longer than the {name} stick"
    assert len(d["cuts"]["72 in"]) == ON_HAND["stick72"][0], "the four 72s are all used"
    assert len(d["cuts"]["31 in"]) == ON_HAND["stick31"][0], "the four 31s are all used"
    assert d["brace_long"] <= ON_HAND["brace"][1] - 0.5 * IN + 1e-9, "shortest brace cannot be recut to the design length"
    assert d["joist_gap"] <= d["ply_span_max"], f"ply spans {d['joist_gap'] / IN:.1f} in between supports"
    assert d["L"] <= SHEET[0][1] and d["D"] <= SHEET[0][0], "top does not fit the sheet"
    # screw bites: a 2-1/2 in screw through a 1-1/2 in member leaves 1.0 in in the next; leg face 1-1/2 in thick
    assert d["screw_len"] - d["t"] >= d["screw_bite_min"] - 1e-9, "screw bite under 6D"
    assert d["screw_len"] - d["t"] <= d["t"] - 0.25 * IN + 1e-9, "screw tip within 1/4 in of the far face"
    assert STATUS in ("concept", "passes", "printed", "parked"), f"STATUS {STATUS!r} not recognised"
    return d


if __name__ == "__main__":
    d = validate()
    f = lambda v: f"{v / IN:.3f} in"
    print(f"desk {f(d['L'])} x {f(d['D'])}, surface {f(d['surface'])}, joists {f(d['joist_gap'])} apart")
    for stock, items in d["cuts"].items():
        print(f"  {stock}: " + ", ".join(f"{n} {f(l)}" for n, l in items))
    print("  buy:", d["buy"])
