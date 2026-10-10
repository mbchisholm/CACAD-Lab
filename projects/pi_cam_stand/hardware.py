"""Bought parts placed in the stand frame: the Pi 4B and Camera Module 2 (camera_reader's solids from the vendor
drawings), the fasteners, and the camera's view pyramid the assembly checks against. Every number is from
params.derive. The camera, its screws and nuts and its view move with the carrier (`carrier_location`).
"""
from __future__ import annotations

from build123d import Compound, Location, Part, Plane, Pos

from projects.camera_reader.hardware import build_cam_local, build_pi4b_local
from projects.camera_reader.params import PARTS as CR_PARTS
from projects.pi_cam_stand.carrier import carrier_location
from projects.pi_cam_stand.geom import cyl, cyl_x, hex_prism, hex_x, view_pyramid
from projects.pi_cam_stand.params import derive


def _hex_r(s: float) -> float:
    return s / (2 * 0.8660254037844386)


def _screw_z(scr, x, y, z_head_face, L, down: bool) -> Part:
    s = -1 if down else 1
    head = cyl(x, y, scr["head_dk"] / 2, *sorted((z_head_face, z_head_face - s * scr["head_k"])))
    return head + cyl(x, y, scr["d"] / 2, *sorted((z_head_face, z_head_face + s * L)))


def _nut_z(scr, x, y, z0) -> Part:
    return hex_prism(x, y, _hex_r(scr["nut_s"]), z0, z0 + scr["nut_m"]) - cyl(x, y, scr["d"] / 2, z0 - 1, z0 + scr["nut_m"] + 1)


def cam_local_location(d: dict) -> Location:
    """Camera drawing frame -> carrier print frame: drawing x runs down the plate from its top edge, drawing y along
    +x, the PCB back on the bosses, lens toward +z."""
    w = d["cam"]["size"][1]
    return Location(Plane(origin=(-w / 2, d["y_cam_top"], d["z_cam_back"]), x_dir=(0, -1, 0), z_dir=(0, 0, 1)))


def build_camera_unit(d: dict) -> dict:
    """Camera, its screws and nuts, and its view, in the carrier's print frame."""
    m2 = d["screws"]["M2"]
    z_front = d["z_cam_back"] + CR_PARTS["cam_v2"]["pcb_t"]
    screws = [_screw_z(m2, x, y, z_front, d["cam_screw"], True) for x, y in d["cam_holes_c"]]
    nuts = [_nut_z(m2, x, y, d["cam_pocket"]["depth"] - m2["nut_m"]) for x, y in d["cam_holes_c"]]
    lx, ly, lz = d["lens_c"]
    # print x is -X in the stand, and the image's long side runs along X
    return dict(camera=cam_local_location(d) * build_cam_local(), cam_screws=Compound(children=screws),
                cam_nuts=Compound(children=nuts), view=view_pyramid((lx, ly, lz), d["cam"]["fov"], d["view_len"]))


def build_hardware(size: str = "V0", tilt: float = 0.0) -> dict:
    d = derive(size)
    hw = {}
    hw["pi4b"] = Pos(d["pi_x0"], d["pi_y0"], d["z_pi_bot"]) * build_pi4b_local()
    m25, m3 = d["screws"]["M2_5"], d["screws"]["M3"]
    hw["pi_screws"] = Compound(children=[_screw_z(m25, x, y, d["z_pi_top"], d["pi_screw"], True) for x, y in d["pi_holes"]])
    hw["pi_nuts"] = Compound(children=[_nut_z(m25, x, y, d["pi_pocket"]["depth"] - m25["nut_m"]) for x, y in d["pi_holes"]])
    xo, hz = d["side_x"][1], d["hinge_z"]
    hw["hinge_screw"] = cyl_x(0, hz, m3["head_dk"] / 2, -xo - m3["head_k"], -xo) + cyl_x(0, hz, m3["d"] / 2, -xo, -xo + d["hinge_screw"])
    xn = xo - d["hinge_pocket"]["depth"]
    hw["hinge_nut"] = hex_x(0, hz, _hex_r(m3["nut_s"]), xn, xn + m3["nut_m"]) - cyl_x(0, hz, m3["d"] / 2, xn - 1, xn + m3["nut_m"] + 1)
    loc = carrier_location(d, tilt)
    for k, v in build_camera_unit(d).items():
        hw[k] = loc * v
    return hw
