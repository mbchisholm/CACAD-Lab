"""Concept D, the instrument panel: printed panel, case and knob, every bought part as an envelope (the
displays and the encoder board from Adafruit's STEPs when ref/ has them), and the concept checks: every pair
of solids apart except where they are meant to touch (zero volume), everything behind the panel inside the
case. Every number from panel_params.derive.

    .venv/bin/python projects/nutrient_controller/panel.py     # build, check, out/D_panel.3mf, out/D_*.step

Frame: front view, X right, Z up, Y into the box, the panel's front face at y = 0.
"""
from __future__ import annotations

import math

from build123d import (Align, Axis, Box, Compound, Cylinder, FontStyle, GeomType, Location, Part, Plane, Pos,
                       RegularPolygon, Rot, Text, extrude, fillet, import_step)

from cacad import export, export_3mf, interference_volume, try_chamfer
from cacad.registries.boards import BOARDS
from projects.nutrient_controller.panel_params import PARTS, validate

HERE = __file__.rsplit("/", 1)[0]   # a string: no os/pathlib in a part file (F23)
OUT = HERE + "/out"
PRINTED = ("panel", "case", "knob")


def _box(x0, x1, y0, y1, z0, z1) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def _cyl_y(d, x, z, y0, y1) -> Part:
    """A cylinder of diameter d along Y from y0 to y1, axis at (x, z)."""
    return Pos(x, (y0 + y1) / 2, z) * Rot(90, 0, 0) * Cylinder(d / 2, abs(y1 - y0))


def _cyl_z(d, x, y, z0, z1) -> Part:
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def legends(d: dict) -> list:
    """(text, (x, z), size, align) for every engraved legend."""
    P = PARTS
    win_left = d["display_x"] - d["window"][0] / 2
    out = [(t, (win_left - 5.0, z), d["label_size"], (Align.MAX, Align.CENTER))
           for t, z in zip(d["display_labels"], d["display_z"])]
    out.append((d["wordmark"][0], d["wordmark"][1], d["wordmark"][2], (Align.CENTER, Align.CENTER)))
    for name, key in (("POWER", "power_lamp"), ("ALERT", "alert_lamp")):
        x, z = d[key]
        out.append((name, (x, z + d["lamp_label_dz"]), d["small_size"], (Align.CENTER, Align.CENTER)))
    kx, kz = d["knob_xz"]
    out.append((d["knob_label"][0], (kx, d["knob_label"][1]), d["small_size"], (Align.CENTER, Align.CENTER)))
    for x, name in zip(d["channel_x"], d["channel_names"]):
        out.append((name, (x, d["channel_label_z"]), d["channel_size"], (Align.CENTER, Align.CENTER)))
        tx = x + d["toggle_dx"] + d["toggle_legend_dx"]
        for i, t in enumerate(d["toggle_legends"]):
            out.append((t, (tx, d["row_z"] + (1 - i) * d["legend_pitch"]), d["small_size"], (Align.MIN, Align.CENTER)))
    return out


def _text(d, t, xz, size, align, y0, depth) -> Part:
    pl = Plane(origin=(xz[0], y0, xz[1]), x_dir=(1, 0, 0), z_dir=(0, -1, 0))   # reads from the front
    sk = Text(t, font_size=size, font=d["font"], font_style=FontStyle.BOLD, align=align)
    return extrude(pl * sk, amount=-depth)                                   # into the panel (+y)


def build_panel(d: dict) -> Part:
    t = d["panel_t"]
    p = _box(d["x0"], d["x1"], 0, t, d["z0"], d["z1"])
    p = fillet(p.edges().filter_by(Axis.Y), d["corner_r"])
    # lip on the back: locates the panel in the case opening, broken at the corner bosses
    gap = 0.3
    xi, zi = d["W"] / 2 - d["wall"] - gap, d["H"] / 2 - d["wall"] - gap
    ro = d["corner_r"] - d["wall"] - gap          # follows the case's inner corner rounding
    lip = fillet(_box(-xi, xi, t, t + d["lip_h"], -zi, zi).edges().filter_by(Axis.Y), ro) - \
        fillet(_box(-xi + d["lip"], xi - d["lip"], t, t + d["lip_h"], -zi + d["lip"], zi - d["lip"]).edges().filter_by(Axis.Y), ro - d["lip"])
    for x, z in d["panel_screws"]:
        lip -= _cyl_y(d["boss_d"] + 2 * gap, x, z, t, t + d["lip_h"])
    p += lip
    for kind, (x, z), s in d["holes"]:
        if kind == "window":
            p -= _box(x - s[0] / 2, x + s[0] / 2, -1, t + 1, z - s[1] / 2, z + s[1] / 2)
        else:
            p -= _cyl_y(s, x, z, -1, t + d["lip_h"] + 1)
    for leg in legends(d):
        p -= _text(d, *leg, y0=0.0, depth=d["engrave"])
    p -= _box(-d["W"] / 2 + 10, d["W"] / 2 - 10, 0, d["engrave"], d["divider_z"] - d["divider_w"] / 2, d["divider_z"] + d["divider_w"] / 2)
    # finish last: the window bevels (functional: they open the viewing angle), then a cosmetic chamfer round the outline
    front = p.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0]
    wins = [(xz, s) for kind, xz, s in d["holes"] if kind == "window"]
    def on_window(e):
        c = e.center()
        return any(abs(abs(c.X - x) - w / 2) < 1e-4 and abs(c.Z - z) <= h / 2 + 1e-4 or
                   abs(abs(c.Z - z) - h / 2) < 1e-4 and abs(c.X - x) <= w / 2 + 1e-4 for (x, z), (w, h) in wins)
    bevel = [e for e in front.edges() if on_window(e)]
    assert len(bevel) == 4 * len(wins), f"window bevel: found {len(bevel)} edges for {len(wins)} windows"
    p = try_chamfer(p, bevel, d["window_bevel"], (), "window bevel", required=True)
    front = p.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0]
    return try_chamfer(p, front.outer_wire().edges(), d["front_chamfer"], (0.6, 0.4), "panel front chamfer")


def legend_inlays(d: dict) -> Part:
    """Render only: the second colour showing at the bottom of each engraving (filament change after layer 3)."""
    y = d["engrave"] - 0.2
    parts = [_text(d, *leg, y0=y, depth=0.2) for leg in legends(d)]
    parts.append(_box(-d["W"] / 2 + 10, d["W"] / 2 - 10, y, d["engrave"], d["divider_z"] - d["divider_w"] / 2, d["divider_z"] + d["divider_w"] / 2))
    return Compound(children=parts)


SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def lit_digits(d: dict, readings=("6.02", "1.85", "21.4")) -> Compound:
    """Render only: lit segments on each display face, as the 0.56in digits read through the red filter. Digit
    pitch and size are approximate (the STEP draws a plain block)."""
    h, w, sw, y = 14.2, 7.4, 1.5, d["display_face_y"] - 0.02
    cols = (-18.0, -6.0, 6.5, 18.5)
    segs = []
    for reading, z0 in zip(readings, d["display_z"]):
        chars = [c for c in reading if c != "."]
        dp = reading.index(".") - 1 if "." in reading else None
        chars = [" "] * (4 - len(chars)) + chars
        dp = None if dp is None else dp + 4 - len([c for c in reading if c != "."])
        for i, ch in enumerate(chars):
            xc = d["display_x"] + cols[i]
            box = {"a": (0, h / 2, w, sw), "g": (0, 0, w, sw), "d": (0, -h / 2, w, sw),
                   "f": (-w / 2, h / 4, sw, h / 2), "b": (w / 2, h / 4, sw, h / 2),
                   "e": (-w / 2, -h / 4, sw, h / 2), "c": (w / 2, -h / 4, sw, h / 2)}
            for sgm in SEGMENTS.get(ch, ""):
                dx, dz, bw, bh = box[sgm]
                segs.append(_box(xc + dx - bw / 2 + 0.2, xc + dx + bw / 2 - 0.2, y - 0.05, y, z0 + dz - bh / 2 + 0.2, z0 + dz + bh / 2 - 0.2))
            if i == dp:
                segs.append(_box(xc + w / 2 + 1.2, xc + w / 2 + 2.6, y - 0.05, y, z0 - h / 2 - 0.7, z0 - h / 2 + 0.7))
    return Compound(children=segs)


def build_case(d: dict) -> Part:
    t, w = d["panel_t"], d["wall"]
    c = _box(d["x0"], d["x1"], t, d["depth"], d["z0"], d["z1"])
    c = fillet(c.edges().filter_by(Axis.Y), d["corner_r"])
    inner = _box(d["x0"] + w, d["x1"] - w, t - 1, d["back_inner_y"], d["z0"] + w, d["z1"] - w)
    c -= fillet(inner.edges().filter_by(Axis.Y), d["corner_r"] - w)
    for x, z in d["panel_screws"]:   # insert bosses, sunk into the corner walls (F31)
        c += _cyl_y(d["boss_d"], x, z, t, t + d["boss_l"])
        c -= _cyl_y(4.0, x, z, t - 1, t + d["boss_l"] - 1)    # INSERT_BORE_M3-class bore, DESIGN for a concept
    for key, x in d["entries"]:      # cable entries through the bottom wall
        g = PARTS[key]
        c -= _cyl_z(g["hole"], x, d["entry_y"], d["z0"] - 1, d["z0"] + w + 1)
    return c


def build_knob(d: dict) -> Part:
    k = d["knob"]
    body = Pos(0, 0, k["skirt_h"] / 2) * Cylinder(k["skirt_d"] / 2, k["skirt_h"])
    body += Pos(0, 0, k["skirt_h"] + k["h"] / 2) * Cylinder(k["d"] / 2, k["h"])
    for i in range(k["flutes"]):
        a = 2 * math.pi * i / k["flutes"]
        body -= Pos(k["d"] / 2 * math.cos(a), k["d"] / 2 * math.sin(a), k["skirt_h"] + k["h"] / 2 + 1.0) * Cylinder(k["flute_r"], k["h"])
    top = k["skirt_h"] + k["h"]
    body -= Pos(k["dimple_r"], 0, top) * Cylinder(k["dimple_d"] / 2, 2 * k["dimple_depth"])
    enc = PARTS["encoder"]
    bore = enc["shaft_top"] - enc["bushing_top"] - k["gap"] + 0.5
    body -= Pos(0, 0, bore / 2) * Cylinder((enc["shaft_d"] + 0.1) / 2, bore)
    top_edges = body.edges().filter_by(GeomType.CIRCLE).filter_by(lambda e: abs(e.center().Z - top) < 1e-6 and abs(e.radius - k["d"] / 2) < 1e-6)
    body = try_chamfer(body, top_edges, 1.5, (1.0, 0.6), "knob top chamfer")
    x, z = d["knob_xz"]
    return Pos(x, d["knob_base_y"], z) * Rot(90, 0, 0) * body    # local +Z (the knob's face) points out of the panel (-y)


def _vendor(path: str):
    try:
        return import_step(path)
    except (OSError, ValueError, RuntimeError):
        return None


def build_bought(d: dict) -> dict:
    """Envelope per bought part, placed. Vendor STEPs where ref/ has them."""
    P, t = PARTS, d["panel_t"]
    out = {}
    disp = _vendor(HERE + "/ref/vendor_step/878 7-segment display backpack.step")
    pcb_w, pcb_h, pcb_t = P["display"]["pcb"]
    for i, z in enumerate(d["display_z"]):
        x = d["display_x"]
        fy = d["display_face_y"]
        if disp is not None:   # STEP frame: PCB z 0..1.6, display on top to 9.6; +z turns to -y (towards the panel)
            out[f"display {i}"] = disp.rotate(Axis.X, 90).moved(Location((x, fy + P["display"]["body_h"] + pcb_t, z)))
        else:
            out[f"display {i}"] = _box(x - pcb_w / 2, x + pcb_w / 2, fy + P["display"]["body_h"], fy + P["display"]["body_h"] + pcb_t,
                                       z - pcb_h / 2, z + pcb_h / 2) + \
                _box(x - P["display"]["face"][0] / 2, x + P["display"]["face"][0] / 2, fy, fy + P["display"]["body_h"],
                     z - P["display"]["face"][1] / 2, z + P["display"]["face"][1] / 2)
        yb = fy + P["display"]["body_h"] + pcb_t
        out[f"display {i} back parts"] = _box(x - pcb_w / 2 + 3, x + pcb_w / 2 - 3, yb, yb + P["display"]["back_parts"], z - pcb_h / 2 + 3, z + pcb_h / 2 - 3)
        fw, fh, ft = d["filter"]
        out[f"filter {i}"] = _box(x - fw / 2, x + fw / 2, t, t + ft, z - fh / 2, z + fh / 2)
    enc = _vendor(HERE + "/ref/vendor_step/4991 QT Rotary Encoder.step")
    kx, kz = d["knob_xz"]
    E = P["encoder"]
    if enc is not None:
        out["encoder"] = enc.rotate(Axis.X, 90).moved(Location((kx, d["encoder_pcb_y"], kz)))
    else:
        out["encoder"] = _box(kx - 12.7, kx + 12.7, d["encoder_pcb_y"] - E["pcb"][2], d["encoder_pcb_y"], kz - 12.7, kz + 12.7) + \
            _cyl_y(E["shaft_d"], kx, kz, d["shaft_tip_y"], t)
    out["encoder nut"] = _cyl_y(10.0, kx, kz, -E["nut_t"], 0) - _cyl_y(E["bushing_d"] + 0.05, kx, kz, -E["nut_t"] - 1, 1)
    L = P["lamp"]
    for name, (x, z) in d["lamps"]:
        lamp = _cyl_y(L["bezel_d"], x, z, -L["bezel_h"], 0) - _cyl_y(5.6, x, z, -L["bezel_h"] - 1, -1.0)   # bezel round the 5 mm lens
        lamp += _cyl_y(L["hole"] - 0.1, x, z, 0, L["length"] - L["bezel_h"])
        lamp += _box(x - 1.5, x + 1.5, L["length"] - L["bezel_h"], d["lamp_back_y"], z - 2.5, z + 2.5)   # lugs
        out[f"lamp {name} {x:.0f}"] = lamp
        out[f"lens {name} {x:.0f}"] = _cyl_y(5.4, x, z, -L["bezel_h"], -1.0)
        nut = Pos(x, t + L["nut_t"] / 2, z) * Rot(90, 0, 0) * extrude(RegularPolygon(L["nut_af"] / math.sqrt(3), 6), L["nut_t"] / 2, both=True)
        out[f"lamp nut {x:.0f}"] = nut - _cyl_y(L["hole"], x, z, t - 1, t + L["nut_t"] + 1)
    T = P["toggle"]
    for x, z in d["toggles"]:
        boot = Pos(x, -T["nut_t"] / 2, z) * Rot(90, 0, 0) * extrude(RegularPolygon(T["boot_d"] / math.sqrt(3), 6), T["nut_t"] / 2, both=True)
        boot += _cyl_y(8.0, x, z, -T["boot_h"], -T["nut_t"])
        bw, bd, bl = T["body"]
        body = _box(x - bw / 2, x + bw / 2, t, t + bl, z - bd / 2, z + bd / 2) + _box(x - bw / 2 + 1, x + bw / 2 - 1, t + bl, d["toggle_back_y"], z - 4, z + 4)
        body += _cyl_y(T["hole"] - 0.1, x, z, 0, t)   # bushing through the panel
        out[f"toggle {x:.0f}"] = boot + body
    pump = P["pump"]
    fl_t = 3.0   # flange thickness: drawn, not dimensioned (UNVERIFIED)
    for x, z in d["pumps"]:
        fw, fh = pump["flange"]
        flange = _box(x - fw / 2, x + fw / 2, -fl_t, 0, z - fh / 2, z + fh / 2)
        for s in (-1, 1):
            flange -= _cyl_y(pump["hole_d"], x + s * pump["hole_pitch"] / 2, z, -fl_t - 1, 1)
        out[f"pump {x:.0f} flange"] = flange
        out[f"pump {x:.0f} head"] = _cyl_y(pump["head_d"], x, z, -pump["head_depth"], -fl_t)
        out[f"pump {x:.0f} motor"] = _cyl_y(pump["motor_d"], x, z, 0, pump["motor_l"])
        ty = -(pump["head_depth"] + fl_t) / 2
        out[f"pump {x:.0f} tubes"] = Compound(children=[
            _cyl_z(pump["tube_od"], x + s * pump["tube_pitch"] / 2, ty, z - fh / 2 - d["tube_len"], z - pump["head_d"] / 2)
            for s in (-1, 1)])
    for i, (name, (x, z)) in enumerate(d["back_boards"]):
        sx, sz = BOARDS[name].size
        y1 = d["back_inner_y"] - d["board_standoff"]
        out[f"board {i} {name}"] = _box(x - sx / 2, x + sx / 2, y1 - 1.6, y1, z - sz / 2, z + sz / 2)
    for key, x in d["entries"]:
        g = P[key]
        zb = d["z0"] + d["wall"]
        if "nut_a" in g:
            gl = _cyl_z(g["hole"] - 0.1, x, d["entry_y"], d["z0"], d["z0"] + g["thread"])
            gl += _cyl_z(g["nut_a"], x, d["entry_y"], zb, zb + g["nut_b"]) - _cyl_z(g["hole"], x, d["entry_y"], zb - 1, zb + g["nut_b"] + 1)
            gl += _cyl_z(g["a"], x, d["entry_y"], d["z0"] - (g["c_max"] - g["thread"]), d["z0"])
        else:
            gl = _cyl_z(g["body_d"], x, d["entry_y"], zb, zb + g["body_l"]) + _cyl_z(g["hole"] - 0.1, x, d["entry_y"], d["z0"], zb)
        out[key] = gl
    return out


def check(parts: dict, d: dict) -> dict:
    """Pairwise: no two solids overlap (touching is zero volume). Then everything behind the panel is inside the case."""
    names = list(parts)
    bad, pairs = [], 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.startswith(b.split(" ")[0]) and b.startswith("display") and "back" in a:   # a display and its own back parts
                continue
            lo_a, hi_a = tuple(parts[a].bounding_box().min), tuple(parts[a].bounding_box().max)
            lo_b, hi_b = tuple(parts[b].bounding_box().min), tuple(parts[b].bounding_box().max)
            if any(lo_a[k] > hi_b[k] + 1e-6 or lo_b[k] > hi_a[k] + 1e-6 for k in range(3)):
                continue
            pairs += 1
            v = interference_volume(parts[a], parts[b])
            if v > 1e-3:
                bad.append(f"{a} x {b}: {v:.3f} mm^3")
    assert not bad, "concept D: overlaps\n  " + "\n  ".join(bad)
    through = {k for k, _ in d["entries"]}   # cable entries pass through the bottom wall; pumps, lamps, toggles the panel
    inside = [n for n in names if n not in (*PRINTED, *through) and not n.startswith(("pump", "encoder nut", "lamp", "toggle"))]
    for n in inside:
        bb = parts[n].bounding_box()
        assert d["x0"] + d["wall"] - 1e-6 <= bb.min.X and bb.max.X <= d["x1"] - d["wall"] + 1e-6, f"{n} outside the case in x"
        assert d["z0"] + d["wall"] - 1e-6 <= bb.min.Z and bb.max.Z <= d["z1"] - d["wall"] + 1e-6, f"{n} outside the case in z"
        assert bb.max.Y <= d["back_inner_y"] + 1e-6, f"{n} through the back wall"
    return dict(pairs=pairs, solids=len(names))


ROLES = (("display", "displays"), ("filter", "filters"), ("encoder nut", "nuts"), ("encoder", "encoder"),
         ("lamp nut", "nuts"), ("lamp", "lamp_bezels"), ("lens run", "lens_run"), ("lens power", "lens_power"),
         ("lens alert", "lens_alert"), ("toggle", "toggles"), ("pump", None), ("board", "boards"),
         ("gland", "entries"), ("dc_jack", "entries"))


def groups(parts: dict, r: dict) -> dict:
    """Envelopes by role, for colouring a view; render-only solids last."""
    out = {}
    for n, p in parts.items():
        if n in PRINTED:
            continue
        role = next(rl for prefix, rl in ROLES if n.startswith(prefix))
        if role is None:   # pumps: "pump <x> flange|head|motor|tubes"
            role = "pump_" + n.split(" ")[-1]
        out.setdefault(role, []).append(p)
    out["inlays"] = [r["inlays"]]
    out["digits"] = [lit_digits(r["d"])]
    return out


def build_all(**overrides) -> dict:
    d = validate(**overrides)
    printed = dict(panel=build_panel(d), case=build_case(d), knob=build_knob(d))
    for name, p in printed.items():
        assert p.is_valid, f"{name} invalid"
    parts = {**printed, **build_bought(d)}
    return dict(d=d, parts=parts, printed=printed, inlays=legend_inlays(d))


if __name__ == "__main__":
    r = build_all()
    d, parts = r["d"], r["parts"]
    rep = check(parts, d)
    for name, p in r["printed"].items():
        bb = p.bounding_box().size
        print(f"{name}: {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f}, {p.volume / 1000:.1f} cm3, solids {len(p.solids())}, valid {p.is_valid}")
    print(f"checks: {rep['solids']} solids, {rep['pairs']} touching pairs measured, no overlap; everything inside the case")
    for name, p in r["printed"].items():
        export(p, f"D_{name}", OUT)
    export_3mf(r["printed"], OUT + "/D_panel.3mf")
    for role, shapes in groups(parts, r).items():
        export(Compound(children=[sol for sh in shapes for sol in sh.solids()]), f"D_{role}", OUT)
    print("exported: printed parts (STEP, STL, 3MF) and", ", ".join(groups(parts, r)))
