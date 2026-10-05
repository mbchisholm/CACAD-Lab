"""Nutrient controller B1 body: back plate, four walls, open front. Board bosses
(nut pockets from the back face, heat-set inserts for the carrier), rest pads,
corner insert columns for the cover, three keyholes, the bottom-wall entries
(two glands, DC jack, USB-C), the pump's motor hole, flange slots and sliding
nut channels on the -Y wall. Box frame and every number from params.derive.
Prints on its back face; holes through the walls are truncated teardrops.

    .venv/bin/python projects/nutrient_controller/body.py
"""
from __future__ import annotations

from build123d import Axis, Part, Plane, Polygon, extrude, fillet

from cacad import export, single_solid
from projects.nutrient_controller.geom import box, cyl, hex_prism, slot_teardrop, teardrop
from projects.nutrient_controller.params import ACTIVE_SIZES, derive


def build_body(size: str = "B1") -> Part:
    d = derive(size)
    W, H, D, w, bt = d["W"], d["H"], d["D"], d["wall"], d["back_t"]
    (yi0, yi1), (zi0, zi1) = d["inner_y"], d["inner_z"]
    body = box(0, D, -W / 2, W / 2, 0, H)
    try:
        body = fillet(body.edges().filter_by(Axis.X), d["corner_r"])
    except Exception:
        pass
    body -= box(bt, D + 1, yi0, yi1, zi0, zi1)

    # cover insert columns in the four inner corners, insert bores from the rim
    for y, z in d["cover_screw_pts"]:
        body += cyl(d["insert_boss_od"], "x", ((bt + D) / 2, y, z), D - bt)
    # board bosses and rest pads
    for b in d["bosses"]:
        y, z = b["at"]
        body += cyl(b["od"], "x", (bt + b["h"] / 2, y, z), b["h"])
    for p in d["rest_pads"]:
        y, z = p["at"]
        body += cyl(d["rest_pad_d"], "x", (bt + p["h"] / 2, y, z), p["h"])

    # pump: nut-channel blocks on the -Y wall's inner face, 45 deg underside (print up = +x)
    px, pz = d["pump_xz"]
    nut = d["screws"]["M3"]
    ch_s, ch_t = d["nut_channel_s"], nut["nut_m"] + 0.4
    blk_t = ch_t + d["min_wall"] + 0.4
    x_low = px - d["pump_slot"] - ch_s / 2 - d["min_wall"]
    for zc in d["pump_hole_z"]:
        hz = ch_s / 2 + d["min_wall"]
        prof = Plane.XY.offset(zc - hz) * Polygon((D, yi0), (D, yi0 + blk_t), (x_low, yi0 + blk_t), (x_low - blk_t, yi0), align=None)
        body += extrude(prof, amount=2 * hz)

    cuts = []
    for y, z in d["cover_screw_pts"]:
        cuts.append(cyl(4.0, "x", (D - d["insert_depth"] / 2, y, z), d["insert_depth"] + 0.01))   # INSERT_BORE_M3
    for b in d["bosses"]:
        y, z = b["at"]
        top = bt + b["h"]
        if b["insert"]:
            cuts.append(cyl(4.0, "x", (top - d["insert_depth"] / 2, y, z), d["insert_depth"] + 0.01))
        else:
            cuts.append(cyl(b["bore"], "x", (top / 2, y, z), top + 0.02))
            cuts.append(hex_prism(b["pocket"]["s"], "x", (b["pocket"]["depth"] / 2 - 0.01, y, z), b["pocket"]["depth"] + 0.02, "z"))
    # keyholes: big hole below, slot up to the rest position
    for y, z in d["keyholes"]:
        cuts.append(cyl(d["keyhole_big"], "x", (bt / 2, y, z - d["slide"]), bt + 0.02))
        cuts.append(box(-0.01, bt + 0.01, y - d["keyhole_slot"] / 2, y + d["keyhole_slot"] / 2, z - d["slide"], z))
        cuts.append(cyl(d["keyhole_slot"], "x", (bt / 2, y, z), bt + 0.02))
    # bottom wall: glands, jack (truncated teardrops), USB-C opening
    cap = d["teardrop_cap"]
    for k in ("gland_tds", "gland_ds"):
        y, x = d[f"{k}_yx"]
        cuts.append(teardrop(d["gland_holes"][k], "z", (x, y, w / 2), w + 0.02, "x", cap))
    y, x = d["jack_yx"]
    cuts.append(teardrop(d["jack_hole"], "z", (x, y, w / 2), w + 0.02, "x", cap))
    uy, ux = d["usb_opening"]
    cuts.append(box(d["usb_x"] - ux / 2, d["usb_x"] + ux / 2, d["xiao"]["y"] - uy / 2, d["xiao"]["y"] + uy / 2, -0.01, w + 0.01))
    # pump: motor hole and flange slots through the -Y wall, channels open to the rim
    cuts.append(teardrop(d["motor_hole"], "y", (px, -W / 2 + w / 2, pz), w + 0.02, "x", cap))
    for zc in d["pump_hole_z"]:
        cuts.append(slot_teardrop(d["pump_slot_w"], d["pump_slot"], "y", (px, -W / 2 + (w + blk_t) / 2, zc), w + blk_t + 0.02, "x"))
        cuts.append(box(px - d["pump_slot"] - ch_s * 0.58, D + 1, yi0 - 0.01, yi0 + ch_t, zc - ch_s / 2, zc + ch_s / 2))
    for c in cuts:
        body -= c
    return body


def check_body(part: Part, size: str = "B1") -> dict:
    from cacad import assert_bbox, assert_material
    from cacad.checks.orientation import check_declared_orientation
    from cacad.checks.overhang import check_overhang
    d = derive(size)
    single_solid(part)
    assert part.is_valid, "body: invalid solid"
    assert_bbox(part, (d["D"], d["W"], d["H"]), 0.0, 0.05, "body")   # x0 = 0 is the bed face, checked below
    printed = part.rotate(Axis.Y, -90)                                 # +x -> +z: the print orientation
    o = dict(d["print_orientation"]["body"], up=(0, 0, 1), bed_z=0.0)
    check_declared_orientation(printed, o)
    rep = check_overhang(printed, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"],
                                       exceptions=d["body_overhang_exceptions"]))
    # material probes: back plate solid between bosses, a gland hole open, a keyhole slot open, motor hole open
    gy, gx = d["gland_tds_yx"]
    ky, kz = d["keyholes"][0]
    assert_material(part, {
        "back plate": ((d["back_t"] / 2, -5.0, 120.0), True),
        "TDS gland hole": ((gx, gy, d["wall"] / 2), False),
        "keyhole slot": ((d["back_t"] / 2, ky, kz - d["slide"] / 2), False),
        "motor hole": ((d["pump_xz"][0], -d["W"] / 2 + d["wall"] / 2, d["pump_xz"][1]), False),
        "cover insert bore": ((d["D"] - 1.0, *d["cover_screw_pts"][0]), False),
    })
    return rep


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        b = build_body(size)
        rep = check_body(b, size)
        bb = b.bounding_box()
        print(f"body {size}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {b.volume / 1000:.1f} cm3, "
              f"worst overhang {rep['worst_ok']:.0f} deg, exceptions {len(rep['exceptions_found'])}")
        export(b, f"{size}_body", out)
    result = b
