"""Nutrient controller L1: the logic box and its lid, the bought parts in them as envelopes, the print and assembly
checks, and the print set (box, lid and the standoff_plate ANALOG_NODE plate) as one 3MF.

The body prints on its back: M2 and M3 nut pockets open to the bed face, the jack hole a truncated teardrop, the
keyholes vertical through the ears. The lid prints on its outer face. Every number is from lean_params.derive.

    .venv/bin/python projects/nutrient_controller/lean_box.py     # build, check, out/L1_*.step|stl, out/L1_print_set.3mf
"""
from __future__ import annotations

import math

from build123d import Axis, Compound, Location, Part, fillet

from cacad import assert_bbox, assert_material, interference_volume, single_solid
from cacad.checks.orientation import check_declared_orientation, to_print_orientation
from cacad.checks.overhang import check_overhang
from projects.nutrient_controller.geom import box, cyl, hex_prism, teardrop
from projects.nutrient_controller.lean_params import SCREWS, derive


def build_body(d: dict | None = None) -> Part:
    d = d or derive()
    W, H, D, w, bt = d["W"], d["H"], d["D"], d["wall"], d["back_t"]
    (xi0, xi1), (yi0, yi1) = d["inner_x"], d["inner_y"]
    body = fillet(box(-W / 2, W / 2, 0, H, 0, D).edges().filter_by(Axis.Z), d["corner_r"])
    body -= box(xi0, xi1, yi0, yi1, bt, D + 1)
    # lid-screw columns, board bosses and rest pads, each sunk 0.5 into the back plate
    for x, y in d["columns"]:
        body += cyl(d["column_d"], "z", (x, y, (bt - 0.5 + D) / 2), D - bt + 0.5)
    for b in d["bosses"]:
        body += cyl(d["m2_boss_d"], "z", (*b["at"], (bt - 0.5 + d["z_board"]) / 2), d["standoff"] + 0.5)
    for r in d["rest_pads"]:
        body += cyl(d["rest_pad_d"], "z", (*r["at"], (bt - 0.5 + d["z_board"]) / 2), d["standoff"] + 0.5)
    # keyhole ears, 1.0 into the side wall, outer corners rounded
    ew, _ = d["ear_size"]
    for e in d["ears"]:
        x0, x1 = e["x"]
        ear = box(x0 - 1.0, x1, *e["y"], 0, d["ear_t"]) if e["side"] > 0 else box(x0, x1 + 1.0, *e["y"], 0, d["ear_t"])
        outer = W / 2 + ew
        ear = fillet(ear.edges().filter_by(Axis.Z).filter_by(lambda g: abs(abs(g.center().X) - outer) < 1e-6), 3.0)
        body += ear

    cuts = []
    p2, p3 = d["m2_pocket"], d["m3_pocket"]
    for b in d["bosses"]:
        x, y = b["at"]
        cuts.append(cyl(d["m2_bore"], "z", (x, y, d["z_board"] / 2), d["z_board"] + 0.02))
        cuts.append(hex_prism(p2["s"], "z", (x, y, p2["depth"] / 2 - 0.01), p2["depth"] + 0.02))
    for x, y in d["columns"]:
        cuts.append(cyl(d["m3_bore"], "z", (x, y, D / 2), D + 0.02))
        cuts.append(hex_prism(p3["s"], "z", (x, y, p3["depth"] / 2 - 0.01), p3["depth"] + 0.02))
    jk = d["jack"]
    cuts.append(teardrop(d["jack_hole"], "y", (jk["x"], w / 2, jk["z"]), w + 0.02, "z", d["teardrop_cap"]))
    for n in d["notch_list"]:
        cuts.append(box(n["x"] - n["w"] / 2, n["x"] + n["w"] / 2, -0.01, w + 0.01, n["z0"], D + 0.01))
    for e in d["ears"]:
        (bx, by), (rx, ry) = e["big"], e["rest"]
        cuts.append(cyl(d["keyhole_big"], "z", (bx, by, d["ear_t"] / 2), d["ear_t"] + 0.02))
        cuts.append(box(rx - d["keyhole_slot"] / 2, rx + d["keyhole_slot"] / 2, by, ry, -0.01, d["ear_t"] + 0.01))
        cuts.append(cyl(d["keyhole_slot"], "z", (rx, ry, d["ear_t"] / 2), d["ear_t"] + 0.02))
    for c in cuts:
        body -= c
    return body


def build_lid(d: dict | None = None) -> Part:
    d = d or derive()
    W, H, D = d["W"], d["H"], d["D"]
    lid = fillet(box(-W / 2, W / 2, 0, H, D, d["lid_top"]).edges().filter_by(Axis.Z), d["corner_r"])
    for x, y in d["columns"]:
        lid -= cyl(d["m3_bore"], "z", (x, y, (D + d["lid_top"]) / 2), d["lid_t"] + 0.02)
    return lid


def build_hardware(d: dict | None = None) -> dict[str, Compound]:
    """Bought parts at their assembled positions: envelopes, not models."""
    d = d or derive()
    m2, m3 = SCREWS["M2"], SCREWS["M3"]
    hexr = lambda s: s / math.sqrt(3)
    boards, tops, plugs, reach, screws, nuts = [], [], [], [], [], []
    for b in d["boards"]:
        x0, x1, y0, y1 = b["rect"]
        zt = d["z_board"] + b["t"]
        slab = box(x0, x1, y0, y1, d["z_board"], zt)
        for hx, hy in b["holes"]:
            slab -= cyl(b["board"].hole_dia, "z", (hx, hy, (d["z_board"] + zt) / 2), b["t"] + 0.02)
        boards.append(slab)
        # the tallest part, over the whole board but clear of the screw heads (conservative everywhere else)
        top = box(x0, x1, y0, y1, zt, zt + b["top"])
        for hx, hy in b["holes"]:
            top -= cyl(m2["head_dk"] + 1.0, "z", (hx, hy, zt + b["top"] / 2), b["top"] + 0.02)
        tops.append(top)
        for cn in b["conns"]:
            (mx, my), fx = cn["mouth"], cn["facing"][0]
            m = cn["mating"]
            for L, dest in ((m.plug_len, plugs), (cn["reach"], reach)):
                xa, xb = sorted((mx, mx + fx * L))
                dest.append(box(xa, xb, my - m.plug_w / 2, my + m.plug_w / 2, zt, zt + m.plug_h))
        for hx, hy in b["holes"]:
            tip = zt - b["m2_len"]
            screws.append(cyl(m2["d"], "z", (hx, hy, (tip + zt) / 2), b["m2_len"]) + cyl(m2["head_dk"], "z", (hx, hy, zt + m2["head_k"] / 2), m2["head_k"]))
            nz = d["m2_pocket"]["depth"] - m2["nut_m"]
            nut = hex_prism(m2["nut_s"], "z", (hx, hy, nz + m2["nut_m"] / 2), m2["nut_m"]) - cyl(m2["d"], "z", (hx, hy, nz + m2["nut_m"] / 2), m2["nut_m"] + 0.02)
            nuts.append(nut)
    lid_screws, lid_nuts = [], []
    for x, y in d["columns"]:
        tip, top = d["lid_screw_tip"], d["lid_top"]
        lid_screws.append(cyl(m3["d"], "z", (x, y, (tip + top) / 2), top - tip) + cyl(m3["head_dk"], "z", (x, y, top + m3["head_k"] / 2), m3["head_k"]))
        nz = d["m3_pocket"]["depth"] - m3["nut_m"]
        lid_nuts.append(hex_prism(m3["nut_s"], "z", (x, y, nz + m3["nut_m"] / 2), m3["nut_m"]) - cyl(m3["d"], "z", (x, y, nz + m3["nut_m"] / 2), m3["nut_m"] + 0.02))
    jk = d["jack"]
    y_in = d["inner_y"][0]
    jack = cyl(jk["body_d"], "y", (jk["x"], y_in + jk["body_l"] / 2, jk["z"]), jk["body_l"])
    # the mount screws at their rest positions: shank in the slot, head on the ear
    m4 = SCREWS["M4"]
    mounts = [cyl(m4["d"], "z", (*e["rest"], -5.0 + (d["ear_t"] + 5.0) / 2), d["ear_t"] + 5.0)
              + cyl(m4["head_dk"], "z", (*e["rest"], d["ear_t"] + m4["head_k"] / 2), m4["head_k"]) for e in d["ears"]]
    C = lambda xs: Compound(children=xs)
    return dict(boards=C(boards), tops=C(tops), plugs=C(plugs), reach=C(reach), screws=C(screws), nuts=C(nuts),
                lid_screws=C(lid_screws), lid_nuts=C(lid_nuts), jack=C([jack]), mounts=C(mounts))


def check_body(part: Part, d: dict | None = None) -> dict:
    d = d or derive()
    single_solid(part)
    assert part.is_valid, "body: invalid solid"
    ew, _ = d["ear_size"]
    assert_bbox(part, (d["W"] + 2 * ew, d["H"], d["D"]), 0.0, 0.05, "body")
    o = d["print_orientation"]["body"]
    check_declared_orientation(part, o)
    rep = check_overhang(part, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"],
                                    exceptions=d["body_overhang_exceptions"]))
    w, D = d["wall"], d["D"]
    probes = {"cavity": ((0.0, d["H"] / 2, D - 1.0), False)}
    car = d["boards"][0]
    probes["back plate"] = ((car["rect"][1] + 2.0, car["centre"][1], d["back_t"] / 2), True)
    hx, hy = d["bosses"][0]["at"]
    probes.update({"M2 pocket": ((hx, hy, 1.0), False), "M2 bore": ((hx, hy, d["z_board"] - 0.5), False),
                   "M2 boss wall": ((hx + (d["m2_bore"] / 2 + d["m2_boss_d"] / 2) / 2, hy, d["z_board"] - 1.0), True)})
    for i, (x, y) in enumerate(d["columns"]):
        sx = 1.0 if x < 0 else -1.0
        probes[f"column {i} bore"] = ((x, y, D - 1.0), False)
        probes[f"column {i} pocket"] = ((x, y, 1.0), False)
        probes[f"column {i} wall"] = ((x + sx * (d["m3_bore"] / 2 + 1.0), y, D - 1.0), True)
    for n in d["notch_list"]:
        probes[f"notch {n['name']} open"] = ((n["x"], w / 2, D - 0.5), False)
        probes[f"notch {n['name']} floor"] = ((n["x"], w / 2, n["z0"] - 0.3), True)
        probes[f"notch {n['name']} side"] = ((n["x"] + n["w"] / 2 + 0.5, w / 2, D - 0.5), True)
    jk = d["jack"]
    probes["jack hole"] = ((jk["x"], w / 2, jk["z"]), False)
    probes["wall beside jack"] = ((jk["x"] + d["jack_hole"] / 2 + 0.6, w / 2, jk["z"]), True)
    for i, e in enumerate(d["ears"]):
        (bx, by), (rx, ry) = e["big"], e["rest"]
        probes[f"ear {i} big hole"] = ((bx, by, d["ear_t"] / 2), False)
        probes[f"ear {i} slot"] = ((rx, (by + ry) / 2, d["ear_t"] / 2), False)
        probes[f"ear {i} rest"] = ((rx, ry, d["ear_t"] / 2), False)
        probes[f"ear {i} above rest"] = ((rx, ry + d["keyhole_slot"] / 2 + 1.0, d["ear_t"] / 2), True)
        probes[f"ear {i} beside slot"] = ((rx + d["keyhole_slot"] / 2 + 1.0, (by + ry) / 2 + 2.0, d["ear_t"] / 2), True)
    assert_material(part, probes)
    return rep


def check_lid(part: Part, d: dict | None = None) -> dict:
    d = d or derive()
    single_solid(part)
    assert part.is_valid, "lid: invalid solid"
    bb = part.bounding_box()
    assert abs(bb.size.X - d["W"]) < 0.05 and abs(bb.size.Y - d["H"]) < 0.05 and abs(bb.size.Z - d["lid_t"]) < 0.05, f"lid {bb.size}"
    o = d["print_orientation"]["lid"]
    check_declared_orientation(part, o)
    printed = to_print_orientation(part, o)
    rep = check_overhang(printed, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"]))
    x, y = d["columns"][0]
    assert_material(part, {"lid screw hole": ((x, y, d["D"] + d["lid_t"] / 2), False),
                           "lid plate": ((0.0, d["H"] / 2, d["D"] + d["lid_t"] / 2), True)})
    return rep


def check_assembly(body: Part, lid: Part, hw: dict, d: dict | None = None) -> list[str]:
    """Every bought part clear of both printed parts and of each other where it must be. Returns failures."""
    d = d or derive()
    fails = []

    def clear(a, b, what, tol=1e-6):
        v = interference_volume(a, b)
        if v > tol:
            fails.append(f"{what}: {v:.3f} mm^3")

    clear(body, lid, "body vs lid")
    for name, env in hw.items():
        clear(body, env, f"body vs {name}")
        clear(lid, env, f"lid vs {name}")
    clear(hw["reach"], hw["boards"], "plug reach vs boards")
    clear(hw["jack"], hw["boards"], "jack vs boards")
    clear(hw["jack"], hw["tops"], "jack vs board tops")
    clear(hw["screws"], hw["boards"], "M2 screws vs boards")
    clear(hw["screws"], hw["nuts"], "M2 screws vs nuts (bore)")
    clear(hw["lid_screws"], hw["lid_nuts"], "M3 screws vs nuts (bore)")
    # the lid closes every notch: lid material directly over each notch
    for n in d["notch_list"]:
        if interference_volume(lid, box(n["x"] - 1, n["x"] + 1, 0.0, d["wall"], d["D"], d["D"] + 0.5)) < 1e-6:
            fails.append(f"lid does not cover notch {n['name']}")
    return fails


def print_set(body: Part, lid: Part, plate: Part, d: dict | None = None) -> dict[str, Part]:
    """The three prints in their print orientation, side by side on the bed."""
    d = d or derive()
    ew, _ = d["ear_size"]
    gap = 8.0
    lid_f = to_print_orientation(lid, d["print_orientation"]["lid"])   # the flip mirrors y: place by bounding box
    lb, pb = lid_f.bounding_box(), plate.bounding_box()
    lid_p = lid_f.moved(Location((-lb.center().X, d["H"] + gap - lb.min.Y, -lb.min.Z)))
    plate_p = plate.moved(Location((-pb.center().X, -gap - pb.max.Y, -pb.min.Z)))
    parts = {"L1_body": body, "L1_lid": lid_p, "ANALOG_NODE_plate": plate_p}
    names = list(parts)
    for i in range(len(names)):   # nothing overlaps on the bed, and everything fits on it
        for j in range(i + 1, len(names)):
            a, b = parts[names[i]].bounding_box(), parts[names[j]].bounding_box()
            assert a.max.Y + 1e-6 < b.min.Y or b.max.Y + 1e-6 < a.min.Y, f"print set: {names[i]} overlaps {names[j]}"
    allbb = Compound(children=list(parts.values())).bounding_box()
    assert allbb.size.X <= d["bed"][0] and allbb.size.Y <= d["bed"][1] and abs(allbb.min.Z) < 1e-6, f"print set {allbb.size}"
    return parts


if __name__ == "__main__":
    from build123d import export_step

    from cacad import export, export_3mf
    from projects.standoff_plate.plate import build_plate, check_plate

    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys (F23)
    d = derive()
    body, lid = build_body(d), build_lid(d)
    rb, rl = check_body(body, d), check_lid(lid, d)
    hw = build_hardware(d)
    fails = check_assembly(body, lid, hw, d)
    assert not fails, "assembly: " + "; ".join(fails)
    plate = build_plate("ANALOG_NODE")
    check_plate("ANALOG_NODE", plate)
    for name, p in (("body", body), ("lid", lid)):
        bb = p.bounding_box().size
        print(f"L1 {name}: {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f}, {p.volume / 1000:.1f} cm3, valid {p.is_valid}")
    print(f"  body worst overhang {rb['worst_ok']:.0f} deg, declared ceilings found {len(rb['exceptions_found'])}; "
          f"lid worst {rl['worst_ok']:.0f} deg; assembly clear ({len(hw)} envelope groups)")
    bb = plate.bounding_box().size
    print(f"ANALOG_NODE plate: {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f}, {plate.volume / 1000:.1f} cm3")
    export(body, "L1_body", OUT)
    export(lid, "L1_lid", OUT)
    export(plate, "ANALOG_NODE_plate", OUT)
    export_3mf(print_set(body, lid, plate, d), OUT + "/L1_print_set.3mf")
    # one STEP per envelope group, and the plate's boards and screws, for lean_view.py (FreeCAD). Before the
    # assemblies below: Compound(children=...) re-parents these compounds, and build123d then refuses to write them alone
    for k, v in hw.items():
        export_step(v, OUT + f"/L1_hw_{k}.step")
    from projects.standoff_plate.plate import build_hardware as plate_hardware
    phw = plate_hardware("ANALOG_NODE")
    for k in ("boards", "screws", "nuts", "mount_screws"):
        export_step(phw[k], OUT + f"/ANALOG_NODE_{k}.step")
    # the assembly as it hangs: box, lid, boards and hardware; the analog plate beside it on the same wall
    ew, _ = d["ear_size"]
    pbb = plate.bounding_box()
    plate_on_wall = plate.moved(Location((d["W"] / 2 + ew + 15.0 - pbb.min.X, d["H"] - pbb.max.Y, 0)))
    export_step(Compound(children=[body, lid, plate_on_wall, *[v for v in hw.values()]]), OUT + "/L1_assembly.step")
    export_step(Compound(children=[body, *[hw[k] for k in ("boards", "tops", "plugs", "screws", "jack", "mounts")]]),
                OUT + "/L1_open.step")
    result = body
