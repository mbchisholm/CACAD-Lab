"""Nutrient controller concepts A_lid, B_wall, C_split: printed shells, the
bought parts as envelopes, and the tote as context, all in the tote frame
(params docstring). Massing models for choosing a direction: no cradles,
grommets, fasteners or finish features yet. Every number from params.derive.

    .venv/bin/python projects/nutrient_controller/concepts.py [--show]     # builds params.ACTIVE_CONCEPTS

Checks per concept: every bought-part envelope clear of every printed part and
of each other (pairwise, F7), every dry part inside its dry cavity, every
printed part on the bed, the lowest opening above the waterline. Writes
out/<concept>.3mf (one mesh per printed part, per bought part, and the tote)
and out/<concept>_assembly.step for rendering.
"""
from __future__ import annotations

import math

from build123d import (Axis, Box, Compound, Cylinder, Location, Part, Plane, Polygon, Pos, Rectangle, Rot, extrude,
                       fillet, loft)

from cacad import export, export_3mf, interference_volume, is_inside, maybe_show
from projects.nutrient_controller.params import ACTIVE_CONCEPTS, derive, validate

def _box(x, y, z, at=(0, 0, 0), rot=0.0, base=True) -> Part:
    """Box with its base (or centre) at `at`, turned `rot` deg about Z."""
    b = Box(x, y, z)
    return Pos(*at) * Rot(0, 0, rot) * (Pos(0, 0, z / 2) * b if base else b)


def _cyl(d, l, at, axis="Z") -> Part:
    c = Cylinder(d / 2, l)
    rot = {"Z": Rot(0, 0, 0), "X": Rot(0, 90, 0), "Y": Rot(90, 0, 0)}[axis]
    return Pos(*at) * rot * c


def _rounded(part: Part, r: float) -> Part:
    try:
        return fillet(part.edges().filter_by(Axis.Z), r)
    except Exception:          # cosmetic: a concept is fine without it
        return part


def _wedge(W, D, z_front, z_back, z0) -> Part:
    """Prism along X: floor at z0, top sloping from z_front (y = -D/2) to z_back (y = +D/2)."""
    prof = Plane.YZ * Polygon((-D / 2, z0), (D / 2, z0), (D / 2, z_back), (-D / 2, z_front), align=None)
    return extrude(prof, amount=W / 2, both=True)


class Slope:
    """The sloped top of a wedge box: positions by (x, s), s measured up the slope from the front edge."""

    def __init__(self, cx, cy, z_front, D, theta_deg):
        self.cx, self.cy, self.zf, self.D, self.t = cx, cy, z_front, D, math.radians(theta_deg)
        self.deg = theta_deg

    def loc(self, x, s, inset=0.0) -> Location:
        y = self.cy - self.D / 2 + s * math.cos(self.t)
        z = self.zf + s * math.sin(self.t)
        n = (0.0, -math.sin(self.t), math.cos(self.t))
        return Location((self.cx + x - n[0] * inset, y - n[1] * inset, z - n[2] * inset), (self.deg, 0, 0))


def _wedge_box(d, W, D, hf, hb, cx, cy, z0):
    """Outer and inner (cavity) solids of a closed wedge box and its slope frame."""
    w, fl = d["wall"], d["floor"]
    th = math.atan2(hb - hf, D)
    outer = _rounded(Pos(cx, cy, 0) * _wedge(W, D, z0 + hf, z0 + hb, z0), d["corner_r"])
    dz = w / math.cos(th)
    zi_f = z0 + hf + w * math.tan(th) - dz
    zi_b = z0 + hf + (D - w) * math.tan(th) - dz
    inner = Pos(cx, cy, 0) * _wedge(W - 2 * w, D - 2 * w, zi_f, zi_b, z0 + fl)
    return outer, inner, Slope(cx, cy, z0 + hf, D, math.degrees(th))


def _ui(d, slope: Slope, ui, parts) -> tuple[list, dict]:
    """Cutters through the slope and the UI envelopes under it."""
    P, w = d["parts"], d["wall"]
    cuts, hw = [], {}
    ox, os_ = ui["oled"]
    win = P["oled"]["window"]
    cuts.append(slope.loc(ox, os_) * Box(win[0] - 2 * d["window_lip"], win[1] - 2 * d["window_lip"], 4 * w))
    sx, sy, sz = P["oled"]["size"]
    hw["oled"] = slope.loc(ox, os_, w + sz / 2) * Box(sx, sy, sz)
    bx, by, bz = P["button"]["size"]
    for i, (x, s) in enumerate(ui["buttons"]):
        cuts.append(slope.loc(x, s) * Cylinder(P["button"]["hole_d"] / 2, 4 * w))
        hw[f"button_{i + 1}"] = slope.loc(x, s, w + bz / 2) * Box(bx, by, bz)
    lx, ls = ui["led"]
    cuts.append(slope.loc(lx, ls) * Cylinder(P["led"]["d"] / 2 + 0.1, 4 * w))
    hw["led"] = slope.loc(lx, ls, w + P["led"]["l"] / 2) * Cylinder(P["led"]["flange_d"] / 2, P["led"]["l"])
    return cuts, hw


def _floor_parts(d, layout, cx, cy, z_floor) -> dict:
    P = d["parts"]
    hw = {}
    for name, (x, y, rot) in layout.items():
        sx, sy, sz = P[name]["size"]
        hw[name] = _box(sx, sy, sz, (cx + x, cy + y, z_floor + d["standoff"]), rot)
    return hw


def _pump_on_wall(d, wall_x, y, z_axis, outward=+1):
    """Motor inside the dry box through an X wall, head outside, drip canopy over the head (open below)."""
    P, w, air = d["parts"], d["wall"], d["part_air"]
    m = P["pump_motor"]
    hx, hy, hz = P["pump_head"]["size"]         # head: hx across (Y), hy out from the wall (X), hz tall
    motor = _cyl(m["d"], m["l"], (wall_x - outward * m["l"] / 2, y, z_axis), "X")
    head = _box(hy, hx, hz, (wall_x + outward * hy / 2, y, z_axis), base=False)
    hole = _cyl(m["d"] + 1.0, 4 * w, (wall_x - outward * w / 2, y, z_axis), "X")
    cw, ch = hx + 2 * (air + w), hz / 2 + air + w            # canopy: roof + two cheeks, open below and outward
    reach = hy + air
    roof_z = z_axis + hz / 2 + air
    canopy = _box(reach, cw, w, (wall_x + outward * reach / 2, y, roof_z))
    for sgn in (-1, 1):
        canopy += _box(reach, w, ch, (wall_x + outward * reach / 2, y + sgn * (cw - w) / 2, roof_z + w - ch))
    return dict(pump_motor=motor, pump_head=head), hole, canopy


def _tote(d, lid_cuts=()) -> dict:
    t, tw = d["tote"], d["tote_wall"]
    L, W = t["top"]
    lip = d["tote_lip"]
    top = (L - 2 * lip, W - 2 * lip)
    bot = (t["bottom_in"][0] + 2 * tw, t["bottom_in"][1] + 2 * tw)
    H = t["height"]
    outer = loft([Plane.XY.offset(-H) * Rectangle(*bot), Plane.XY * Rectangle(*top)])
    inner = loft([Plane.XY.offset(-H + tw) * Rectangle(bot[0] - 2 * tw, bot[1] - 2 * tw),
                  Plane.XY.offset(0.01) * Rectangle(top[0] - 2 * tw, top[1] - 2 * tw)])
    rim = Pos(0, 0, -2.5) * Box(L, W, 5) - Pos(0, 0, -2.5) * Box(top[0] - 2 * tw, top[1] - 2 * tw, 5)
    body = outer - inner + rim
    lid = Pos(0, 0, d["lid_t"] / 2) * Box(L, W, d["lid_t"])
    for c in lid_cuts:
        lid -= c
    wh = t["waterline_z"] - (t["floor_z"] + tw)
    water = Pos(0, 0, t["floor_z"] + tw + wh / 2) * Box(bot[0] - 2 * tw - 40, bot[1] - 2 * tw - 40, wh)
    return dict(tote=body, lid=lid, water=water)


def _probes(d, exits_xy, z_from) -> dict:
    """Probe bodies hanging `immersion` below the waterline, under their cable exits, plus the cable runs."""
    P, t = d["parts"], d["tote"]
    tip = t["waterline_z"] - d["immersion"]
    hw = {}
    for (x, y), name in zip(exits_xy, ("tds_probe", "ds18b20")):
        p = P[name]
        hw[name] = _cyl(p["d"], p["l"], (x, y, tip + p["l"] / 2))
        run = z_from - (tip + p["l"])
        hw[f"{name}_cable"] = _cyl(p["cable_d"], run, (x, y, tip + p["l"] + run / 2))
    return hw


def build_A(d) -> dict:
    bx, by = d["box"]
    cx, cy = d["at"]
    z0, w = d["box_z0"], d["wall"]
    outer, inner, slope = _wedge_box(d, bx, by, d["h_front"], d["h_back"], cx, cy, z0)
    zf = z0 + d["floor"]
    cuts, hw = _ui(d, slope, d["ui"], d["parts"])
    hw.update(_floor_parts(d, d["floor_parts"], cx, cy, zf))
    pump, motor_hole, canopy = _pump_on_wall(d, cx + bx / 2, cy + d["pump"][1], zf + d["pump"][2])
    hw.update(pump)
    P = d["parts"]
    cuts.append(motor_hole)
    # back wall: USB-C slot at the XIAO and the DC jack
    xiao_top = zf + d["standoff"] + P["xiao"]["size"][2]
    cuts.append(_box(12.0, 4 * w, 7.0, (cx + d["usb"][1], cy + by / 2, xiao_top - 2.0), base=False))   # PLACEHOLDER plug
    jx, jz = d["jack"][1], zf + d["jack"][2]
    cuts.append(_cyl(P["dc_jack"]["hole_d"], 4 * w, (cx + jx, cy + by / 2, jz), "Y"))
    hw["dc_jack"] = _cyl(P["dc_jack"]["d"], P["dc_jack"]["l"], (cx + jx, cy + by / 2 - w - P["dc_jack"]["l"] / 2, jz), "Y")
    holes = [(cx + x, cy + y) for x, y in d["cable_holes"]]
    for (x, y), name in zip(holes, ("tds_probe", "ds18b20")):
        cuts.append(_cyl(P[name]["cable_d"] + d["cable_hole_extra"], 4 * d["floor"], (x, y, z0)))
    shell = outer - inner
    for c in cuts:
        shell -= c
    split = Pos(cx, cy, z0 + d["split_z"] + 200) * Box(bx * 3, by * 3, 400)
    cover = shell & split
    base = shell - split
    # flange skirt with lid screws, and the canopy on the base
    f = d["flange"]
    skirt = _rounded(_box(bx + 2 * f, by + 2 * f, 3.0, (cx, cy, z0)), d["corner_r"] + f)
    screw_pts = [(cx + sx * (bx / 2 + f / 2), cy + sy * (by / 2 - 10)) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in screw_pts:
        skirt -= _cyl(d["lid_screw_d"], 10, (x, y, z0))
    base = base + skirt + canopy
    for c in cuts:
        base -= c
    # bottle holster on the lid
    B = P["stock_bottle"]
    ring_od = B["d"] + 2 * (d["part_air"] + w)
    holster = _cyl(ring_od, 30, (*d["bottle_at"], z0 + 15)) - _cyl(B["d"] + 2 * d["part_air"], 31, (*d["bottle_at"], z0 + 15))
    hw["stock_bottle"] = _cyl(B["d"], B["h"], (*d["bottle_at"], z0 + B["h"] / 2))
    hw.update(_probes(d, holes, z0))
    tube_x, tube_y = d["exits"]["tube"][0], cy + d["pump"][1]
    pump_bottom = zf + d["pump"][2] - P["pump_head"]["size"][2] / 2
    tube_l = pump_bottom - (d["tote"]["waterline_z"] + 30)
    hw["dose_tube"] = _cyl(P["tube_od"]["d"], tube_l, (tube_x, tube_y, pump_bottom - tube_l / 2))
    lid_cuts = [_cyl(P[n]["cable_d"] + d["cable_hole_extra"], 20, (x, y, 0)) for (x, y), n in zip(holes, ("tds_probe", "ds18b20"))]
    lid_cuts.append(_cyl(P["tube_od"]["d"] + d["cable_hole_extra"], 20, (tube_x, tube_y, 0)))
    lid_cuts += [_cyl(d["lid_screw_d"], 20, (x, y, 0)) for x, y in screw_pts]
    return dict(printed=dict(base=base, cover=cover, holster=holster), hardware=hw, cavity=inner,
                context=_tote(d, lid_cuts), dry=("xiao", "ads1115", "tds_board", "relay", "buck", "oled"))


def build_B(d) -> dict:
    wy, dx, hz = d["box"]
    w, P = d["wall"], d["parts"]
    tan = math.tan(math.radians(d["tote_draft_deg"]))
    x_wall = lambda z: d["tote_end_x_top"] + z * tan                     # outer face of the drafted end wall
    z_top = d["top_z"]
    z_s1, z_s2 = d["spacer_z"]
    x_b = x_wall(z_s1) + 3.0                                             # body back: 3 mm spacer at its top
    cx = x_b + dx / 2
    zc = z_top - hz / 2
    outer = _rounded(_box(dx, wy, hz, (cx, 0, zc), base=False), d["corner_r"])
    inner = _box(dx - w + 1, wy - 2 * w, hz - 2 * w, (cx + w / 2 + 0.5, 0, zc), base=False)   # open to the front
    cavity = _box(dx - 2 * w, wy - 2 * w, hz - 2 * w, (cx, 0, zc), base=False)
    body = outer - inner
    front = _rounded(_box(w, wy, hz, (x_b + dx + w / 2, 0, zc), base=False), d["corner_r"])
    # wedge spacer between the drafted wall and the vertical back
    prof = Plane.XZ * Polygon((x_wall(z_s1), z_s1), (x_b, z_s1), (x_b, z_s2), (x_wall(z_s2), z_s2), align=None)
    spacer = extrude(prof, amount=50.0, both=True)
    hw, cuts_body, cuts_front = {}, [], []
    # boards on the back plate, standing off it in +X
    for name, (y, zr) in d["back_parts"].items():
        sx, sy, sz = P[name]["size"]
        hw[name] = Pos(x_b + w + d["standoff"] + sz / 2, y, z_top + zr) * Box(sz, sx, sy)
    # UI through the front plate
    xf = x_b + dx
    oy, oz = d["ui"]["oled"]
    win = P["oled"]["window"]
    cuts_front.append(_box(4 * w, win[0] - 2 * d["window_lip"], win[1] - 2 * d["window_lip"], (xf, oy, z_top + oz), base=False))
    sx, sy, sz = P["oled"]["size"]
    hw["oled"] = _box(sz, sx, sy, (xf - sz / 2, oy, z_top + oz), base=False)
    bx, by, bz = P["button"]["size"]
    for i, (y, zr) in enumerate(d["ui"]["buttons"]):
        cuts_front.append(_cyl(P["button"]["hole_d"], 4 * w, (xf, y, z_top + zr), "X"))
        hw[f"button_{i + 1}"] = _box(bz, bx, by, (xf - bz / 2, y, z_top + zr), base=False)
    ly, lz = d["ui"]["led"]
    cuts_front.append(_cyl(P["led"]["d"] + 0.2, 4 * w, (xf, ly, z_top + lz), "X"))
    hw["led"] = _cyl(P["led"]["flange_d"], P["led"]["l"], (xf - P["led"]["l"] / 2, ly, z_top + lz), "X")
    # bottom wall: USB-C and DC jack
    zb = z_top - hz
    cuts_body.append(_box(7.0, 12.0, 4 * w, (x_b + w + d["standoff"] + 2.5, d["usb"][1], zb), base=False))
    cuts_body.append(_cyl(P["dc_jack"]["hole_d"], 4 * w, (cx, d["jack"][1], zb)))
    hw["dc_jack"] = _cyl(P["dc_jack"]["d"], P["dc_jack"]["l"], (cx, d["jack"][1], zb + w + P["dc_jack"]["l"] / 2))
    # pump on the -Y side wall: motor in, head out, canopy with a tube hole
    m, (hx, hy, hzz) = P["pump_motor"], P["pump_head"]["size"]
    zp = z_top + d["pump"][1]
    yw = -wy / 2
    hw["pump_motor"] = _cyl(m["d"], m["l"], (cx, yw + m["l"] / 2, zp), "Y")
    hw["pump_head"] = _box(hx, hy, hzz, (cx, yw - hy / 2, zp), base=False)
    cuts_body.append(_cyl(m["d"] + 1.0, 4 * w, (cx, yw, zp), "Y"))
    # one grommet hole through the tote wall, a tunnel through spacer and back; two bolts
    hole_z = d["wall_hole_z"]
    tunnel = _cyl(d["wall_hole_d"], 80, (x_b, 0, hole_z), "X")
    bolts = [(sy * d["bolt_dy"] / 2, z_top + d["bolt_z"]) for sy in (-1, 1)]
    bolt_cuts = [_cyl(d["wall_bolt_d"], 80, (x_b, y, z), "X") for y, z in bolts]
    for y, z in bolts:
        xw = x_wall(z)
        L = (x_b + w + 6) - (xw - d["tote_wall"])
        hw[f"bolt_{'n' if y < 0 else 'p'}"] = _cyl(5.0, L, ((x_b + w + 6 + xw - d["tote_wall"]) / 2, y, z), "X")
    body -= tunnel
    spacer -= tunnel
    for c in bolt_cuts:
        body -= c
        spacer -= c
    for c in cuts_body:
        body -= c
    for c in cuts_front:
        front -= c
    # bottle holster under the box, on the pump side
    B = P["stock_bottle"]
    ring_od = B["d"] + 2 * (d["part_air"] + w)
    by0 = -wy / 2 + ring_od / 2
    bottle_top = zb - 10.0                                   # DESIGN: room for the suction line over the cap
    ring_z = bottle_top - B["h"] + 45.0
    holster = _cyl(ring_od, 30, (cx, by0, ring_z)) - _cyl(B["d"] + 2 * d["part_air"], 31, (cx, by0, ring_z))
    for sgn in (-1, 1):
        sy = by0 + sgn * (ring_od / 2 - w)
        holster += _box(10.0, 2 * w, zb - (ring_z + 15), (cx, sy, ring_z + 15))
    hw["stock_bottle"] = _cyl(B["d"], B["h"], (cx, by0, bottle_top - B["h"] / 2))
    # tube: head top -> up -> into the tote through its own small hole
    ty, tz = d["tube_hole"]
    tx = cx - hx / 2 + 6
    head_top = zp + hzz / 2
    hw["dose_tube_up"] = _cyl(P["tube_od"]["d"], tz - head_top, (tx, ty + 8, (tz + head_top) / 2))
    hw["dose_tube_in"] = _cyl(P["tube_od"]["d"], tx - x_wall(tz) + 30, ((tx + x_wall(tz) - 30) / 2, ty + 8, tz), "X")
    # probes hang inside the wall hole
    xin = x_wall(hole_z) - d["tote_wall"] - 30
    hw.update(_probes(d, [(xin, -8), (xin, 8)], hole_z))
    # the tote-wall holes as markers: the cut tote is a valid solid but meshes invalid for 3MF (context only)
    tote = _tote(d)
    marks = [_cyl(d["wall_hole_d"], 12, (x_wall(hole_z), 0, hole_z), "X"),
             _cyl(P["tube_od"]["d"] + 2, 12, (x_wall(tz), ty + 8, tz), "X")]
    marks += [_cyl(d["wall_bolt_d"], 12, (x_wall(z), y, z), "X") for y, z in bolts]
    tote["wall_holes"] = Compound(marks)
    return dict(printed=dict(body=body, front=front, spacer=spacer, holster=holster), hardware=hw, cavity=cavity,
                context=tote, dry=("xiao", "ads1115", "tds_board", "relay", "buck"))


def build_C(d) -> dict:
    P, w = d["parts"], d["wall"]
    hw, printed = {}, {}
    # --- UI head on a 2020 post ---
    hx, hy = d["head"]
    cx, cy, z0 = d["head_at"]
    outer, inner, slope = _wedge_box(d, hx, hy, d["head_h_front"], d["head_h_back"], cx, cy, z0)
    cuts, ui = _ui(d, slope, d["head_ui"], P)
    hw.update({f"head_{k}": v for k, v in ui.items()})
    zf = z0 + d["floor"]
    hw.update({f"head_{k}": v for k, v in _floor_parts(d, d["head_floor_parts"], cx, cy, zf).items()})
    xiao_top = zf + d["standoff"] + P["xiao"]["size"][2]
    cuts.append(_box(4 * w, 12.0, 7.0, (cx + hx / 2, cy + d["head_usb"][1], xiao_top - 2.0), base=False))
    cuts.append(_cyl(8.0, 4 * w, (cx + d["head_gland"][1], cy + hy / 2, zf + 8), "Y"))
    shell = outer - inner
    for c in cuts:
        shell -= c
    split_z = zf + d["standoff"] + 6
    upper = Pos(cx, cy, split_z + 100) * Box(hx * 2, hy * 2, 200)
    printed["head_cover"], printed["head_base"] = shell & upper, shell - upper
    r = d["rail"]
    clamp = _box(r + 2 * 4, 16, 40, (cx - hx / 4, cy + hy / 2 + 8, z0 - 10)) - _box(r + 0.8, r + 0.8, 60, (cx - hx / 4, cy + hy / 2 + 8 + 2 + r / 2, z0 - 20))
    printed["head_base"] = printed["head_base"] + clamp
    post_x, post_y = cx - hx / 4, cy + hy / 2 + 8 + 2 + r / 2
    post_bot = d["tote"]["floor_z"] - 23.0
    hw["rail_2020"] = _box(r, r, z0 + 25 - post_bot, (post_x, post_y, post_bot))
    # --- wet pod on the lid ---
    px, py, pz = d["pod"]
    qx, qy = d["pod_at"]
    q0 = d["pod_z0"]
    pod_out = _rounded(_box(px, py, pz, (qx, qy, q0)), d["corner_r"])
    pod_in = _box(px - 2 * w, py - 2 * w, pz - 2 * w, (qx, qy, q0 + w))
    pod = pod_out - pod_in
    qf = q0 + w
    hw.update({f"pod_{k}": v for k, v in _floor_parts(d, d["pod_floor_parts"], qx, qy, qf).items()})
    pump, motor_hole, canopy = _pump_on_wall(d, qx + px / 2, qy + d["pump"][1], qf + d["pump"][2])
    hw.update(pump)
    pod -= motor_hole
    pod += canopy
    holes = [(qx + x, qy + y) for x, y in d["pod_cable_holes"]]
    for (x, y), n in zip(holes, ("tds_probe", "ds18b20")):
        pod -= _cyl(P[n]["cable_d"] + d["cable_hole_extra"], 4 * w, (x, y, q0))
    jy, jz = d["pod_jack"][1], qf + d["pod_jack"][2]
    pod -= _cyl(P["dc_jack"]["hole_d"], 4 * w, (qx - px / 2, qy + jy, jz), "X")
    hw["pod_dc_jack"] = _cyl(P["dc_jack"]["d"], P["dc_jack"]["l"], (qx - px / 2 + w + P["dc_jack"]["l"] / 2, qy + jy, jz), "X")
    gx, gz = d["pod_gland"][1], qf + d["pod_gland"][2]
    pod -= _cyl(10.0, 4 * w, (qx + gx, qy - py / 2, gz), "Y")
    B = P["stock_bottle"]
    ring_od = B["d"] + 2 * (d["part_air"] + w)
    holster = _cyl(ring_od, 30, (*d["bottle_at"], q0 + 15)) - _cyl(B["d"] + 2 * d["part_air"], 31, (*d["bottle_at"], q0 + 15))
    hw["stock_bottle"] = _cyl(B["d"], B["h"], (*d["bottle_at"], q0 + B["h"] / 2))
    printed.update(pod=pod, holster=holster)
    hw.update(_probes(d, holes, q0))
    tube_x, tube_y = d["exits"]["tube"][0], qy + d["pump"][1]
    pump_bottom = qf + d["pump"][2] - P["pump_head"]["size"][2] / 2
    tube_l = pump_bottom - (d["tote"]["waterline_z"] + 30)
    hw["dose_tube"] = _cyl(P["tube_od"]["d"], tube_l, (tube_x, tube_y, pump_bottom - tube_l / 2))
    lid_cuts = [_cyl(P[n]["cable_d"] + d["cable_hole_extra"], 20, (x, y, 0)) for (x, y), n in zip(holes, ("tds_probe", "ds18b20"))]
    lid_cuts.append(_cyl(P["tube_od"]["d"] + d["cable_hole_extra"], 20, (tube_x, tube_y, 0)))
    # the head <-> pod tether, a straight segment for the reach check
    a = (qx + gx, qy - py / 2, gz)
    b = (cx + d["head_gland"][1], cy + hy / 2, zf + 8)
    L = math.dist(a, b)
    mid = tuple((u + v) / 2 for u, v in zip(a, b))
    hw["tether"] = Location(mid) * Location(Plane(origin=(0, 0, 0), z_dir=tuple(v - u for u, v in zip(a, b)))) * Cylinder(3.0, L)
    return dict(printed=printed, hardware=hw, cavity=[inner, pod_in], context=_tote(d, lid_cuts),
                dry=("head_xiao", "head_ads1115", "head_tds_board", "pod_relay", "pod_buck", "head_oled"))


BUILDERS = dict(A_lid=build_A, B_wall=build_B, C_split=build_C)


def check(concept: str, m: dict) -> list[str]:
    """Function checks; returns failures (empty = pass)."""
    d = derive(concept)
    fails = []
    hw, pr = m["hardware"], m["printed"]
    names = list(hw)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if b.startswith(a) or a.startswith(b) or {a.split("_")[0], b.split("_")[0]} == {"pump"}:
                continue                         # a probe and its own cable, motor and head: touching by design
            if {a, b} & {"tether", "rail_2020"} or {a, b} == {"dose_tube_up", "dose_tube_in"}:
                continue
            v = interference_volume(hw[a], hw[b])
            if v > 1e-3:
                fails.append(f"{a} x {b}: {v:.1f} mm3 overlap")
        for pn, p in pr.items():
            if a.startswith("pump_motor") or a in ("tether", "rail_2020") or a.startswith("dose_tube"):
                continue                         # the motor passes its wall hole; the tube passes the canopy
            v = interference_volume(hw[a], p)
            if v > 1e-3:
                fails.append(f"{a} x printed {pn}: {v:.1f} mm3 overlap")
    cavities = m["cavity"] if isinstance(m["cavity"], list) else [m["cavity"]]
    for n in m["dry"]:
        c = hw[n].center()
        if not any(is_inside(cv, c) for cv in cavities):
            fails.append(f"{n} is not inside a dry cavity")
    for pn, p in pr.items():
        bb = p.bounding_box()
        size = sorted((bb.size.X, bb.size.Y, bb.size.Z))
        if any(s > b for s, b in zip(size, sorted(d["bed"]))):
            fails.append(f"printed {pn} {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} exceeds the bed")
    return fails


def report(concept: str, m: dict) -> None:
    d = derive(concept)
    print(f"--- {concept}")
    for pn, p in m["printed"].items():
        bb = p.bounding_box()
        print(f"  printed {pn:12s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f}  "
              f"vol {p.volume / 1000:6.1f} cm3  solids {len(p.solids())}")
    print(f"  lowest opening {d['exit_above_water']:+.0f} mm over the waterline; lid lifts alone: {d['lid_removable_alone']}")
    for p, r in d["reach"].items():
        print(f"  {p}: lead need {r['need']:.0f} of {r['have']:.0f} mm, margin {r['margin']:+.0f}")


def main(concepts):
    out = __file__.rsplit("/", 1)[0] + "/out"
    allfail = {}
    for c in concepts:
        validate(c)
        d = derive(c)
        m = BUILDERS[c](d)
        report(c, m)
        fails = check(c, m)
        allfail[c] = fails
        for f in fails:
            print(f"  FAIL {f}")
        meshes = {f"printed_{k}": v for k, v in m["printed"].items()}
        meshes.update({f"hw_{k}": v for k, v in m["hardware"].items()})
        meshes.update({f"ctx_{k}": v for k, v in m["context"].items()})
        export_3mf(meshes, f"{out}/{c}.3mf")
        for k, v in m["printed"].items():
            export(v, f"{c}_{k}", out)
        near = Compound(list(m["printed"].values()) + list(m["hardware"].values()))
        export(near, f"{c}_assembly", out)
        export(Compound([near, m["context"]["tote"], m["context"]["lid"]]), f"{c}_in_tote", out)
        maybe_show(*m["printed"].values(), *m["hardware"].values(), names=list(m["printed"]) + list(m["hardware"]))
    return allfail


if __name__ == "__main__":
    res = main(ACTIVE_CONCEPTS)
    print("\n" + "\n".join(f"{c}: {'PASS' if not f else f'{len(f)} FAIL'}" for c, f in res.items()))
