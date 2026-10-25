"""Stand: the base plate with the Pi's four bosses (M2.5 nuts captured from underneath), and the U column behind the
Pi's GPIO edge. The column's side walls are the hinge cheeks: an M3 bolt goes through both and the carrier's knuckle
between them, head on the -X wall, nut in a pocket in the +X wall. Behind the hinge axis the walls stop at the web's
top, so the carrier plate swings back past them. A window through the web just above the GPIO header lets the ribbon
into the column. Prints upright, base on the bed; the hinge bore is a teardrop.

    .venv/bin/python projects/pi_cam_stand/stand.py
"""
from __future__ import annotations

from build123d import Part

from projects.pi_cam_stand.geom import box, cyl, hex_prism, hex_x, teardrop_x
from projects.pi_cam_stand.params import derive


def build_stand(size: str = "V0") -> Part:
    d = derive(size)
    (bx0, bx1), (by0, by1) = d["base_x"], d["base_y"]
    part = box(bx0, bx1, by0, by1, 0, d["base_t"])
    for x, y in d["pi_holes"]:
        part += cyl(x, y, d["pi_boss_r"], d["base_t"], d["z_pi_bot"])
    xi, xo = d["side_x"]
    hz, cr = d["hinge_z"], d["cheek_r"]
    for sx in (-1, 1):
        lo, hi = sorted((sx * xi, sx * xo))
        part += box(lo, hi, d["y_wb"], cr, 0, d["z_web_top"])          # wall, full depth up to the web's top
        part += box(lo, hi, -cr, cr, d["z_web_top"], d["z_col_top"])   # cheek round the hinge axis
    part += box(-xo, xo, d["y_wb"], d["y_wf"], 0, d["z_web_top"])
    # holes
    for x, y in d["pi_holes"]:
        part -= cyl(x, y, d["pi_bore"] / 2, -1, d["z_pi_bot"] + 1)
        part -= hex_prism(x, y, d["pi_pocket"]["r"], -1, d["pi_pocket"]["depth"])
    for x, y in d["fix_xy"]:
        part -= cyl(x, y, d["fix_bore"] / 2, -1, d["base_t"] + 1)
    part -= box(-xi, xi, d["y_wb"] - 1, d["y_wf"] + 1, *d["window_z"])
    part -= teardrop_x(0, hz, d["hinge_bore"] / 2, -xo - 1, xo + 1)
    part -= hex_x(0, hz, d["hinge_pocket"]["r"], xo - d["hinge_pocket"]["depth"], xo + 1)
    return part


def check_stand(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "stand must be one valid solid"
    bb = part.bounding_box()
    (bx0, bx1), (by0, by1) = d["base_x"], d["base_y"]
    for got, want in ((bb.min.X, bx0), (bb.max.X, bx1), (bb.min.Y, by0), (bb.max.Y, by1), (bb.min.Z, 0.0),
                      (bb.max.Z, d["z_col_top"])):
        assert abs(got - want) < 1e-3, f"stand bbox {got:.3f} != {want:.3f}"


if __name__ == "__main__":
    from cacad import export
    p = build_stand()
    check_stand(p)
    print("stand", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "stand", __file__.rsplit("/", 1)[0] + "/out")
