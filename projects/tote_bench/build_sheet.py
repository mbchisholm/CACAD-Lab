"""Build sheet from params: what to cut from what is on hand, the layout marks
on the legs and posts measured from the floor, an assembly order that can be
built, the screws per joint and the shopping list. Nothing here holds a
number; every length, mark and count is read from params.validate().

The marks come from contact: each board or prism that touches a leg or post
gives the face it lands on and its height range there. The assembly order is
checked against screw access: a screw whose head ends up buried against
another member has to go in before that member, and a pair that needs both
orders is listed under "Open issues".

    .venv/bin/python projects/tote_bench/build_sheet.py     # -> out/build_sheet.md
"""
from __future__ import annotations

from projects.tote_bench.params import DESIGN, IN, INVENTORY, STORE_2X4, tape, validate

TOL = 0.05   # mm: faces closer than this touch (params bbox_tol)

# screw (through, into) name prefixes -> params' joint name. Checked against each screw's length and bite.
JOINT_OF = (
    (("RUNG-",), ("JOIST-",), "rung->joist"),
    (("RUNG-", "TIE-"), ("LEG-", "POST-"), "rung->leg/post"),
    (("RAIL-",), ("LEG-", "POST-"), "rail->leg/post"),
    (("STR-",), ("LEG-",), "stretcher->leg"),
    (("DIAG-",), ("LEG-",), "diagonal->leg"),
    (("BACK",), ("LEG-", "POST-"), "back panel->leg/post"),
    (("RUNG-",), ("RUN-",), "rung->runner"),
    (("BRACE-S",), ("RAIL-",), "brace->rail"),
    (("BRACE-B",), ("LEG-",), "back brace->leg"),
    (("TIE-",), ("BRACE-B",), "tie->back brace"),
)


def joint_of(d: dict, screw) -> str:
    nm, thr, into, _, _, ln, pen = screw
    for a, b, jn in JOINT_OF:
        if thr.startswith(a) and into.startswith(b):
            through, _, jl = d["joints"][jn]
            assert abs(jl - ln) < 1e-6 and abs(ln - through - pen) < 1e-6, f"{nm}: not a {jn} screw"
            return jn
    raise AssertionError(f"{nm}: no joint for {thr} -> {into}")


def screws_by_joint(d: dict) -> dict[str, list]:
    out = {jn: [] for jn in d["joints"]}
    for sc in d["screws"]:
        out[joint_of(d, sc)].append(sc)
    return out


def toe_screw_length(d: dict) -> float:
    """The length params counts the toe screws at: what screw_counts holds beyond the modelled and top screws."""
    rest = dict(d["screw_counts"])
    for sc in d["screws"]:
        rest[sc[5]] -= 1
    rest[d["joints"]["top->frame"][2]] -= d["top_screws"]
    left = {ln: n for ln, n in rest.items() if n}
    assert list(left.values()) == [d["toe_screws"]], f"screw_counts does not reconcile: {left}"
    return next(iter(left))


# ---------------------------------------------------------------------------
# geometry, as boxes and prisms (no kernel)
# ---------------------------------------------------------------------------
def extents(d: dict) -> dict[str, tuple]:
    """name -> (min xyz, max xyz) for every board and prism."""
    ex = {nm: (lo, tuple(a + b for a, b in zip(lo, size))) for nm, (_, size, lo) in d["boards"].items()}
    for nm, (_, axis, lo, th, poly) in d["prisms"].items():
        us, zs = [p[0] for p in poly], [p[1] for p in poly]
        if axis == "x":
            ex[nm] = ((lo, min(us), min(zs)), (lo + th, max(us), max(zs)))
        else:
            ex[nm] = ((min(us), lo, min(zs)), (max(us), lo + th, max(zs)))
    return ex


def _in_poly(u: float, z: float, poly) -> bool:
    inside = False
    for (u0, z0), (u1, z1) in zip(poly, poly[1:] + poly[:1]):
        if (z0 > z) != (z1 > z) and u < u0 + (z - z0) * (u1 - u0) / (z1 - z0):
            inside = not inside
    return inside


def solid_at(d: dict, p) -> list[str]:
    """Every board, prism or the top that holds point p strictly inside."""
    hit = [nm for nm, (_, size, lo) in d["boards"].items()
           if all(lo[i] + TOL < p[i] < lo[i] + size[i] - TOL for i in range(3))]
    for nm, (_, axis, lo, th, poly) in d["prisms"].items():
        a, u = (0, 1) if axis == "x" else (1, 0)
        if lo + TOL < p[a] < lo + th - TOL and _in_poly(p[u], p[2], list(poly)):
            hit.append(nm)
    tp = d["top"]
    if all(tp["lo"][i] + TOL < p[i] < tp["lo"][i] + tp["size"][i] - TOL for i in range(3)):
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
    out = []
    for a in bh:
        for b in bh:
            if a[1] == b[2] and b[1] == a[2] and a[0] < b[0]:
                out.append((a[0], b[0]))
    return out


def marks(d: dict) -> dict[str, list[tuple[str, str, float, float, str]]]:
    """upright -> [(face, member, z bottom, z top, what)] for every member that lands on a leg's or post's face."""
    ex = extents(d)
    W = d["W"]
    out = {}
    for up in [n for n in d["boards"] if n.startswith(("LEG-", "POST-"))]:
        ulo, uhi = ex[up]
        rows = []
        for m, (mlo, mhi) in ex.items():
            if m == up:
                continue
            for i, word_lo, word_hi in ((0, "", ""), (1, "front face", "back face")):
                j = 1 - i
                side = None
                if abs(mhi[i] - ulo[i]) < TOL:
                    side = "lo"
                elif abs(mlo[i] - uhi[i]) < TOL:
                    side = "hi"
                if side is None:
                    continue
                if min(mhi[j], uhi[j]) - max(mlo[j], ulo[j]) <= TOL or min(mhi[2], uhi[2]) - max(mlo[2], ulo[2]) <= TOL:
                    continue
                if i == 0:
                    outer = (side == "lo") == ((ulo[0] + uhi[0]) / 2 < W / 2)
                    face = "outer face" if outer else "inner face"
                else:
                    face = word_lo if side == "lo" else word_hi
                if m in d["prisms"]:
                    _, axis, _, _, poly = d["prisms"][m]
                    k = 1 if axis == "x" else 0          # the polygon's u is y for "x" prisms, x for "y" prisms
                    on = [z for u, z in poly if ulo[k] - TOL <= u <= uhi[k] + TOL]
                    if not on:
                        continue
                    rows.append((face, m, min(on), max(on), "plumb end"))
                else:
                    rows.append((face, m, max(mlo[2], ulo[2]), min(mhi[2], uhi[2]), ""))
        out[up] = sorted(rows, key=lambda r: (r[0], r[2]))
    return out


# ---------------------------------------------------------------------------
# the sheet
# ---------------------------------------------------------------------------
def render(d: dict) -> str:
    f = tape
    t, w, s, D, W, H = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"]
    b, pr = d["boards"], d["prisms"]
    lev = d["levels"]
    by_joint = screws_by_joint(d)
    n_j = {jn: len(v) for jn, v in by_joint.items()}
    names = lambda pre: [n for n in list(b) + list(pr) if n.startswith(pre)]
    rails_work = [n for n in names("RAIL-") if n.endswith("WORK")]
    rails_top = [n for n in names("RAIL-") if n.endswith("TOP")]
    posts, joists, runners = names("POST-"), names("JOIST-"), names("RUN-")
    rungs_f = [f"RUNG-F{r}" for r in range(len(d["rows"]))]
    rungs_b = [f"RUNG-B{r}" for r in range(len(d["rows"]))]
    lo_b, hi_b = DESIGN["brace_range"][0]
    tp = d["top"]
    stick = INVENTORY["x2x2"][1]
    L = [
        "# Build sheet: tote rack workbench", "",
        f"{f(W + 2 * t)} wide over the side rails (legs {f(W)} outside to outside), {f(D)} deep, {f(H)} tall. "
        f"Work surface {f(d['work_surface'])} from the floor. {d['cols'] * lev} HDX 27 gal totes, {d['cols']} columns x {lev} levels, "
        f"each sitting on its bottom across a front and a back 2x2 rung. Origin is the floor at the outer corner of the "
        f"front-left leg; every height below is measured from the floor, every position along a rung from its left end.",
        "", "Generated by `build_sheet.py` from `params.py`; change params, not this file.", "",
        "## 1. Cut", "",
        "### On hand", "",
        f"- **Legs**, 4 x {f(INVENTORY['leg72'][1])} 2x4, no cut: " + ", ".join(d["plan_on_hand"]["legs (on hand, 72 in, no cut)"]) + ".",
        f"- **Side rails**, 4 x {f(INVENTORY['x2x4_31'][1])} 2x4: trim each to **{f(D)}** (take {f(d['rail_trim'])} off one end): "
        + ", ".join(d["plan_on_hand"]["31 in 2x4s, trimmed"]) + ". At full length the tote bottom misses the front rung.",
        f"- **Knee braces**, 4 x 45 deg both ends, used as they are: " + ", ".join(d["plan_on_hand"]["45 deg braces (on hand, no cut)"])
        + f". Drawn at a {f(d['brace_long_point'])} long point; any length from {f(lo_b)} to {f(hi_b)} fits (UNVERIFIED: measure yours "
        "and use the brace marks in section 2 as a guide only).",
        f"- **2x2**, {len(d['plan_2x2'])} of {INVENTORY['x2x2'][0]} sticks ({d['spare_2x2']} spare), taken as {f(stick)} long (UNVERIFIED). "
        f"Kerf {f(d['kerf'])} per cut is in the plan.", "",
        "| stick | pieces | offcut |", "|---|---|---|",
    ]
    for i, st in enumerate(d["plan_2x2"], start=1):
        used = sum(ln + d["kerf"] for _, ln in st)
        L.append(f"| {i} | " + " + ".join(f"{n} {f(ln)}" for n, ln in st) + f" | {f(stick - used)} |")
    diag = names("DIAG-")
    L += ["", f"The diagonals {', '.join(diag)} have **plumb ends** (both vertical when fitted, parallel to each other): "
          f"{f(d['diag_len'])} long point to long point on either edge, each end cut {d['diag_cut_angle']:.1f} deg off square "
          f"(params `diag_cut_angle`; the saw setting). Cut one, offer it up to the side frame, then cut the second to match.", "",
          "### Bought", ""]
    for i, st in enumerate(d["plan_bought_2x4"], start=1):
        used = sum(ln + d["kerf"] for _, ln in st)
        L.append(f"- 2x4 x {f(STORE_2X4[0])} stick {i}: " + " + ".join(
            f"{n} {f(ln)}" + (f" ({f(b[n][1][0])} x {f(b[n][1][2])} section)" if n.startswith("JOIST-") else "") for n, ln in st)
            + f", offcut {f(STORE_2X4[0] - used)}")
    notch_words = []
    for x, y, sx, sy in tp["notches"]:
        side = "left" if x - tp["lo"][0] < tp["size"][0] / 2 else "right"
        edge = "front" if y - tp["lo"][1] < tp["size"][1] / 2 else "back"
        inset = x - tp["lo"][0] if side == "left" else tp["lo"][0] + tp["size"][0] - (x + sx)
        notch_words.append(f"{edge}-{side}: {f(sx)} wide x {f(sy)} deep, open to the {edge} edge, {f(inset)} in from the {side} edge")
    L += [f"- Plywood TOP, {f(tp['size'][0])} x {f(tp['size'][1])} from the 23/32 in panel, notched at the four legs (they run up through it):"]
    L += [f"  - {n}" for n in notch_words]

    # --- layout marks
    L += ["", "## 2. Layout marks", "",
          "Heights from the floor (the bottom end of the leg or post), bottom edge to top edge of the member that lands there. "
          "Outer face = the 3-1/2 in face away from the bench; front and back faces are the 1-1/2 in faces.", ""]
    for up, rows in marks(d).items():
        L.append(f"**{up}**")
        L.append("")
        for face in sorted({r[0] for r in rows}):
            items = [f"{m}{' ' + what if what else ''} {f(z0)} to {f(z1)}" for fc, m, z0, z1, what in rows if fc == face]
            L.append(f"- {face}: " + "; ".join(items))
        L.append("")
    ex = extents(d)
    along = [(n, ex[n][0][0], ex[n][1][0]) for n in posts + joists + runners]
    L += [f"On every rung and tie (left end flush with the left leg's outer face): "
          + "; ".join(f"{n} from {f(a)} to {f(z)}" for n, a, z in along) + f". Each column is {f(d['col'])} clear between a leg and a post.", ""]
    sb = pr[names("BRACE-S")[0]][4]
    bb = pr[names("BRACE-B")[0]][4]
    L += [f"Brace ends at the drawn {f(d['brace_long_point'])} long point (they move with the length of the brace you have): "
          f"side brace top edge flush with the top rail's top, its upper end from {f(sb[1][0])} to {f(sb[2][0])} back from the front of the bench; "
          f"back brace upper end under the back tie, {f(abs(bb[1][0] - bb[0][0]))} to {f(abs(bb[2][0] - bb[0][0]))} in from the leg's outer face.", ""]

    # --- assembly
    j = d["joints"]
    per = lambda jn: f"{f(j[jn][2])}"
    conflicts = access_conflicts(d)
    buried = buried_heads(d)
    L += ["## 3. Assemble", "",
          "Drill a pilot for every screw (pine splits near ends) and **glue every face joint**: the rung, rail and panel screws "
          "sit close to the ends of the wood, and the glue is what carries the load there. "
          "Everything lands on its mark from section 2; ends are flush with the faces they meet unless the step says otherwise.", "",
          f"1. **Left side frame, flat.** Lay LEG-FL and LEG-BL on their inner faces, outer faces up, front face of LEG-FL to back face of "
          f"LEG-BL {f(D)}. Screw on STR-L (bottom edge flush with the floor ends), then RAIL-L-WORK (top at {f(d['work_top'])}), "
          f"both ends flush with the legs' front and back faces: 2 x {per('stretcher->leg')} per leg for the stretcher, "
          f"2 x {per('rail->leg/post')} per leg for the rail, driven from the outside. Measure corner to corner both ways, "
          f"then screw on DIAG-L, low end on the front leg and plumb with its front face, high end plumb with the back leg's back face "
          f"under the rail: 2 x {per('diagonal->leg')} per end. Leave RAIL-L-TOP off: the top has to drop over the legs first.",
          f"2. **Right side frame**, the same with LEG-FR, LEG-BR, STR-R, RAIL-R-WORK and DIAG-R (a mirror image: rails and diagonal on its outer face).",
          f"3. **Stand both frames up**, {f(W)} apart outside to outside. Screw the floor rungs {rungs_f[0]} (behind the front legs) and "
          f"{rungs_b[0]} (in front of the back legs) across, ends flush with the legs' outer faces, then "
          + ", ".join(rungs_f[1:] + rungs_b[1:]) + f": 2 x {per('rung->leg/post')} per leg, driven from inside the bench through the rung. "
          "Check square across the top of the legs.",
          f"4. **Middle posts.** Stand {', '.join(posts)} on the floor at their marks on the rungs, in the plane of the legs "
          f"(front face of {posts[0]} flush with the front legs, back face of {posts[-1]} with the back legs): "
          f"2 x {per('rung->leg/post')} per rung, driven from inside through the rung into the post.",
          f"5. **Joist and runners.** Drop {', '.join(joists)} between the two work rungs {rungs_f[-1]} and {rungs_b[-1]}, beside the post, top flush with the rungs' tops: "
          f"{n_j['rung->joist'] // max(1, len(joists))} x {per('rung->joist')} per joist through the rungs into its end grain"
          + (" (see Open issues: the post is in the way of these)." if conflicts else ".")
          + f" Then the runners {', '.join(runners)} between the front and back rungs of each tote level, {f(d['runner_offset'])} either side "
          f"of each column's centre, tops flush with the rung tops (the floor-level ones lie on the floor): 1 x {per('rung->runner')} per end "
          "through the rung into the runner's end grain, the back ones driven from behind before the back panel goes on. "
          "The totes slide on these; without them a full tote's bottom spans the 19-5/8 in between the rungs and drops.",
          f"6. **Back panel.** Screw BACK ({f(W)} x {f(d['work_top'])} plywood) to the back faces of the back legs and post, bottom on the floor, "
          f"top at the work rungs' top: {n_j['back panel->leg/post']} x {per('back panel->leg/post')} down the centre of each. It braces the bench "
          "side to side below the top and stops the totes over their full height.",
          f"7. **Top.** Lower the plywood TOP from above over the four legs, notches round the legs, onto the work rungs, work rails and joist "
          f"(work surface {f(d['work_surface'])}). Screw it down at {f(d['top_screw_pitch'])} or closer along each work rung, each work rail "
          f"and the joist: {d['top_screws']} x {per('top->frame')}. It goes on now because the top rails and ties above close off the legs.",
          f"8. **Top rails and ties.** Screw {', '.join(rails_top)} to the legs' outer faces, top flush with the legs' tops "
          f"(2 x {per('rail->leg/post')} per leg), then TIE-F behind the front legs and TIE-B in front of the back legs, top flush "
          f"(2 x {per('rung->leg/post')} per leg, from inside).",
          f"9. **Braces.** Side braces {', '.join(names('BRACE-S'))}: in the line of the legs, flat against the inner face of the top rail, "
          f"upper end cut level with the rail's top, plumb end on the back face of the front leg; 2 x {per('brace->rail')} through the "
          f"brace into the rail, and {d['toe_screws'] // 2} toe screws at the plumb end into the leg. Back braces {', '.join(names('BRACE-B'))}: "
          f"slide in from the front under TIE-B, plumb end on the back leg's front face flush with its outer face; 2 x {per('back brace->leg')} "
          f"through the brace into the leg, then 1 x {per('tie->back brace')} down through the tie into the brace's top end.",
          f"10. **Anchor.** Fix the tops of the back legs to a wall stud with the two L-brackets: a {f(H)} frame on a {f(D)} base "
          "tips forward with a modest pull at the top.",
          f"11. **Totes.** Slide each tote in from the front between a leg and the post, on its runners, until it meets the back panel. "
          f"Parked, its bottom lies across the front and back rungs, {d['bearing_front'] / IN:.2f} and {d['bearing_back'] / IN:.2f} in on each "
          f"(at least {d['bearing_min'] / IN:.2f}), and on both runners.",
          ""]

    # --- screws
    L += ["## 4. Screws", "", "#8 wood screws, each long enough to bite 6D into the member it holds and short enough to stay "
          f"{f(d['screw_tip_cover'])} inside it.", "",
          "| joint | length | through | into | count |", "|---|---|---|---|---|"]
    for jn, (through, into, ln) in j.items():
        n = d["top_screws"] if jn == "top->frame" else n_j[jn]
        L.append(f"| {jn} | {f(ln)} | {f(through)} | {f(into)} | {n} |")
    toe = toe_screw_length(d)
    L += [f"| toe: side brace -> front leg | {f(toe)} | angled | | {d['toe_screws']} |", "",
          f"The top screws are counted at {f(d['top_screw_pitch'])} pitch, and the toe screws ({d['toe_screws'] // 2} per side brace, "
          "angled through the brace's lower end into the back face of the front leg) are counted, not clash-checked. "
          "Every other screw is modelled and checked: it bites its member and touches nothing else.", "",
          "Totals: " + ", ".join(f"{n} x {f(ln)}" for ln, n in d["screw_counts"].items()) + ".", ""]

    # --- shopping
    L += ["## 5. Shopping list", ""]
    for item, n, note in d["shopping"]:
        L.append(f"- {n} x {item}" + (f" ({note})" if note else ""))
    L += [f"- Not needed: the 2x4 scraps on hand; spare 2x2 sticks: {d['spare_2x2']}.", ""]

    # --- open issues
    L += ["## Open issues", ""]
    if conflicts:
        pairs: dict[tuple, set] = {}
        for a, bn in conflicts:
            ta = next(x for x in buried if x[0] == a)
            tb = next(x for x in buried if x[0] == bn)
            pairs.setdefault(tuple(sorted((ta[1], tb[1]))), set()).update((a, bn))
        for (m1, m2), scs in pairs.items():
            L.append(f"- **Screw access, no order works between {m1} and {m2}.** Each of these screws has its head buried "
                     f"against the other member, so whichever goes on second blocks the first one's screws: "
                     + ", ".join(f"`{x}`" for x in sorted(scs)) + ". Needs a change in params before building.")
    else:
        L.append("- none")
    others = [x for x in buried if not any(x[0] in c for c in conflicts)]
    if others:
        L += ["", "Screws whose heads end up under another member (drive them before it goes on):", ""]
        L += [f"- `{nm}` before {cov}" for nm, _, cov in others]
    return "\n".join(L) + "\n"


def main():
    from pathlib import Path
    d = validate()
    out = Path(__file__.rsplit("/", 1)[0]) / "out"
    out.mkdir(exist_ok=True)
    md = out / "build_sheet.md"
    md.write_text(render(d))
    n = len(access_conflicts(d))
    print(f"tote_bench: {md} ({len(d['screws'])} modelled screws, {n} access conflict{'s' if n != 1 else ''})")


if __name__ == "__main__":
    main()
