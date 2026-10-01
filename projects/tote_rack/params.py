"""Tote rack family: a single column of totes, N high, that hang by their rim
on a pair of 1x1 runners and slide out like drawers. Source: the "Garage Tote
Bin Storage Rack - CAD-Ready Spec" (Sep 2026); its section numbers are cited
as "spec S7" etc. Everything downstream (rack.py, tests, freecad_view.py)
reads `derive(rack)`.

Load path (spec S1): tote rim -> 1x1 runner -> 1x2 stringer on edge -> 2x4 leg -> floor.
The runner sits on top of its stringer; the stringer is screwed to the inner
X face of the legs; the front is open below a top tie.

Coordinates (spec S2), kept exactly so its bounding-box table is a test:
origin = bottom outer corner of the front-left leg on the floor; +X right,
+Y toward the back, +Z up; the front face is y = 0. Every member is an
axis-aligned box: name -> (kind, size xyz, min corner xyz), in mm.

    plan, front-left corner (front is down):
                                  x
        0     1.5 2.25
        +------+---+
        |      | S |R|        LEG 2x4, x [0, 1.5], y [0, 3.5]
        | LEG  | T |U|        STR 1x2 on edge, x [1.5, 2.25], full depth
        |      | R |N|        RUN 1x1 on the stringer, x [1.5, 2.25]; its inner face x = 2.25 bounds the clear span
        +------+---+          the tote rim rests on the runner tops, its body hangs through the clear span
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan, seg_dist

IN = 25.4

# ---------------------------------------------------------------------------
# Bought lumber and screws. Actual (dressed) sizes, not nominal. Caliper the
# boards you buy and change the row, not the derive().
# ---------------------------------------------------------------------------
LUMBER = MappingProxyType(dict(
    # ALSC PS 20 dressed sizes: 2 in nominal thickness -> 1-1/2, 4 in nominal width -> 3-1/2. 8 ft stock.
    x2x4=dict(t=1.5 * IN, w=3.5 * IN, stock=(96 * IN,), label="2x4",
              source="ALSC PS 20: 2x4 dresses to 1-1/2 x 3-1/2 in; 8 ft stock"),
    # ALSC PS 20: 1 in nominal board -> 3/4; 2 in nominal width -> 1-1/2.
    x1x2=dict(t=0.75 * IN, w=1.5 * IN, stock=(96 * IN,), label="1x2",
              source="ALSC PS 20: 1x2 dresses to 3/4 x 1-1/2 in; 8 ft stock"),
    # Sold as 3/4 in square S4S moulding or ripped from a 1x4 (spec S3, S9). Not in the PS 20 width table: caliper before cutting.
    x1x1=dict(t=0.75 * IN, w=0.75 * IN, stock=(96 * IN,), label="1x1",
              source="spec S3: 3/4 x 3/4 in; 8 ft stock. Caliper: 1x1 is not a PS 20 size"),
))

# #8 wood screw: shank 0.164 in (ASME B18.6.1 gauge table). Length ladder as sold in boxes. Minimum penetration into
# the main member 6D (AWC NDS 2018, wood screws). The spec's shopping list (S9) names 2.5 and 1.25 in boxes; derive()
# picks from the ladder per joint and validate() refuses a screw that exits the member it bites into.
SCREWS = MappingProxyType(dict(
    no8=dict(d=0.164 * IN, lengths=tuple(x * IN for x in (1.25, 1.625, 2.0, 2.5, 3.0)),
             label="#8 wood screw", min_penetration_d=6.0),
))

# The bin this rack is for. Envelope from the label on the bin (ref/27 Gallon HDX Tough Tote - Label 02.JPG);
# the vendor model in ref/ is Parasolid (.x_t), which neither kernel here reads, and carries no drawing dimensions.
# Rim width, body width and rim lip thickness are not on the label: caliper the bin, or export the .x_t to STEP
# (Onshape imports Parasolid) and read them there. A None here is a failing validate() until then.
TOTES = MappingProxyType(dict(
    HDX_207585=dict(label="HDX 27 gal Tough Tote, Home Depot 207 585",
                    lid_l=28.6 * IN, lid_w=19.6 * IN, h_with_lid=15.2 * IN,
                    source="label: 28.6 in W x 19.6 in L x 15.2 in H (72.6 x 49.7 x 38.6 cm), with lid"),
))

COMMON = MappingProxyType(dict(
    # --- cutting ---
    kerf=IN / 8,                      # per cut: material lost to the blade. 1/8 in covers a full-kerf 7-1/4 in blade
    # --- joinery (spec S10) ---
    screw="no8",
    screws_stringer_end=2,            # stringer -> leg, per end, through the stringer's inner face along X
    screws_tie_end=2,                 # tie -> leg, per end, through the leg's outer face along X into the tie's end grain
    screw_rows=(0.25, 0.75),          # two screws per joint at these fractions of the member's face height/width
    runner_screw_pitch_max=10 * IN,   # runner -> stringer, "every ~10 in" (spec S10), vertical, countersunk flush
    runner_screw_inset=4 * IN,        # first/last runner screw from the runner end: past the leg (3.5 deep) so it
                                      # cannot meet a stringer -> leg screw inside the stringer. Design choice
    screw_gap_min=3.0,                # closest approach of two screw shanks (axis distance minus d), mm
    # --- fit rules (spec S4) ---
    rim_bearing_min=0.5 * IN,         # (TWr - S_rail) / 2 per side must be at least this; 0.75 ideal
    tote_clear_under=2 * IN,          # hanging tote base to the rail-top of the level below, "P >= TH + 2"
    # --- exploded view (display only, FreeCAD) ---
    explode_legs_out=2.0,             # legs move straight out in X by this many leg thicknesses
    explode_ties_out=2.0,             # ties move out in Y by this many leg depths
    explode_runner_lift=2.0,          # runners lift by this many runner heights
    # --- checks ---
    bbox_tol=0.05,
))

# ---------------------------------------------------------------------------
# Family axis: the tote and the level pitch. Inputs only (spec S4, in inches).
# UNVERIFIED = spec S6 example tote; caliper the tote you own before cutting.
# ---------------------------------------------------------------------------
RACKS = {
    "4x27gal": dict(
        TL=30.0 * IN,       # UNVERIFIED tote length, front to back
        TWr=20.5 * IN,      # UNVERIFIED tote rim (top lip) width
        TWb=18.5 * IN,      # UNVERIFIED tote body width below the rim
        TH=15.0 * IN,       # UNVERIFIED tote height, rim top to base
        T_rim=0.75 * IN,    # UNVERIFIED rim lip thickness, rim top to rim underside. Spec S7's interference check
                            #   "base = railtop - TH + 0.75" implies it; S4 leaves it out. Caliper it
        N=4,                # levels
        S_rail=19.0 * IN,   # clear span between the runners' inner faces
        P=17.0 * IN,        # vertical pitch, rail top to rail top
        Z1=17.0 * IN,       # rail top of the lowest level
        D_clear=1.0 * IN,   # depth clearance added to the tote length
        Z_toptie=2.5 * IN,  # top rail to the underside of the front top tie
    ),
    # Spec S11: N=3 clears most garage obstructions
    "3x27gal": dict(TL=30.0 * IN, TWr=20.5 * IN, TWb=18.5 * IN, TH=15.0 * IN, T_rim=0.75 * IN, N=3,
                    S_rail=19.0 * IN, P=17.0 * IN, Z1=17.0 * IN, D_clear=1.0 * IN, Z_toptie=2.5 * IN),
}

# The bin in ref/: length and height from the label (lid envelope, so upper bounds on the bin); rim, body and lip
# unknown until calipered. Rim width cannot exceed the lid width, so S_rail=19 leaves at most 0.3 in bearing: the
# span will have to come down once TWr is known.
RACKS["hdx_207585"] = dict(
    tote="HDX_207585",
    TL=TOTES["HDX_207585"]["lid_l"], TH=TOTES["HDX_207585"]["h_with_lid"],
    TWr=None, TWb=None, T_rim=None,
    N=4, S_rail=19.0 * IN, P=17.0 * IN, Z1=17.0 * IN, D_clear=1.0 * IN, Z_toptie=2.5 * IN,
)

ACTIVE_RACKS = ("4x27gal",)


def derive(rack: str, **overrides) -> dict:
    """Every dimension rack.py and the tests need. Overrides are for what-if tables only."""
    s = dict(RACKS[rack])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(rack=rack, **s, **c)
    L24, L12, L11 = LUMBER["x2x4"], LUMBER["x1x2"], LUMBER["x1x1"]
    sc = SCREWS[c["screw"]]
    leg_t, leg_d = L24["t"], L24["w"]          # leg: 1.5 in X, 3.5 in Y
    str_t, str_h = L12["t"], L12["w"]          # stringer on edge: 0.75 in X, 1.5 in Z
    run_t, run_h = L11["t"], L11["w"]          # runner: 0.75 in X, 0.75 in Z
    N, P, Z1 = s["N"], s["P"], s["Z1"]
    d.update(leg_t=leg_t, leg_d=leg_d, str_t=str_t, str_h=str_h, run_t=run_t, run_h=run_h, screw_spec=sc)

    # spec S5
    W = s["S_rail"] + 2 * leg_t + 2 * str_t                      # = S_rail + 4.5
    D = s["TL"] + s["D_clear"]
    railtops = [Z1 + i * P for i in range(N)]
    H = railtops[-1] + s["Z_toptie"] + str_h
    d.update(W=W, D=D, H=H, railtops=railtops)
    xl, xr = leg_t, W - leg_t - str_t                              # left and right stringer/runner min X
    d["span_inner"] = (xl + str_t, xr)                            # runner inner faces: the clear span
    d["clear_span"] = xr - (xl + str_t)
    known = all(s[k] is not None for k in ("TWr", "TWb", "T_rim"))
    d["tote_known"] = known
    d["rim_bearing"] = (s["TWr"] - s["S_rail"]) / 2 if known else None
    d["inside_legs"] = W - 2 * leg_t                              # what the rim must pass between
    d["rim_side_clear"] = (d["inside_legs"] - s["TWr"]) / 2 if known else None   # per side, rim to leg. Spec S5 gives 0 for its example

    # boards: name -> (kind, size xyz, min corner xyz). Names are the spec S7 IDs
    b = {}
    for nm, x, y in (("LEG-FL", 0, 0), ("LEG-FR", W - leg_t, 0), ("LEG-BL", 0, D - leg_d), ("LEG-BR", W - leg_t, D - leg_d)):
        b[nm] = ("x2x4", (leg_t, leg_d, H), (x, y, 0.0))
    for i, rt in enumerate(railtops, start=1):
        for side, x in (("L", xl), ("R", xr)):
            b[f"STR-{side}{i}"] = ("x1x2", (str_t, D, str_h), (x, 0.0, rt - run_h - str_h))
            b[f"RUN-{side}{i}"] = ("x1x1", (run_t, D, run_h), (x, 0.0, rt - run_h))
    tie_len = W - 2 * leg_t
    b["TIE-FRONT-TOP"] = ("x1x2", (tie_len, str_t, str_h), (leg_t, 0.0, H - str_h))
    b["TIE-BACK-TOP"] = ("x1x2", (tie_len, str_t, str_h), (leg_t, D - str_t, H - str_h))
    b["TIE-BACK-BOT"] = ("x2x4", (tie_len, leg_d, leg_t), (leg_t, D - leg_d, 0.0))   # 2x4 flat, 1.5 tall
    d["boards"] = b
    d["tie_len"] = tie_len

    # totes, as check envelopes: rim underside on the rail tops, centred in X, centred in the depth
    tote_y = (D - s["TL"]) / 2
    totes = {}
    for i, rt in enumerate(railtops, start=1):
        if not known:
            break
        totes[f"TOTE-{i}-RIM"] = ((s["TWr"], s["TL"], s["T_rim"]), (W / 2 - s["TWr"] / 2, tote_y, rt))
        totes[f"TOTE-{i}-BODY"] = ((s["TWb"], s["TL"], s["TH"] - s["T_rim"]), (W / 2 - s["TWb"] / 2, tote_y, rt + s["T_rim"] - s["TH"]))
    d["totes"] = totes
    d["tote_y"] = tote_y
    if known:
        d["tote_base"] = [rt + s["T_rim"] - s["TH"] for rt in railtops]
        d["tote_rim_top"] = [rt + s["T_rim"] for rt in railtops]
        d["gap_under_tote"] = [d["tote_base"][0] - leg_t] + [d["tote_base"][i] - railtops[i - 1] for i in range(1, N)]   # level 1: to the back bottom tie top
        d["gap_over_top_tote"] = (H - str_h) - d["tote_rim_top"][-1]
        d["body_side_clear"] = (s["S_rail"] - s["TWb"]) / 2
    else:
        d["tote_base"] = d["tote_rim_top"] = d["gap_under_tote"] = None
        d["gap_over_top_tote"] = d["body_side_clear"] = None

    # screws: (name, through board, into board, head xyz, unit direction, length, penetration)
    def pick(through_t: float, into_t: float):
        need = through_t + sc["min_penetration_d"] * sc["d"]
        fit = [ln for ln in sc["lengths"] if ln >= need - 1e-9 and ln < through_t + into_t - 1e-9]
        return fit[0] if fit else None
    joints = {}   # joint kind -> (through_t, into_t, length)
    joints["stringer->leg"] = (str_t, leg_t, pick(str_t, leg_t))
    joints["runner->stringer"] = (run_t, str_h, pick(run_t, str_h))
    joints["tie->leg"] = (leg_t, tie_len, pick(leg_t, tie_len))
    d["joints"] = joints
    screws = []
    n_run = int(math.ceil((D - 2 * c["runner_screw_inset"]) / c["runner_screw_pitch_max"])) + 1
    d["runner_screws_each"] = n_run
    for nm, (kind, size, lo) in b.items():
        if nm.startswith("STR-"):
            through, into, ln = joints["stringer->leg"]
            if ln is None:
                continue
            side = nm[4]
            sx = -1 if side == "L" else 1                       # screw points toward the leg: -X on the left
            x_head = lo[0] + (size[0] if side == "L" else 0.0)
            for leg_nm, ly in ((f"LEG-F{side}", 0.0), (f"LEG-B{side}", D - leg_d)):
                y = ly + leg_d / 2
                for f in c["screw_rows"][: c["screws_stringer_end"]]:
                    screws.append((f"{nm}>{leg_nm}@{f}", nm, leg_nm, (x_head, y, lo[2] + f * size[2]), (sx, 0, 0), ln, ln - through))
        elif nm.startswith("RUN-"):
            through, into, ln = joints["runner->stringer"]
            if ln is None:
                continue
            str_nm = "STR-" + nm[4:]
            x = lo[0] + size[0] / 2
            for k in range(n_run):
                y = c["runner_screw_inset"] + k * (D - 2 * c["runner_screw_inset"]) / (n_run - 1)
                screws.append((f"{nm}>{str_nm}#{k}", nm, str_nm, (x, y, lo[2] + size[2]), (0, 0, -1), ln, ln - through))
        elif nm.startswith("TIE-"):
            through, into, ln = joints["tie->leg"]
            if ln is None:
                continue
            fb = "F" if nm.startswith("TIE-FRONT") else "B"
            for side, sx in (("L", 1), ("R", -1)):
                leg_nm = f"LEG-{fb}{side}"
                x_head = 0.0 if side == "L" else W
                # the 1x2 ties stand on edge (screws stacked in Z); the flat 2x4 tie lies (screws side by side in Y)
                on_edge = size[2] > size[1]
                for f in c["screw_rows"][: c["screws_tie_end"]]:
                    if on_edge:
                        head = (x_head, lo[1] + size[1] / 2, lo[2] + f * size[2])
                    else:
                        head = (x_head, lo[1] + f * size[1], lo[2] + size[2] / 2)
                    screws.append((f"{nm}>{leg_nm}@{f}", leg_nm, nm, head, (sx, 0, 0), ln, ln - through))
    d["screws"] = screws
    d["screw_penetration_min"] = sc["min_penetration_d"] * sc["d"]

    # cut plan per lumber size
    plans, buy = {}, {}
    for kind, L in LUMBER.items():
        pieces = [(nm, max(sz)) for nm, (k, sz, _) in b.items() if k == kind]
        plans[kind] = cut_plan(pieces, L["stock"][0], 0.0, c["kerf"])
        buy[kind] = len(plans[kind])
    d["cut_plans"] = plans
    d["sticks_needed"] = buy

    # exploded view: one move per set of parts; each part's total offset is the sum of its moves
    moves = [
        ("left legs out", ["LEG-FL", "LEG-BL"], (-c["explode_legs_out"] * leg_t, 0, 0)),
        ("right legs out", ["LEG-FR", "LEG-BR"], (c["explode_legs_out"] * leg_t, 0, 0)),
        ("front tie out", ["TIE-FRONT-TOP"], (0, -c["explode_ties_out"] * leg_d, 0)),
        ("back ties out", ["TIE-BACK-TOP", "TIE-BACK-BOT"], (0, c["explode_ties_out"] * leg_d, 0)),
        ("runners up", [nm for nm in b if nm.startswith("RUN-")], (0, 0, c["explode_runner_lift"] * run_h)),
    ]
    d["explode_moves"] = moves
    d["explode_offset"] = {nm: tuple(sum(v[a] for _, parts, v in moves if nm in parts) for a in range(3)) for nm in b}

    d["wood_volume"] = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in b.values())
    return d


def validate(rack: str) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(rack)
    s = RACKS[rack]
    sc = d["screw_spec"]
    mm = lambda x: f"{x:.1f} mm ({x / IN:.2f} in)"
    # the tote must be known before any fit rule means anything
    missing = [k for k in ("TWr", "TWb", "T_rim") if s[k] is None]
    assert not missing, f"{rack}: tote {s.get('tote', '?')} {missing} not known: caliper the bin (ref/ has no readable model)"
    if "tote" in s:
        t = TOTES[s["tote"]]
        assert s["TWr"] <= t["lid_w"], f"{rack}: rim {mm(s['TWr'])} wider than the lid {mm(t['lid_w'])} on the label"
        assert s["TL"] <= t["lid_l"] and s["TH"] <= t["h_with_lid"], f"{rack}: tote exceeds the label envelope"
    # fit rules, spec S4
    assert s["TWb"] < s["S_rail"] < s["TWr"], f"{rack}: TWb < S_rail < TWr fails: {s['TWb'] / IN} < {s['S_rail'] / IN} < {s['TWr'] / IN}"
    assert d["rim_bearing"] >= d["rim_bearing_min"] - 1e-9, f"{rack}: rim bearing {mm(d['rim_bearing'])} < {mm(d['rim_bearing_min'])}"
    assert d["rim_side_clear"] >= 0, f"{rack}: rim {mm(s['TWr'])} wider than the inside of the legs {mm(d['inside_legs'])}"
    for i, g in enumerate(d["gap_under_tote"], start=1):
        floor = d["tote_clear_under"] if i > 1 else 0.0
        assert g >= floor - 1e-9, f"{rack}: level {i} tote base clears what is below by {mm(g)}, need {mm(floor)}"
    assert d["gap_over_top_tote"] > 0, f"{rack}: top tote rim hits the front top tie by {mm(-d['gap_over_top_tote'])}"
    assert abs(d["clear_span"] - s["S_rail"]) < 1e-9, f"{rack}: clear span {d['clear_span']} != S_rail"
    # screws: every joint has a stocked length that bites 6D and stays inside the member
    for jn, (through, into, ln) in d["joints"].items():
        assert ln is not None, (f"{rack}: {jn}: no stocked {sc['label']} bites {mm(d['screw_penetration_min'])} through "
                                f"{mm(through)} and stays inside {mm(into)}")
    for i in range(len(d["screws"])):
        for j in range(i + 1, len(d["screws"])):
            a, b = d["screws"][i], d["screws"][j]
            if not ({a[1], a[2]} & {b[1], b[2]}):
                continue   # no board in common: they cannot meet
            tip = lambda scr: tuple(h + u * scr[5] for h, u in zip(scr[3], scr[4]))
            gap = seg_dist(a[3], tip(a), b[3], tip(b)) - sc["d"]
            assert gap >= d["screw_gap_min"], f"{rack}: screws {a[0]} and {b[0]} {gap:.1f} mm apart"
    # every stringer, runner and tie is screwed at both ends
    for nm in d["boards"]:
        n = sum(1 for scr in d["screws"] if nm in (scr[1], scr[2]) and not nm.startswith("LEG"))
        if nm.startswith("STR-"):
            assert n == 2 * d["screws_stringer_end"] + d["runner_screws_each"], f"{rack}: {nm} has {n} screws"
        elif nm.startswith("RUN-"):
            assert n == d["runner_screws_each"], f"{rack}: {nm} has {n} screws"
        elif nm.startswith("TIE-"):
            assert n == 2 * d["screws_tie_end"], f"{rack}: {nm} has {n} screws"
    return d


def report(rack: str) -> str:
    d = derive(rack)
    s = RACKS[rack]
    mm_in = lambda x: f"{x:.1f} mm ({x / IN:.2f} in)"
    if not d["tote_known"]:
        return (f"{rack}: W x D x H {d['W'] / IN:.2f} x {d['D'] / IN:.2f} x {d['H'] / IN:.2f} in; tote {s.get('tote')} "
                f"rim/body/lip not known, fit not derived")
    lines = [
        f"{rack}: W x D x H {d['W'] / IN:.2f} x {d['D'] / IN:.2f} x {d['H'] / IN:.2f} in "
        f"({d['W']:.0f} x {d['D']:.0f} x {d['H']:.0f} mm), {s['N']} levels, rail tops at "
        + ", ".join(f"{z / IN:g}" for z in d["railtops"]) + " in",
        f"  clear span {mm_in(d['clear_span'])}; rim bearing per side {mm_in(d['rim_bearing'])} (min {d['rim_bearing_min'] / IN:g}); "
        f"body to runner per side {mm_in(d['body_side_clear'])}",
        f"  rim to leg per side {mm_in(d['rim_side_clear'])}" + ("  <- zero: the rim touches both legs; measure the tote" if d["rim_side_clear"] < 1e-9 else ""),
        f"  tote base above what is below, per level: " + ", ".join(f"{g / IN:.2f}" for g in d["gap_under_tote"])
        + f" in (level 1: back bottom tie; others: {d['tote_clear_under'] / IN:g} min)",
        f"  top tote rim top {d['tote_rim_top'][-1] / IN:.2f} to front top tie underside {(d['H'] - d['str_h']) / IN:.2f}: {mm_in(d['gap_over_top_tote'])}",
        f"  screws ({d['screw_spec']['label']}, 6D = {mm_in(d['screw_penetration_min'])} min bite):",
    ]
    for jn, (through, into, ln) in d["joints"].items():
        n = sum(1 for scr in d["screws"] if (scr[1] if jn != "tie->leg" else scr[2]).startswith(jn.split("->")[0][:3].upper()))
        lines.append(f"    {jn:18s} {ln / IN if ln else float('nan'):.3f} in: through {through / IN:.2f}, bites "
                     f"{(ln - through) / IN if ln else float('nan'):.2f} of {into / IN:.2f}; {n} screws")
    lines.append(f"  {len(d['screws'])} screws in all; runner screws {d['runner_screws_each']} each at <= {d['runner_screw_pitch_max'] / IN:g} in")
    lines.append("  cut list:")
    for kind, L in LUMBER.items():
        pieces = sorted(((nm, max(sz)) for nm, (k, sz, _) in d["boards"].items() if k == kind), key=lambda p: -p[1])
        by_len = {}
        for nm, ln in pieces:
            by_len.setdefault(round(ln, 3), []).append(nm)
        lines.append(f"    {L['label']}: " + ", ".join(f"{len(v)} x {k / IN:g} in" for k, v in by_len.items())
                     + f"  -> {d['sticks_needed'][kind]} x 8 ft (kerf {d['kerf'] / IN:g})")
        for i, st in enumerate(d["cut_plans"][kind]):
            used = sum(l + d["kerf"] for _, l in st)
            lines.append(f"      stick {i + 1}: " + " + ".join(f"{l / IN:g}" for _, l in st) + f"  (offcut {(L['stock'][0] - used) / IN:.2f} in)")
    lines.append(f"  wood {d['wood_volume'] / 1e6:.2f} L")
    return "\n".join(lines)


if __name__ == "__main__":
    for rack in RACKS:
        try:
            validate(rack)
            print(report(rack), "\n  ok" + ("" if rack in ACTIVE_RACKS else " (inactive)"))
        except AssertionError as e:
            print(f"{rack}: FAIL: {e}")
