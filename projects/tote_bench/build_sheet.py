"""Build sheet from params: what to cut from what is on hand, the layout marks
on the legs measured from the floor, an assembly order that can be built, the
screws per joint and the shopping list. Nothing here holds a number; every
length, mark and count is read from params.validate().

The marks come from contact: each board or brace that touches a leg gives the
face it lands on and its height range there. The assembly order is a schedule
that is checked, not just written: each step brings pieces (or a sub-assembly)
in along one direction onto the work so far, and

- a modelled screw is driven in the step where its two members first meet; if
  its head ends up against a third member, that member must arrive in a later
  step (the head is buried once it is there);
- nothing already in place may stand in the path of a piece being brought in
  (a sweep of its box along the step's direction; the top's notches count).

Anything that fails either rule is listed under "Open issues".

    .venv/bin/python projects/tote_bench/build_sheet.py     # -> out/build_sheet.md
"""
from __future__ import annotations

import math

from projects.tote_bench.params import INVENTORY, SCREW, STORE_2X4, STORE_PEG, STORE_PLY, tape, validate

# screw (through, into) names -> params' joint name. A pattern ending in "-" is a prefix, otherwise the exact name.
JOINT_OF = (
    (("LEG-",), ("SIDE-",), "leg->side rail"),
    (("SIDE-",), ("APRON-", "SHELF-RAIL-", "STRETCHER-"), "side rail->apron/rail"),
    (("APRON-",), ("JOIST-TOP",), "apron->joist"),
    (("SHELF",), ("LIP",), "ply->lip"),
    (("CLEAT-",), ("LEG-",), "cleat->leg"),
    (("ARM-",), ("LEG-",), "arm->leg"),
    (("BRACE-",), ("ARM-",), "brace->arm"),
)

# directions a piece is brought in along: (axis, sign of the motion)
DOWN, FROM_FRONT, FROM_LEFT, FROM_RIGHT = (2, -1), (1, 1), (0, 1), (0, -1)
HOW = {DOWN: "lowered from above", FROM_FRONT: "brought in from the front",
       FROM_LEFT: "offered up from the left", FROM_RIGHT: "offered up from the right"}


def _is(nm: str, pats) -> bool:
    return any(nm.startswith(p) if p.endswith("-") else nm == p for p in pats)


def joint_of(d: dict, screw) -> str:
    nm, thr, into, _, _, ln, pen = screw
    for a, b, jn in JOINT_OF:
        if _is(thr, a) and _is(into, b):
            through, _, jl = d["joints"][jn]
            assert abs(jl - ln) < 1e-6 and abs(ln - through - pen) < 1e-6, f"{nm}: not a {jn} screw"
            return jn
    raise AssertionError(f"{nm}: no joint for {thr} -> {into}")


def screws_by_joint(d: dict) -> dict[str, list]:
    out = {jn: [] for jn in d["joints"]}
    for sc in d["screws"]:
        out[joint_of(d, sc)].append(sc)
    return out


def counted_screws(d: dict) -> dict[float, int]:
    """Modelled + plywood + toe screws by length; params' screw_counts must equal it."""
    out: dict[float, int] = {}
    for sc in d["screws"]:
        out[sc[5]] = out.get(sc[5], 0) + 1
    lp = d["joints"]["ply->frame"][2]
    out[lp] = out.get(lp, 0) + sum(d["ply_screws"].values())
    toe = SCREW["toe_len"][0]
    out[toe] = out.get(toe, 0) + sum(d["toe_screws"].values())
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# geometry, as boxes (no kernel)
# ---------------------------------------------------------------------------
def extents(d: dict, top: bool = False, totes: bool = False) -> dict[str, tuple]:
    """name -> (min xyz, max xyz) for every board and prism (prisms by their box), optionally the top and the totes."""
    ex = {nm: (lo, tuple(a + b for a, b in zip(lo, size))) for nm, (_, size, lo) in d["boards"].items()}
    for nm, (_, axis, lo, th, poly) in d["prisms"].items():
        us, zs = [p[0] for p in poly], [p[1] for p in poly]
        ex[nm] = ((lo, min(us), min(zs)), (lo + th, max(us), max(zs))) if axis == "x" else \
                 ((min(us), lo, min(zs)), (max(us), lo + th, max(zs)))
    if top:
        tp = d["top"]
        ex["TOP"] = (tp["lo"], tuple(a + b for a, b in zip(tp["lo"], tp["size"])))
    if totes:
        for nm, (size, lo) in d["totes"].items():
            ex[nm] = (lo, tuple(a + b for a, b in zip(lo, size)))
    return ex


def _in_poly(u: float, z: float, poly) -> bool:
    inside = False
    for (u0, z0), (u1, z1) in zip(poly, poly[1:] + poly[:1]):
        if (z0 > z) != (z1 > z) and u < u0 + (z - z0) * (u1 - u0) / (z1 - z0):
            inside = not inside
    return inside


def solid_at(d: dict, p) -> list[str]:
    """Every board, prism or the top that holds point p strictly inside."""
    tol = d["bbox_tol"]
    hit = [nm for nm, (_, size, lo) in d["boards"].items()
           if all(lo[i] + tol < p[i] < lo[i] + size[i] - tol for i in range(3))]
    for nm, (_, axis, lo, th, poly) in d["prisms"].items():
        a, u = (0, 1) if axis == "x" else (1, 0)
        if lo + tol < p[a] < lo + th - tol and _in_poly(p[u], p[2], list(poly)):
            hit.append(nm)
    tp = d["top"]
    if all(tp["lo"][i] + tol < p[i] < tp["lo"][i] + tp["size"][i] - tol for i in range(3)):
        if not any(x < p[0] < x + sx and y < p[1] < y + sy for x, y, sx, sy in tp["notches"]):
            hit.append("TOP")
    return hit


def buried_heads(d: dict) -> list[tuple[str, str, str]]:
    """(screw, its target, the member its head ends up against): those screws go in before that member."""
    out = []
    for nm, thr, into, head, u, _, _ in d["screws"]:
        behind = tuple(h - ui * 1.0 for h, ui in zip(head, u))     # 1 mm behind the head, where the driver goes
        for m in solid_at(d, behind):
            if m not in (thr, into):
                out.append((nm, into, m))
    return out


def access_conflicts(d: dict) -> list[tuple[str, str]]:
    """Pairs of buried screws that need both orders: A's head is under B's target and B's head under A's target."""
    bh = buried_heads(d)
    return [(a[0], b[0]) for a in bh for b in bh if a[1] == b[2] and b[1] == a[2] and a[0] < b[0]]


def _overlap(ex, a, b, axes, tol) -> bool:
    return all(min(ex[a][1][i], ex[b][1][i]) - max(ex[a][0][i], ex[b][0][i]) > tol for i in axes)


def _in_notch(d: dict, ex, a, b) -> bool:
    """The plan overlap of a and b falls inside one of the top's notches (so the top does not cover it)."""
    tol = d["bbox_tol"]
    lo = [max(ex[a][0][i], ex[b][0][i]) for i in (0, 1)]
    hi = [min(ex[a][1][i], ex[b][1][i]) for i in (0, 1)]
    return any(x - tol <= lo[0] and hi[0] <= x + sx + tol and y - tol <= lo[1] and hi[1] <= y + sy + tol
               for x, y, sx, sy in d["top"]["notches"])


def blocks(d: dict, ex, a: str, b: str, how) -> bool:
    """Does a, already in place, stand in the path of b brought in along `how` from far away?"""
    axis, sg = how
    tol = d["bbox_tol"]
    if not _overlap(ex, a, b, [i for i in range(3) if i != axis], tol):
        return False
    if axis == 2 and "TOP" in (a, b) and _in_notch(d, ex, a, b):
        return False
    return ex[a][0][axis] >= ex[b][1][axis] - tol if sg < 0 else ex[a][1][axis] <= ex[b][0][axis] + tol


def marks(d: dict) -> dict[str, list[tuple[str, str, float, float, str]]]:
    """leg -> [(face, member, z bottom, z top, what)] for every board or brace that lands on a leg's face."""
    ex = extents(d)
    W, tol = d["W"], d["bbox_tol"]
    out = {}
    for up in [n for n in d["boards"] if n.startswith("LEG-")]:
        ulo, uhi = ex[up]
        rows = []
        for m, (mlo, mhi) in ex.items():
            if m == up:
                continue
            for i, word_lo, word_hi in ((0, "", ""), (1, "front face", "back face")):
                j = 1 - i
                side = "lo" if abs(mhi[i] - ulo[i]) < tol else "hi" if abs(mlo[i] - uhi[i]) < tol else None
                if side is None:
                    continue
                if min(mhi[j], uhi[j]) - max(mlo[j], ulo[j]) <= tol or min(mhi[2], uhi[2]) - max(mlo[2], ulo[2]) <= tol:
                    continue
                if i == 0:
                    outer = (side == "lo") == ((ulo[0] + uhi[0]) / 2 < W / 2)
                    face = "outer face" if outer else "inner face"
                else:
                    face = word_lo if side == "lo" else word_hi
                if m in d["prisms"]:
                    _, axis, _, _, poly = d["prisms"][m]
                    k = 1 if axis == "x" else 0
                    on = [z for u, z in poly if ulo[k] - tol <= u <= uhi[k] + tol]
                    if on:
                        rows.append((face, m, min(on), max(on), "plumb end"))
                else:
                    rows.append((face, m, max(mlo[2], ulo[2]), min(mhi[2], uhi[2]), ""))
        out[up] = sorted(rows, key=lambda r: (r[0], r[2]))
    return out


# ---------------------------------------------------------------------------
# assembly schedule
# ---------------------------------------------------------------------------
def steps(d: dict) -> list[dict]:
    """The assembly order: each step brings `move` [(name, how)] (a name stands for the sub-assembly it is in by then)
    onto the sub-assembly holding `onto`; `counted` lists the screws params counts but does not model."""
    f = tape
    t, w, s, D, W, H = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"]
    ex = extents(d, top=True, totes=True)
    sp, toe = d["ply_screws"], d["toe_screws"]
    lp, tl = d["joints"]["ply->frame"][2], SCREW["toe_len"][0]
    jt = ex["JOIST-TOP"][0][0] - ex["APRON-F"][0][0]
    js = ex["JOIST-SHELF"][0][0] - ex["SHELF-RAIL-F"][0][0]
    lip_in = ex["LIP"][0][0] - ex["SHELF"][0][0]
    diag = math.hypot(W - 2 * t, D)
    over_top = [n for n in ex if n != "TOP" and blocks(d, ex, n, "TOP", DOWN)]
    per_brace = toe["brace_feet"] // len(d["prisms"])
    peg_z = ex["PEGBOARD"][0][2]
    floor_t = sorted(n for n in d["totes"] if d["totes"][n][1][2] == 0.0)
    shelf_t = sorted(n for n in d["totes"] if n not in floor_t)
    return [
        dict(key="top joist", move=[("JOIST-TOP", DOWN)], onto=["APRON-F", "APRON-B"], counted=[],
             text=f"**Top frame, flat on the floor.** Stand APRON-F and APRON-B on edge, and drop JOIST-TOP (on edge) between "
                  f"them, its left face {f(jt)} from the aprons' left ends, tops flush. Screw through each apron's outer face "
                  f"into the joist's end grain."),
        dict(key="top frame", move=[("APRON-F", DOWN)], onto=["SIDE-L-TOP", "SIDE-R-TOP"], counted=[],
             text=f"Set the aprons between SIDE-L-TOP and SIDE-R-TOP (on edge), aprons' outer faces flush with the side "
                  f"rails' ends, all tops flush. Screw through each side rail's outer face into the aprons' end grain, on "
                  f"the apron's centre line. Square it: {f(diag)} corner to corner both ways."),
        dict(key="shelf frame", move=[("SHELF-RAIL-F", DOWN), ("SHELF-RAIL-B", DOWN)], onto=["SIDE-L-SHELF", "SIDE-R-SHELF"],
             counted=[],
             text=f"**Shelf frame.** SHELF-RAIL-F and SHELF-RAIL-B lie flat between SIDE-L-SHELF and SIDE-R-SHELF (on edge), "
                  f"outer edges flush with the side rails' ends, tops flush. Screw through each side rail's outer face into "
                  f"the rails' end grain, mid-thickness. Square it: {f(diag)} corner to corner."),
        dict(key="shelf joist", move=[("JOIST-SHELF", DOWN)], onto=["SHELF-RAIL-F"],
             counted=[(toe["shelf_joist"], tl, "toe, shelf joist -> shelf rails")],
             text=f"Drop the 2x2 JOIST-SHELF between the shelf rails' inner edges, its left face {f(js)} from the rails' left "
                  f"ends, top flush. Toe-screw {toe['shelf_joist'] // 2} per end into the rails."),
        dict(key="shelf panel", move=[("LIP", DOWN)], onto=["SHELF"], counted=[],
             text=f"**Shelf panel, upside down.** Lay the 2x2 LIP on the bench and the SHELF plywood on it, good face down: "
                  f"the panel's back edge flush with the lip's back face, the lip {f(lip_in)} in from each side edge. Screw down "
                  f"through the plywood into the lip, {f(s / 2)} in from the back edge, then turn the panel over."),
        dict(key="shelf on", move=[("SHELF", DOWN)], onto=["SIDE-L-SHELF"],
             counted=[(sp["shelf"], lp, "ply->frame, shelf")],
             text=f"Lay the shelf panel on the shelf frame, lip up at the back, edges flush with the side rails' outer faces "
                  f"and the frame's ends: the panel squares the frame. Screw down at {f(d['ply_screw_pitch'])} or closer into "
                  f"both side rails, both shelf rails and the joist; along the back rail keep to the {f(w - s)} strip in front "
                  f"of the lip."),
        dict(key="floor frame", move=[("STRETCHER-B", DOWN)], onto=["SIDE-L-FLOOR", "SIDE-R-FLOOR"], counted=[],
             text=f"**Floor frame.** STRETCHER-B on edge between SIDE-L-FLOOR and SIDE-R-FLOOR (on edge), its outer face "
                  f"flush with the side rails' back ends, bottoms flush. Screw through each side rail's outer face into its end "
                  f"grain. Square it: {f(diag)} corner to corner."),
        dict(key="left legs", move=[("LEG-FL", FROM_LEFT), ("LEG-BL", FROM_LEFT)],
             onto=["SIDE-L-TOP", "SIDE-L-SHELF", "SIDE-L-FLOOR"], counted=[],
             text=f"**Left legs.** Lay the three frames on their right side rails, front ends in a line, and lay LEG-FL and "
                  f"LEG-BL across the left side rails, outer faces up: LEG-FL's front face flush with the frames' front ends, "
                  f"LEG-BL's back face with their back ends, both bottoms flush with the floor frame's bottom edge, each rail "
                  f"on its marks (section 2). Four screws per joint from the leg's outer face, at the positions in section 4 "
                  f"(they miss the frames' end screws under the leg)."),
        dict(key="right legs", move=[("LEG-FR", FROM_RIGHT), ("LEG-BR", FROM_RIGHT)],
             onto=["SIDE-R-TOP", "SIDE-R-SHELF", "SIDE-R-FLOOR"], counted=[],
             text="**Right legs.** Turn it over and do the same with LEG-FR and LEG-BR. Stand the bench up on its legs."),
        dict(key="top", move=[("TOP", DOWN)], onto=["LEG-BL"], counted=[(sp["top"], lp, "ply->frame, top")],
             text=f"**Top.** Lift the TOP over the back legs and lower it, notches round them, onto the front legs and the "
                  f"top frame, flush at the front and sides (work surface {f(d['work_surface'])}). Screw down at "
                  f"{f(d['ply_screw_pitch'])} or closer into the aprons, the top side rails and the joist. It goes on now: "
                  + ", ".join(over_top) + " all stand over it."),
        dict(key="arms", move=[("ARM-L", DOWN), ("ARM-R", DOWN)], onto=["LEG-BL"], counted=[],
             text=f"**Hutch arms.** ARM-L and ARM-R on edge on the back legs' inner faces, tops flush with the legs' tops "
                  f"({f(H)}), back ends flush with the legs' back faces; they stand {f(d['hutch_shelf_d'] - w)} in front of the "
                  f"legs. Screw from inside through the arm into the leg."),
        dict(key="braces", move=[("BRACE-L", FROM_LEFT), ("BRACE-R", FROM_RIGHT)], onto=["LEG-BL"],
             counted=[(toe["brace_feet"], tl, "toe, brace feet -> back legs")],
             text=f"**Braces.** BRACE-L and BRACE-R in the plane of the back legs against the arms' outer faces, outer faces "
                  f"flush with the legs' outer faces: plumb end on the leg's front face, top cut face level with the leg's and "
                  f"arm's tops, long point down. Screw through the brace into the arm, then {per_brace} toe screw through the "
                  f"foot into the leg."),
        dict(key="cleats", move=[("CLEAT-L", FROM_FRONT), ("CLEAT-R", FROM_FRONT)], onto=["LEG-BL"], counted=[],
             text=f"**Pegboard cleats.** CLEAT-L and CLEAT-R (2x2, {f(d['peg_h'])}) on the back legs' inner faces, front faces "
                  f"flush with the legs' front faces, bottom ends at {f(peg_z)}. Screw through the cleat into the leg."),
        dict(key="pegboard", move=[("PEGBOARD", FROM_FRONT)], onto=["CLEAT-L"], counted=[],
             text=f"**Pegboard** against the cleats' front faces between the back legs, bottom edge at {f(peg_z)} "
                  f"({f(d['peg_lift'])} over the work surface): {d['peg_screws']} pan-head screws with washers through its "
                  f"holes, {d['peg_screws'] // 2} per cleat."),
        dict(key="hutch shelf", move=[("HUTCH", DOWN)], onto=["ARM-L"], counted=[(sp["hutch"], lp, "ply->frame, hutch shelf")],
             text=f"**Hutch shelf** on the legs, arms and braces, flush with the back and the legs' outer faces. Screw down "
                  f"into the arms and the leg tops."),
        dict(key="totes", move=[(n, FROM_FRONT) for n in floor_t + shelf_t], onto=["LEG-FL"], counted=[],
             text=f"**Totes.** Slide {' and '.join(floor_t)} in on the floor until they meet STRETCHER-B, and "
                  f"{' and '.join(shelf_t)} in on the shelf until they meet the LIP; parked, their fronts are "
                  f"{f(d['front_reveal'])} behind the bench front, lids {', '.join(f(g) for g in d['lid_gap'])} under the "
                  f"rail above."),
    ]


def schedule(d: dict, order: list[str] | None = None) -> dict:
    """Run the steps (or the same steps in `order`, by key): when each screw is driven, which buried heads are covered
    too early, what blocks a piece's path, what never joins."""
    ex = extents(d, top=True, totes=True)
    group = {n: frozenset([n]) for n in ex}
    driven, covered, blocked = {}, {}, []
    buried = buried_heads(d)
    st_all = steps(d)
    if order is not None:
        by_key = {st["key"]: st for st in st_all}
        st_all = [by_key[k] for k in order]
    for k, st in enumerate(st_all):
        mov = frozenset().union(*(group[n] for n, _ in st["move"]))
        sta = frozenset().union(*(group[n] for n in st["onto"]))
        assert not mov & sta, f"step {st['key']}: moves part of what it lands on"
        for n, how in st["move"]:
            for b in group[n]:
                blocked += [(st["key"], b, a) for a in sorted(sta) if blocks(d, ex, a, b, how)]
        new = mov | sta
        for n in new:
            group[n] = new
        for sc in d["screws"]:
            if sc[0] not in driven and sc[2] in group[sc[1]]:
                driven[sc[0]] = k
        for nm, into, m in buried:
            if (nm, m) not in covered and m in group[into]:
                covered[(nm, m)] = k
    late = [(nm, m) for nm, _, m in buried if nm in driven and covered.get((nm, m), len(st_all)) <= driven[nm]]
    return dict(steps=st_all, driven=driven, late=late, blocked=blocked,
                undriven=[sc[0] for sc in d["screws"] if sc[0] not in driven],
                loose=sorted(n for n in ex if len(group[n]) < len(ex)))


def open_issues(d: dict) -> list[str]:
    sch = schedule(d)
    out = []
    for a, b in access_conflicts(d):
        out.append(f"Screw access: `{a}` and `{b}` each have their head under the other's target; no order drives both.")
    for nm, m in sch["late"]:
        out.append(f"Screw access: `{nm}` ends up under {m}, which is in place before the screw can be driven.")
    for key, b, a in sch["blocked"]:
        out.append(f"Path: in step '{key}', {a} is in the way of {b}.")
    out += [f"Never driven: `{nm}`." for nm in sch["undriven"]]
    out += [f"Never assembled: {n}." for n in sch["loose"]]
    return out


# ---------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------
def _offsets(vals, base) -> str:
    return " and ".join(tape(v - base) for v in sorted({round(v, 3) for v in vals}))


def render(d: dict) -> str:
    f = tape
    t, w, s, D, W, H, ply = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"], d["ply"]
    b, pr = d["boards"], d["prisms"]
    sch = schedule(d)
    by_joint = screws_by_joint(d)
    kerf, trim = d["kerf"], d["end_trim"]
    con = d["cut_on_hand"]
    lo_b, _ = INVENTORY["brace45"][1]
    L = [
        "# Build sheet: tote workbench", "",
        f"{f(W)} wide, {f(D)} deep; work surface {f(d['work_surface'])} from the floor; back legs to {f(H)}, hutch shelf "
        f"on top to {f(H + ply)}. Four HDX 27 gal totes in one {f(d['bay'])} bay, two on the floor and two on the plywood "
        f"shelf at {f(d['shelf_surf'])}. Origin is the floor at the outer corner of the front-left leg; every height is "
        f"from the floor.",
        "", "Generated by `build_sheet.py` from `params.py`; change params, not this file. Readings are to the 1/16 in.", "",
        "## 1. Cut", "",
        "### On hand", "",
        f"- **72 in 2x4** (4): {con['72 in 2x4'][0][0]} and {con['72 in 2x4'][1][0]} as they are ({f(H)}). "
        f"{con['72 in 2x4'][2][0]} and {con['72 in 2x4'][3][0]} cut to **{f(d['front_leg'])}**; each offcut "
        f"({f(d['leg_offcut'])}) trimmed to **{f(D)}** for " + " and ".join(n for n, _ in con["72 in offcuts"]) + ".",
        f"- **31 in 2x4** (4), as they are ({f(D)}): " + ", ".join(n for n, _ in con["31 in 2x4"]) + ".",
        f"- **45 deg braces**: " + " and ".join(n for n, _ in con["45 deg braces"]) + f" from two of the four, recut to a "
        f"**{f(d['brace_long_point'])}** long point with both 45 deg ends kept: on the long edge measure "
        f"{f(d['brace_long_point'])} from one long point and cut 45 deg back toward the short edge, converging with the "
        f"kept end (short edge {f(d['brace_long_point'] - 2 * w)}). The shortest on hand is taken as {f(lo_b)} "
        f"(UNVERIFIED), so each loses at least {f(lo_b - d['brace_long_point'])}. {d['spare']['braces']} spare.",
        f"- **2x2**: {len(d['plan_2x2'])} of {INVENTORY['x2x2'][0]} sticks ({d['spare']['x2x2']} spare), taken as "
        f"{f(INVENTORY['x2x2'][1])} long (UNVERIFIED). {f(trim)} squared off one end first, {f(kerf)} kerf per cut.", "",
        "| stick | pieces | offcut |", "|---|---|---|",
    ]
    for i, st in enumerate(d["plan_2x2"], start=1):
        used = trim + sum(ln + kerf for _, ln in st)
        L.append(f"| {i} | " + " + ".join(f"{n} {f(ln)}" for n, ln in st) + f" | {f(INVENTORY['x2x2'][1] - used)} |")
    L += ["", "### Bought", "",
          f"2x4 x {f(STORE_2X4[0])}, {len(d['plan_bought_2x4'])} sticks, {f(trim)} squared off one end first:", "",
          "| stick | pieces | offcut |", "|---|---|---|"]
    for i, st in enumerate(d["plan_bought_2x4"], start=1):
        used = trim + sum(ln + kerf for _, ln in st)
        L.append(f"| {i} | " + " + ".join(f"{n} {f(ln)}" for n, ln in st) + f" | {f(STORE_2X4[0] - used)} |")
    pw, pl = STORE_PLY[0]
    L += ["", f"Plywood, one {f(pw)} x {f(pl)} sheet: cross-cut from one end, then rip each piece to width "
              f"(the 23/32 in sheet's face grain runs along the {f(pl)}):", ""]
    pos = 0.0
    for nm, wd, dp in d["plan_sheet"]:
        L.append(f"- **{nm}** {f(wd)} x {f(dp)}: {f(pos)} to {f(pos + dp)} along the sheet, ripped to {f(wd)}.")
        pos += dp + kerf
    L.append(f"- Offcut {f(pw)} x {f(pl - pos)}.")
    tp = d["top"]
    x0, y0 = tp["lo"][0], tp["lo"][1]
    for x, y, sx, sy in tp["notches"]:
        nx0, nx1 = max(x, x0), min(x + sx, x0 + tp["size"][0])
        ny0, ny1 = max(y, y0), min(y + sy, y0 + tp["size"][1])
        side = "left" if nx0 - x0 < tp["size"][0] / 2 else "right"
        L.append(f"- TOP notch, back-{side} corner: {f(nx1 - nx0)} in from the {side} edge by {f(ny1 - ny0)} in from the "
                 f"back edge (the back leg plus {f(d['notch_clear'])} each side).")
    gw, gh = STORE_PEG[0]
    pg = b["PEGBOARD"][1]
    L += [f"- PEGBOARD from the {f(gw)} x {f(gh)} panel: cut to {f(pg[0])} x {f(pg[2])}.", ""]

    # --- layout marks
    L += ["## 2. Layout marks", "",
          "Heights from the floor (the bottom end of the leg), bottom edge to top edge of what lands there. Outer face = "
          "the 3-1/2 in face away from the bench; front and back faces are the 1-1/2 in faces.", ""]
    for up, rows in marks(d).items():
        items = []
        for face in sorted({r[0] for r in rows}):
            items.append(f"{face}: " + "; ".join(f"{m}{' ' + wh if wh else ''} {f(z0)} to {f(z1)}"
                                                  for fc, m, z0, z1, wh in rows if fc == face))
        L.append(f"- **{up}** ({f(b[up][1][2])}): " + ". ".join(items) + ".")
    L += [f"- The front legs' tops carry the TOP at {f(d['top_frame'])}; the back legs pass through its notches from "
          f"{f(d['top_frame'])} to {f(d['work_surface'])}.", ""]

    # --- assembly
    L += ["## 3. Assemble", "",
          "Drill a pilot for every screw (SPF splits near ends) and glue every face joint and every end-grain joint. "
          "Each step lists its screws; section 4 says where the leg screws go.", ""]
    buried = buried_heads(d)
    for k, st in enumerate(sch["steps"]):
        here = [sc for sc in d["screws"] if sch["driven"].get(sc[0]) == k]
        cnt: dict[tuple, int] = {}
        for sc in here:
            key = (joint_of(d, sc), sc[5])
            cnt[key] = cnt.get(key, 0) + 1
        parts = [f"{n} x {f(ln)} ({jn})" for (jn, ln), n in cnt.items()]
        parts += [f"{n} x {f(ln)} ({what})" for n, ln, what in st["counted"]]
        if st["key"] == "pegboard":
            parts.append(f"{d['peg_screws']} x pan-head + washer")
        cover = sorted({m for nm, _, m in buried if nm in {sc[0] for sc in here}})
        line = f"{k + 1}. {st['text']}"
        if parts:
            line += " Screws: " + ", ".join(parts) + "."
        if cover:
            line += (f" These heads end up under {', '.join(cover)}: drive them now, before "
                     + ("it goes on." if len(cover) == 1 else "those go on."))
        L.append(line)
    L.append("")

    # --- screws
    j = d["joints"]
    L += ["## 4. Screws", "",
          f"#8 wood screws, each the shortest stocked length that bites {SCREW['min_penetration_d'][0]:.0f}D into the "
          f"member it holds and stays {f(d['screw_tip_cover'])} inside it.", "",
          "| joint | length | through | into | count |", "|---|---|---|---|---|"]
    for jn, (through, into, ln) in j.items():
        n = len(by_joint[jn]) if jn != "ply->frame" else sum(d["ply_screws"].values())
        L.append(f"| {jn} | {f(ln)} | {f(through)} | {f(into)} | {n} |")
    for k_, n in d["toe_screws"].items():
        L.append(f"| toe, {k_.replace('_', ' ')} | {f(SCREW['toe_len'][0])} | angled | | {n} |")
    L.append(f"| pegboard -> cleats | pan-head + washer | {f(d['peg'])} | | {d['peg_screws']} |")
    legs = by_joint["leg->side rail"]
    fl = [sc for sc in legs if sc[1].startswith("LEG-F")]
    bl = [sc for sc in legs if sc[1].startswith("LEG-B")]
    rail_lo = lambda sc: b[sc[2]][2][2]
    shelf = [sc for sc in legs if sc[2].endswith("SHELF")]
    other = [sc for sc in legs if not sc[2].endswith("SHELF")]
    L += ["", f"Leg screws, four per joint from the leg's outer face: on a front leg {_offsets([sc[3][1] for sc in fl], 0.0)} "
              f"back from its front face, on a back leg {_offsets([sc[3][1] for sc in bl], D - w)} back from its front face; "
              f"{_offsets([sc[3][2] - rail_lo(sc) for sc in other], 0.0)} up from the rail's bottom edge at the floor and top "
              f"rails, {_offsets([sc[3][2] - rail_lo(sc) for sc in shelf], 0.0)} at the shelf rails (under the flat shelf "
              f"rail's end screws).",
          f"Plywood screws are counted at {f(d['ply_screw_pitch'])} pitch along every member under the panel, and toe screws "
          "are counted; neither is clash-checked. Every other screw is modelled: it bites its member, touches nothing else "
          "and is driven before anything covers its head.", "",
          "Totals: " + ", ".join(f"{n} x {f(ln)}" for ln, n in d["screw_counts"].items())
          + f", {d['peg_screws']} pan-head + washers.", ""]

    # --- shopping
    L += ["## 5. Shopping list", ""]
    for item, n, note in d["shopping"]:
        L.append(f"- {n} x {item}" + (f" ({note})" if note else ""))
    L += [f"- Not needed: the 2x4 scraps on hand, {d['spare']['x2x2']} 2x2 sticks, {d['spare']['braces']} braces.", ""]

    # --- open issues
    L += ["## Open issues", ""]
    iss = open_issues(d)
    L += [f"- {x}" for x in iss] if iss else ["- none: every modelled screw is driven before anything covers its head, and "
                                              "nothing in place blocks a piece on its way in."]
    return "\n".join(L) + "\n"


def main():
    from pathlib import Path
    d = validate()
    out = Path(__file__.rsplit("/", 1)[0]) / "out"
    out.mkdir(exist_ok=True)
    md = out / "build_sheet.md"
    md.write_text(render(d))
    n = len(open_issues(d))
    print(f"tote_bench: {md} ({len(d['screws'])} modelled screws, {n} open issue{'s' if n != 1 else ''})")


if __name__ == "__main__":
    main()
