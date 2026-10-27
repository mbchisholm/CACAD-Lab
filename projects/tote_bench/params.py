"""Tote workbench: four HDX 27 gal totes in two bays (two on the floor, two on
a plywood shelf) under a 3/4 in plywood work top, with a pegboard hutch and a
top shelf on the two back legs. Built mostly from lumber on hand (INVENTORY);
SHOPPING is what is left to buy. Everything downstream (bench.py,
freecad_view.py, build_sheet.py, tests) reads `derive()`.

How it is laid out, and why:
- Four legs at the corners and nothing else upright. The front legs stop under
  the top; the back legs run on to 72 in and carry the hutch.
- Three side rails per side (floor, shelf, top), 2x4 on edge on the inside
  faces of the legs, four screws each. They sit outside the tote bay, so they
  can stand on edge without costing height; they are the 31 in 2x4s on hand.
- Across the bay only the members that must be: the top's front and back
  aprons on edge (a stiff work top), the shelf's front and back rails flat
  (1-1/2 in, so two tote levels fit under a ~38-1/2 in top), and a back
  stretcher at the floor that stops the floor totes.
- Plywood top and shelf: totes slide on the shelf; the plywood squares the
  frame. A 2x2 lip on the shelf's back edge stops the shelf totes.
- Hutch: pegboard on 2x2 cleats between the back legs; a top shelf on 2x4
  arms, each held up by one of the 45 deg braces bearing on the leg.

Coordinates: origin = floor at the outer corner of the front-left leg; +X to
the right, +Y toward the back, +Z up. Boards are boxes: name -> (kind, size,
min corner). Braces are prisms: name -> (kind, axis, lo, thickness, polygon)
with the polygon in (y, z) for axis "x".

    plan, front-left corner (front is down):

        |   |SIDE| bay ...       LEG    2x4, 1-1/2 in X, 3-1/2 in Y
        |LEG|RAIL|               SIDE   2x4 on edge on the leg's inner face, full depth
        |   |    +--------       APRON  top front rail, 2x4 on edge, between the side rails
        +---+----+ APRON

    .venv/bin/python projects/tote_bench/params.py      # design, cut plan, shopping list
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan, seg_dist
from cacad.registries.reservoirs import HDX_27GAL

STATUS = "concept"   # concept | passes | printed | parked

IN = 25.4
LBF = 4.448222       # N per lbf
PSI = 0.00689476     # MPa per psi
SIXTEENTH = IN / 16

# ---------------------------------------------------------------------------
# Bought lumber, sheet goods, screws, the tote. (value, TAG, source).
# ---------------------------------------------------------------------------
LUMBER = MappingProxyType(dict(
    x2x4=dict(t=1.5 * IN, w=3.5 * IN, label="2x4", source="ALSC PS 20: 2 in nominal -> 1-1/2, 4 in -> 3-1/2"),
    x2x2=dict(t=1.5 * IN, w=1.5 * IN, label="2x2", source="ALSC PS 20: 2 in nominal -> 1-1/2"),
))
PLY_T = (23 / 32 * IN, "STANDARD", "US DOC PS 1: 23/32 Performance Category, sold as 3/4 in plywood")
PEG_T = (0.25 * IN, "VENDOR", "1/4 in tempered hardboard pegboard, 1/4 in holes on 1 in centres, 2 x 4 ft panel")

# HDX 27 gal Tough Storage Tote, from the repo registry (homedepot.com 999-27G-HDX page, archived).
_TL, _TW, _TH = HDX_27GAL.exterior_top
_REG = "cacad.registries.reservoirs.HDX_27GAL (homedepot.com 999-27G-HDX)"
TOTE = MappingProxyType(dict(
    W=(_TW, "VENDOR", f"exterior width at top, {_REG}"),
    L=(_TL, "VENDOR", f"exterior length at top, {_REG}"),
    H=(_TH, "VENDOR", f"exterior height at top, with lid, {_REG}"),
    capacity=(75 * LBF, "VENDOR", "weight capacity 75 lb (Home Depot listing)"),
))

# #8 wood screws, NDS 6D minimum penetration. Lengths as stocked in boxes.
SCREW = MappingProxyType(dict(
    d=(0.164 * IN, "STANDARD", "ASME B18.6.1: #8 wood screw shank 0.164 in"),
    lengths=(tuple(x * IN for x in (1.25, 1.625, 1.75, 2.0, 2.5, 3.0)), "VENDOR", "#8 wood screw boxes: 1-1/4 .. 3 in"),
    min_penetration_d=(6.0, "STANDARD", "AWC NDS 2018 wood screws: 6D minimum penetration into the main member"),
    toe_len=(3.0 * IN, "DESIGN", "toe screws (middle joist ends, brace feet): driven at ~30 deg, a 3 in reaches"),
))

# SPF No.2 reference design values (AWC NDS Supplement 2018, Table 4A, Spruce-Pine-Fir No.2).
SPF = MappingProxyType(dict(
    Fb=(875 * PSI, "STANDARD", "NDS Supplement Table 4A, SPF No.2: Fb 875 psi"),
    E=(1.4e6 * PSI, "STANDARD", "NDS Supplement Table 4A, SPF No.2: E 1,400,000 psi"),
    CF=(1.5, "STANDARD", "NDS Supplement Table 4A size factor, 2-4 in wide: 1.5"),
    Cfu=(1.1, "STANDARD", "NDS Supplement Table 4A flat-use factor, 2x4: 1.1"),
    CD_storage=(0.9, "STANDARD", "NDS 2.3.2 load duration, long-term storage: 0.9"),
    CD_work=(1.0, "STANDARD", "NDS 2.3.2 load duration, normal (ten years cumulative): 1.0"),
))

# ---------------------------------------------------------------------------
# On hand. The braces and the 2x2 length were not measured: the braces are recut to one long point that the
# shortest of them reaches, and the 2x2s are taken as the 8 ft they were bought as.
# ---------------------------------------------------------------------------
INVENTORY = MappingProxyType(dict(
    leg72=(4, 72 * IN, "x2x4", "on hand: 72 in 2x4s, square ends"),
    x2x4_31=(4, 31 * IN, "x2x4", "on hand: 31 in 2x4s"),
    brace45=(4, (18 * IN, 24 * IN), "x2x4", "on hand: 18-24 in long point, 45 deg both ends. UNVERIFIED length"),
    x2x2=(8, 96 * IN, "x2x2", "on hand: 8 x 2x2. UNVERIFIED length: taken as the 8 ft they are sold in"),
    scraps=(None, None, "x2x4", "on hand: several shorter 2x4 scraps, lengths unknown; nothing depends on them"),
))
STORE_2X4 = (96 * IN, "VENDOR", "2x4 x 8 ft, any home centre")
STORE_PLY = ((48 * IN, 96 * IN), "VENDOR", "23/32 in plywood, 4 x 8 ft sheet: work top, tote shelf, hutch shelf")
STORE_PEG = ((24 * IN, 48 * IN), "VENDOR", "1/4 in pegboard, 2 x 4 ft panel")

DESIGN = MappingProxyType(dict(
    D=(31 * IN, "DESIGN", "bench depth = the 31 in 2x4s on hand, uncut: tote 28.6 + back lip 1.5 + front reveal"),
    clear_side=(0.25 * IN, "DESIGN", "tote rim to the side rail, per side"),
    clear_mid=(0.5 * IN, "DESIGN", "between the two totes of a level"),
    clear_lid=(0.75 * IN, "DESIGN", "lid top to the rail above: the tote slides in without lifting"),
    front_reveal_min=(0.5 * IN, "DESIGN", "parked tote's front at least this far behind the bench front"),
    work_height_range=((36 * IN, 39 * IN), "DESIGN", "standing work height window; 2 tote levels set ~38-1/2 in"),
    hutch_shelf_d=(12 * IN, "DESIGN", "hutch shelf depth from the back face: a standard 12 in shelf; both arms come out of one board"),
    peg_h=(24 * IN, "DESIGN", "pegboard height: the 2 ft panel's short side, standing on the work top's back edge"),
    peg_lift=(0.5 * IN, "DESIGN", "pegboard bottom above the work surface: clears the top for wiping"),
    brace_headroom=(18 * IN, "DESIGN", "brace feet above the work surface: clear of a head over the back of the bench"),
    brace_recut_min=(0.5 * IN, "DESIGN", "each brace's long point is recut at least this much, so all four start square"),
    defl_limit_shelf=(240, "DESIGN", "shelf rail deflection limit L/240 under full totes (storage practice)"),
    defl_limit_top=(360, "DESIGN", "top apron deflection limit L/360 under the point load (bench practice)"),
    point_load=(200 * LBF, "DESIGN", "a 200 lb point load mid-span on a top apron: someone leaning on the front edge"),
    hutch_load=(50 * LBF, "DESIGN", "hutch shelf load, uniform: paint cans and boxes"),
    kerf=(IN / 8, "DESIGN", "material lost per cut: 1/8 in covers a full-kerf 7-1/4 in circular-saw blade"),
    end_trim=(1 * IN, "DESIGN", "squared off the factory end of every stick or board before the first cut"),
    notch_clear=(IN / 16, "DESIGN", "plywood notches round the back legs, per side: the top drops on without binding"),
    screw_gap_min=(3.0, "DESIGN", "closest approach of two screw shanks, mm (axis distance minus d)"),
    screw_tip_cover=(0.25 * IN, "DESIGN", "wood left past a screw tip in the member it bites"),
    ply_screw_pitch=(8 * IN, "DESIGN", "plywood screwed down into every rail and joist under it at <= 8 in"),
    explode=(3.0, "DESIGN", "display only, FreeCAD exploded view: moves in 2x4 widths"),
    bbox_tol=(0.05, "DESIGN", "mm, geometry checks"),
))


def ceil16(mm: float) -> float:
    return math.ceil(mm / SIXTEENTH - 1e-9) * SIXTEENTH


def floor16(mm: float) -> float:
    return math.floor(mm / SIXTEENTH + 1e-9) * SIXTEENTH


def tape(mm: float) -> str:
    """Tape-measure reading to the nearest 1/16 in, e.g. 29-5/8"."""
    n = round(mm / SIXTEENTH)
    whole, rem = divmod(n, 16)
    if rem == 0:
        return f'{whole}"'
    g = math.gcd(rem, 16)
    frac = f"{rem // g}/{16 // g}"
    return f'{whole}-{frac}"' if whole else f'{frac}"'


def brace_polygon(corner, su: float, sz: float, L: float, w: float):
    """45 deg brace in the corner of a vertical face and a horizontal line, long point L, board width w.
    corner = (u, z) where they meet; su = +1/-1 along the horizontal; sz = -1/+1 down/up the vertical face.
    Points (u, z): short edge on the vertical face, short edge on the horizontal, long edge on the horizontal,
    long edge on the vertical face."""
    u0, z0 = corner
    e = w * math.sqrt(2)            # each cut face is w / sin 45
    a = L / math.sqrt(2) - e        # corner to the short-edge points
    assert a > 0, f"brace long point {L / IN:.2f} in too short for a {w / IN} in board"
    return ((u0, z0 + sz * a), (u0 + su * a, z0), (u0 + su * (a + e), z0), (u0, z0 + sz * (a + e)))


def derive(**overrides) -> dict:
    d = {k: v[0] for k, v in DESIGN.items()}
    d.update({f"tote_{k}": v[0] for k, v in TOTE.items()})
    for k, v in overrides.items():
        assert k in d, f"override {k!r} is not a DESIGN or tote_ value"
        d[k] = v
    t, w = LUMBER["x2x4"]["t"], LUMBER["x2x4"]["w"]
    s = LUMBER["x2x2"]["t"]
    ply, peg = PLY_T[0], PEG_T[0]
    TW, TL, TH = d["tote_W"], d["tote_L"], d["tote_H"]
    D = d["D"]
    H = INVENTORY["leg72"][1]
    d.update(t=t, w=w, s=s, ply=ply, peg=peg, H=H)

    # --- plan: one bay for two totes side by side between the side rails
    bay = ceil16(2 * TW + 2 * d["clear_side"] + d["clear_mid"])
    W = bay + 4 * t                               # legs and side rails, both sides
    x_in = 2 * t                                  # bay starts at the left side rail's inner face
    d.update(bay=bay, W=W, x_in=x_in)

    # --- elevation, floor up, every height to the 1/16 in
    shelf_rail = ceil16(TH + d["clear_lid"])       # underside of the shelf's flat front/back rails
    shelf_top = shelf_rail + t                     # top of the shelf frame
    shelf_surf = shelf_top + ply                   # tote 2 stands here
    apron = ceil16(shelf_surf + TH + d["clear_lid"])   # underside of the top aprons
    top_frame = apron + w                          # top of the top frame = front leg height
    work = top_frame + ply
    d.update(shelf_rail=shelf_rail, shelf_top=shelf_top, shelf_surf=shelf_surf, apron=apron,
             top_frame=top_frame, work_surface=work, front_leg=top_frame)
    d["tote_base"] = [0.0, shelf_surf]
    d["lid_gap"] = [shelf_rail - TH, apron - (shelf_surf + TH)]

    b = {}
    # legs: front legs cut to the top frame, back legs the full 72
    for nm, x, y, h in (("LEG-FL", 0, 0, top_frame), ("LEG-FR", W - t, 0, top_frame),
                        ("LEG-BL", 0, D - w, H), ("LEG-BR", W - t, D - w, H)):
        b[nm] = ("x2x4", (t, w, h), (x, y, 0.0))
    # side rails: on edge on the legs' inner faces, full depth; floor, shelf, top
    for lvl, ztop in (("FLOOR", w), ("SHELF", shelf_top), ("TOP", top_frame)):
        for side, x in (("L", t), ("R", W - 2 * t)):
            b[f"SIDE-{side}-{lvl}"] = ("x2x4", (t, D, w), (x, 0.0, ztop - w))
    # across the bay, between the side rails
    b["APRON-F"] = ("x2x4", (bay, t, w), (x_in, 0.0, apron))
    b["APRON-B"] = ("x2x4", (bay, t, w), (x_in, D - t, apron))
    b["SHELF-RAIL-F"] = ("x2x4", (bay, w, t), (x_in, 0.0, shelf_rail))
    b["SHELF-RAIL-B"] = ("x2x4", (bay, w, t), (x_in, D - w, shelf_rail))
    b["STRETCHER-B"] = ("x2x4", (bay, t, w), (x_in, D - t, 0.0))
    # joists down the middle of the bay, where the two totes' gap is
    xm = x_in + bay / 2
    b["JOIST-TOP"] = ("x2x4", (t, D - 2 * t, w), (xm - t / 2, t, apron))
    b["JOIST-SHELF"] = ("x2x2", (s, D - 2 * w, s), (xm - s / 2, w, shelf_top - s))
    # plywood: the top (notched round the back legs, built from d["top"]) and the shelf between the legs
    b["SHELF"] = ("plywood", (W - 2 * t, D, ply), (t, 0.0, shelf_top))
    b["LIP"] = ("x2x2", (bay, s, s), (x_in, D - s, shelf_surf))
    c = d["notch_clear"]
    d["top"] = dict(size=(W, D, ply), lo=(0.0, 0.0, top_frame),
                    notches=[(x - c, D - w - c, t + 2 * c, w + 2 * c) for x in (0.0, W - t)])

    # --- hutch: pegboard on 2x2 cleats on the back legs' inner faces; top shelf on 2x4 arms and braces
    peg_z = work + d["peg_lift"]
    peg_y = D - w - peg                            # in front of the back legs' front faces
    for side, x in (("L", t), ("R", W - t - s)):
        b[f"CLEAT-{side}"] = ("x2x2", (s, s, d["peg_h"]), (x, D - w, peg_z))
    b["PEGBOARD"] = ("pegboard", (W - 2 * t, peg, d["peg_h"]), (t, peg_y, peg_z))
    arm_len = d["hutch_shelf_d"]
    for side, x in (("L", t), ("R", W - 2 * t)):
        b[f"ARM-{side}"] = ("x2x4", (t, arm_len, w), (x, D - arm_len, H - w))
    b["HUTCH"] = ("plywood", (W, arm_len, ply), (0.0, D - arm_len, H))
    d["boards"] = b

    # braces: in the plane of each back leg, plumb end bearing on the leg's front face, top end level with the arm's
    # top and screwed to the arm's outer face. Recut so the long edge reaches the arm's front end.
    reach = arm_len - w                            # leg front face to the arm's front end
    L = floor16(reach * math.sqrt(2))              # long point that reaches it, to the 1/16 in
    d["brace_long_point"] = L
    poly = brace_polygon((D - w, H), -1, -1, L, w)
    pr = {"BRACE-L": ("x2x4", "x", 0.0, t, poly), "BRACE-R": ("x2x4", "x", W - t, t, poly)}
    d["prisms"] = pr
    d["brace_low"] = min(p[1] for p in poly)

    # --- totes, as check envelopes: pushed back against the stretcher (floor) or the lip (shelf), centred in halves
    totes = {}
    for lv, (zb, y_back) in enumerate(((0.0, D - t), (shelf_surf, D - s)), start=1):
        for k, ab in enumerate("AB"):
            x0 = x_in + d["clear_side"] + k * (TW + d["clear_mid"])
            totes[f"TOTE-{lv}{ab}"] = ((TW, TL, TH), (x0, y_back - TL, zb))
    d["totes"] = totes
    d["front_reveal"] = min(lo[1] for _, lo in totes.values())

    # --- structure
    Fb, E = SPF["Fb"][0] * SPF["CF"][0], SPF["E"][0]
    P = d["tote_capacity"] / 2                     # each tote's bottom bears near the front and back rails: half each
    a = d["clear_side"] + TW / 2                   # tote centre from the side rail
    I_flat, S_flat = w * t ** 3 / 12, w * t ** 2 / 6
    d["shelf_rail_stress"] = P * a / S_flat
    d["shelf_rail_Fb"] = Fb * SPF["Cfu"][0] * SPF["CD_storage"][0]
    d["shelf_rail_defl"] = P * a * (3 * bay ** 2 - 4 * a ** 2) / (24 * E * I_flat)
    I_edge, S_edge = t * w ** 3 / 12, t * w ** 2 / 6
    d["apron_stress"] = d["point_load"] * bay / 4 / S_edge
    d["apron_Fb"] = Fb * SPF["CD_work"][0]
    d["apron_defl"] = d["point_load"] * bay ** 3 / (48 * E * I_edge)
    # hutch: shelf load on two arms; each brace takes it in compression at 45 deg
    d["brace_force"] = d["hutch_load"] / 2 * math.sqrt(2)

    # --- screws: (name, through, into, head, unit dir, length, penetration). Shortest stocked length that bites 6D.
    sd = SCREW["d"][0]
    need = SCREW["min_penetration_d"][0] * sd

    def pick(through, into):
        fit = [ln for ln in SCREW["lengths"][0] if ln - through >= need - 1e-9 and ln - through <= into - d["screw_tip_cover"] + 1e-9]
        return min(fit) if fit else None

    joints = {
        "leg->side rail": (t, t, pick(t, t)),                 # from outside, through the leg into the side rail
        "side rail->apron/rail": (t, bay, pick(t, bay)),      # through the side rail into the cross member's end grain
        "apron->joist": (t, D, pick(t, D)),                   # through the apron into the joist's end grain
        "ply->frame": (ply, t, pick(ply, t)),                 # plywood into a flat rail (the shallowest it lands on)
        "ply->lip": (ply, s, pick(ply, s)),                   # up through the shelf into the lip
        "cleat->leg": (s, t, pick(s, t)),
        "arm->leg": (t, t, pick(t, t)),
        "brace->arm": (t, t, pick(t, t)),
    }
    d["joints"] = joints
    scr = []

    def add(nm, through, into, head, u, joint):
        ln = joints[joint][2]
        if ln is not None:
            scr.append((nm, through, into, head, u, ln, ln - joints[joint][0]))

    # legs to side rails: four per joint from the leg's outer face. At the front leg keep to the back of the patch and
    # at the back leg to the front: the cross members' end screws come through the side rail at the outer end.
    for side in ("L", "R"):
        for lvl in ("FLOOR", "SHELF", "TOP"):
            rail = f"SIDE-{side}-{lvl}"
            _, rsz, rlo = b[rail]
            for fb in ("F", "B"):
                leg = f"LEG-{fb}{side}"
                lx, ly, _ = b[leg][2]
                x_head, u = (lx, (1, 0, 0)) if side == "L" else (lx + t, (-1, 0, 0))
                ys = (ly + 2.25 * IN, ly + 3.0 * IN) if fb == "F" else (ly + 0.5 * IN, ly + 1.25 * IN)
                # shelf rails are flat in the top 1.5 in of the side rail: keep below them there
                zs = (rlo[2] + 0.6 * IN, rlo[2] + 1.6 * IN) if lvl == "SHELF" else (rlo[2] + 0.9 * IN, rlo[2] + 2.6 * IN)
                for i, y in enumerate(ys):
                    for j, z in enumerate(zs):
                        add(f"{leg}>{rail}#{i}{j}", leg, rail, (x_head, y, z), u, "leg->side rail")
    # cross members into the side rails' inner faces... from the side rail's outer face, before the legs go on
    for nm in ("APRON-F", "APRON-B", "SHELF-RAIL-F", "SHELF-RAIL-B", "STRETCHER-B"):
        _, sz, lo = b[nm]
        lvl = "TOP" if nm.startswith("APRON") else "SHELF" if nm.startswith("SHELF") else "FLOOR"
        on_edge = sz[2] > sz[1]
        pts = [(lo[1] + sz[1] / 2, lo[2] + f * sz[2]) for f in (0.3, 0.7)] if on_edge else \
              [(lo[1] + f * sz[1], lo[2] + sz[2] / 2) for f in (0.3, 0.7)]
        for side, x_head, u in (("L", t, (1, 0, 0)), ("R", W - t, (-1, 0, 0))):
            for k, (y, z) in enumerate(pts):
                add(f"SIDE-{side}-{lvl}>{nm}#{k}", f"SIDE-{side}-{lvl}", nm, (x_head, y, z), u, "side rail->apron/rail")
    # top joist through the aprons
    _, jsz, jlo = b["JOIST-TOP"]
    for ap, y_head, u in (("APRON-F", 0.0, (0, 1, 0)), ("APRON-B", D, (0, -1, 0))):
        for k, f in enumerate((0.3, 0.7)):
            add(f"{ap}>JOIST-TOP#{k}", ap, "JOIST-TOP", (jlo[0] + t / 2, y_head, jlo[2] + f * w), u, "apron->joist")
    # lip: up through the shelf plywood
    _, lsz, llo = b["LIP"]
    n_lip = int(math.ceil(lsz[0] / d["ply_screw_pitch"])) + 1
    for k in range(n_lip):
        x = llo[0] + 2 * IN + k * (lsz[0] - 4 * IN) / (n_lip - 1)
        if abs(x - xm) < 1.5 * IN:
            x += 2 * IN                             # step off the shelf joist's end
        add(f"SHELF>LIP#{k}", "SHELF", "LIP", (x, llo[1] + s / 2, shelf_top), (0, 0, 1), "ply->lip")
    # pegboard cleats into the back legs
    for side in ("L", "R"):
        cl, leg = f"CLEAT-{side}", f"LEG-B{side}"
        _, csz, clo = b[cl]
        x_head, u = (clo[0] + s, (-1, 0, 0)) if side == "L" else (clo[0], (1, 0, 0))
        for k, f in enumerate((0.15, 0.5, 0.85)):
            add(f"{cl}>{leg}#{k}", cl, leg, (x_head, clo[1] + s / 2, clo[2] + f * csz[2]), u, "cleat->leg")
    # hutch arms into the back legs (four, from inside), braces into the arms (two, from outside)
    for side in ("L", "R"):
        arm, leg, br = f"ARM-{side}", f"LEG-B{side}", f"BRACE-{side}"
        _, asz, alo = b[arm]
        x_head, u = (alo[0] + t, (-1, 0, 0)) if side == "L" else (alo[0], (1, 0, 0))
        for i, y in enumerate((D - w + 0.9 * IN, D - 0.9 * IN)):
            for j, z in enumerate((H - w + 0.9 * IN, H - 0.9 * IN)):
                add(f"{arm}>{leg}#{i}{j}", arm, leg, (x_head, y, z), u, "arm->leg")
        bx = 0.0 if side == "L" else W
        ub = (1, 0, 0) if side == "L" else (-1, 0, 0)
        p1, p2, p3, p4 = poly
        zc = H - w / 2
        for k, f in enumerate((0.3, 0.7)):
            y_short = p2[0] + (H - zc)               # short edge at height zc (it falls toward the leg)
            y_long = p3[0] + (H - zc)                # long edge at height zc
            add(f"{br}>{arm}#{k}", br, arm, (bx, y_long + f * (y_short - y_long), zc), ub, "brace->arm")
    d["screws"] = scr

    # counted, not modelled: plywood screws at <= pitch along every member under it, and toe screws
    along = lambda n_: int(math.ceil(n_ / d["ply_screw_pitch"])) + 1
    d["ply_screws"] = dict(
        top=2 * along(W) + 2 * along(D) + along(D),          # aprons, top side rails, joist
        shelf=2 * along(bay) + 2 * along(D) + along(D),      # shelf rails, shelf side rails, joist
        hutch=2 * along(arm_len) + along(W) // 2,            # arms, and into the leg tops
    )
    d["toe_screws"] = dict(shelf_joist=4, brace_feet=2)
    d["peg_screws"] = 2 * 4                                  # pan-head + washer, 4 per cleat

    # --- cuts against the inventory and the shopping list
    def plen(nm):
        return max(b[nm][1]) if nm in b else L
    d["cut_on_hand"] = {
        "72 in 2x4": [("LEG-BL", H), ("LEG-BR", H), ("LEG-FL", top_frame), ("LEG-FR", top_frame)],
        "72 in offcuts": [("SIDE-L-FLOOR", D), ("SIDE-R-FLOOR", D)],
        "31 in 2x4": [(n, D) for n in ("SIDE-L-SHELF", "SIDE-R-SHELF", "SIDE-L-TOP", "SIDE-R-TOP")],
        "45 deg braces": [("BRACE-L", L), ("BRACE-R", L)],
    }
    d["leg_offcut"] = H - top_frame - d["kerf"]
    two_by_two = [(n, plen(n)) for n in b if b[n][0] == "x2x2"]
    d["plan_2x2"] = cut_plan(two_by_two, INVENTORY["x2x2"][1], d["end_trim"], d["kerf"])
    bought = [(n, plen(n)) for n in b if b[n][0] == "x2x4" and n.startswith(("APRON", "SHELF-RAIL", "STRETCHER", "JOIST", "ARM"))]
    d["plan_bought_2x4"] = cut_plan(bought, STORE_2X4[0], d["end_trim"], d["kerf"])
    d["plan_sheet"] = [("TOP", W, D), ("SHELF", W - 2 * t, D), ("HUTCH", W, arm_len)]
    d["spare"] = dict(x2x2=INVENTORY["x2x2"][0] - len(d["plan_2x2"]), braces=INVENTORY["brace45"][0] - len(pr))

    counts = {}
    for sc in scr:
        counts[sc[5]] = counts.get(sc[5], 0) + 1
    lp = joints["ply->frame"][2]
    counts[lp] = counts.get(lp, 0) + sum(d["ply_screws"].values())
    toe = SCREW["toe_len"][0]
    counts[toe] = counts.get(toe, 0) + sum(d["toe_screws"].values())
    d["screw_counts"] = dict(sorted(counts.items()))
    d["shopping"] = [
        ("2x4 x 8 ft", len(d["plan_bought_2x4"]), "aprons, shelf rails, back stretcher, top joist, hutch arms"),
        ("23/32 in plywood, 4 x 8 ft sheet", 1, f"top {tape(W)} x {tape(D)}, shelf {tape(W - 2 * t)} x {tape(D)}, "
                                                f"hutch shelf {tape(W)} x {tape(arm_len)}"),
        ("1/4 in pegboard, 2 x 4 ft", 1, f"cut to {tape(W - 2 * t)} x {tape(d['peg_h'])}"),
    ] + [(f"#8 wood screws {tape(ln)}", n, "") for ln, n in d["screw_counts"].items()] + [
        ("#8 pan-head screws 1-1/4\" + washers", d["peg_screws"], "pegboard to the cleats"),
        ("wood glue", 1, "every face joint and every end-grain joint"),
        ("HDX 27 gal Tough Storage Tote", 4, "if not already on hand"),
    ]

    # --- exploded view (display only): the frame stays, the plywood lifts, the legs and side rails move out
    m = d["explode"] * w
    left = [n for n in b if n.endswith("L") and n.startswith("LEG")] + [n for n in b if n.startswith("SIDE-L")]
    right = [n for n in b if n.endswith("R") and n.startswith("LEG")] + [n for n in b if n.startswith("SIDE-R")]
    moves = [
        ("top up", ["TOP"], (0.0, 0.0, m)),
        ("shelf up", ["SHELF", "LIP"], (0.0, 0.0, m / 2)),
        ("left legs and rails out", left, (-m, 0.0, 0.0)),
        ("right legs and rails out", right, (m, 0.0, 0.0)),
        ("hutch forward", ["HUTCH", "ARM-L", "ARM-R", "BRACE-L", "BRACE-R", "PEGBOARD", "CLEAT-L", "CLEAT-R"], (0.0, -m, m / 2)),
    ]
    d["explode_moves"] = moves
    d["explode_offset"] = {nm: tuple(sum(v[i] for _, parts, v in moves if nm in parts) for i in range(3))
                           for nm in list(b) + list(pr) + ["TOP"]}
    return d


def validate(**overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(**overrides)
    mm = lambda x: f"{x:.1f} mm ({x / IN:.3f} in)"
    rows = dict(ply=PLY_T, peg=PEG_T, store_2x4=STORE_2X4, store_ply=STORE_PLY, store_peg=STORE_PEG)
    for table in (DESIGN, TOTE, SCREW, SPF, MappingProxyType(rows)):
        for k, v in table.items():
            assert len(v) == 3 and v[1] and v[2], f"{k}: every number needs (value, TAG, source)"
    assert STATUS in ("concept", "passes", "printed", "parked")
    t, w, s, D, W, H = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"]
    # inventory
    assert D <= INVENTORY["x2x4_31"][1] + 1e-9, f"side rails {mm(D)} longer than the 31 in on hand"
    assert d["leg_offcut"] >= D - 1e-9, f"front-leg offcut {mm(d['leg_offcut'])} too short for a {mm(D)} side rail"
    lo, hi = INVENTORY["brace45"][1]
    assert d["brace_long_point"] <= lo - d["brace_recut_min"] + 1e-9, \
        f"brace long point {mm(d['brace_long_point'])}: the shortest brace on hand ({mm(lo)}) cannot be recut to it"
    assert len(d["plan_2x2"]) <= INVENTORY["x2x2"][0]
    # fit: totes in the bay, behind the front, under the rail above
    assert d["bay"] >= 2 * d["tote_W"] + 2 * d["clear_side"] + d["clear_mid"] - 1e-9
    assert d["front_reveal"] >= d["front_reveal_min"] - 1e-9, f"tote front {mm(d['front_reveal'])} behind the bench front"
    for i, g in enumerate(d["lid_gap"], start=1):
        assert g >= d["clear_lid"] - 1e-9, f"level {i} lid to the rail above {mm(g)}"
    lo_h, hi_h = d["work_height_range"]
    assert lo_h <= d["work_surface"] <= hi_h, f"work surface {mm(d['work_surface'])} outside the window"
    # hutch: the braces stand in the legs' plane, outside the pegboard; their feet stay well above the work top
    assert d["brace_low"] - d["work_surface"] >= d["brace_headroom"] - 1e-9, \
        f"brace feet {mm(d['brace_low'] - d['work_surface'])} above the work top"
    assert d["work_surface"] + d["peg_lift"] + d["peg_h"] <= d["H"] - d["w"], "pegboard runs into the hutch arms"
    # sheet goods: the three plywood pieces across the sheet's width, along its length
    pw, pl = STORE_PLY[0]
    assert all(wd <= pw for _, wd, _ in d["plan_sheet"]), "a plywood piece is wider than the sheet"
    assert sum(dp for _, _, dp in d["plan_sheet"]) + len(d["plan_sheet"]) * d["kerf"] <= pl, "plywood pieces exceed the sheet"
    gw, gh = STORE_PEG[0]
    assert W - 2 * t <= gh and d["peg_h"] <= gw, "pegboard larger than the panel"
    # structure
    assert d["shelf_rail_stress"] <= d["shelf_rail_Fb"], f"shelf rail {d['shelf_rail_stress'] / PSI:.0f} psi"
    assert d["shelf_rail_defl"] <= d["bay"] / d["defl_limit_shelf"], f"shelf rail sags {mm(d['shelf_rail_defl'])}"
    assert d["apron_stress"] <= d["apron_Fb"], f"apron {d['apron_stress'] / PSI:.0f} psi under the point load"
    assert d["apron_defl"] <= d["bay"] / d["defl_limit_top"], f"apron deflects {mm(d['apron_defl'])} under the point load"
    # screws: stocked lengths; no two shanks in a shared member closer than screw_gap_min
    for jn, (through, into, ln) in d["joints"].items():
        assert ln is not None, f"{jn}: no stocked #8 screw bites 6D through {mm(through)} and stays inside {mm(into)}"
    sd = SCREW["d"][0]
    tip = lambda sc: tuple(h + u * sc[5] for h, u in zip(sc[3], sc[4]))
    for i in range(len(d["screws"])):
        for j in range(i + 1, len(d["screws"])):
            a, b_ = d["screws"][i], d["screws"][j]
            if not ({a[1], a[2]} & {b_[1], b_[2]}):
                continue
            gap = seg_dist(a[3], tip(a), b_[3], tip(b_)) - sd
            assert gap >= d["screw_gap_min"], f"screws {a[0]} and {b_[0]} {gap:.1f} mm apart"
    return d


def report(d: dict) -> str:
    f = tape
    L = [
        f"Tote workbench: {f(d['W'])} W x {f(d['D'])} D; work surface {f(d['work_surface'])}; back legs and hutch to {f(d['H'] + d['ply'])}",
        f"  bay {f(d['bay'])} for two {d['tote_W'] / IN:.1f} in totes; floor totes on the floor, shelf at {f(d['shelf_surf'])}; "
        f"lid gaps " + ", ".join(f"{g / IN:.2f}" for g in d["lid_gap"]) + f" in; tote fronts {d['front_reveal'] / IN:.2f} in behind the front",
        f"  shelf rails (flat): {d['shelf_rail_stress'] / PSI:.0f} psi of {d['shelf_rail_Fb'] / PSI:.0f}, sag {d['shelf_rail_defl'] / IN:.3f} in "
        f"under two full totes; aprons: {d['apron_stress'] / PSI:.0f} psi of {d['apron_Fb'] / PSI:.0f}, "
        f"{d['apron_defl'] / IN:.3f} in under {d['point_load'] / LBF:.0f} lb",
        f"  hutch: pegboard {f(d['W'] - 2 * d['t'])} x {f(d['peg_h'])} from {f(d['work_surface'] + d['peg_lift'])}; "
        f"shelf {f(d['hutch_shelf_d'])} deep at {f(d['H'])}; braces recut to a {f(d['brace_long_point'])} long point "
        f"({d['brace_force'] / LBF:.0f} lb each in compression)",
        "",
        "ON HAND",
        f"  4 x 72\" 2x4    back legs as they are; front legs cut to {f(d['front_leg'])} (offcut {f(d['leg_offcut'])} -> floor side rails, {f(d['D'])})",
        f"  4 x 31\" 2x4    shelf and top side rails, as they are",
        f"  4 x 45 deg     2 recut to a {f(d['brace_long_point'])} long point as hutch braces; {d['spare']['braces']} spare",
        f"  2x2            {len(d['plan_2x2'])} of 8 sticks ({d['spare']['x2x2']} spare):",
    ]
    for i, st in enumerate(d["plan_2x2"], start=1):
        used = d["end_trim"] + sum(l + d["kerf"] for _, l in st)
        L.append(f"      stick {i}: " + " + ".join(f"{n} {f(l)}" for n, l in st) + f"   offcut {f(INVENTORY['x2x2'][1] - used)}")
    L += ["", "TO BUY"]
    for item, n, note in d["shopping"]:
        L.append(f"  {n:>3} x {item}" + (f"   ({note})" if note else ""))
    L.append("  bought 2x4 cut plan:")
    for i, st in enumerate(d["plan_bought_2x4"], start=1):
        used = d["end_trim"] + sum(l + d["kerf"] for _, l in st)
        L.append(f"      board {i}: " + " + ".join(f"{n} {f(l)}" for n, l in st) + f"   offcut {f(STORE_2X4[0] - used)}")
    L += ["", "SCREWS BY JOINT (#8, 6D bite, tip >= 1/4 in inside)"]
    for jn, (through, into, ln) in d["joints"].items():
        L.append(f"  {jn:22s} {f(ln) if ln else 'NONE':>7}  through {f(through)}")
    return "\n".join(L)


if __name__ == "__main__":
    d = validate()
    print(report(d))
    print("\nok")
