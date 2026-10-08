"""Snout: a collar that slides over the stand's camera rim and stops on it,
then a tapered tunnel with three 45 deg light-trap baffles to a flange that
bolts to the cell box's front wall (4x M3 + nut). Prints flange down.

    .venv/bin/python projects/camera_reader/snout.py
"""
from __future__ import annotations

from build123d import Part

from projects.camera_reader.geom import box, cyl_y, loft_y, prism_y
from projects.camera_reader.params import derive


def build_snout(size: str = "V0") -> Part:
    d = derive(size)
    s, LX, LZ = d["snout"], d["lens"][0], d["lens"][2]
    nx, nz = s["near_c"]
    y0, ys, yf = s["y_collar"], s["y_stop"], s["y_far"]
    yb = yf + d["flange_t"]
    part = prism_y(y0, ys, nx, nz, *s["collar_out"])
    part += loft_y(ys, (nx, nz, *s["collar_out"]), yf, (LX, LZ, *s["far_out"]))
    part += prism_y(yf, yb, LX, LZ, *s["flange"])
    part -= prism_y(y0 - 1, ys, nx, nz, *s["collar_in"])                 # collar bore; its end is the stop face
    part -= loft_y(ys, (nx, nz, *s["near_in"]), yf, (LX, LZ, *s["far_in"]))
    part -= prism_y(yf - 0.01, yb + 1, LX, LZ, *s["far_in"])
    # Ribbon notch in the collar floor, open at the collar's end
    nw, nd = d["ribbon_notch"]
    cz0 = nz - s["collar_out"][1] / 2
    part -= box(nx - nw / 2, nx + nw / 2, y0 - 1, y0 + nd, cz0 - 1, nz - s["collar_in"][1] / 2 + 0.01)
    # Baffles: aperture at y, opening at 45 deg to the tunnel wall towards +Y (the bed side when printed)
    for y, (ax, az) in zip(s["baffles"], d["baffle_ap"]):
        cx, cz, tw, th = d["tunnel_in"](y)
        depth = max((tw - ax) / 2, (cz + th / 2) - (LZ + az / 2), (LZ - az / 2) - (cz - th / 2))
        ye = y + depth
        ring = loft_y(y, (cx, cz, tw + 0.02, th + 0.02), ye, d["tunnel_in"](ye)[:2] + tuple(
            v + 0.02 for v in d["tunnel_in"](ye)[2:]))
        cx2, cz2, tw2, th2 = d["tunnel_in"](ye)
        ring -= loft_y(y - 0.01, (LX, LZ, ax, az), ye + 0.01, (cx2, cz2, tw2 + 0.2, th2 + 0.2))
        part += ring
    for hx, hz in d["flange_holes"]:
        part -= cyl_y(d["m3_bore"], hx, hz, yf - 1, yb + 1)
    return part


def check_snout(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "snout must be one valid solid"
    bb = part.bounding_box()
    s = d["snout"]
    assert abs(bb.min.Y - s["y_collar"]) < 1e-3 and abs(bb.max.Y - (s["y_far"] + d["flange_t"])) < 1e-3


if __name__ == "__main__":
    from cacad import export
    p = build_snout()
    check_snout(p)
    bb = p.bounding_box()
    print("snout", [round(v, 2) for v in bb.size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "snout", __file__.rsplit("/", 1)[0] + "/out")
