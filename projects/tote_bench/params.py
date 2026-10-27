"""Tote rack workbench: a 2x4 / 2x2 frame with four HDX 27 gal totes under a
3/4 in plywood work top (two columns, two levels) and an open upper frame to
72 in, braced by the four 45 deg knee braces. Built from what is on hand
(INVENTORY); SHOPPING is what is left to buy. Everything downstream (bench.py,
freecad_view.py, build_sheet.py, tests) reads `derive()`.

Each tote sits on its BOTTOM across two 2x2 rungs (front and back). It is
not hung by its rim: a 1-1/2 in rail would need the rim to stand ~1-3/8 in
proud of the wall, which HDX does not publish. Sitting on rungs depends only
on published numbers: width and length at the top, height with lid, interior
bottom length.

Coordinates: origin = floor at the outer corner of the front-left leg; +X to
the right, +Y toward the back, +Z up. The side rails sit outside the legs
(x < 0 and x > W). Boards are boxes: name -> (kind, size xyz, min corner).
Braces and diagonals are prisms: name -> (kind, axis, lo, thickness, polygon)
with the polygon in the other two axes ((y, z) for axis "x", (x, z) for "y").

    plan, front-left corner (front is down):

          |  |STR|        LEG   2x4, 1.5 in X, 3.5 in Y, 72 tall
        R |  |   |        RUNG  2x2 across the back face of the front legs (and the front face of the back legs)
        A |LEG   |        RAIL  2x4 on edge on the outer face of the legs (work level and top)
        I |  |   |        tote  sits on the front and back rungs, between a leg and the middle post
        L +--+---+-----   POST  2x4 middle post, front and back, floor to the work top
          |  RUNG

    .venv/bin/python projects/tote_bench/params.py      # design, cut plan, shopping list
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.lumber import cut_plan, seg_dist

STATUS = "concept"   # concept | passes | printed | parked

IN = 25.4
LBF = 4.448222       # N per lbf
PSI = 0.00689476     # MPa per psi
SIXTEENTH = IN / 16

# ---------------------------------------------------------------------------
# Bought lumber, as dressed sizes, and the HDX tote. (value, TAG, source).
# ---------------------------------------------------------------------------
LUMBER = MappingProxyType(dict(
    x2x4=dict(t=1.5 * IN, w=3.5 * IN, label="2x4", source="ALSC PS 20: 2 in nominal -> 1-1/2, 4 in -> 3-1/2"),
    x2x2=dict(t=1.5 * IN, w=1.5 * IN, label="2x2", source="ALSC PS 20: 2 in nominal -> 1-1/2"),
))
PLY_T = (23 / 32 * IN, "STANDARD", "US DOC PS 1: 23/32 Performance Category, sold as 3/4 in plywood")

# HDX 27 gal Tough Storage Tote (Home Depot 207 585). Two published listings disagree slightly; each value takes the
# side that is safe for its use (the larger envelope for clearance, the shorter bottom for bearing).
TOTE = MappingProxyType(dict(
    W=(19.61 * IN, "VENDOR", "exterior width at top: 19.61 in (Home Depot listing via Refinery29); 19.6 on the label"),
    L=(28.6 * IN, "VENDOR", "exterior length at top: 28.6 in (label, Home Depot spec); 28.55 in another listing"),
    H=(15.27 * IN, "VENDOR", "exterior height with lid: 15.27 in (listing); 15.2 on the label"),
    Lb=(22.98 * IN, "VENDOR", "interior length at bottom: 22.98 in (listing); 23.5 in another. Exterior >= interior"),
    capacity=(75 * LBF, "VENDOR", "weight capacity 75 lb (listing)"),
    bottom_centred=(True, "INFERRED", "the bottom is centred under the rim: the tote is mirror-symmetric front to back"),
))

# #8 wood screws, NDS 6D minimum penetration. Lengths as stocked in boxes.
SCREW = MappingProxyType(dict(
    d=(0.164 * IN, "STANDARD", "ASME B18.6.1: #8 wood screw shank 0.164 in"),
    lengths=(tuple(x * IN for x in (1.25, 1.625, 1.75, 2.0, 2.5, 3.0)), "VENDOR", "#8 wood screw boxes: 1-1/4, 1-5/8, 1-3/4, 2, 2-1/2, 3 in"),
    min_penetration_d=(6.0, "STANDARD", "AWC NDS 2018 wood screws: 6D minimum penetration into the main member"),
    toe_len=(3.0 * IN, "DESIGN", "toe screws at the side brace lower ends: driven at ~30 deg, a 3 in reaches the leg"),
))

# SPF No.2 reference design values (AWC NDS Supplement 2018, Table 4A, Spruce-Pine-Fir No.2).
SPF = MappingProxyType(dict(
    Fb=(875 * PSI, "STANDARD", "NDS Supplement Table 4A, SPF No.2: Fb 875 psi"),
    E=(1.4e6 * PSI, "STANDARD", "NDS Supplement Table 4A, SPF No.2: E 1,400,000 psi"),
    CF_2in=(1.5, "STANDARD", "NDS Supplement Table 4A size factor, 2 in and 3 in wide: 1.5 (2x2) / 1.5 (2x4)"),
    CD_storage=(0.9, "STANDARD", "NDS 2.3.2 load duration, permanent/long-term storage: 0.9"),
))

# ---------------------------------------------------------------------------
# What is on hand. The 45 deg braces and the 2x2 length were not measured: the design is checked at both ends of
# the brace range and the 2x2s are taken as the 8 ft they were bought as.
# ---------------------------------------------------------------------------
INVENTORY = MappingProxyType(dict(
    leg72=(4, 72 * IN, "x2x4", "on hand: cut from 8 ft 2x4s at 72 in, square ends"),
    x2x4_31=(4, 31 * IN, "x2x4", "on hand: 31 in 2x4s"),
    brace45=(4, (18 * IN, 24 * IN), "x2x4", "on hand: 18-24 in long point, 45 deg both ends. UNVERIFIED length"),
    x2x2=(8, 96 * IN, "x2x2", "on hand: 8 x 2x2. UNVERIFIED length: taken as the 8 ft they are sold in"),
    scraps=(None, None, "x2x4", "on hand: several shorter 2x4 scraps, lengths unknown; nothing depends on them"),
))
STORE_2X4 = (96 * IN, "VENDOR", "2x4 x 8 ft, any home centre")
STORE_PLY = ((48 * IN, 48 * IN), "VENDOR", "23/32 in plywood project panel 4 x 4 ft (or half a 4 x 8 sheet)")

DESIGN = MappingProxyType(dict(
    cols=(2, "DESIGN", "two tote columns side by side: a 44-3/4 in wide bench"),
    levels=(2, "DESIGN", "two tote levels under the work top"),
    clear_side=(0.25 * IN, "DESIGN", "tote top to leg or middle post, per side: slides in without guiding by hand"),
    clear_lid=(0.75 * IN, "DESIGN", "lid top to the rung above: room to slide the tote onto its rungs"),
    D=(29.625 * IN, "DESIGN", "bench depth: tote length + 1 in; the 31 in 2x4s are trimmed to it (see bearing)"),
    bearing_min=(0.75 * IN, "DESIGN", "tote bottom on each rung, minimum, with the tote against its back stop"),
    stop_below_top=(0.25 * IN, "DESIGN", "back stop top below the tote's lid top: the stop meets the rim/lid band"),
    brace_long_point=(21 * IN, "UNVERIFIED", "45 deg braces as drawn: mid of the 18-24 in range on hand"),
    brace_range=((18 * IN, 24 * IN), "UNVERIFIED", "every brace check runs at both ends of this range"),
    kerf=(IN / 8, "DESIGN", "material lost per cut: 1/8 in covers a full-kerf 7-1/4 in circular-saw blade"),
    work_height_range=((34 * IN, 39 * IN), "DESIGN", "standing work height window; the tote stack sets the value"),
    defl_limit=(240, "DESIGN", "rung deflection limit L/240 under full totes (storage shelving practice)"),
    point_load=(100 * LBF, "DESIGN", "a 100 lb point load at mid-span of a work-top rung, e.g. leaning on the front edge"),
    screw_gap_min=(3.0, "DESIGN", "closest approach of two screw shanks, mm (axis distance minus d)"),
    screw_tip_cover=(0.25 * IN, "DESIGN", "wood left past a screw tip in the member it bites"),
    top_screw_pitch=(8 * IN, "DESIGN", "plywood top screwed down into rails, rungs and joist at <= 8 in"),
    explode_top_lift=(4.0, "DESIGN", "display only, FreeCAD exploded view: the plywood top lifts this many 2x4 widths"),
    explode_side_out=(3.0, "DESIGN", "display only: each side (legs, rails, stretcher, diagonal, side brace) moves out in X by this many 2x4 widths"),
    explode_back_out=(2.0, "DESIGN", "display only: the back stops and the back braces move back in Y by this many 2x4 widths"),
    bbox_tol=(0.05, "DESIGN", "mm, geometry checks"),
))


def _v(table, k):
    return table[k][0]


def ceil16(mm: float) -> float:
    return math.ceil(mm / SIXTEENTH - 1e-9) * SIXTEENTH


def tape(mm: float) -> str:
    """Tape-measure reading to the nearest 1/16 in, e.g. 29-5/8"."""
    n = round(mm / SIXTEENTH)
    whole, rem = divmod(n, 16)
    if rem == 0:
        return f'{whole}"'
    g = math.gcd(rem, 16)
    frac = f"{rem // g}/{16 // g}"
    return f'{whole}-{frac}"' if whole else f'{frac}"'


def brace_polygon(corner, sx: float, sz: float, L: float, w: float):
    """Knee brace in the corner of a vertical face and a horizontal face, 45 deg both ends, long point L, width w.
    corner = (u, z) where the faces meet; sx = +1/-1 the direction along the horizontal face; sz = -1/+1 down/up the
    vertical face. Returns 4 points (u, z): short edge on the vertical face, short edge on the horizontal face, long
    edge on the horizontal face, long edge on the vertical face."""
    u0, z0 = corner
    e = w * math.sqrt(2)            # each cut face is w / sin 45
    a = L / math.sqrt(2) - e        # corner to the short-edge points
    assert a > 0, f"brace long point {L / IN:.2f} in too short for a {w / IN} in board"
    return ((u0, z0 + sz * a), (u0 + sx * a, z0), (u0 + sx * (a + e), z0), (u0, z0 + sz * (a + e)))


def derive(**overrides) -> dict:
    d = {k: v[0] for k, v in DESIGN.items()}
    d.update({f"tote_{k}": v[0] for k, v in TOTE.items()})
    for k, v in overrides.items():
        assert k in d, f"override {k!r} is not a DESIGN or tote_ value"
        d[k] = v
    t, w = LUMBER["x2x4"]["t"], LUMBER["x2x4"]["w"]     # 2x4: 1.5 x 3.5
    s = LUMBER["x2x2"]["t"]                              # 2x2: 1.5 square
    ply = PLY_T[0]
    TW, TL, TH, Lb = d["tote_W"], d["tote_L"], d["tote_H"], d["tote_Lb"]
    D, cols, levels = d["D"], d["cols"], d["levels"]
    d.update(t=t, w=w, s=s, ply=ply)

    # --- plan: columns between leg and middle post, each the tote top plus a clearance per side, to the 1/16 in
    col = ceil16(TW + 2 * d["clear_side"])
    inside = cols * col + (cols - 1) * t
    W = inside + 2 * t
    d.update(col=col, inside=inside, W=W)
    post_x = [t + (i + 1) * col + i * t for i in range(cols - 1)]   # min X of each middle post

    # --- elevation: rung rows to the 1/16 in, floor up. Row 0 is on the floor; the last row carries the work top.
    rows = [0.0]
    for _ in range(levels):
        rows.append(ceil16(rows[-1] + s + TH + d["clear_lid"]))
    work_top = rows[-1] + s                       # top of the work-level rungs, rails, posts and joist
    H = 72 * IN                                   # the legs on hand
    d.update(rows=rows, work_top=work_top, work_surface=work_top + ply, H=H)
    d["tote_base"] = [rows[i] + s for i in range(levels)]
    d["tote_top"] = [b + TH for b in d["tote_base"]]
    d["lid_gap"] = [rows[i + 1] - d["tote_top"][i] for i in range(levels)]

    # --- boards
    b = {}
    for nm, x, y in (("LEG-FL", 0, 0), ("LEG-FR", W - t, 0), ("LEG-BL", 0, D - w), ("LEG-BR", W - t, D - w)):
        b[nm] = ("x2x4", (t, w, H), (x, y, 0.0))
    for i, px in enumerate(post_x, start=1):
        b[f"POST-F{i}"] = ("x2x4", (t, w, work_top), (px, 0.0, 0.0))
        b[f"POST-B{i}"] = ("x2x4", (t, w, work_top), (px, D - w, 0.0))
    for r, z in enumerate(rows):
        b[f"RUNG-F{r}"] = ("x2x2", (W, s, s), (0.0, w, z))
        b[f"RUNG-B{r}"] = ("x2x2", (W, s, s), (0.0, D - w - s, z))
    b["TIE-F"] = ("x2x2", (W, s, s), (0.0, w, H - s))
    b["TIE-B"] = ("x2x2", (W, s, s), (0.0, D - w - s, H - s))
    for side, x in (("L", -t), ("R", W)):
        b[f"RAIL-{side}-WORK"] = ("x2x4", (t, D, w), (x, 0.0, work_top - w))
        b[f"RAIL-{side}-TOP"] = ("x2x4", (t, D, w), (x, 0.0, H - w))
        b[f"STR-{side}"] = ("x2x2", (s, D, s), (x, 0.0, 0.0))
    # middle joist under the top: 2x2 between the work rungs, beside the middle post (not over it), so the rung->post
    # screw heads and the rung->joist screw heads each land on an open face
    j_y0, j_y1 = w + s, D - w - s
    for i, px in enumerate(post_x, start=1):
        b[f"JOIST-{i}"] = ("x2x2", (s, j_y1 - j_y0, s), (px + t, j_y0, work_top - s))
    # back stops: 2x2 across the back face of the back legs and posts, top just under each level's lid top
    stops = []
    for i, top in enumerate(d["tote_top"], start=1):
        z0 = top - d["stop_below_top"] - s
        b[f"STOP-{i}"] = ("x2x2", (W, s, s), (0.0, D, z0))
        stops.append(z0)
    d["stop_z"] = stops
    d["boards"] = b

    # --- prisms: lower side diagonals (2x2 flat on the outer faces, plumb ends over the legs) and the 45 deg braces
    pr = {}
    z_lo, z_hi = s, work_top - w                  # above the bottom stretcher, below the work rail
    hv = s * math.hypot(D, z_hi - z_lo) / D       # vertical thickness of a strip s wide at that slope
    diag = ((0.0, z_lo), (0.0, z_lo + hv), (D, z_hi), (D, z_hi - hv))
    for side, x in (("L", -t), ("R", W)):
        pr[f"DIAG-{side}"] = ("x2x2", "x", x, s, diag)
    d["diag_len"] = math.hypot(D, z_hi - z_lo - hv)          # either edge of the parallelogram: plumb cut to plumb cut
    d["diag_cut_angle"] = math.degrees(math.atan2(z_hi - z_lo - hv, D))   # each plumb end, off square: the saw setting
    L = d["brace_long_point"]
    # side braces: in the leg line, against the inner face of the top rail, down onto the back face of the front leg
    sb = brace_polygon((w, H), +1, -1, L, w)
    pr["BRACE-SL"] = ("x2x4", "x", 0.0, t, sb)
    pr["BRACE-SR"] = ("x2x4", "x", W - t, t, sb)
    # back braces: in the back rung plane, from the outer face of the back leg up under the back top tie
    for side, x0, sx in (("L", 0.0, +1), ("R", W, -1)):
        pr[f"BRACE-B{side}"] = ("x2x4", "y", D - w - s, t, brace_polygon((x0, H - s), sx, -1, L, w))
    d["prisms"] = pr

    # --- plywood top: over the side rails, notched round the legs (the legs run on up)
    d["top"] = dict(size=(W + 2 * t, D, ply), lo=(-t, 0.0, work_top),
                    notches=[(lo[0], lo[1], t, w) for nm, (_, _, lo) in b.items() if nm.startswith("LEG-")])

    # --- totes, as check envelopes: against the back stops, centred in each column; the bottom is the bearing face
    totes, bottoms = {}, {}
    for lv in range(levels):
        for c in range(cols):
            x0 = t + c * (col + t) + (col - TW) / 2
            y0 = D - TL
            totes[f"TOTE-{lv + 1}{'AB'[c]}"] = ((TW, TL, TH), (x0, y0, d["tote_base"][lv]))
            yb = y0 + (TL - Lb) / 2
            bottoms[f"TOTE-{lv + 1}{'AB'[c]}"] = (yb, yb + Lb)
    d["totes"], d["tote_bottoms"] = totes, bottoms
    yb0, yb1 = next(iter(bottoms.values()))
    d["bearing_front"] = min(w + s, yb1) - max(w, yb0)
    d["bearing_back"] = min(D - w, yb1) - max(D - w - s, yb0)

    # --- structure: each tote's 75 lb over two rungs = 37.5 lb at each tote centre on a rung spanning one column
    # (the middle post supports the rungs between columns). Simply supported, conservative.
    span = col
    P = d["tote_capacity"] / 2
    I2, S2 = s ** 4 / 12, s ** 3 / 6
    Fb = SPF["Fb"][0] * SPF["CF_2in"][0] * SPF["CD_storage"][0]
    E = SPF["E"][0]
    d["rung_span"] = span
    d["rung_stress"] = P * span / 4 / S2
    d["rung_defl"] = P * span ** 3 / (48 * E * I2)
    d["rung_point_stress"] = d["point_load"] * span / 4 / S2
    d["rung_Fb_allow"] = Fb

    # --- screws: (name, through board, into board, head xyz, unit dir, length, penetration). Pick from the ladder.
    sd = SCREW["d"][0]
    need = SCREW["min_penetration_d"][0] * sd

    def pick(through, into):
        fit = [ln for ln in SCREW["lengths"][0] if ln - through >= need - 1e-9 and ln - through <= into - d["screw_tip_cover"] + 1e-9]
        return min(fit) if fit else None   # shortest that bites 6D: keeps tips away from the other joints

    joints = {
        "rung->leg/post": (s, w, pick(s, w)),       # through the 2x2 along Y into the leg's 3.5 depth
        "rail->leg/post": (t, t, pick(t, t)),       # through the side rail along X into the leg's 1.5
        "stretcher->leg": (s, t, pick(s, t)),
        "diagonal->leg": (s, t, pick(s, t)),
        "stop->leg/post": (s, w, pick(s, w)),
        "rung->joist": (s, j_y1 - j_y0, pick(s, j_y1 - j_y0)),   # into the joist's end grain
        "brace->rail": (t, t, pick(t, t)),          # side brace face against the top rail's inner face
        "back brace->leg": (t, w, pick(t, w)),      # back brace face against the back leg's front face
        "tie->back brace": (s, L, pick(s, L)),      # down through the top tie into the brace's end grain
        "top->frame": (ply, s, pick(ply, s)),       # plywood into rungs (the shallowest member it lands on)
    }
    d["joints"] = joints
    scr = []

    def add(nm, through, into, head, u, joint):
        ln = joints[joint][2]
        if ln is None:
            return
        scr.append((nm, through, into, head, u, ln, ln - joints[joint][0]))

    uprights = {nm: lo for nm, (_, _, lo) in b.items() if nm.startswith(("LEG-", "POST-"))}
    # rungs, ties: two screws per upright, staggered on the 1.5 x 1.5 patch where the 2x2 crosses it
    for nm, (_, size, lo) in b.items():
        if not nm.startswith(("RUNG-", "TIE-")):
            continue
        front = nm[-2] == "F" if nm.startswith("RUNG") else nm.endswith("F")
        for up, ulo in uprights.items():
            if (up[-2] == "F" if up.startswith("LEG") else up.startswith("POST-F")) != front:
                continue
            if ulo[2] + b[up][1][2] < lo[2] + s - 1e-6:
                continue            # the post stops below this rung
            y_head, u = (lo[1] + s, (0, -1, 0)) if front else (lo[1], (0, 1, 0))
            for k, (fx, fz) in enumerate(((0.3, 0.3), (0.7, 0.7))):
                add(f"{nm}>{up}#{k}", nm, up, (ulo[0] + fx * t, y_head, lo[2] + fz * s), u, "rung->leg/post")
    # side rails and bottom stretchers: two screws per leg along X, staggered in Y and Z (clear of the rung screws,
    # which sit within s of the leg's inner Y face)
    for nm, (_, size, lo) in b.items():
        if not nm.startswith(("RAIL-", "STR-")):
            continue
        left = "-L" in nm
        x_head, u = (lo[0], (1, 0, 0)) if left else (lo[0] + size[0], (-1, 0, 0))
        joint = "rail->leg/post" if nm.startswith("RAIL") else "stretcher->leg"
        for up in (("LEG-FL", "LEG-BL") if left else ("LEG-FR", "LEG-BR")):
            ulo = uprights[up]
            front = up[-2] == "F"
            # rung screws bite the 1 in next to the leg's inner Y face, stop screws the 1 in next to the back face:
            # front legs take these in the outer 1/2 of the depth, back legs on the mid line, staggered in Z
            ys = (0.15, 0.43) if front else (0.5, 0.5)
            zs = (0.3, 0.75) if nm.startswith("RAIL") else (0.33, 0.67)
            for k in range(2):
                add(f"{nm}>{up}#{k}", nm, up, (x_head, ulo[1] + ys[k] * w, lo[2] + zs[k] * size[2]), u, joint)
    # back stops: into the back face of every back leg and post, staggered
    for nm, (_, size, lo) in b.items():
        if not nm.startswith("STOP-"):
            continue
        for up, ulo in uprights.items():
            if not (up in ("LEG-BL", "LEG-BR") or up.startswith("POST-B")):
                continue
            for k, (fx, fz) in enumerate(((0.3, 0.3), (0.7, 0.7))):
                add(f"{nm}>{up}#{k}", nm, up, (ulo[0] + fx * t, lo[1] + s, lo[2] + fz * s), (0, -1, 0), "stop->leg/post")
    # joists: through each work rung into the joist end grain
    for i, px in enumerate(post_x, start=1):
        jn = f"JOIST-{i}"
        _, jsz, jlo = b[jn]
        for rn, y_head, u in ((f"RUNG-F{levels}", jlo[1] - s, (0, 1, 0)), (f"RUNG-B{levels}", jlo[1] + jsz[1] + s, (0, -1, 0))):
            for k, fx in enumerate((0.5,)):
                add(f"{rn}>{jn}#{k}", rn, jn, (jlo[0] + fx * t, y_head, jlo[2] + t / 2), u, "rung->joist")
    # diagonals: two screws per end, along X into the leg's outer face, inside the plumb end's footprint on the leg
    for side in ("L", "R"):
        nm = f"DIAG-{side}"
        _, _, x0, th, poly = pr[nm]
        left = side == "L"
        x_head, u = (x0, (1, 0, 0)) if left else (x0 + th, (-1, 0, 0))
        legs = ("LEG-FL", "LEG-BL") if left else ("LEG-FR", "LEG-BR")
        slope = (z_hi - hv - z_lo) / D    # both edges of the strip rise at this slope
        # same bands as the rail screws: outer half of the front leg, mid line of the back leg (stop screws behind)
        for up, pts in ((legs[0], ((0.15 * w, 0.0), (0.43 * w, 0.0))), (legs[1], ((D - 0.5 * w, -0.25), (D - 0.5 * w, 0.25)))):
            for k, (y, dz) in enumerate(pts):
                zc = z_lo + slope * y + hv / 2 + dz * hv
                add(f"{nm}>{up}#{k}", nm, up, (x_head, y, zc), u, "diagonal->leg")
    # side braces: two screws through the brace into the top rail's inner face, in the band where they overlap
    for side, rail in (("L", "RAIL-L-TOP"), ("R", "RAIL-R-TOP")):
        nm = f"BRACE-S{side}"
        _, _, x0, th, poly = pr[nm]
        x_head, u = (x0 + th, (-1, 0, 0)) if side == "L" else (x0, (1, 0, 0))
        (p1, p2, p3, p4) = poly
        zc = H - w / 2
        for k, f in enumerate((0.35, 0.65)):
            # along the brace at the rail's mid-height: between the two long/short edges at that z
            y_in = p2[0] - (H - zc)          # short edge (45 deg) at height zc
            y_out = p3[0] - (H - zc)         # long edge at height zc
            add(f"{nm}>{rail}#{k}", nm, rail, (x_head, y_in + f * (y_out - y_in), zc), u, "brace->rail")
    # back braces: through the brace into the back leg's front face, and down through the top tie into its end
    for side in ("L", "R"):
        nm = f"BRACE-B{side}"
        _, _, y0, th, poly = pr[nm]
        leg = f"LEG-B{side}"
        lx = uprights[leg][0]
        p1, p2, p3, p4 = poly
        for k, f in enumerate((0.35, 0.65)):
            z = p4[1] + f * (p1[1] - p4[1])  # along the plumb end, which lies on the leg
            add(f"{nm}>{leg}#{k}", nm, leg, (lx + t / 2, y0, z), (0, 1, 0), "back brace->leg")
        xm = (p2[0] + p3[0]) / 2
        add(f"TIE-B>{nm}", "TIE-B", nm, (xm, y0 + th / 2, H), (0, 0, -1), "tie->back brace")
    d["screws"] = scr
    # the plywood top: rows along each work rung and side rail, at <= top_screw_pitch; counted, not clash-checked
    n_along = lambda span_: int(math.ceil(span_ / d["top_screw_pitch"])) + 1
    d["top_screws"] = 2 * n_along(W) + 2 * n_along(D) + (cols - 1) * n_along(j_y1 - j_y0)
    # side brace lower ends: toe-screwed into the back face of the front leg, two each; counted, not clash-checked
    d["toe_screws"] = 2 * 2

    # --- cut plan against the inventory
    def plen(nm):
        if nm in b:
            return max(b[nm][1])
        return d["diag_len"] if nm.startswith("DIAG") else None
    plan = {}
    plan["legs (on hand, 72 in, no cut)"] = [n for n in b if n.startswith("LEG-")]
    plan["31 in 2x4s, trimmed"] = [n for n in b if n.startswith("RAIL-")]
    plan["45 deg braces (on hand, no cut)"] = [n for n in pr if n.startswith("BRACE-")]
    two_by_two = [(n, plen(n)) for n in list(b) + list(pr) if (n in b and b[n][0] == "x2x2") or (n in pr and pr[n][0] == "x2x2")]
    d["plan_2x2"] = cut_plan(two_by_two, INVENTORY["x2x2"][1], 0.0, d["kerf"])
    bought_2x4 = [(n, plen(n)) for n in b if n.startswith("POST-")]
    d["plan_bought_2x4"] = cut_plan(bought_2x4, STORE_2X4[0], 0.0, d["kerf"])
    d["plan_on_hand"] = plan
    d["rail_trim"] = INVENTORY["x2x4_31"][1] - D

    # --- shopping list
    sc_count = {}
    for _, _, _, _, _, ln, _ in scr:
        sc_count[ln] = sc_count.get(ln, 0) + 1
    ln_top = joints["top->frame"][2]
    sc_count[ln_top] = sc_count.get(ln_top, 0) + d["top_screws"]
    toe = SCREW["toe_len"][0]
    sc_count[toe] = sc_count.get(toe, 0) + d["toe_screws"]
    d["screw_counts"] = dict(sorted(sc_count.items()))
    d["shopping"] = [
        (f"2x4 x 8 ft", len(d["plan_bought_2x4"]), "middle posts: " + ", ".join(f"{n} {tape(l)}" for st in d["plan_bought_2x4"] for n, l in st)),
        ("23/32 in plywood, 4 x 4 ft panel", 1, f"work top {tape(W + 2 * t)} x {tape(D)}, notched {tape(t)} x {tape(w)} at the 4 legs"),
    ] + [(f"#8 wood screws {tape(ln)}", n, "") for ln, n in d["screw_counts"].items()] + [
        ("HDX 27 gal Tough Storage Tote", cols * levels, "if not already on hand"),
        ("wood glue (optional)", 1, "every face joint"),
    ]
    d["spare_2x2"] = INVENTORY["x2x2"][0] - len(d["plan_2x2"])

    # --- exploded view (display only, FreeCAD): one move per set of parts; each part's offset is the sum of its moves.
    # Posts, rungs, ties and joists stay put as the reference.
    side = lambda sd: [n for n in list(b) + list(pr) if n in (f"LEG-F{sd}", f"LEG-B{sd}", f"STR-{sd}", f"DIAG-{sd}", f"BRACE-S{sd}")
                       or n.startswith(f"RAIL-{sd}-")]
    moves = [
        ("top up", ["TOP"], (0.0, 0.0, d["explode_top_lift"] * w)),
        ("left side out", side("L"), (-d["explode_side_out"] * w, 0.0, 0.0)),
        ("right side out", side("R"), (d["explode_side_out"] * w, 0.0, 0.0)),
        ("back stops out", [n for n in b if n.startswith("STOP-")], (0.0, d["explode_back_out"] * w, 0.0)),
        ("back braces out", [n for n in pr if n.startswith("BRACE-B")], (0.0, d["explode_back_out"] * w, 0.0)),
    ]
    d["explode_moves"] = moves
    d["explode_offset"] = {nm: tuple(sum(v[a] for _, parts, v in moves if nm in parts) for a in range(3))
                           for nm in list(b) + list(pr) + ["TOP"]}
    d["wood_volume"] = sum(math.prod(sz) for _, sz, _ in b.values())
    return d


def _brace_checks(d: dict, L: float) -> list[str]:
    """The braces at long point L: inside their gap, clear of the other brace, the rungs, the top tie."""
    t, w, s, D, W, H = d["t"], d["w"], d["s"], d["D"], d["W"], d["H"]
    bad = []
    sb = brace_polygon((w, H), +1, -1, L, w)
    reach_y = max(p[0] for p in sb)
    if reach_y > D - w:
        bad.append(f"side brace L={L / IN:.1f} in reaches y {reach_y / IN:.2f} in, past the back leg's front face")
    low = min(p[1] for p in sb)
    if low < d["work_surface"] + 12 * IN:
        bad.append(f"side brace L={L / IN:.1f} in hangs to {low / IN:.2f} in, less than 12 in above the work top")
    bb = brace_polygon((0.0, H - s), +1, -1, L, w)
    reach_x = max(p[0] for p in bb)
    if 2 * reach_x > W:
        bad.append(f"back braces L={L / IN:.1f} in meet in the middle: each reaches {reach_x / IN:.2f} of {W / IN:.2f} in")
    if min(p[1] for p in bb) < d["work_surface"] + 12 * IN:
        bad.append(f"back brace L={L / IN:.1f} in hangs within 12 in of the work top")
    return bad


def validate(**overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    d = derive(**overrides)
    mm = lambda x: f"{x:.1f} mm ({x / IN:.3f} in)"
    for table in (DESIGN, TOTE, SCREW, SPF, MappingProxyType(dict(ply=PLY_T, store_2x4=STORE_2X4, store_ply=STORE_PLY))):
        for k, v in table.items():
            assert len(v) == 3 and v[1] and v[2], f"{k}: every number needs (value, TAG, source)"
    assert STATUS in ("concept", "passes", "printed", "parked")
    t, w, s, D, W = d["t"], d["w"], d["s"], d["D"], d["W"]
    # inventory: what the design uses exists
    assert d["H"] == INVENTORY["leg72"][1], "legs are the 72 in 2x4s on hand"
    assert D <= INVENTORY["x2x4_31"][1], f"side rails {mm(D)} longer than the 31 in 2x4s on hand"
    assert len([n for n in d["boards"] if n.startswith("RAIL-")]) <= INVENTORY["x2x4_31"][0]
    assert len([n for n in d["prisms"] if n.startswith("BRACE-")]) <= INVENTORY["brace45"][0]
    assert len(d["plan_2x2"]) <= INVENTORY["x2x2"][0], f"2x2 cut plan needs {len(d['plan_2x2'])} sticks, {INVENTORY['x2x2'][0]} on hand"
    lo, hi = DESIGN["brace_range"][0]
    assert lo <= d["brace_long_point"] <= hi
    # fit: the tote passes between leg and post, bears on both rungs at its stop, clears the rung above
    assert d["col"] >= d["tote_W"] + 2 * d["clear_side"] - 1e-9
    assert D >= d["tote_L"], f"tote {mm(d['tote_L'])} sticks out of a {mm(D)} deep bench"
    assert d["bearing_front"] >= d["bearing_min"] - 1e-9, f"tote bottom on the front rung {mm(d['bearing_front'])}"
    assert d["bearing_back"] >= d["bearing_min"] - 1e-9, f"tote bottom on the back rung {mm(d['bearing_back'])}"
    for i, g in enumerate(d["lid_gap"], start=1):
        assert g >= d["clear_lid"] - 1e-9, f"level {i} lid to the rung above {mm(g)}"
    lo_h, hi_h = d["work_height_range"]
    assert lo_h <= d["work_surface"] <= hi_h, f"work surface {mm(d['work_surface'])} outside the standing range"
    assert d["work_top"] < d["H"] - w - 12 * IN, "no room above the work top"
    # the top fits the panel
    pw, pd = STORE_PLY[0]
    tw, td, _ = d["top"]["size"]
    assert (tw <= pw and td <= pd) or (tw <= pd and td <= pw), f"top {mm(tw)} x {mm(td)} does not fit the panel"
    # structure: a full tote's share on a rung, and a point load on the work rung
    assert d["rung_stress"] <= d["rung_Fb_allow"], f"rung stress {d['rung_stress'] / PSI:.0f} psi > {d['rung_Fb_allow'] / PSI:.0f}"
    assert d["rung_defl"] <= d["rung_span"] / d["defl_limit"], f"rung sags {mm(d['rung_defl'])}"
    assert d["rung_point_stress"] <= d["rung_Fb_allow"], f"work rung under {d['point_load'] / LBF:.0f} lb: {d['rung_point_stress'] / PSI:.0f} psi"
    # braces at both ends of the range on hand
    for L in DESIGN["brace_range"][0]:
        bad = _brace_checks(d, L)
        assert not bad, "; ".join(bad)
    # screws: every joint has a stocked length; no two shanks in a shared board come closer than screw_gap_min
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
        f"Tote rack workbench: {f(d['W'] + 2 * d['t'])} W (legs {f(d['W'])}) x {f(d['D'])} D x {f(d['H'])} H; "
        f"work surface {f(d['work_surface'])}; {d['cols'] * d['levels']} totes ({d['cols']} cols x {d['levels']} levels)",
        f"  column {f(d['col'])} between leg and post for a {d['tote_W'] / IN:.2f} in tote; "
        f"rung rows (bottom, from the floor) " + ", ".join(f(z) for z in d["rows"]) + f"; top tie {f(d['H'] - d['s'])}",
        f"  tote bottom on each rung: front {d['bearing_front'] / IN:.2f}, back {d['bearing_back'] / IN:.2f} in "
        f"(min {d['bearing_min'] / IN:g}); lid to rung above " + ", ".join(f"{g / IN:.2f}" for g in d["lid_gap"]) + " in",
        f"  back stops (bottom) " + ", ".join(f(z) for z in d["stop_z"]),
        f"  2x2 rung, {f(d['rung_span'])} span: full totes {d['rung_stress'] / PSI:.0f} psi, sag {d['rung_defl'] / IN:.3f} in; "
        f"{d['point_load'] / LBF:.0f} lb point {d['rung_point_stress'] / PSI:.0f} psi; allowed {d['rung_Fb_allow'] / PSI:.0f} psi",
        "",
        "ON HAND",
        f"  4 x 72\" 2x4      legs, as cut",
        f"  4 x 31\" 2x4      side rails: trim each to {f(d['D'])} (take {f(d['rail_trim'])} off)",
        f"  4 x 45 deg 2x4   knee braces as they are: 2 at the top of the sides, 2 at the top of the back",
        f"  {len(d['plan_2x2'])} of 8 x 2x2  ({d['spare_2x2']} spare):",
    ]
    for i, st in enumerate(d["plan_2x2"], start=1):
        used = sum(l + d["kerf"] for _, l in st)
        L.append(f"      stick {i}: " + " + ".join(f"{n} {f(l)}" for n, l in st) + f"   offcut {f(INVENTORY['x2x2'][1] - used)}")
    L.append("  scraps           not needed")
    L += ["", "TO BUY"]
    for item, n, note in d["shopping"]:
        L.append(f"  {n:>3} x {item}" + (f"   ({note})" if note else ""))
    L += ["", "SCREWS BY JOINT (#8, 6D bite, tip >= 1/4 in inside)"]
    for jn, (through, into, ln) in d["joints"].items():
        L.append(f"  {jn:18s} {f(ln) if ln else 'NONE':>7}  through {f(through)} into {f(into)}")
    return "\n".join(L)


if __name__ == "__main__":
    d = validate()
    print(report(d))
    print("\nok")
