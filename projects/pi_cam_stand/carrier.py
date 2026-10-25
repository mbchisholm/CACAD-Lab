"""Camera carrier: a plate the Camera Module 2 screws to by its four holes, on bosses that hold its back-side connector
off the plate, M2 nuts captured in pockets in the plate's back. A knuckle on the plate's bottom edge sits between the
stand's side walls on the M3 hinge bolt; tightening the bolt clamps it. The camera's connector edge faces the knuckle
and the ribbon turns back through a slot just under it.

Built in its print frame: back face on the bed at z = 0, +z forward (toward what the camera sees), +y up the plate,
the hinge axis along x at (y, z) = (0, knuckle_y / 2). `carrier_location(tilt)` places it in the stand's frame.

    .venv/bin/python projects/pi_cam_stand/carrier.py
"""
from __future__ import annotations

from build123d import Location, Part, Plane, Pos, Rot

from projects.pi_cam_stand.geom import box, cyl, hex_prism, teardrop_x
from projects.pi_cam_stand.params import derive


def build_carrier(size: str = "V0") -> Part:
    d = derive(size)
    hw, ky, kz = d["w_k"] / 2, *d["knuckle"]
    px, t = d["plate_x"], d["plate_t"]
    part = box(-hw, hw, -kz / 2, kz / 2, 0, ky)                        # knuckle
    part += box(-hw, hw, kz / 2, d["y_plate0"], 0, t)                  # neck up to the plate
    part += box(-px, px, d["y_plate0"], d["y_plate1"], 0, t)
    for x, y in d["cam_holes_c"]:
        part += cyl(x, y, d["cam_boss_r"], t, d["z_cam_back"])
        part -= cyl(x, y, d["cam_bore"] / 2, -1, d["z_cam_back"] + 1)
        part -= hex_prism(x, y, d["cam_pocket"]["r"], -1, d["cam_pocket"]["depth"])
    (sx0, sx1), (sy0, sy1) = d["slot_c"]
    part -= box(sx0, sx1, sy0, sy1, -1, t + 1)
    part -= teardrop_x(0, d["k_axis_z"], d["hinge_bore"] / 2, -hw - 1, hw + 1)
    return part


def carrier_location(d: dict, tilt: float = 0.0) -> Location:
    """Print frame -> stand frame at `tilt` degrees about the hinge axis (negative looks down). Print x -> -X,
    y -> +Z, z -> +Y, the hinge axis onto (y, z) = (0, hinge_z)."""
    hz = d["hinge_z"]
    place = Location(Plane(origin=(0, -d["k_axis_z"], hz), x_dir=(-1, 0, 0), z_dir=(0, 1, 0)))
    return Pos(0, 0, hz) * Rot(tilt, 0, 0) * Pos(0, 0, -hz) * place


def check_carrier(part: Part, size: str = "V0") -> None:
    d = derive(size)
    assert part.is_valid and len(part.solids()) == 1, "carrier must be one valid solid"
    bb = part.bounding_box()
    for got, want in ((bb.min.Z, 0.0), (bb.max.Z, d["z_cam_back"]), (bb.min.Y, -d["knuckle"][1] / 2),
                      (bb.max.Y, d["y_plate1"]), (bb.max.X, d["plate_x"])):
        assert abs(got - want) < 1e-3, f"carrier bbox {got:.3f} != {want:.3f}"


if __name__ == "__main__":
    from cacad import export
    p = build_carrier()
    check_carrier(p)
    print("carrier", [round(v, 2) for v in p.bounding_box().size], "volume", round(p.volume / 1000, 1), "cm3")
    export(p, "carrier", __file__.rsplit("/", 1)[0] + "/out")
