"""Nutrient controller B1 assembly: the four printed parts, every bought part
as an envelope (boards with their tallest parts, plugs with finger room,
glands, jack, buttons, LED, pump, tubes), and the tote wall and waterline as
context, in the box frame. Function checks:

- every envelope clear of every printed part and of every other envelope
  (pairwise, F7), designed contacts excepted by name;
- the box can be hung: with the box `slide` higher, each post head travels
  along x through the back plate; at rest the box touches neither the posts
  nor the plate;
- the outlet tube passes through the plate slot; every tote-wall hole is
  above the waterline (params.validate);
- dry electronics sit inside the body's cavity.

Writes out/B1.3mf (one mesh per part, F15) and out/B1_assembly.step.

    .venv/bin/python projects/nutrient_controller/assembly.py
"""
from __future__ import annotations

from build123d import Compound, Location, Part

from cacad import export, export_3mf, interference_volume, is_inside
from cacad.registries.boards import BOARDS
from projects.nutrient_controller.body import build_body
from projects.nutrient_controller.cover import build_cover
from projects.nutrient_controller.geom import box, cyl
from projects.nutrient_controller.params import ACTIVE_SIZES, derive, validate
from projects.nutrient_controller.rim_hook import build_hook, build_knob, build_pad, clamp_locations
from projects.nutrient_controller.wall_plate import build_backing, build_plate, plate_x


def _slab(x0, x1, cy, cz, ey, ez):
    return box(x0, x1, cy - ey / 2, cy + ey / 2, cz - ez / 2, cz + ez / 2)


def build_hardware(size: str = "B1") -> dict:
    d = derive(size)
    P = d["parts"]
    W, H, D, w, t = d["W"], d["H"], d["D"], d["wall"], d["pcb_t"]
    hw = {}
    # boards on the back plate: PCB, then a component envelope over the outline up to the tallest part
    for k, b in d["boards"].items():
        (cy, cz), (ey, ez) = b["centre"], b["extent"]
        hw[f"{k}_pcb"] = _slab(b["x0"], b["x0"] + t, cy, cz, ey, ez)
        if k != "carrier":
            hw[f"{k}_parts"] = _slab(b["x0"] + t, b["top_x"], cy, cz, ey - 2.0, ez - 2.0)
        for i, cn in enumerate(b["conns"]):
            m = cn["mating"]
            fy, fz = cn["facing"]
            ay, az = cn["at"]
            my, mz = ay + fy * m.header_depth / 2, az + fz * m.header_depth / 2
            L = m.plug_len + d["finger"].get((k, cn["kind"]), d["plug_finger"])
            xs = (b["x0"] + t, b["x0"] + t + m.plug_h)
            if fy:
                hw[f"{k}_plug{i}"] = box(*xs, *sorted((my, my + fy * L)), az - m.plug_w / 2, az + m.plug_w / 2)
            else:
                hw[f"{k}_plug{i}"] = box(*xs, ay - m.plug_w / 2, ay + m.plug_w / 2, *sorted((mz, mz + fz * L)))
    # the carrier's passengers
    x = d["xiao"]
    hw["xiao"] = box(*x["x"], x["y"] - x["width"] / 2, x["y"] + x["width"] / 2, *x["z"])
    po = d["pololu"]
    hw["pololu"] = _slab(*po["x"], po["y"], po["z"], po["size"][1], po["size"][0])
    # OLED on the cover: PCB, glass towards the window, components and plugs towards the box
    o = P["oled"]
    ob = BOARDS["OLED_938"]
    oy, oz = d["oled_yz"]
    xb = d["oled_board_x"]
    hw["oled_pcb"] = _slab(xb, xb + t, oy, oz, *ob.size)
    hw["oled_glass"] = _slab(xb + t, xb + t + o["panel_t"], oy + o["glass_off"][0], oz + o["glass_off"][1], *o["glass"])
    from cacad.registries.connectors import MATINGS
    sh = MATINGS["JST_SH4"]
    for i, cn in enumerate(ob.connectors):
        fy = cn.facing[0]
        my = oy + cn.x + fy * sh.header_depth / 2
        hw[f"oled_plug{i}"] = box(xb - sh.plug_h, xb, *sorted((my, my + fy * (sh.plug_len + d["plug_finger"]))),
                                  oz - sh.plug_w / 2, oz + sh.plug_w / 2)
    # buttons, LED: bezel outside, body behind the panel
    bt = P["button"]
    for i, (y, z) in enumerate(d["buttons_yz"]):
        hw[f"button{i}"] = cyl(bt["hole"], "x", (D - bt["behind"] / 2, y, z), bt["behind"])
        hw[f"button{i}_bezel"] = cyl(bt["bezel_d"], "x", (D + d["cover_t"] + 1.0, y, z), 2.0)
    le = P["led"]
    ly, lz = d["led_yz"]
    hw["led"] = cyl(le["ring_d"], "x", (D - (le["ring_h"] + le["body_l"]) / 2, ly, lz), le["ring_h"] + le["body_l"])
    # bottom wall: gland bodies outside, locknuts inside; jack body inside; plugs outside
    for k in ("gland_tds", "gland_ds"):
        g = P[k]
        y, xg = d[f"{k}_yx"]
        hw[f"{k}_nut"] = cyl(g["nut_a"], "z", (xg, y, w + g["nut_b"] / 2), g["nut_b"])
        hw[f"{k}_body"] = cyl(g["a"], "z", (xg, y, -(g["c_max"] - g["thread"]) / 2), g["c_max"] - g["thread"])
    y, xj = d["jack_yx"]
    j = P["dc_jack"]
    hw["jack"] = cyl(j["body_d"], "z", (xj, y, w + j["body_l"] / 2), j["body_l"])
    hw["jack_plug"] = cyl(10.0, "z", (xj, y, -17.5), 35.0)                       # PLACEHOLDER 5.5 mm plug
    ow, oh = P["usb_plug"]["overmold"]
    hw["usb_plug"] = box(d["usb_x"] - oh / 2, d["usb_x"] + oh / 2, x["y"] - ow / 2, x["y"] + ow / 2, -25.0, 0.0)
    # pump: flange + head outside the -Y wall, motor inside
    pp = P["pump"]
    px, pz = d["pump_xz"]
    fx, fz = pp["flange"][1], pp["flange"][0]                                    # rotated: 40.3 along x, 54.5 along z
    hw["pump_head"] = box(px - fx / 2, px + fx / 2, -W / 2 - pp["head_depth"], -W / 2, pz - fz / 2, pz + fz / 2)
    hw["pump_motor"] = cyl(pp["motor_d"], "y", (px, -W / 2 + pp["motor_l"] / 2, pz), pp["motor_l"])
    # tubes leave the head towards the plate. Wall mount: the outlet (upper) goes through the tote wall. Rim
    # mount: both stop just past the plate; the outlet is routed by hand up and over the rim in the hook's groove.
    ty = -W / 2 - pp["head_depth"] / 2
    xp0, xp1 = plate_x(d)
    xt = xp0 - max(d["tote_wall_t"]) - d["backing_t"] - 10.0 if d["mount"] == "wall" else xp0 - 5.0
    x_head = px - fx / 2
    lo, hi = d["tube_z"]
    hw["tube_out"] = cyl(pp["tube_od"], "x", ((x_head + xt) / 2, ty, hi), x_head - xt)
    hw["tube_in"] = cyl(pp["tube_od"], "x", ((x_head + xp1 + 3.0) / 2, ty, lo), x_head - xp1 - 3.0)
    hw["tube_in_down"] = cyl(pp["tube_od"], "z", (xp1 + 3.0 + pp["tube_od"] / 2, ty, lo / 2), lo)
    if d["mount"] == "rim":
        hw.update(_clamp_hardware(d))
    return hw


def _clamp_hardware(d, c=None) -> dict:
    """Rim clamp fasteners: two ISO 4762 M5 (heads on the leg's container face, nuts in the plate bosses) and the
    ISO 4017 M6 screw with its nut, placed for a container of thickness c (default: mid range)."""
    c = sum(d["rim_c"]) / 2 if c is None else c
    m5, m6 = d["screws"]["M5"], d["screws"]["M6"]
    xl0 = d["x_leg"][0]
    x1 = plate_x(d)[1]
    nb_d, nb_h = d["plate_nut_boss"]
    pk = d["plate_nut_pocket"]
    hw = {}
    for i, y in enumerate(d["hook_bolts_y"]):
        z = d["hook_bolts_z"]
        L = d["hook_bolt_len"]
        hw[f"m5_{i}_head"] = cyl(m5["head_dk"], "x", (xl0 - m5["head_k"] / 2, y, z), m5["head_k"])
        hw[f"m5_{i}_shank"] = cyl(m5["d"], "x", (xl0 + L / 2, y, z), L)
        nx0 = x1 + nb_h - pk["depth"]
        hw[f"m5_{i}_nut"] = cyl(m5["nut_s"], "x", (nx0 + m5["nut_m_plain"] / 2, y, z), m5["nut_m_plain"])
    loc = clamp_locations(d, c)
    tip, head_top = loc["screw"]
    y, z = d["hook_y"], d["screw_z"]
    hw["m6_shank"] = cyl(m6["d"], "x", ((tip + head_top - m6["head_k"]) / 2, y, z), head_top - m6["head_k"] - tip)
    hw["m6_head"] = cyl(m6["head_s"], "x", (head_top - m6["head_k"] / 2, y, z), m6["head_k"])
    pkn = d["screw_nut_pocket"]
    hw["m6_nut"] = cyl(m6["nut_s"], "x", (xl0 + pkn["depth"] - m6["nut_m"] / 2, y, z), m6["nut_m"])
    return hw


def build_context(size: str = "B1", c=None) -> dict:
    """The container wall as a slab and the HDX waterline. Rim mount: the wall's inside face on the inner jaw,
    thickness c at the screw (default mid range); it says nothing about any one container's real profile."""
    d = derive(size)
    top = d["H"] + d["top_below_rim"]
    if d["mount"] == "wall":
        xp0 = plate_x(d)[0]
        tw = max(d["tote_wall_t"])
        x0, x1 = xp0 - tw, xp0
    else:
        c = sum(d["rim_c"]) / 2 if c is None else c
        x0, x1 = d["x_jaw_face"], d["x_jaw_face"] + c
    wall = box(x0, x1, -200.0, 150.0, -60.0, top)
    water = box(x0 - 150.0, x0, -200.0, 150.0, -60.0, d["waterline_z"])
    return dict(tote_wall=wall, water=water)


# contacts that are the design: a part seated on, through or against another
CONTACTS = {
    ("pump_motor", "body"), ("pump_head", "body"), ("pump_motor", "pump_head"),
    ("tube_in", "tube_in_down"), ("tube_out", "pump_head"), ("tube_in", "pump_head"),
    ("tube_out", "backing"),
    ("m5_0_head", "m5_0_shank"), ("m5_1_head", "m5_1_shank"), ("m5_0_shank", "m5_0_nut"), ("m5_1_shank", "m5_1_nut"),
    ("m6_shank", "m6_head"), ("m6_shank", "m6_nut"), ("m6_head", "knob"), ("m6_shank", "knob"), ("m6_shank", "pad"),
    ("m6_nut", "hook"), ("m5_0_head", "hook"), ("m5_1_head", "hook"), ("m5_0_nut", "plate"), ("m5_1_nut", "plate"),
    ("button0", "cover"), ("button1", "cover"), ("button2", "cover"), ("led", "cover"),
    ("button0", "button0_bezel"), ("button1", "button1_bezel"), ("button2", "button2_bezel"),
    ("oled_glass", "oled_pcb"), ("oled_pcb", "oled_plug0"), ("oled_pcb", "oled_plug1"),
}


def _contact(a, b):
    return (a, b) in CONTACTS or (b, a) in CONTACTS


def check_assembly(printed: dict, hw: dict, size: str = "B1") -> list[str]:
    d = derive(size)
    fails = []
    names = list(hw)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _contact(a, b) or a.split("_")[0] == b.split("_")[0] and a.split("_")[0] in {d_ for d_ in d["boards"]} | {"oled"}:
                continue
            v = interference_volume(hw[a], hw[b])
            if v > 1e-3:
                fails.append(f"{a} x {b}: {v:.2f} mm3")
        for pn, p in printed.items():
            if _contact(a, pn) or (pn == "plate" and a.startswith("tube")) or (pn == "backing" and a == "tube_out"):
                continue
            v = interference_volume(hw[a], p)
            if v > 1e-3:
                fails.append(f"{a} x printed {pn}: {v:.2f} mm3")
    pn = list(printed)
    for i, a in enumerate(pn):
        for b in pn[i + 1:]:
            v = interference_volume(printed[a], printed[b])
            if v > 1e-3:
                fails.append(f"printed {a} x {b}: {v:.2f} mm3")
    # hanging: with the box `slide` higher, each post head travels along x through the back plate (the box
    # is offered up to the wall), then the box drops onto the necks
    raised = printed["body"].moved(Location((0, 0, d["slide"])))
    x1 = plate_x(d)[1]
    for y, z in d["keyholes"]:
        sweep = cyl(d["post_head_d"], "x", ((x1 + d["back_t"] + 1.0) / 2, y, z), d["back_t"] + 1.0 - x1)
        v = interference_volume(raised, sweep)
        if v > 1e-3:
            fails.append(f"post head at ({y:g}, {z:g}) does not pass the keyholes with the box raised {d['slide']}: {v:.2f} mm3")
    v = interference_volume(printed["body"], printed["plate"])
    if v > 1e-3:
        fails.append(f"box at rest hits the plate or posts: {v:.2f} mm3")
    # the tubes pass the plate slot (no overlap with the plate)
    for t in ("tube_out", "tube_in"):
        v = interference_volume(hw[t], printed["plate"])
        if v > 1e-3:
            fails.append(f"{t} hits the plate: {v:.2f} mm3")
    if d["mount"] == "rim":
        fails += _check_clamp(printed, d)
    # dry electronics inside the body's cavity
    cav = box(d["back_t"], d["D"], *d["inner_y"], *d["inner_z"])
    for n in ("tds_pcb", "ads_pcb", "mosfet_pcb", "carrier_pcb", "xiao", "pololu", "oled_pcb", "pump_motor"):
        if not is_inside(cav, hw[n].center()):
            fails.append(f"{n} is not inside the body")
    return fails


def _check_clamp(printed: dict, d: dict) -> list[str]:
    """Across the container range: the hook clears the wall, the pad lands on it, the knob clears everything,
    and the M6 still reaches the pad and the nut."""
    fails = []
    pad0, knob0 = build_pad(d["size"]), build_knob(d["size"])
    lo, hi = d["rim_c"]
    for c in (lo, (lo + hi) / 2, hi):
        wall = build_context(d["size"], c)["tote_wall"]
        loc = clamp_locations(d, c)
        pad, knob = loc["pad"] * pad0, loc["knob"] * knob0
        for name, part in (("hook", printed["hook"]), ("pad", pad), ("plate", printed["plate"]), ("knob", knob)):
            v = interference_volume(wall, part)
            if v > 1e-3:
                fails.append(f"container {c:g} mm x {name}: {v:.2f} mm3")
        for name in ("body", "cover", "plate", "hook"):
            v = interference_volume(knob, printed[name])
            if v > 1e-3:
                fails.append(f"knob at container {c:g} mm x {name}: {v:.2f} mm3")
        v = interference_volume(pad, printed["hook"])
        if v > 1e-3:
            fails.append(f"pad at container {c:g} mm x hook: {v:.2f} mm3")
        tip, head_top = loc["screw"]
        nut_x = d["x_leg"][0] + d["screw_nut_pocket"]["depth"] - d["screws"]["M6"]["nut_m"]
        if not tip < nut_x:
            fails.append(f"M6 tip at container {c:g} mm does not pass its nut")
    for hw_bolt in ("m5_0_head", "m5_1_head"):
        h = _clamp_hardware(d, hi)[hw_bolt]
        v = interference_volume(h, build_context(d["size"], hi)["tote_wall"])
        if v > 1e-3:
            fails.append(f"{hw_bolt} hits the thickest container: {v:.2f} mm3")
    return fails


def build_printed(size: str) -> dict:
    d = derive(size)
    printed = dict(body=build_body(size), cover=build_cover(size), plate=build_plate(size))
    if d["mount"] == "wall":
        printed["backing"] = build_backing(size)
    else:
        loc = clamp_locations(d, sum(d["rim_c"]) / 2)
        printed.update(hook=build_hook(size), knob=loc["knob"] * build_knob(size), pad=loc["pad"] * build_pad(size))
    return printed


def main():
    out = __file__.rsplit("/", 1)[0] + "/out"
    res = {}
    for size in ACTIVE_SIZES:
        validate(size)
        printed = build_printed(size)
        hw = build_hardware(size)
        ctx = build_context(size)
        fails = check_assembly(printed, hw, size)
        res[size] = fails
        for pn, p in printed.items():
            bb = p.bounding_box()
            print(f"  {pn:8s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f}  {p.volume / 1000:6.1f} cm3")
        for f in fails:
            print(f"  FAIL {f}")
        meshes = {f"printed_{k}": v for k, v in printed.items()}
        meshes.update({f"hw_{k}": v for k, v in hw.items()})
        meshes.update({f"ctx_{k}": v for k, v in ctx.items()})
        export_3mf(meshes, f"{out}/{size}.3mf")
        export(Compound(list(printed.values()) + list(hw.values())), f"{size}_assembly", out)
        print(f"{size}: {'PASS' if not fails else f'{len(fails)} FAIL'}  ({len(hw)} envelopes, {len(printed)} printed parts)")
    return res


if __name__ == "__main__":
    main()
