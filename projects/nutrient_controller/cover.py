"""Nutrient controller B1 front cover: a plate over the body's open front with
a drip skirt around the body's outer edge. OLED window and four bosses
(trimmed flat towards the glass), three PV0 button holes, the CR-174 LED hole,
four M3 holes to the body's inserts. Box frame; every number from
params.derive. Prints face down: no overhangs.

    .venv/bin/python projects/nutrient_controller/cover.py
"""
from __future__ import annotations

from build123d import Axis, Location, Part, fillet

from cacad import export, single_solid
from cacad.registries.materials import clearance_bore
from projects.nutrient_controller.geom import box, cyl
from projects.nutrient_controller.params import ACTIVE_SIZES, derive


def _rounded(p: Part, r: float) -> Part:
    """Round the edges parallel to x (the outline seen from the front)."""
    return fillet(p.edges().filter_by(Axis.X), r)


def build_cover(size: str = "B1") -> Part:
    d = derive(size)
    W, H, D, t, sk = d["W"], d["H"], d["D"], d["cover_t"], d["skirt"]
    cw, ch = d["cover_outer"]
    fc = d["fit_clear"]
    cover = _rounded(box(D - sk, D + t, -cw / 2, cw / 2, H / 2 - ch / 2, H / 2 + ch / 2), d["corner_r"] + (cw - W) / 2)
    # skirt opening: the body's outline grown by the fit clearance, its corner radius grown with it
    cover -= _rounded(box(D - sk - 1, D, -W / 2 - fc, W / 2 + fc, -fc, H + fc), d["corner_r"] + fc)
    # OLED bosses, trimmed flat towards the glass
    P = d["parts"]["oled"]
    gy, gz = d["oled_yz"][0] + P["glass_off"][0], d["oled_yz"][1] + P["glass_off"][1]
    gh = P["glass"][1] / 2 + d["oled_boss_flat"]
    h = d["oled_boss_h"]
    for y, z in d["oled_holes"]:
        boss = cyl(d["oled_boss_od"], "x", (D - h / 2, y, z), h)
        boss -= box(D - h - 1, D + 0.01, y - 5, y + 5, gz - gh, gz + gh)
        cover += boss
    cuts = []
    wy, wz = d["oled_window"]
    cy, cz = d["oled_window_c"]
    cuts.append(box(D - 1, D + t + 1, cy - wy / 2, cy + wy / 2, cz - wz / 2, cz + wz / 2))
    for y, z in d["oled_holes"]:
        cuts.append(cyl(d["boards"]["ads"]["bore"], "x", (D + (t - h) / 2, y, z), t + h + 0.02))
    for y, z in d["buttons_yz"]:
        cuts.append(cyl(d["button_hole"], "x", (D + t / 2, y, z), t + 0.02))
    ly, lz = d["led_yz"]
    cuts.append(cyl(d["led_hole"], "x", (D + t / 2, ly, lz), t + 0.02))
    for y, z in d["cover_screw_pts"]:
        cuts.append(cyl(clearance_bore("M3"), "x", (D + t / 2, y, z), t + 0.02))
    for c in cuts:
        cover -= c
    return cover


def check_cover(part: Part, size: str = "B1") -> dict:
    from cacad import assert_material
    from cacad.checks.orientation import check_declared_orientation
    from cacad.checks.overhang import check_overhang
    d = derive(size)
    single_solid(part)
    assert part.is_valid, "cover: invalid solid"
    bb = part.bounding_box()
    cw, ch = d["cover_outer"]
    assert abs(bb.size.Y - cw) < 0.05 and abs(bb.size.Z - ch) < 0.05, f"cover outline {bb.size}"
    assert abs(bb.size.X - (d["cover_t"] + max(d["skirt"], d["oled_boss_h"]))) < 0.05, f"cover depth {bb.size.X}"
    printed = part.rotate(Axis.Y, 90).moved(Location((0, 0, d["D"] + d["cover_t"])))
    o = dict(d["print_orientation"]["cover"], up=(0, 0, 1), bed_z=0.0)
    check_declared_orientation(printed, o)
    rep = check_overhang(printed, dict(up=(0, 0, 1), bed_z=0.0, max_deg=45.0, nozzle_d=d["nozzle_d"]))
    cy, cz = d["oled_window_c"]
    by, bz = d["buttons_yz"][0]
    assert_material(part, {
        "OLED window": ((d["D"] + d["cover_t"] / 2, cy, cz), False),
        "button hole": ((d["D"] + d["cover_t"] / 2, by, bz), False),
        "plate": ((d["D"] + d["cover_t"] / 2, 0.0, 40.0), True),
        "skirt": ((d["D"] - d["skirt"] / 2, d["W"] / 2 + d["fit_clear"] + 0.8, 75.0), True),
        "skirt clear of body": ((d["D"] - d["skirt"] / 2, d["W"] / 2 + d["fit_clear"] / 2, 75.0), False),
    })
    return rep


if __name__ == "__main__":
    out = __file__.rsplit("/", 1)[0] + "/out"
    for size in ACTIVE_SIZES:
        c = build_cover(size)
        rep = check_cover(c, size)
        bb = c.bounding_box()
        print(f"cover {size}: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}, {c.volume / 1000:.1f} cm3, "
              f"worst overhang {rep['worst_ok']:.0f} deg")
        export(c, f"{size}_cover", out)
    result = c
