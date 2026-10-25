"""Raised bed family: an open-bottom box of 1x6 cedar fence pickets screwed to
a 4x4 cedar post in each inside corner. No legs, no floor.

Axis convention: Z up, Z=0 is the ground. The bed is centred on X and Y; X is
the long side. Pickets lie on edge in courses stacked from the ground. At a
corner the long picket runs the full outer length and covers the short
picket's end grain; the short picket butts between the long ones. The post
sits in the inside corner against both, top flush with the top course, so it
does not show from outside.

    plan, one corner (outside is down/left):

        |   |
        | S |######
        |   |# P  #          S  short-side picket, t thick, x in [-L/2, -L/2 + t]
        |   |######          P  post, p x p, x and y from -L/2 + t, -W/2 + t
        +---+----------      L  long-side picket, t thick, y in [-W/2, -W/2 + t], full length
        |     L

Everything downstream (bed.py, tests) reads `derive(bed)`.
"""
from __future__ import annotations

import math
from types import MappingProxyType

STATUS = "passes"   # concept | passes | printed | parked

IN = 25.4

# ---------------------------------------------------------------------------
# Bought lumber and screws. Actual (dressed) sizes, not nominal. Caliper the
# boards you buy and change the row, not the derive().
# ---------------------------------------------------------------------------
LUMBER = MappingProxyType(dict(
    # Common 5/8 x 5-1/2 x 6 ft; actual 0.57 x 5.5 x 72 in (Lowe's item 50333333, Alta Forest Products,
    # Western red cedar dog-ear picket). One end is dog-eared: two 45 deg corner clips leaving a flat top.
    picket=dict(t=0.57 * IN, w=5.5 * IN, stock=(72 * IN,), dog_ear=True,
                source="Lowe's 50333333 (Alta Forest Products) actual 0.57 x 5.5 in x 6 ft"),
    # 4x4 nominal, dressed 3-1/2 x 3-1/2 in (ALSC PS 20 dressed-size table, 4 in nominal).
    post=dict(t=3.5 * IN, w=3.5 * IN, stock=(96 * IN,), dog_ear=False,
              source="ALSC PS 20: 4 in nominal dresses to 3-1/2 in; 8 ft stock"),
))

# #8 exterior wood screw: shank 0.164 in (ASME B18.6.1 gauge table). Length ladder as sold in
# boxes of exterior/deck screws. Minimum penetration into the main member 6D (AWC NDS 2018, wood screws).
SCREWS = MappingProxyType(dict(
    no8=dict(d=0.164 * IN, lengths=tuple(x * IN for x in (1.25, 1.625, 2.0, 2.5, 3.0)),
             label="#8 exterior wood screw", min_penetration_d=6.0),
))

COMMON = MappingProxyType(dict(
    # --- cutting ---
    kerf=IN / 8,                  # per cut: material lost to the blade. 1/8 in covers a full-kerf 7-1/4 in blade
    # --- joinery ---
    screw="no8",
    screws_per_end=2,             # per picket end, into the post. Design choice
    screw_rows=(0.25, 0.75),      # height of each screw within the picket, as a fraction of w. Design choice
    # --- exploded view (display only, FreeCAD) ---
    explode_out_posts=2.0,        # pickets move straight out by this many post widths
    explode_lift_widths=0.5,      # each course lifts this many picket widths above the one below
    # --- checks ---
    screw_gap_min=3.0,            # closest approach between two screws' axes inside a post, minus their diameter
    bbox_tol=0.05,
))

# ---------------------------------------------------------------------------
# Family axis: outer footprint and number of courses. Inputs only.
# ---------------------------------------------------------------------------
BEDS = {
    # 4 x 2 ft outer, three courses (16.5 in): a common small bed, reachable from one side
    "4x2": dict(outer_l=48 * IN, outer_w=24 * IN, courses=3),
    # 4 x 4 ft, same height: each short side needs its own picket, see the cut plan
    "4x4": dict(outer_l=48 * IN, outer_w=48 * IN, courses=3),
    # sized so one picket yields one long and one short piece per course
    "46x24": dict(outer_l=46 * IN, outer_w=24 * IN, courses=3),
}

ACTIVE_BEDS = ("4x2",)


def _cut_plan(pieces: list[tuple[str, float]], stock: float, end_trim: float, kerf: float) -> list[list[tuple[str, float]]]:
    """First-fit decreasing: pack pieces into sticks of `stock`, each losing `end_trim` at one end and a kerf per cut.
    Returns one list of (name, length) per stick."""
    usable = stock - end_trim
    sticks: list[list[tuple[str, float]]] = []
    for name, ln in sorted(pieces, key=lambda p: -p[1]):
        assert ln + kerf <= usable + 1e-9, f"piece {name} {ln:.1f} longer than usable stock {usable:.1f}"
        for st in sticks:
            if sum(l + kerf for _, l in st) + ln + kerf <= usable + 1e-9:
                st.append((name, ln))
                break
        else:
            sticks.append([(name, ln)])
    return sticks


def _seg_dist(p0, p1, q0, q1) -> float:
    """Closest distance between segments p0-p1 and q0-q1 (3D), by sampling. Screws are short; 1 mm steps are enough."""
    def pts(a, b):
        n = max(2, int(math.dist(a, b)) + 1)
        return [tuple(a[i] + (b[i] - a[i]) * k / (n - 1) for i in range(3)) for k in range(n)]
    return min(math.dist(a, b) for a in pts(p0, p1) for b in pts(q0, q1))


def derive(bed: str, **overrides) -> dict:
    """Every dimension bed.py and the tests need. Overrides are for what-if tables only."""
    s = dict(BEDS[bed])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(bed=bed, **s, **c)
    pk, po = LUMBER["picket"], LUMBER["post"]
    sc = SCREWS[c["screw"]]
    t, w, p = pk["t"], pk["w"], po["t"]
    L, W, n = s["outer_l"], s["outer_w"], s["courses"]
    d.update(t=t, w=w, p=p, screw_spec=sc)

    d["height"] = n * w
    d["long_len"] = L
    d["short_len"] = W - 2 * t
    d["post_len"] = d["height"]                       # flush with the top course
    d["inner"] = (L - 2 * t, W - 2 * t)
    d["post_gap_long"] = d["inner"][0] - 2 * p        # clear span between posts, long side
    d["post_gap_short"] = d["inner"][1] - 2 * p

    # boards: name -> (kind, size xyz, min corner xyz)
    boards = {}
    for i in range(n):
        z = i * w
        boards[f"long_-Y_{i}"] = ("picket", (L, t, w), (-L / 2, -W / 2, z))
        boards[f"long_+Y_{i}"] = ("picket", (L, t, w), (-L / 2, W / 2 - t, z))
        boards[f"short_-X_{i}"] = ("picket", (t, d["short_len"], w), (-L / 2, -W / 2 + t, z))
        boards[f"short_+X_{i}"] = ("picket", (t, d["short_len"], w), (L / 2 - t, -W / 2 + t, z))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x0 = -L / 2 + t if sx < 0 else L / 2 - t - p
            y0 = -W / 2 + t if sy < 0 else W / 2 - t - p
            boards[f"post_{'-+'[sx > 0]}X{'-+'[sy > 0]}Y"] = ("post", (p, p, d["post_len"]), (x0, y0, 0.0))
    d["boards"] = boards

    # screws: shortest stocked length that reaches min penetration into the post; axis at the post's centre line
    need = t + sc["min_penetration_d"] * sc["d"]
    fit = [ln for ln in sc["lengths"] if ln >= need - 1e-9]
    d["screw_len"] = fit[0] if fit else None
    d["screw_penetration"] = (d["screw_len"] - t) if fit else None
    d["screw_penetration_min"] = sc["min_penetration_d"] * sc["d"]
    screws = []
    if fit:
        for name, (kind, size, lo) in boards.items():
            if kind != "picket":
                continue
            z0 = lo[2]
            for sx in (-1, 1):
                for sy in (-1, 1):
                    # post centre in plan
                    pcx = (L / 2 - t - p / 2) * sx
                    pcy = (W / 2 - t - p / 2) * sy
                    for f in c["screw_rows"][: c["screws_per_end"]]:
                        z = z0 + f * w
                        if name.startswith("long") and (name[5:7] == ("+Y" if sy > 0 else "-Y")):
                            y_out = sy * W / 2
                            screws.append((name, (pcx, y_out, z), (pcx, y_out - sy * d["screw_len"], z)))
                        if name.startswith("short") and (name[6:8] == ("+X" if sx > 0 else "-X")):
                            x_out = sx * L / 2
                            screws.append((name, (x_out, pcy, z), (x_out - sx * d["screw_len"], pcy, z)))
    d["screws"] = screws                              # (board, head point, tip point)
    # tip must stay inside the post: penetration < p
    d["screw_tip_inside_post"] = (d["screw_penetration"] is not None) and d["screw_penetration"] < p

    # cut plan
    trim = w / 2 if pk["dog_ear"] else 0.0            # a 45 deg dog-ear with a flat top clips less than w/2 of length
    d["picket_end_trim"] = trim
    pieces = [(nm, sz[0] if nm.startswith("long") else sz[1]) for nm, (k, sz, _) in boards.items() if k == "picket"]
    d["picket_plan"] = _cut_plan(pieces, pk["stock"][0], trim, c["kerf"])
    d["post_plan"] = _cut_plan([(nm, d["post_len"]) for nm, (k, _, _) in boards.items() if k == "post"], po["stock"][0], 0.0, c["kerf"])
    d["pickets_needed"] = len(d["picket_plan"])
    d["posts_needed"] = len(d["post_plan"])
    used = sum(ln for _, ln in pieces)
    d["picket_yield"] = used / (d["pickets_needed"] * pk["stock"][0])

    # soil: inside the pickets, less the posts, filled to the top
    d["soil_area"] = d["inner"][0] * d["inner"][1] - 4 * p * p
    d["soil_volume_l"] = d["soil_area"] * d["height"] / 1e6
    d["soil_volume_cuft"] = d["soil_volume_l"] / 28.3168

    # exploded view: one move per set of parts, applied in order; each part's total offset is the sum of its moves
    out, lift = c["explode_out_posts"] * p, c["explode_lift_widths"] * w
    pk_names = [nm for nm, (k, _, _) in boards.items() if k == "picket"]
    moves = [(f"{side} out", [nm for nm in pk_names if side in nm], vec) for side, vec in
             (("-Y", (0, -out, 0)), ("+Y", (0, out, 0)), ("-X", (-out, 0, 0)), ("+X", (out, 0, 0)))]
    moves += [(f"courses {i}+ up", [nm for nm in pk_names if int(nm.rsplit("_", 1)[1]) >= i], (0, 0, lift)) for i in range(1, n)]
    d["explode_moves"] = moves
    d["explode_offset"] = {nm: tuple(sum(v[a] for _, parts, v in moves if nm in parts) for a in range(3)) for nm in boards}

    # hand volume of wood, for check_bed
    d["wood_volume"] = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in boards.values())
    return d


def validate(bed: str) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(bed)
    sc = d["screw_spec"]
    assert d["short_len"] > 2 * d["p"], f"{bed}: short side {d['short_len']:.1f} does not fit two posts"
    assert d["post_gap_short"] > 0 and d["post_gap_long"] > 0, f"{bed}: posts meet"
    assert d["screw_len"] is not None, (
        f"{bed}: no stocked {sc['label']} reaches {d['t'] + d['screw_penetration_min']:.1f} (picket + 6D)")
    assert d["screw_penetration"] >= d["screw_penetration_min"] - 1e-9
    assert d["screw_tip_inside_post"], f"{bed}: screw {d['screw_len']:.1f} exits the post"
    # screws from the long and the short picket into the same post must not meet
    by_post = {}
    for board, head, tip in d["screws"]:
        key = (math.copysign(1, head[0]), math.copysign(1, head[1]))
        by_post.setdefault(key, []).append((board, head, tip))
    for key, ss in by_post.items():
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                if ss[i][0] == ss[j][0]:
                    continue
                gap = _seg_dist(ss[i][1], ss[i][2], ss[j][1], ss[j][2]) - sc["d"]
                assert gap >= d["screw_gap_min"], f"{bed}: screws {ss[i][0]} and {ss[j][0]} {gap:.1f} apart in post {key}"
    # every picket end reaches a post
    for nm, (k, sz, lo) in d["boards"].items():
        if k == "picket":
            assert sum(1 for b, _, _ in d["screws"] if b == nm) == 2 * d["screws_per_end"], f"{bed}: {nm} not screwed at both ends"
    return d


def report(bed: str) -> str:
    d = derive(bed)
    mm_in = lambda x: f"{x:.1f} mm ({x / IN:.2f} in)"
    lines = [
        f"{bed}: outer {d['outer_l']:.1f} x {d['outer_w']:.1f} x {d['height']:.1f} mm "
        f"({d['outer_l'] / IN:.1f} x {d['outer_w'] / IN:.1f} x {d['height'] / IN:.1f} in), {d['courses']} courses",
        f"  picket t {d['t']:.2f} w {d['w']:.2f}; post {d['p']:.1f} sq x {mm_in(d['post_len'])}",
        f"  cuts: {2 * d['courses']} x long {mm_in(d['long_len'])}, {2 * d['courses']} x short {mm_in(d['short_len'])}, 4 x post",
        f"  inside {d['inner'][0]:.1f} x {d['inner'][1]:.1f}; clear between posts: long {d['post_gap_long']:.1f}, short {d['post_gap_short']:.1f}",
        f"  screws: {len(d['screws'])} x {d['screw_spec']['label']} {mm_in(d['screw_len'])}, "
        f"{d['screw_penetration']:.1f} into post (min 6D {d['screw_penetration_min']:.1f}, post {d['p']:.1f})",
        f"  pickets: {d['pickets_needed']} x 6 ft (dog-ear end trim {d['picket_end_trim']:.1f}, kerf {d['kerf']:.2f}), "
        f"yield {100 * d['picket_yield']:.0f} %; posts: {d['posts_needed']} x 8 ft 4x4",
    ]
    for i, st in enumerate(d["picket_plan"]):
        used = sum(l + d["kerf"] for _, l in st) + d["picket_end_trim"]
        lines.append(f"    picket {i + 1}: " + " + ".join(f"{l:.1f}" for _, l in st) + f"  (offcut {LUMBER['picket']['stock'][0] - used:.1f})")
    lines.append(f"  soil to the rim: {d['soil_volume_l']:.0f} L ({d['soil_volume_cuft']:.1f} cu ft)")
    return "\n".join(lines)


if __name__ == "__main__":
    for bed in BEDS:
        try:
            validate(bed)
            print(report(bed), "\n  ok" + ("" if bed in ACTIVE_BEDS else " (inactive)"))
        except AssertionError as e:
            print(f"{bed}: FAIL: {e}")
