"""Tote bench: a workbench for the garage lip wall that a miter saw can cut
and one screw can hold. HDX 27 gal totes stand two high in columns, the lower
one on the slab, the upper one on a 2x6 slat shelf; a chair version leaves a
knee space with a footrest. Lumber, not a print. bench.py, build_sheet.py,
freecad_view.py and the tests read only `derive(version)`.

What makes it easy:
  - two lumber sizes (2x4, 2x6), every cut square across the board; no rips,
    no plywood, no angles. Lengths land on 1/16 in.
  - one screw: #8 x 2-1/2 in, every joint.
  - N identical ladders (front leg, back leg, a 2x4 rail pair at the shelf
    and at the top). Build them flat on the floor, stand them up, and the
    slats and planks space and square them.
  - the top is six 2x6 planks: 33 in deep, no glue-up. The chair version is
    sized so its planks are uncut 8 ft boards.

The lip (projects/garage) does what it did for projects/workbench: back legs
stand on it on leveling feet, its face stops the lower tote, the bench cannot
go backward. A 2x4 laid flat on the back slat stops the upper tote.

Coordinates are the garage's: +X along the wall from the left ladder's outer
rail, +Y out of the wall (wall face y = 0, lip face y = lip_depth), +Z up from
the floor at the lip face. Members are axis-aligned boxes:
name -> (kind, size xyz, min corner xyz), mm.

    plan, one ladder between two columns (wall at the bottom):

          front leg                   rails are 2x4 on edge, one on each face of
       [R][=LEG=][R]   <- y_front     the legs, at the shelf and at the top.
        A         A                   slats and planks rest on the rails;
        I  column I  column           columns are a tote (19.6 in, short side out)
        L         L                   + 1/2 in per side, or the knee space.
       [R][=LEG=][R]   <- back leg on the lip
       ===== lip =====
       ----- wall -----
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan, frac_in, seg_dist
from cacad.registries.reservoirs import RESERVOIRS
from projects.garage.params import FLOOR, WALLS
from projects.tote_rack.params import LUMBER as LUMBER_RACK, SCREWS
from projects.workbench.params import FOOT

IN = 25.4

LUMBER = MappingProxyType(dict(
    x2x4=dict(LUMBER_RACK["x2x4"]),
    # ALSC PS 20: 2 in nominal -> 1-1/2; 6 in nominal width -> 5-1/2. Sold 8, 10, 12 ft.
    x2x6=dict(t=1.5 * IN, w=5.5 * IN, stock=(96 * IN, 120 * IN, 144 * IN), label="2x6",
              source="ALSC PS 20: 2x6 dresses to 1-1/2 x 5-1/2 in; 8, 10, 12 ft stock"),
))

COMMON = MappingProxyType(dict(
    tote="HDX_27GAL",                 # cacad.registries.reservoirs: exterior at the top, with lid
    # --- clearances (DESIGN): each separates two named surfaces ---
    tote_side_clear=0.5 * IN,         # tote to the rail beside it, per side
    tote_gap_over=1.0 * IN,           # tote lid to whatever is above it (slat underside, plank underside)
    tote_stop_gap=0.25 * IN,          # tote back to its stop (lip face, upper stop), pushed home
    wall_gap=0.25 * IN,               # wall face to back legs, rails and top: drywall is not flat
    lip_edge_min=0.25 * IN,           # back foot pad to the lip's front edge
    knee_min=22.0 * IN,               # knee space between rail faces: a stool and two knees
    # --- top and shelf (DESIGN) ---
    top_h_target=36.0 * IN,           # the common workbench height; derive() raises it if the totes need more
    top_planks=6,                     # 2x6 planks front to back: 33 in deep, holds a tote 28.6 deep plus the lip
    top_overhang_end=1.0 * IN,        # top past each end ladder's outer rail
    top_overhang_front=1.5 * IN,      # top past the front legs: covers the footrest's 1-1/2 in
    slat_gap_max=1.25 * IN,           # gap between shelf slats; a tote's base ribs bridge it
    stop_lip=1.5 * IN,                # the upper stop stands this far above the slats (a 2x4 laid flat)
    footrest_top=10.0 * IN,           # footrest bar top above the floor: a stool user's feet at a 36 in bench
    mark_step=IN / 8,                 # positions marked on a leg land on 1/8 in, rounded toward more clearance
    # --- fastening ---
    screw="no8",
    screws_per_crossing=2,            # a plank or slat over a rail; a rail over a leg; a footrest over a leg
    screw_rows=(1.5 * IN, 2.75 * IN), # rail->leg and footrest->leg: marks below the board's top edge; the upper one
                                      # sits 1/2 in under the tips of the plank and slat screws coming down
    stop_screw_pitch_max=8.0 * IN,
    screw_gap_min=3.0,                # mm: closest approach of two screw shanks in a shared board
    # --- cutting ---
    kerf=IN / 8,
    bbox_tol=0.05,
))

# Inputs only. columns: T = a tote column (two totes), K = knee space. plank_stock: the 2x6 length the top comes
# from; with fit_planks the knee space is derived so the planks go on uncut.
VERSIONS = {
    "compact": dict(columns="TT", plank_stock=96 * IN, fit_planks=False,
                    note="two tote columns, no chair: the shortest bench, 4 totes"),
    "desk": dict(columns="TKT", plank_stock=96 * IN, fit_planks=True,
                 note="tote column, knee space, tote column: 4 totes, a stool, uncut 8 ft planks"),
    "long": dict(columns="TTKT", plank_stock=120 * IN, fit_planks=True,
                 note="three tote columns and a knee space: 6 totes, uncut 10 ft planks"),
}

ACTIVE_VERSIONS = ("compact", "desk", "long")


def _up(x: float, step: float) -> float:
    return math.ceil(x / step - 1e-9) * step


def derive(version: str, **overrides) -> dict:
    """Every dimension the build scripts need. Overrides are for what-if tables only."""
    s = dict(VERSIONS[version])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(version=version, **s, **c)
    site = dict(WALLS["lip_wall"])
    d.update(lip_depth=site["lip_depth"], lip_h=site["lip_h"], lip_h_dev=site["lip_h_dev"], floor_dev=FLOOR["floor_dev"])
    L24, L26, sc = LUMBER["x2x4"], LUMBER["x2x6"], SCREWS[c["screw"]]
    t = L24["t"]                                   # 1-1/2: every board's thickness
    leg_x, leg_y, rail_h, plank_w = L24["w"], t, L24["w"], L26["w"]
    d.update(t=t, leg_x=leg_x, leg_y=leg_y, rail_h=rail_h, plank_w=plank_w, screw_spec=sc, foot=dict(FOOT))

    r = RESERVOIRS[c["tote"]]
    TL, TW, TH = r.exterior_top
    tx, ty = TW, TL                               # short side out: the handle end faces the room
    d.update(tote_label=r.model, tote_x=tx, tote_y=ty, tote_h=TH)

    # --- foot, set mid-travel ---
    d["foot_h"] = (FOOT["h_min"] + FOOT["h_max"]) / 2
    d["foot_travel_each_way"] = min(d["foot_h"] - FOOT["h_min"], FOOT["h_max"] - d["foot_h"])
    d["foot_must_absorb"] = max(FLOOR["floor_dev"], site["lip_h_dev"])

    # --- X: ladders and columns. A ladder is rail | leg | rail ---
    cols = s["columns"]
    n_lad = len(cols) + 1
    lad_w = 2 * t + leg_x
    tote_col = _up(tx + 2 * c["tote_side_clear"], IN / 16)      # slats are cut to it: a tape reading, never less clearance
    fixed = n_lad * lad_w + cols.count("T") * tote_col + 2 * c["top_overhang_end"]
    n_knee = cols.count("K")
    if n_knee and s["fit_planks"]:
        knee = (s["plank_stock"] - fixed) / n_knee
        knee = math.floor(knee / (IN / 16) + 1e-9) * (IN / 16)    # a tape reading; the planks come out a hair short
        d["knee_governed_by"] = f"uncut {s['plank_stock'] / IN / 12:g} ft planks"
    else:
        knee = c["knee_min"]
        d["knee_governed_by"] = "knee_min (DESIGN)"
    widths = [tote_col if k == "T" else knee for k in cols]
    x = 0.0
    ladders, columns = [], []
    for i in range(n_lad):
        ladders.append(dict(i=i, rail_L=x, leg=x + t, rail_R=x + t + leg_x))
        x += lad_w
        if i < len(cols):
            columns.append(dict(j=i, kind=cols[i], x0=x, x1=x + widths[i]))
            x += widths[i]
    frame_len = x
    W = frame_len + 2 * c["top_overhang_end"]
    d.update(n_ladders=n_lad, ladders=ladders, columns=columns, tote_col=tote_col, knee=knee if n_knee else None,
             lad_w=lad_w, frame_len=frame_len, W=W, top_x0=-c["top_overhang_end"])

    # --- Y ---
    y_back = c["wall_gap"]
    D = c["top_planks"] * plank_w
    y_front = y_back + D - c["top_overhang_front"]
    rail_len = y_front - y_back
    d.update(y_back=y_back, y_front=y_front, rail_len=rail_len, D=D)
    d["back_leg_y"] = (y_back, y_back + leg_y)
    d["front_leg_y"] = (y_front - leg_y, y_front)
    d["back_pad_y"] = (y_back + leg_y / 2 - FOOT["pad_d"] / 2, y_back + leg_y / 2 + FOOT["pad_d"] / 2)

    # --- Z: lower tote on the slab, slats over it, upper tote, planks ---
    mid_top = _up(FLOOR["floor_dev"] + TH + c["tote_gap_over"], c["mark_step"])
    slat_top = mid_top + t
    top_need = slat_top + TH + c["tote_gap_over"] + t
    top_h = _up(max(c["top_h_target"], top_need), c["mark_step"])
    d["top_h_governed_by"] = "top_h_target (DESIGN)" if top_h <= c["top_h_target"] + 1e-9 else "two totes stacked"
    top_rail_top = top_h - t
    d.update(mid_top=mid_top, slat_top=slat_top, top_need=top_need, top_h=top_h, H=top_h, top_rail_top=top_rail_top)
    d["mid_rail_z"] = (mid_top - rail_h, mid_top)
    d["top_rail_z"] = (top_rail_top - rail_h, top_rail_top)
    d["front_leg_z"] = (d["foot_h"], top_rail_top)
    d["back_leg_z"] = (site["lip_h"] + d["foot_h"], top_rail_top)
    d["mid_rail_from_top"] = top_rail_top - mid_top    # marked on the legs from their tops: one mark per leg
    d["gap_over_lower"] = mid_top - (FLOOR["floor_dev"] + TH)
    d["gap_over_upper"] = top_rail_top - (slat_top + TH)

    # --- boards ---
    b = {}
    for lad in ladders:
        i = lad["i"]
        b[f"L{i}-LEG-BACK"] = ("x2x4", (leg_x, leg_y, d["back_leg_z"][1] - d["back_leg_z"][0]), (lad["leg"], y_back, d["back_leg_z"][0]))
        b[f"L{i}-LEG-FRONT"] = ("x2x4", (leg_x, leg_y, d["front_leg_z"][1] - d["front_leg_z"][0]), (lad["leg"], d["front_leg_y"][0], d["front_leg_z"][0]))
        for side in ("L", "R"):
            for lvl, (z0, _) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                b[f"L{i}-RAIL-{lvl}-{side}"] = ("x2x4", (t, rail_len, rail_h), (lad[f"rail_{side}"], y_back, z0))
    # slats: n 2x6 flat across each tote column, resting on its two rails; back one at y_back, front one at y_front
    n_sl = math.ceil((rail_len + c["slat_gap_max"]) / (plank_w + c["slat_gap_max"]) - 1e-9)
    slat_gap = (rail_len - n_sl * plank_w) / (n_sl - 1)
    d.update(n_slats=n_sl, slat_gap=slat_gap)
    for col in columns:
        j = col["j"]
        sx0, sx1 = col["x0"] - t, col["x1"] + t
        if col["kind"] == "T":
            for k in range(n_sl):
                b[f"C{j}-SLAT-{k}"] = ("x2x6", (sx1 - sx0, plank_w, t), (sx0, y_back + k * (plank_w + slat_gap), mid_top))
            b[f"C{j}-STOP"] = ("x2x4", (sx1 - sx0, leg_x, t), (sx0, y_back, slat_top))
        else:
            # footrest: 2x4 on edge across the front faces of the two front legs either side of the knee space
            fx0 = ladders[j]["leg"]
            fx1 = ladders[j + 1]["leg"] + leg_x
            b[f"C{j}-FOOTREST"] = ("x2x4", (fx1 - fx0, t, rail_h), (fx0, y_front, c["footrest_top"] - rail_h))
    for k in range(c["top_planks"]):
        b[f"PLANK-{k}"] = ("x2x6", (W, plank_w, t), (-c["top_overhang_end"], y_back + k * plank_w, top_rail_top))
    d["boards"] = b
    d["upper_tote_y"] = y_back + leg_x + c["tote_stop_gap"]
    d["lower_tote_y"] = site["lip_depth"] + c["tote_stop_gap"]

    # --- feet ---
    d["feet"] = {f"FOOT-{nm[:2]}-{nm.split('-')[-1]}": ((lo[0] + sz[0] / 2, lo[1] + sz[1] / 2, lo[2] - d["foot_h"]), FOOT["pad_d"] / 2, d["foot_h"])
                 for nm, (_, sz, lo) in b.items() if "-LEG-" in nm}

    # --- totes, as envelopes ---
    totes = {}
    for col in columns:
        if col["kind"] != "T":
            continue
        xc = (col["x0"] + col["x1"]) / 2 - tx / 2
        totes[f"TOTE-C{col['j']}-LOWER"] = ((tx, ty, TH), (xc, d["lower_tote_y"], 0.0))
        totes[f"TOTE-C{col['j']}-UPPER"] = ((tx, ty, TH), (xc, d["upper_tote_y"], slat_top))
    d["totes"] = totes

    # --- screws: (name, through board, into board, head xyz, unit dir, length). All one size ---
    ln = _pick(sc, t, t)
    d["screw_len"] = ln
    screws = []
    for lad in ladders:
        i = lad["i"]
        for side, sx in (("L", 1), ("R", -1)):           # left rail screws toward +X into the leg
            for lvl, (z0, z1) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                rail = f"L{i}-RAIL-{lvl}-{side}"
                xh = lad["rail_L"] if side == "L" else lad["rail_R"] + t
                for end, (y0, y1) in (("BACK", d["back_leg_y"]), ("FRONT", d["front_leg_y"])):
                    for f in c["screw_rows"]:
                        screws.append((f"{rail}>{end}@{f / IN:g}", rail, f"L{i}-LEG-{end}", (xh, (y0 + y1) / 2, z1 - f), (sx, 0, 0), ln))
    for nm, (kind, size, lo) in b.items():
        if nm.startswith("PLANK-") or "-SLAT-" in nm:
            lvl = "TOP" if nm.startswith("PLANK") else "MID"
            j = None if lvl == "TOP" else int(nm[1:nm.index("-")])
            ov0, ov1 = max(lo[1], y_back), min(lo[1] + size[1], y_front)   # where the board is over the rails
            yc, q = (ov0 + ov1) / 2, (ov1 - ov0) / 4
            for lad in ladders:
                for side in ("L", "R"):
                    rail = f"L{lad['i']}-RAIL-{lvl}-{side}"
                    _, rs, rl = b[rail]
                    if not (lo[0] - 1e-6 <= rl[0] and rl[0] + rs[0] <= lo[0] + size[0] + 1e-6):
                        continue                          # this slat does not cover that rail
                    for dy in (-q, q):
                        screws.append((f"{nm}>{rail}{dy:+.0f}", nm, rail, (rl[0] + t / 2, yc + dy, lo[2] + t), (0, 0, -1), ln))
        elif nm.endswith("-STOP"):
            n = int(math.ceil((size[0] - 2 * IN) / c["stop_screw_pitch_max"])) + 1
            for k in range(n):
                xs = lo[0] + IN + 2 * t + k * (size[0] - 2 * IN - 4 * t) / (n - 1)   # clear of the slat screws over the rails
                screws.append((f"{nm}#{k}", nm, nm[:nm.index('-')] + "-SLAT-0", (xs, lo[1] + size[1] / 2, lo[2] + t), (0, 0, -1), ln))
        elif nm.endswith("-FOOTREST"):
            j = int(nm[1:nm.index("-")])
            for lad in (ladders[j], ladders[j + 1]):
                for f in c["screw_rows"]:
                    screws.append((f"{nm}>L{lad['i']}@{f / IN:g}", nm, f"L{lad['i']}-LEG-FRONT",
                                   (lad["leg"] + leg_x / 2, lo[1] + t, lo[2] + rail_h - f), (0, -1, 0), ln))
    d["screws"] = screws

    # --- cutting: one plan per lumber size; planks from their own stock length ---
    plans = {}
    pieces24 = [(nm, max(sz)) for nm, (k, sz, _) in b.items() if k == "x2x4"]
    plans["x2x4"] = (96 * IN, cut_plan(pieces24, 96 * IN, 0.0, c["kerf"]))
    planks = [(nm, sz[0]) for nm, (k, sz, _) in b.items() if nm.startswith("PLANK")]
    slats = [(nm, sz[0]) for nm, (k, sz, _) in b.items() if "-SLAT-" in nm]
    plank_cut = W < s["plank_stock"] - 1e-6
    if plank_cut and s["plank_stock"] == 96 * IN:
        # cut planks and slats share 8 ft sticks: a plank's offcut is a slat
        plans["x2x6_planks"] = (96 * IN, [])
        plans["x2x6"] = (96 * IN, cut_plan(planks + slats, 96 * IN, 0.0, c["kerf"]))
    else:
        plans["x2x6_planks"] = (s["plank_stock"], cut_plan(planks, s["plank_stock"], 0.0, c["kerf"] if plank_cut else 0.0))
        plans["x2x6"] = (96 * IN, cut_plan(slats, 96 * IN, 0.0, c["kerf"]))
    d["plank_cut"] = plank_cut
    d["cut_plans"] = plans
    d["wood_volume"] = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in b.values())
    d["unverified"] = [
        f"lip {site['lip_depth'] / IN:g} x {site['lip_h'] / IN:g} in: owner's rough figures",
        f"floor +-{FLOOR['floor_dev'] / IN:g} in: allowance",
        "leveling foot: no product chosen",
        f"wall length: the bench needs {frac_in(W)} in",
    ]
    return d


def _pick(sc: dict, through: float, into: float) -> float | None:
    need = through + sc["min_penetration_d"] * sc["d"]
    fit = [ln for ln in sc["lengths"] if ln >= need - 1e-9 and ln < through + into - 1e-9]
    return fit[0] if fit else None


def validate(version: str, **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(version, **overrides)
    sc = d["screw_spec"]
    fi = lambda x: f"{frac_in(x)} in"
    assert d["foot_travel_each_way"] >= d["foot_must_absorb"] - 1e-9, f"{version}: feet travel {fi(d['foot_travel_each_way'])} < {fi(d['foot_must_absorb'])}"
    assert d["back_pad_y"][0] >= 0 and d["back_pad_y"][1] <= d["lip_depth"] - d["lip_edge_min"] + 1e-9, (
        f"{version}: back foot pad not on the lip (pad to y {fi(d['back_pad_y'][1])}, lip usable to {fi(d['lip_depth'] - d['lip_edge_min'])})")
    assert d["mid_rail_z"][0] >= d["back_leg_z"][0] - 1e-9, f"{version}: mid rail starts below the back leg"
    for nm, g in (("lower", d["gap_over_lower"]), ("upper", d["gap_over_upper"])):
        assert g >= d["tote_gap_over"] - 1e-9, f"{version}: {nm} tote lid clears by {fi(g)}"
    for tn, (size, lo) in d["totes"].items():
        assert lo[1] + size[1] <= d["y_back"] + d["D"] + 1e-9, f"{version}: {tn} sticks out past the top's front edge"
    if d["knee"] is not None:
        assert d["knee"] >= d["knee_min"] - 1e-9, f"{version}: knee space {fi(d['knee'])} < {fi(d['knee_min'])}"
    assert d["slat_gap"] <= d["slat_gap_max"] + 1e-9 and d["slat_gap"] >= 0, f"{version}: slat gap {fi(d['slat_gap'])}"
    assert d["W"] <= d["plank_stock"] + 1e-9, f"{version}: top {fi(d['W'])} longer than the {fi(d['plank_stock'])} planks"
    # one screw, everywhere: it bites 6D and stays inside every member it enters
    assert d["screw_len"] is not None, f"{version}: no stocked {sc['label']} bites 6D through 1-1/2 into 1-1/2"
    pen = d["screw_len"] - d["t"]
    assert pen >= sc["min_penetration_d"] * sc["d"] - 1e-9
    # every cut is a crosscut a miter saw makes: no board narrower than stock (no rips), every length a 1/16 reading
    for nm, (kind, size, _) in d["boards"].items():
        L = LUMBER[kind]
        assert sorted(size)[:2] == sorted((L["t"], L["w"])), f"{version}: {nm} is ripped: {size}"
        ln = max(size)
        assert abs(ln / (IN / 16) - round(ln / (IN / 16))) < 1e-6, f"{version}: {nm} {ln / IN:.4f} in is not a 1/16 reading"
    # screws: none meets another in a shared board
    S = d["screws"]
    tip = lambda s: tuple(h + u * s[5] for h, u in zip(s[3], s[4]))
    for a in range(len(S)):
        for bb in range(a + 1, len(S)):
            if not ({S[a][1], S[a][2]} & {S[bb][1], S[bb][2]}):
                continue
            gap = seg_dist(S[a][3], tip(S[a]), S[bb][3], tip(S[bb])) - sc["d"]
            assert gap >= d["screw_gap_min"], f"{version}: screws {S[a][0]} and {S[bb][0]} {gap:.1f} mm apart"
    return d


def report(version: str) -> str:
    d = derive(version)
    fi = lambda x: frac_in(x)
    cols = " | ".join("tote" if c["kind"] == "T" else "knee" for c in d["columns"])
    lines = [
        f"{version}: {d['note']}",
        f"  top {fi(d['W'])} x {fi(d['D'])} in, {fi(d['H'])} in high ({d['W']:.0f} x {d['D']:.0f} x {d['H']:.0f} mm); "
        f"{d['n_ladders']} identical ladders; columns {cols}",
        f"  tote column {fi(d['tote_col'])} in between rails"
        + (f"; knee space {fi(d['knee'])} in (governed by {d['knee_governed_by']})" if d["knee"] else ""),
        f"  height governed by {d['top_h_governed_by']} (totes need {d['top_need'] / IN:.2f} in); "
        f"lid gaps {fi(d['gap_over_lower'])} lower (slab {fi(d['floor_dev'])} high), {fi(d['gap_over_upper'])} upper",
        f"  shelf: {d['n_slats']} 2x6 slats, gaps {fi(d['slat_gap'])} in; mid rails' top edge {fi(d['mid_rail_from_top'])} in below the leg tops",
        f"  screws: {len(d['screws'])} x {d['screw_spec']['label']} {fi(d['screw_len'])} in, every joint",
    ]
    for kind, (stock, plan) in d["cut_plans"].items():
        if not plan:
            continue
        lab = LUMBER[kind[:4]]["label"]
        lines.append(f"  {lab} {stock / IN / 12:g} ft x {len(plan)}" + (" (planks, uncut)" if kind.endswith("planks") and not d["plank_cut"] else ""))
    lines.append(f"  feet: {2 * d['n_ladders']} x {d['foot']['label']}")
    lines.append("  UNVERIFIED: " + "; ".join(d["unverified"]))
    return "\n".join(lines)


if __name__ == "__main__":
    for v in VERSIONS:
        try:
            validate(v)
            print(report(v), "\n  ok" + ("" if v in ACTIVE_VERSIONS else " (inactive)"))
        except AssertionError as e:
            print(f"{v}: FAIL: {e}")
