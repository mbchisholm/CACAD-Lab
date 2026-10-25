"""Tote bench, long: a 10 ft workbench on the garage lip wall, built in the
order it is assembled. Lumber, not a print. bench.py, build_sheet.py,
freecad_view.py and the tests read only `derive(version)`.

Assembly order, which sets the design:
  1. BACK FRAME, built flat on the floor: a 2x4 sill and a 2x4 top ledger,
     both on edge, with a back leg lapped across their front faces at each
     ladder. Stood up on the lip, tight to the drywall, levelled with shims
     under the sill, and screwed through the drywall into every stud. It is
     the bench's level line and its anchor.
  2. RAILS, a 2x4 pair at the shelf and at the top, screwed to each back leg.
  3. FRONT LEGS, one per rail pair: level the top rail front to back, stand a
     leg blank on the floor between the rails, mark the rail top on it, cut,
     screw. The floor's slope and the lip's height go into that one cut, so
     no leveling feet and no measuring.
  4. SLATS (the upper tote shelf), FOOTREST (the knee space), PLANKS (the top).
Totes go in last, handle out: the lower one on the slab until it touches the
lip face, the upper one on the slats until it touches the top ledger.

Lumber: 2x4 and 2x6, square crosscuts on 1/16 in readings, no rips; the
sill, ledger and planks are uncut 10 ft boards. Screws: #8 x 2-1/2 in for
wood to wood, #10 x 3-1/2 in through the drywall into the studs.

Coordinates are the garage's (projects/garage): +X along the wall from the
bench's left end, +Y out of the wall (drywall face y = 0, lip face
y = lip_depth), +Z up from the floor at the lip face. Members are axis-
aligned boxes: name -> (kind, size xyz, min corner xyz), mm.

    section through a ladder (wall at the left):

      |LEDGER|BACK LEG|== top rail ======================| front leg, cut
      |  on  |  on    |                                  | to fit between
      | edge | lip    |== mid rail =======================| the floor and
      |------|        |                                  | the top rail
      | SILL |        |                                  |
      ===== lip ======+                                  |
                      ==================================== slab
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan, frac_in, seg_dist
from cacad.registries.reservoirs import RESERVOIRS
from projects.garage.params import FLOOR, WALLS
from projects.tote_rack.params import LUMBER as LUMBER_RACK, SCREWS

IN = 25.4

LUMBER = MappingProxyType(dict(
    x2x4=dict(LUMBER_RACK["x2x4"], stock=(96 * IN, 120 * IN),
              source="ALSC PS 20: 2x4 dresses to 1-1/2 x 3-1/2 in; 8 and 10 ft stock"),
    x2x6=dict(t=1.5 * IN, w=5.5 * IN, stock=(96 * IN, 120 * IN), label="2x6",
              source="ALSC PS 20: 2x6 dresses to 1-1/2 x 5-1/2 in; 8 and 10 ft stock"),
))

# Wall screw: #10 is 0.190 in (ASME B18.6.1 gauge table). 3-1/2 in through a 1-1/2 in ledger and 5/8 in drywall leaves
# 1-3/8 in in the stud; the 6D minimum (AWC NDS, as for the #8) is 1.14 in.
WALL_SCREW = MappingProxyType(dict(d=0.190 * IN, length=3.5 * IN, label="#10 wood screw", min_penetration_d=6.0))

COMMON = MappingProxyType(dict(
    tote="HDX_27GAL",                 # cacad.registries.reservoirs: exterior at the top, with lid
    # --- clearances (DESIGN): each separates two named surfaces ---
    tote_side_clear=0.5 * IN,         # tote to the rail beside it, per side
    tote_gap_over=0.75 * IN,          # tote lid to what is above it, in the worst case (lip low, slab high)
    tote_stop_gap=0.25 * IN,          # tote back to its stop (lip face, top ledger), pushed home
    wall_gap=0.25 * IN,               # drywall to the back plank: drywall is not flat
    lip_edge_min=0.25 * IN,           # sill's front face to the lip's front edge
    knee_min=22.0 * IN,               # knee space between rail faces: a stool and two knees
    front_leg_blank_extra=1.5 * IN,   # front leg blanks are cut this much over the nominal leg, then trimmed in place
    # --- top and shelf (DESIGN) ---
    top_h_target=36.0 * IN,           # the common workbench height; derive() raises it if the totes need more
    top_planks=6,                     # 2x6 planks front to back: 33 in deep
    top_overhang_end=1.0 * IN,        # top past each end ladder's outer rail
    top_overhang_front=1.5 * IN,      # top past the front legs: covers the footrest
    slat_gap_max=1.25 * IN,           # gap between shelf slats; a tote's base ribs bridge it
    footrest_top=10.0 * IN,           # footrest top above the floor: a stool user's feet at a 36 in bench
    mark_step=IN / 8,                 # heights marked on a leg land on 1/8 in, rounded toward more clearance
    # --- fastening: rows are marks below a board's top edge ---
    screw="no8",
    rail_rows=(1.5 * IN, 2.75 * IN),  # rail -> leg and footrest -> leg; the upper one 1/2 in under the plank screw tips
    lap_rows=(1.375 * IN, 2.875 * IN),   # back leg -> sill and ledger, at the leg's centre line
    stud_rows=(0.625 * IN, 2.125 * IN),  # sill and ledger -> stud; 3/4 in from every lap row, so they never meet
    screw_gap_min=3.0,                # mm: closest approach of two screw shanks in a shared board
    # --- cutting ---
    kerf=IN / 8,
    bbox_tol=0.05,
))

VERSIONS = {
    "long": dict(columns="TTKT", length=120 * IN,
                 note="three tote columns and a knee space: 6 totes and a stool, on uncut 10 ft boards"),
}

ACTIVE_VERSIONS = ("long",)


def _up(x: float, step: float) -> float:
    return math.ceil(x / step - 1e-9) * step


def _pick(sc: dict, through: float, into: float) -> float | None:
    need = through + sc["min_penetration_d"] * sc["d"]
    fit = [ln for ln in sc["lengths"] if ln >= need - 1e-9 and ln < through + into - 1e-9]
    return fit[0] if fit else None


def derive(version: str, **overrides) -> dict:
    """Every dimension the build scripts need. Overrides are for what-if tables only."""
    s = dict(VERSIONS[version])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(version=version, **s, **c)
    site = dict(WALLS["lip_wall"])
    d.update(lip_depth=site["lip_depth"], lip_h=site["lip_h"], lip_h_dev=site["lip_h_dev"], floor_dev=FLOOR["floor_dev"],
             drywall_t_max=site["drywall_t_max"], stud_oc=site["stud_oc"])
    L24, L26, sc = LUMBER["x2x4"], LUMBER["x2x6"], SCREWS[c["screw"]]
    t, w4, w6 = L24["t"], L24["w"], L26["w"]
    d.update(t=t, leg_x=w4, rail_h=w4, plank_w=w6, screw_spec=sc, wall_screw=dict(WALL_SCREW))

    r = RESERVOIRS[c["tote"]]
    TL, TW, TH = r.exterior_top
    tx, ty = TW, TL                               # short side out: the handle end faces the room
    d.update(tote_label=r.model, tote_x=tx, tote_y=ty, tote_h=TH)

    # --- X: ladders (rail | leg | rail) and columns; the knee space takes what the 10 ft top leaves ---
    cols = s["columns"]
    n_lad = len(cols) + 1
    lad_w = 2 * t + w4
    tote_col = _up(tx + 2 * c["tote_side_clear"], IN / 16)
    rest = s["length"] - 2 * c["top_overhang_end"] - n_lad * lad_w - cols.count("T") * tote_col
    knee = math.floor(rest / max(cols.count("K"), 1) / (IN / 16) + 1e-9) * (IN / 16) if "K" in cols else None
    x = c["top_overhang_end"]
    ladders, columns = [], []
    for i in range(n_lad):
        ladders.append(dict(i=i, rail_L=x, leg=x + t, rail_R=x + t + w4))
        x += lad_w
        if i < len(cols):
            wd = tote_col if cols[i] == "T" else knee
            columns.append(dict(j=i, kind=cols[i], x0=x, x1=x + wd))
            x += wd
    W = x + c["top_overhang_end"]
    d.update(n_ladders=n_lad, ladders=ladders, columns=columns, tote_col=tote_col, knee=knee, lad_w=lad_w, W=W)
    d["ladder_marks"] = [lad["leg"] for lad in ladders]           # back legs' left edges, from the sill's left end

    # --- Y: sill and ledger against the drywall, back legs in front of them, rails from there to the front legs ---
    D = c["top_planks"] * w6
    y_lap = t                                      # back face of the back legs = front face of sill and ledger
    y_front = c["wall_gap"] + D - c["top_overhang_front"]
    rail_len = y_front - y_lap
    d.update(y_lap=y_lap, y_front=y_front, rail_len=rail_len, D=D)
    d["back_leg_y"] = (y_lap, y_lap + t)
    d["front_leg_y"] = (y_front - t, y_front)

    # --- Z: lower tote on the slab, slats, upper tote, planks. The back frame stands on the lip, so a low lip and a
    # high slab both eat the lower tote's clearance ---
    mid_top = _up(site["lip_h_dev"] + FLOOR["floor_dev"] + TH + c["tote_gap_over"], c["mark_step"])
    slat_top = mid_top + t
    top_need = slat_top + TH + c["tote_gap_over"] + t
    top_h = _up(max(c["top_h_target"], top_need), c["mark_step"])
    d["top_h_governed_by"] = "top_h_target (DESIGN)" if top_h <= c["top_h_target"] + 1e-9 else "two totes stacked"
    trt = top_h - t                                # top rail top = ledger top = leg tops
    d.update(mid_top=mid_top, slat_top=slat_top, top_need=top_need, top_h=top_h, H=top_h, top_rail_top=trt)
    d["mid_rail_z"] = (mid_top - w4, mid_top)
    d["top_rail_z"] = (trt - w4, trt)
    d["sill_z"] = (site["lip_h"], site["lip_h"] + w4)
    d["ledger_z"] = d["top_rail_z"]
    d["back_leg_z"] = (site["lip_h"], trt)
    d["front_leg_z"] = (0.0, trt)                  # as trimmed in place, on the nominal floor
    d["mid_rail_from_top"] = trt - mid_top
    d["gap_over_lower_worst"] = mid_top - (site["lip_h_dev"] + FLOOR["floor_dev"] + TH)
    d["gap_over_lower"] = mid_top - TH
    d["gap_over_upper"] = trt - (slat_top + TH)
    d["front_leg_nominal"] = trt
    d["front_leg_blank"] = _up(trt + site["lip_h_dev"] + FLOOR["floor_dev"] + c["front_leg_blank_extra"], IN / 2)

    # --- boards ---
    b = {}
    b["SILL"] = ("x2x4", (W, t, w4), (0.0, 0.0, d["sill_z"][0]))
    b["LEDGER"] = ("x2x4", (W, t, w4), (0.0, 0.0, d["ledger_z"][0]))
    for lad in ladders:
        i = lad["i"]
        b[f"L{i}-LEG-BACK"] = ("x2x4", (w4, t, trt - site["lip_h"]), (lad["leg"], y_lap, site["lip_h"]))
        b[f"L{i}-LEG-FRONT"] = ("x2x4", (w4, t, trt), (lad["leg"], d["front_leg_y"][0], 0.0))
        for side in ("L", "R"):
            for lvl, (z0, _) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                b[f"L{i}-RAIL-{lvl}-{side}"] = ("x2x4", (t, rail_len, w4), (lad[f"rail_{side}"], y_lap, z0))
    n_sl = math.ceil((rail_len + c["slat_gap_max"]) / (w6 + c["slat_gap_max"]) - 1e-9)
    slat_gap = (rail_len - n_sl * w6) / (n_sl - 1)
    d.update(n_slats=n_sl, slat_gap=slat_gap)
    for col in columns:
        j = col["j"]
        if col["kind"] == "T":
            for k in range(n_sl):
                b[f"C{j}-SLAT-{k}"] = ("x2x6", (col["x1"] - col["x0"] + 2 * t, w6, t), (col["x0"] - t, y_lap + k * (w6 + slat_gap), mid_top))
        else:
            fx0, fx1 = ladders[j]["leg"], ladders[j + 1]["leg"] + w4
            b[f"C{j}-FOOTREST"] = ("x2x4", (fx1 - fx0, t, w4), (fx0, y_front, c["footrest_top"] - w4))
    for k in range(c["top_planks"]):
        b[f"PLANK-{k}"] = ("x2x6", (W, w6, t), (0.0, c["wall_gap"] + k * w6, trt))
    d["boards"] = b
    d["lower_tote_y"] = site["lip_depth"] + c["tote_stop_gap"]
    d["upper_tote_y"] = t + c["tote_stop_gap"]                  # against the ledger
    d["stop_engage"] = slat_top + TH - d["ledger_z"][0]

    totes = {}
    for col in columns:
        if col["kind"] == "T":
            xc = (col["x0"] + col["x1"]) / 2 - tx / 2
            totes[f"TOTE-C{col['j']}-LOWER"] = ((tx, ty, TH), (xc, d["lower_tote_y"], 0.0))
            totes[f"TOTE-C{col['j']}-UPPER"] = ((tx, ty, TH), (xc, d["upper_tote_y"], slat_top))
    d["totes"] = totes

    # --- screws: (name, through board, into board, head xyz, unit dir, length); one length ---
    ln = _pick(sc, t, t)
    d["screw_len"] = ln
    screws = []
    for lad in ladders:
        i, lx = lad["i"], lad["leg"] + w4 / 2
        for frame, (z0, z1) in (("SILL", d["sill_z"]), ("LEDGER", d["ledger_z"])):
            for f in c["lap_rows"]:
                screws.append((f"L{i}-LEG-BACK>{frame}@{f / IN:g}", f"L{i}-LEG-BACK", frame, (lx, 2 * t, z1 - f), (0, -1, 0), ln))
        for side, sx in (("L", 1), ("R", -1)):
            xh = lad["rail_L"] if side == "L" else lad["rail_R"] + t
            for lvl, (z0, z1) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                rail = f"L{i}-RAIL-{lvl}-{side}"
                for end, (y0, y1) in (("BACK", d["back_leg_y"]), ("FRONT", d["front_leg_y"])):
                    for f in c["rail_rows"]:
                        screws.append((f"{rail}>{end}@{f / IN:g}", rail, f"L{i}-LEG-{end}", (xh, (y0 + y1) / 2, z1 - f), (sx, 0, 0), ln))
    for nm, (kind, size, lo) in b.items():
        if nm.startswith("PLANK-") or "-SLAT-" in nm:
            lvl = "TOP" if nm.startswith("PLANK") else "MID"
            ov0, ov1 = max(lo[1], y_lap), min(lo[1] + size[1], y_front)   # where the board is over the rails
            yc, q = (ov0 + ov1) / 2, (ov1 - ov0) / 4
            for lad in ladders:
                for side in ("L", "R"):
                    rail = f"L{lad['i']}-RAIL-{lvl}-{side}"
                    rl = b[rail][2]
                    if not (lo[0] - 1e-6 <= rl[0] and rl[0] + t <= lo[0] + size[0] + 1e-6):
                        continue
                    for dy in (-q, q):
                        screws.append((f"{nm}>{rail}{dy:+.0f}", nm, rail, (rl[0] + t / 2, yc + dy, lo[2] + t), (0, 0, -1), ln))
        elif nm.endswith("-FOOTREST"):
            j = int(nm[1:nm.index("-")])
            for lad in (ladders[j], ladders[j + 1]):
                for f in c["rail_rows"]:
                    screws.append((f"{nm}>L{lad['i']}@{f / IN:g}", nm, f"L{lad['i']}-LEG-FRONT",
                                   (lad["leg"] + w4 / 2, lo[1] + t, lo[2] + w4 - f), (0, -1, 0), ln))
    d["screws"] = screws

    # --- wall screws: through sill and ledger and the drywall into every stud, at stud_rows ---
    ws = d["wall_screw"]
    d["wall_bite"] = ws["length"] - t - site["drywall_t_max"]
    d["wall_studs_nominal"] = int(W // site["stud_oc"]) + 1
    d["wall_screws_nominal"] = 2 * len(c["stud_rows"]) * d["wall_studs_nominal"]

    # --- cutting: (stock length, sticks) per lumber; sill, ledger and planks are whole boards ---
    plans = {}
    plans["x2x4 120"] = (120 * IN, [[("SILL", W)], [("LEDGER", W)]])
    pieces = [(nm, max(sz)) for nm, (k, sz, _) in b.items() if k == "x2x4" and nm not in ("SILL", "LEDGER") and "LEG-FRONT" not in nm]
    pieces += [(nm, d["front_leg_blank"]) for nm in b if "LEG-FRONT" in nm]
    plans["x2x4 96"] = (96 * IN, cut_plan(pieces, 96 * IN, 0.0, c["kerf"]))
    plans["x2x6 120"] = (120 * IN, [[(nm, W)] for nm in b if nm.startswith("PLANK")])
    plans["x2x6 96"] = (96 * IN, cut_plan([(nm, sz[0]) for nm, (k, sz, _) in b.items() if "-SLAT-" in nm], 96 * IN, 0.0, c["kerf"]))
    d["cut_plans"] = plans
    d["wood_volume"] = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in b.values())
    d["unverified"] = [
        f"lip {frac_in(site['lip_depth'])} x {frac_in(site['lip_h'])} in: owner's rough figures. Its height goes into "
        "the front-leg cut and shims under the sill; the sill needs 1-3/4 in of its depth",
        f"floor +-{frac_in(FLOOR['floor_dev'])} in: an allowance, taken up by the front-leg cut",
        f"drywall up to {frac_in(site['drywall_t_max'])} in over wood studs: sets the wall screw length",
        f"wall length: the bench needs {frac_in(W)} in along the lip",
    ]
    return d


def validate(version: str, **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(version, **overrides)
    sc, ws = d["screw_spec"], d["wall_screw"]
    fi = lambda x: f"{frac_in(x)} in"
    t = d["t"]
    assert t <= d["lip_depth"] - d["lip_edge_min"] + 1e-9, f"{version}: sill {fi(t)} deep does not fit the lip {fi(d['lip_depth'])}"
    assert d["mid_rail_z"][0] >= d["sill_z"][1] - 1e-9, f"{version}: mid rail overlaps the sill"
    assert d["gap_over_lower_worst"] >= d["tote_gap_over"] - 1e-9, f"{version}: lower tote lid clears by {fi(d['gap_over_lower_worst'])} worst case"
    assert d["gap_over_upper"] >= d["tote_gap_over"] - 1e-9, f"{version}: upper tote lid clears by {fi(d['gap_over_upper'])}"
    assert d["stop_engage"] >= 0.5 * IN, f"{version}: the ledger catches the upper tote by only {fi(d['stop_engage'])}"
    for tn, (size, lo) in d["totes"].items():
        assert lo[1] + size[1] <= d["wall_gap"] + d["D"] + 1e-9, f"{version}: {tn} sticks out past the top's front edge"
    if d["knee"] is not None:
        assert d["knee"] >= d["knee_min"] - 1e-9, f"{version}: knee space {fi(d['knee'])} < {fi(d['knee_min'])}"
    assert 0 <= d["slat_gap"] <= d["slat_gap_max"] + 1e-9, f"{version}: slat gap {fi(d['slat_gap'])}"
    assert abs(d["W"] - d["length"]) < IN / 16, f"{version}: top {fi(d['W'])} is not the {fi(d['length'])} boards"
    # stock: every board a crosscut of stock (no rips), on a 1/16 reading, no longer than its stock
    for nm, (kind, size, _) in d["boards"].items():
        L = LUMBER[kind]
        assert sorted(size)[:2] == sorted((L["t"], L["w"])), f"{version}: {nm} is ripped: {size}"
        assert abs(max(size) / (IN / 16) - round(max(size) / (IN / 16))) < 1e-6, f"{version}: {nm} is not a 1/16 reading"
        assert max(size) <= max(L["stock"]) + 1e-9, f"{version}: {nm} longer than stock"
    assert d["front_leg_blank"] <= 96 * IN
    # screws: the wood screw bites 6D everywhere; the wall screw bites 6D into a stud through the thicker drywall
    assert d["screw_len"] is not None, f"{version}: no stocked {sc['label']} bites 6D through 1-1/2 into 1-1/2"
    assert d["wall_bite"] >= ws["min_penetration_d"] * ws["d"] - 1e-9, f"{version}: wall screw bites {fi(d['wall_bite'])} into a stud"
    # a stud can be anywhere, so wall screws must miss lap screws at any x: rows apart by more than both shanks
    for zs in d["stud_rows"]:
        for zl in d["lap_rows"]:
            assert abs(zs - zl) - (ws["d"] + sc["d"]) / 2 >= d["screw_gap_min"], f"{version}: stud row {fi(zs)} meets lap row {fi(zl)}"
    # rail screws stay below the plank screw tips
    assert min(d["rail_rows"]) - (d["screw_len"] - t) >= 0.5 * IN - 1e-9, f"{version}: rail screws meet the plank screws"
    S = d["screws"]
    tip = lambda s: tuple(h + u * s[5] for h, u in zip(s[3], s[4]))
    for a in range(len(S)):
        for b in range(a + 1, len(S)):
            if not ({S[a][1], S[a][2]} & {S[b][1], S[b][2]}):
                continue
            gap = seg_dist(S[a][3], tip(S[a]), S[b][3], tip(S[b])) - sc["d"]
            assert gap >= d["screw_gap_min"], f"{version}: screws {S[a][0]} and {S[b][0]} {gap:.1f} mm apart"
    return d


def report(version: str) -> str:
    d = derive(version)
    fi = frac_in
    cols = " | ".join("tote" if c["kind"] == "T" else "knee" for c in d["columns"])
    lines = [
        f"{version}: {d['note']}",
        f"  top {fi(d['W'])} x {fi(d['D'])} in, {fi(d['H'])} in high; columns {cols}; tote column {fi(d['tote_col'])}, "
        f"knee {fi(d['knee'])} in",
        f"  back frame: sill + ledger (whole 10 ft 2x4s, on edge) + {d['n_ladders']} back legs "
        f"{fi(d['boards']['L0-LEG-BACK'][1][2])} in at " + ", ".join(fi(x) for x in d["ladder_marks"]) + " in from the left end",
        f"  height governed by {d['top_h_governed_by']} (totes need {d['top_need'] / IN:.2f} in); lower lid gap "
        f"{fi(d['gap_over_lower'])} nominal, {fi(d['gap_over_lower_worst'])} worst; upper {fi(d['gap_over_upper'])}; "
        f"ledger catches the upper tote by {fi(d['stop_engage'])}",
        f"  front legs: blanks {fi(d['front_leg_blank'])} in, trimmed in place (~{fi(d['front_leg_nominal'])} on a nominal floor)",
        f"  screws: {len(d['screws'])} x {d['screw_spec']['label']} {fi(d['screw_len'])} in; "
        f"~{d['wall_screws_nominal']} x {d['wall_screw']['label']} {fi(d['wall_screw']['length'])} in "
        f"(2 per stud per board at 16 in centres, bite {fi(d['wall_bite'])} in)",
    ]
    for k, (stock, plan) in d["cut_plans"].items():
        lines.append(f"  {k.split()[0][1:]} {stock / IN / 12:g} ft x {len(plan)}")
    lines.append("  UNVERIFIED: " + "; ".join(d["unverified"]))
    return "\n".join(lines)


if __name__ == "__main__":
    for v in VERSIONS:
        try:
            validate(v)
            print(report(v), "\n  ok" + ("" if v in ACTIVE_VERSIONS else " (inactive)"))
        except AssertionError as e:
            print(f"{v}: FAIL: {e}")
