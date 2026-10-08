"""Workbench on the lip wall: a 2x4 frame with a two-layer plywood top, and
under it HDX 27 gal totes two high in each bay, sliding out like drawers.
Lumber, not a print. Everything downstream (bench.py, tests,
freecad_view.py) reads `derive(bench)`.

The lip does three jobs (projects/garage: concrete, ~2.5 in deep, ~6 in tall,
the whole length of the wall):
  - the back legs stand on it, so they are 6 in shorter, bear on concrete
    above the slab's puddles, and the top reaches the wall with no gap behind;
  - its face is the lower tote's back stop: push the tote in until it touches;
  - the bench cannot slide or tip backward: the legs are against the lip.
Every leg ends in a leveling foot. Its travel absorbs the floor and the
roughness of the lip height, so neither has to be measured.

Coordinates are the garage's (projects/garage/params.py): +X along the wall
from the bench's left frame, +Y out of the wall (wall face y = 0, lip face
y = lip_depth), +Z up from the floor at the lip face. Every member is an
axis-aligned box: name -> (kind, size xyz, min corner xyz), in mm.

    plan of one bay (wall at the bottom):              section through a bay (wall at the left):

      FRONT LEG   tote 28.6 wide   FRONT LEG            top (2 x 23/32 ply)  ======================
      [===]R|                     |R[===]               stretcher  [S]  upper tote, stops at S
           A|    bay clear         |A                   (top level)       +------------------+
           I|  tote + 2 x 0.5 in   |I                                     |                  |
           L|                     |L                   shelf (23/32 ply) =======================
      [===]R|_____stretcher_______|R[===]  back legs                  back +-----------------+
      BACK LEG     (top level)     BACK LEG on the lip   leg   lower tote, stops at the lip face
      ---- lip ---------------------------------- ---   on    +------------------+
      ---- wall face ------------------------------     lip   |                  |   front leg
                                                       [LIP]  |                  |   on a foot
                                                       =======+==================+====== floor

Legs are 2x4 with 3.5 in along X: racking along the wall bends them about
their strong axis between the shelf and top diaphragms. Rails are 2x4 on edge
screwed to the legs' bay-side faces, front leg to back leg, at shelf and top
level; the shelf and the top rest on them. Nothing crosses the front, so a tote
needs only a ply thickness and a clearance between levels.
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan
from cacad.registries.reservoirs import RESERVOIRS
from projects.garage.params import FLOOR, WALLS
from projects.tote_rack.params import LUMBER, SCREWS

IN = 25.4

# 3/4 in nominal plywood: US PS 1-19 performance category 23/32 in; 4 x 8 ft sheet.
PLY = MappingProxyType(dict(
    t=23 / 32 * IN, sheet=(96 * IN, 48 * IN), label="3/4 in (23/32) plywood, 4 x 8 ft",
    source="US PS 1-19: nominal 3/4 in panel = 23/32 in performance category; 48 x 96 in sheet",
))

# Leveling foot: a threaded-stud leveler in a tee nut set in the leg's end grain. No product chosen yet, so the
# envelope and travel are UNVERIFIED; any 3/8-16 stud leveler with at least this travel works. It is the only bought
# part whose size matters, and only through its travel: validate() checks that the travel covers the floor and lip.
FOOT = MappingProxyType(dict(
    label="3/8-16 stud leveling foot + 3/8-16 tee nut", thread="3/8-16",
    h_min=0.75 * IN,                  # UNVERIFIED: leg end to floor, stud screwed fully in
    h_max=1.75 * IN,                  # UNVERIFIED: leg end to floor, stud at its useful maximum
    pad_d=1.5 * IN,                   # UNVERIFIED: pad diameter; must fit the 1.5 in leg face and stay on the lip
    source="UNVERIFIED: generic 3/8-16 stud leveler; pick one with >= 1 in travel and a pad <= 1.5 in",
))

COMMON = MappingProxyType(dict(
    tote="HDX_27GAL",                 # cacad.registries.reservoirs: exterior at the top, with lid, from the vendor page
    tote_long_along_x=True,           # DESIGN: long side faces the room, so a tote pulls out only 19.6 in
    # --- clearances (in, DESIGN): each separates two named surfaces ---
    tote_side_clear=0.5 * IN,         # tote rim to the rail beside it, per side
    tote_gap_over=1.0 * IN,           # tote lid to whatever is above it (shelf underside, top underside)
    tote_stop_gap=0.25 * IN,          # tote back to its back stop (lip face below, stretcher above), when pushed home
    wall_gap=0.25 * IN,               # wall face to the back legs and the top: drywall is not flat
    lip_edge_min=0.25 * IN,           # back foot pad to the lip's front edge: keeps the pad off a broken concrete arris
    stop_engage_min=0.5 * IN,         # how far the stretcher must hang below the upper tote's lid top to stop it
    top_overhang_front=1.0 * IN,      # top past the front legs' front faces
    top_overhang_end=1.0 * IN,        # top past each end leg
    top_layers=2,                     # two 23/32 ply layers glued: 1.44 in, flat and stiff over a bay
    # --- fastening (DESIGN unless named) ---
    screw="no8",
    screws_rail_end=2,                # rail -> leg, per end, through the rail's bay-side face along X
    screw_rows=(0.25, 0.75),          # those two at these fractions of the rail height
    ply_screw_pitch_max=8.0 * IN,     # ply -> rail / stretcher
    ply_screw_inset=2.0 * IN,         # first and last ply screw from a member's end
    screw_gap_min=3.0,                # mm, closest approach of the two screws meeting in a middle leg from each side
    # --- cutting and checks ---
    kerf=IN / 8,
    bbox_tol=0.05,
))

# Inputs only. One size: two bays, four totes.
BENCHES = {
    "2bay": dict(
        wall="lip_wall",
        bays=2,
        top_h_target=36.0 * IN,       # DESIGN: the common workbench / counter height; raised by derive() if the totes need it
        top_depth=24.0 * IN,          # DESIGN: half a 4 ft sheet, so both top layers rip from one sheet
    ),
}

ACTIVE_BENCHES = ("2bay",)


def _pick(sc: dict, through: float, into: float) -> float | None:
    """Shortest stocked screw that bites 6D past `through` and does not exit `into`."""
    need = through + sc["min_penetration_d"] * sc["d"]
    fit = [ln for ln in sc["lengths"] if ln >= need - 1e-9 and ln < through + into - 1e-9]
    return fit[0] if fit else None


def _sheet_plan(pieces: list[tuple[str, float, float]], sheet: tuple[float, float], kerf: float) -> list[list]:
    """Rip-then-crosscut: pieces of one width share a rip (cut_plan on the sheet length), rips pack across the sheet
    width (cut_plan again). pieces: (name, length, width). Returns sheets, each a list of (width, [(name, length)])."""
    by_w: dict[float, list] = {}
    for nm, ln, w in pieces:
        by_w.setdefault(round(w, 6), []).append((nm, ln))
    rips = []
    for w, ps in by_w.items():
        for i, st in enumerate(cut_plan(ps, sheet[0], 0.0, kerf)):
            rips.append((f"{w:.3f}#{i}", w, st))
    packed = cut_plan([(rid, w) for rid, w, _ in rips], sheet[1], 0.0, kerf)
    lookup = {rid: (w, st) for rid, w, st in rips}
    return [[lookup[rid] for rid, _ in sh] for sh in packed]


def derive(bench: str, **overrides) -> dict:
    """Every dimension bench.py and the tests need. Overrides are for what-if tables only."""
    s = dict(BENCHES[bench])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(bench=bench, **s, **c)
    site = dict(WALLS[s["wall"]])
    d.update(lip_depth=site["lip_depth"], lip_h=site["lip_h"], lip_h_dev=site["lip_h_dev"], floor_dev=FLOOR["floor_dev"])
    L24, sc, ply_t = LUMBER["x2x4"], SCREWS[c["screw"]], PLY["t"]
    leg_x, leg_y = L24["w"], L24["t"]            # leg: 3.5 along X, 1.5 along Y
    rail_t, rail_h = L24["t"], L24["w"]          # rail on edge: 1.5 along X, 3.5 tall
    d.update(leg_x=leg_x, leg_y=leg_y, rail_t=rail_t, rail_h=rail_h, ply_t=ply_t, screw_spec=sc, foot=dict(FOOT))

    r = RESERVOIRS[c["tote"]]
    TL, TW, TH = r.exterior_top                  # 28.6 x 19.6 x 15.2 in, with lid: an envelope, the tote tapers inside it
    tx, ty = (TL, TW) if c["tote_long_along_x"] else (TW, TL)
    d.update(tote_label=r.model, tote_source=r.source, tote_x=tx, tote_y=ty, tote_h=TH)

    # --- foot: set mid-travel, so it can go up or down by the same amount ---
    f = FOOT
    d["foot_h"] = (f["h_min"] + f["h_max"]) / 2
    d["foot_travel_each_way"] = min(d["foot_h"] - f["h_min"], f["h_max"] - d["foot_h"])
    d["foot_must_absorb"] = max(FLOOR["floor_dev"], site["lip_h_dev"])

    # --- X: frames and bays, left to right ---
    n_fr = s["bays"] + 1
    bay_clear = tx + 2 * c["tote_side_clear"]
    x = 0.0
    frames, bays = [], []
    for i in range(n_fr):
        fr = dict(i=i)
        if i > 0:
            fr["rail_L"] = x
            x += rail_t
        fr["leg"] = x
        x += leg_x
        if i < n_fr - 1:
            fr["rail_R"] = x
            x += rail_t
            bays.append((x, x + bay_clear))
            x += bay_clear
        frames.append(fr)
    frame_len = x
    W = frame_len + 2 * c["top_overhang_end"]
    top_x0 = -c["top_overhang_end"]
    d.update(n_frames=n_fr, frames=frames, bays_x=bays, bay_clear=bay_clear, frame_len=frame_len, W=W, top_x0=top_x0)

    # --- Y: back legs against the wall over the lip, front legs under the top's front edge ---
    y_back = c["wall_gap"]
    y_front = y_back + s["top_depth"] - c["top_overhang_front"]   # front legs' front face
    rail_len = y_front - y_back
    d.update(y_back=y_back, y_front=y_front, rail_len=rail_len, D=s["top_depth"], top_y0=y_back)
    d["back_leg_y"] = (y_back, y_back + leg_y)
    d["front_leg_y"] = (y_front - leg_y, y_front)
    d["stretcher_y"] = (y_back, y_back + leg_y)                   # in line with the back legs, so it cannot meet the tote
    d["back_pad_y"] = (y_back + leg_y / 2 - f["pad_d"] / 2, y_back + leg_y / 2 + f["pad_d"] / 2)

    # --- Z: lower tote on the slab, shelf over it, upper tote on the shelf, top over that ---
    shelf_bot = FLOOR["floor_dev"] + TH + c["tote_gap_over"]     # a slab high spot lifts the lower tote by floor_dev
    shelf_top = shelf_bot + ply_t
    top_t = c["top_layers"] * ply_t
    top_h_need = shelf_top + TH + c["tote_gap_over"] + top_t
    top_h = max(s["top_h_target"], top_h_need)
    d["top_h_governed_by"] = "top_h_target (DESIGN)" if top_h == s["top_h_target"] else "two totes stacked"
    top_rail_top = top_h - top_t
    d.update(shelf_bot=shelf_bot, shelf_top=shelf_top, top_t=top_t, top_h=top_h, top_h_need=top_h_need,
             top_rail_top=top_rail_top, H=top_h)
    d["mid_rail_z"] = (shelf_bot - rail_h, shelf_bot)
    d["top_rail_z"] = (top_rail_top - rail_h, top_rail_top)
    d["front_leg_z"] = (d["foot_h"], top_rail_top)
    d["back_leg_z"] = (site["lip_h"] + d["foot_h"], top_rail_top)
    d["gap_over_lower"] = shelf_bot - (TH + FLOOR["floor_dev"])
    d["gap_over_upper"] = top_rail_top - (shelf_top + TH)

    # --- boards ---
    b = {}
    for fr in frames:
        i = fr["i"]
        b[f"LEG-F{i}-BACK"] = ("x2x4", (leg_x, leg_y, d["back_leg_z"][1] - d["back_leg_z"][0]),
                               (fr["leg"], d["back_leg_y"][0], d["back_leg_z"][0]))
        b[f"LEG-F{i}-FRONT"] = ("x2x4", (leg_x, leg_y, d["front_leg_z"][1] - d["front_leg_z"][0]),
                                (fr["leg"], d["front_leg_y"][0], d["front_leg_z"][0]))
        for side in ("L", "R"):
            if f"rail_{side}" not in fr:
                continue
            for lvl, (z0, _) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                b[f"RAIL-F{i}{side}-{lvl}"] = ("x2x4", (rail_t, rail_len, rail_h), (fr[f"rail_{side}"], y_back, z0))
    for j, (x0, x1) in enumerate(bays):
        b[f"STRETCHER-B{j}"] = ("x2x4", (x1 - x0, leg_y, rail_h), (x0, d["stretcher_y"][0], d["top_rail_z"][0]))
        # the shelf covers both rails of its bay: from the left rail's outer face to the right rail's outer face
        sx0, sx1 = x0 - rail_t, x1 + rail_t
        b[f"SHELF-B{j}"] = ("ply", (sx1 - sx0, rail_len, ply_t), (sx0, y_back, shelf_bot))
    for k in range(c["top_layers"]):
        b[f"TOP-{k + 1}"] = ("ply", (W, s["top_depth"], ply_t), (top_x0, y_back, top_rail_top + k * ply_t))
    d["boards"] = b

    # --- feet: centred on each leg's end ---
    feet = {}
    for nm, (kind, size, lo) in b.items():
        if nm.startswith("LEG-"):
            feet["FOOT-" + nm[4:]] = ((lo[0] + size[0] / 2, lo[1] + size[1] / 2, lo[2] - d["foot_h"]), f["pad_d"] / 2, d["foot_h"])
    d["feet"] = feet   # name -> (base centre xyz, radius, height)

    # --- totes, as check envelopes: centred in the bay, pushed home against their stops ---
    y_low = site["lip_depth"] + c["tote_stop_gap"]
    y_up = d["stretcher_y"][1] + c["tote_stop_gap"]
    totes = {}
    for j, (x0, x1) in enumerate(bays):
        xc = (x0 + x1) / 2 - tx / 2
        totes[f"TOTE-B{j}-LOWER"] = ((tx, ty, TH), (xc, y_low, 0.0))
        totes[f"TOTE-B{j}-UPPER"] = ((tx, ty, TH), (xc, y_up, shelf_top))
    d["totes"] = totes
    d["tote_y_lower"], d["tote_y_upper"] = y_low, y_up
    d["stop_engage"] = shelf_top + TH - d["top_rail_z"][0]       # stretcher hangs this far below the upper tote's top

    # --- fastening ---
    joints = {
        "rail->leg": (rail_t, leg_x, _pick(sc, rail_t, leg_x)),
        "ply->rail": (ply_t, rail_h, _pick(sc, ply_t, rail_h)),
        "top->stretcher": (ply_t, rail_h, _pick(sc, ply_t, rail_h)),
    }
    d["joints"] = joints
    n_rail = sum(1 for nm in b if nm.startswith("RAIL-"))
    n_ply = lambda ln: int(math.ceil((ln - 2 * c["ply_screw_inset"]) / c["ply_screw_pitch_max"])) + 1
    d["screw_counts"] = {
        "rail->leg": n_rail * 2 * c["screws_rail_end"],
        "ply->rail": n_ply(rail_len) * n_rail,                     # shelf into mid rails, top layer 1 into top rails
        "top->stretcher": n_ply(bay_clear) * len(bays),
    }
    # two rails meet a middle leg from opposite faces at the same y and z: their tips must stay apart
    ln = joints["rail->leg"][2]
    d["middle_leg_tip_gap"] = leg_x - 2 * (ln - rail_t) if ln else None
    # layer 2 is glued to layer 1; screws from below through layer 1 are clamps while the glue cures. No stocked #8
    # bites 6D into 23/32 ply, so the glue is the joint: the longest screw that does not exit the top.
    lam = [ln for ln in sc["lengths"] if ln < 2 * ply_t - 1e-9]
    d["laminate_clamp_screw"] = lam[-1] if lam else None

    # --- cutting ---
    d["cut_plan_2x4"] = cut_plan([(nm, max(sz)) for nm, (k, sz, _) in b.items() if k == "x2x4"], L24["stock"][0], 0.0, c["kerf"])
    ply_pieces = [(nm, max(sz[0], sz[1]), min(sz[0], sz[1])) for nm, (k, sz, _) in b.items() if k == "ply"]
    d["sheet_plan"] = _sheet_plan(ply_pieces, PLY["sheet"], c["kerf"])
    d["wood_volume"] = sum(sz[0] * sz[1] * sz[2] for _, sz, _ in b.values())
    d["unverified"] = [
        f"lip {site['lip_depth'] / IN:g} in deep x {site['lip_h'] / IN:g} in tall: owner's rough figures",
        f"floor within +-{FLOOR['floor_dev'] / IN:g} in under any foot: allowance, no reading",
        f"leveling foot {f['h_min'] / IN:g}-{f['h_max'] / IN:g} in, pad {f['pad_d'] / IN:g} in: no product chosen",
        "wall length: not given; the bench needs " + f"{W / IN:.1f} in of it",
    ]
    return d


def validate(bench: str, **overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings. Overrides as for derive()."""
    d = derive(bench, **overrides)
    sc = d["screw_spec"]
    mm = lambda x: f"{x:.1f} mm ({x / IN:.2f} in)"
    # leveling: the feet absorb the floor and the rough lip height, both ways
    assert d["foot_travel_each_way"] >= d["foot_must_absorb"] - 1e-9, (
        f"{bench}: feet travel {mm(d['foot_travel_each_way'])} each way, floor/lip need {mm(d['foot_must_absorb'])}")
    assert d["foot"]["pad_d"] <= min(d["leg_x"], d["leg_y"]) + 1e-9, f"{bench}: foot pad wider than the leg end"
    # the back feet stand wholly on the lip, clear of its front edge
    assert d["back_pad_y"][0] >= 0 and d["back_pad_y"][1] <= d["lip_depth"] - d["lip_edge_min"] + 1e-9, (
        f"{bench}: back foot pad y {mm(d['back_pad_y'][0])}..{mm(d['back_pad_y'][1])} not on the lip "
        f"(0..{mm(d['lip_depth'] - d['lip_edge_min'])})")
    # the back legs stay behind the lower tote, which stops at the lip face
    assert d["back_leg_y"][1] <= d["tote_y_lower"] + 1e-9
    # every rail is screwed to a leg over its full height: it starts above the back leg's foot
    assert d["mid_rail_z"][0] >= d["back_leg_z"][0] - 1e-9, f"{bench}: mid rail starts below the back leg"
    # totes: clearance above each, both inside the top's footprint, the upper one actually stopped by the stretcher
    for nm, g in (("lower", d["gap_over_lower"]), ("upper", d["gap_over_upper"])):
        assert g >= d["tote_gap_over"] - 1e-9, f"{bench}: {nm} tote lid clears what is above by {mm(g)}, need {mm(d['tote_gap_over'])}"
    for tn, (size, lo) in d["totes"].items():
        assert lo[1] + size[1] <= d["top_y0"] + d["D"] + 1e-9, f"{bench}: {tn} sticks out past the top's front edge"
    assert d["stop_engage"] >= d["stop_engage_min"] - 1e-9, (
        f"{bench}: stretcher hangs {mm(d['stop_engage'])} below the upper tote's top, need {mm(d['stop_engage_min'])} to stop it")
    assert d["top_h"] >= d["top_h_need"] - 1e-9
    # screws: every structural joint has a stocked length that bites 6D and stays inside the member
    for jn, (through, into, ln) in d["joints"].items():
        assert ln is not None, f"{bench}: {jn}: no stocked {sc['label']} bites {mm(sc['min_penetration_d'] * sc['d'])} past {mm(through)} inside {mm(into)}"
    assert d["middle_leg_tip_gap"] >= d["screw_gap_min"], f"{bench}: rail screws meet inside a middle leg ({mm(d['middle_leg_tip_gap'])} apart)"
    assert d["laminate_clamp_screw"] is not None, f"{bench}: no stocked screw is short enough to clamp the top layers"
    # buildable from stock: every 2x4 piece fits an 8 ft stick, every ply piece a sheet
    assert all(max(sz) <= LUMBER["x2x4"]["stock"][0] for k, sz, _ in d["boards"].values() if k == "x2x4")
    assert all(max(sz[0], sz[1]) <= PLY["sheet"][0] and min(sz[0], sz[1]) <= PLY["sheet"][1]
               for k, sz, _ in d["boards"].values() if k == "ply")
    return d


def report(bench: str) -> str:
    d = derive(bench)
    i_ = lambda x: f"{x / IN:.2f}"
    k = lambda x: f"{x / IN:g}"
    lines = [
        f"{bench}: top {i_(d['W'])} x {i_(d['D'])} in, {i_(d['H'])} in high ({d['W']:.0f} x {d['D']:.0f} x {d['H']:.0f} mm); "
        f"{d['bays']} bays, {2 * d['bays']} totes ({d['tote_label'].split(',')[0]})",
        f"  height governed by {d['top_h_governed_by']}: two totes need {i_(d['top_h_need'])} in",
        f"  bay clear {i_(d['bay_clear'])} in for a {i_(d['tote_x'])} in tote: {k(d['tote_side_clear'])} in per side",
        f"  lower tote on the slab, back against the lip face at y = {i_(d['tote_y_lower'])} in; "
        f"lid to shelf {i_(d['gap_over_lower'])} in with the slab {k(d['floor_dev'])} in high under it",
        f"  upper tote on the shelf (top {i_(d['shelf_top'])} in), stopped by the stretcher at y = {i_(d['tote_y_upper'])} in "
        f"(engages {i_(d['stop_engage'])} in); lid to top {i_(d['gap_over_upper'])} in",
        f"  back legs on the lip: pad y {i_(d['back_pad_y'][0])}..{i_(d['back_pad_y'][1])} in of a {k(d['lip_depth'])} in lip; "
        f"feet set at {i_(d['foot_h'])} in, +-{i_(d['foot_travel_each_way'])} in absorbs floor and lip +-{k(d['foot_must_absorb'])}",
        f"  screws ({d['screw_spec']['label']}, 6D = {i_(d['screw_spec']['min_penetration_d'] * d['screw_spec']['d'])} in min bite):",
    ]
    for jn, (through, into, ln) in d["joints"].items():
        lines.append(f"    {jn:15s} {k(ln)} in: through {i_(through)}, bites {i_(ln - through)} of {i_(into)}; {d['screw_counts'][jn]} screws")
    lines.append(f"    top laminate: glue, clamped by {k(d['laminate_clamp_screw'])} in screws from below (no #8 bites 6D in 23/32 ply)")
    lines.append(f"    middle legs: rail screws from both faces end {d['middle_leg_tip_gap']:.0f} mm apart")
    lines.append("  cut list, 2x4 (8 ft):")
    by_len = {}
    for nm, (kind, sz, _) in d["boards"].items():
        if kind == "x2x4":
            by_len.setdefault((nm.split("-")[0] + ("-" + nm.split("-")[2] if nm.startswith("LEG") else ""), round(max(sz) / IN, 3)), []).append(nm)
    for (grp, ln), names in sorted(by_len.items(), key=lambda kv: -kv[0][1]):
        lines.append(f"    {len(names)} x {ln:g} in  {grp.lower()}")
    for n, st in enumerate(d["cut_plan_2x4"], start=1):
        used = sum(l + d["kerf"] for _, l in st)
        lines.append(f"      stick {n}: " + " + ".join(f"{l / IN:.2f}" for _, l in st) + f"  (offcut {(96 * IN - used) / IN:.1f} in)")
    lines.append(f"  cut list, {PLY['label']}:")
    for n, sh in enumerate(d["sheet_plan"], start=1):
        rips = "; ".join(f"rip {w / IN:.2f} in -> " + " + ".join(f"{nm} {l / IN:.2f}" for nm, l in st) for w, st in sh)
        lines.append(f"    sheet {n}: {rips}")
    lines.append(f"  buy: {len(d['cut_plan_2x4'])} x 2x4 8 ft, {len(d['sheet_plan'])} x {PLY['label']}, "
                 f"{2 * d['n_frames']} x {d['foot']['label']}, wood glue, #8 screws as above")
    lines.append("  UNVERIFIED: " + "; ".join(d["unverified"]))
    return "\n".join(lines)


if __name__ == "__main__":
    for bench in BENCHES:
        try:
            validate(bench)
            print(report(bench), "\n  ok" + ("" if bench in ACTIVE_BENCHES else " (inactive)"))
        except AssertionError as e:
            print(f"{bench}: FAIL: {e}")
