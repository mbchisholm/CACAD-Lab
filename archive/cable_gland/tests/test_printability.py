"""FDM manufacturability checks: printable feature sizes, declared print
orientation, internal-thread overhang, collet finger strain."""
import math

import pytest
from build123d import GeomType, Vector

import params
from cacad import is_inside, max_overhang_deg, min_ring_wall, planar_faces_with_normal


# --- minimum printable feature -------------------------------------------

def test_every_wall_at_least_two_nozzles(size, d):
    for name, w in d["walls"].items():
        assert w >= d["min_printable_wall"], f"{name} = {w:.2f} < 2 x {d['nozzle_d']} nozzle"


def test_slot_width_at_least_one_nozzle(size, d):
    assert d["slot_width"] >= d["min_slot_width"]


def test_measured_walls_on_geometry(size, d, body, collet, nut, inserts):
    """Cross-sections of the real solids, not the params table."""
    lim = max(d["min_printable_wall"], d["min_wall"])
    z_taper_top = d["seat_depth"] + d["collet_cyl_len"] + d["collet_taper_len"]
    for i, ins in inserts.items():
        w = min_ring_wall(ins, d["insert_len"] / 2)
        assert w >= d["min_printable_wall"], f"insert ID{i}: measured wall {w:.2f} < 2 x nozzle"
    probes = {
        "body @ panel thread": (body, -d["panel_thread_len"] / 2),
        "body @ collet seat": (body, d["neck_top_z"] - d["seat_depth"] / 2),
        "collet @ finger root": (collet, d["collet_base_ring_h"] + 0.5),
        "collet @ near tip": (collet, z_taper_top - d["chamfer_edge"] - 0.1),
        "nut @ thread": (nut, d["nut_thread_len"] / 2),
        "nut @ cone": (nut, d["nut_hex_h"] + d["cone_h"] / 2),
    }
    for name, (part, z) in probes.items():
        w = min_ring_wall(part, z)
        assert w >= lim, f"{name}: measured wall {w:.2f} < {lim}"


# --- declared print orientation ------------------------------------------

@pytest.mark.parametrize("part_name", ["body", "nut", "collet", "insert"])
def test_print_orientation_declared_and_bed_face_exists(size, d, part_name, body, nut, collet, inserts):
    o = d["print_orientation"][part_name]
    up = Vector(o["up"])
    assert abs(up.length - 1) < 1e-9, "up must be a unit vector"
    part = dict(body=body, nut=nut, collet=collet, insert=inserts[d["insert_ids"][0]])[part_name]
    bed = planar_faces_with_normal(part, -up, o["bed_z"])
    assert bed, f"{part_name}: declared bed face '{o['bed_face']}' not found at z={o['bed_z']}"
    assert isinstance(o["known_overhangs"], list)


# --- internal thread overhang ----------------------------------------------

def test_internal_thread_overhang_in_declared_orientation(size, d, nut):
    o = d["print_orientation"]["nut"]
    # only faces exposed inside the bore count; the thread solid's outer band
    # (nut_bore_r .. +thread_interference) is buried in the nut wall
    r_lim = d["nut_bore_r"] + 0.01
    z0, z1 = 0.0, d["nut_thread_len"] + d["pitch"]

    first_layer = d["nozzle_d"] / 2   # faces that never rise above the first layer sit on the bed

    def is_thread_face(f):
        bb = f.bounding_box()
        if bb.min.Z < z0 - 0.01 or bb.max.Z > z1 + 0.01:
            return False
        if bb.max.Z <= first_layer:
            return False
        if f.geom_type == GeomType.PLANE:
            return False
        rs = [(v.X**2 + v.Y**2) ** 0.5 for v in f.vertices()]
        return bool(rs) and max(rs) <= r_lim

    faces = nut.faces().filter_by(is_thread_face)
    assert faces, "no internal thread faces found"
    # sliver remnants of the thread/bore fuse (< one nozzle^2) are below what a slicer resolves
    sliver_area = d["nozzle_d"] ** 2
    slivers = [f for f in faces if f.area < sliver_area]
    real = [f for f in faces if f.area >= sliver_area]
    worst, face = max_overhang_deg(real, o["up"])
    bb = face.bounding_box()
    print(f"\n{size} internal thread: max overhang {worst:.1f} deg from vertical "
          f"({face.geom_type.name} face, z {bb.min.Z:.2f}..{bb.max.Z:.2f}, span {bb.max.Z - bb.min.Z:.2f} mm); "
          f"{len(slivers)} sliver faces < {sliver_area} mm2 ignored (max {max((f.area for f in slivers), default=0):.3f} mm2)")
    assert worst <= d["max_overhang_deg"] + 0.5, f"thread overhang {worst:.1f} > {d['max_overhang_deg']}"
    # the reason 60 deg is acceptable: every flank is shorter than one pitch
    assert bb.max.Z - bb.min.Z <= 2 * d["pitch"]


# --- collet finger deflection ----------------------------------------------

def test_collet_finger_ratio_documented_and_within_material(size, d, collet):
    f = d["collet_finger"]
    # geometry matches the model's assumptions: slots stop at the base ring top
    # slots stop at the base ring top (slot floors + insert ledge merge into one coplanar face)
    assert planar_faces_with_normal(collet, Vector(0, 0, 1), d["collet_base_ring_h"]), "slot floors not where the cantilever model assumes"
    r_slot = (d["collet_base_od"] + d["collet_finger_bore_d"]) / 4
    assert is_inside(collet, (r_slot, 0, d["collet_base_ring_h"] - 0.2)) and not is_inside(collet, (r_slot, 0, d["collet_base_ring_h"] + 0.2))
    assert abs(f["length"] - (d["collet_h"] - d["collet_base_ring_h"])) < 1e-9
    assert abs(f["tip_deflection"] - d["nut_travel"] * math.tan(math.radians(d["taper_deg"]))) < 1e-9
    print(f"\n{size} collet finger: L={f['length']:.2f} t={f['root_thickness']:.2f} "
          f"delta={f['tip_deflection']:.3f} delta/t={f['deflection_to_thickness']:.3f} "
          f"root strain={f['root_strain']:.2%} vs {f['material']} bulk {f['material_max_strain']:.1%}, "
          f"across layers ~{f['material_max_strain_across_layers']:.1%} (x{d['layer_adhesion_factor']})")
    assert f["root_strain"] <= f["material_max_strain"]
    if f["root_strain"] > f["material_max_strain_across_layers"]:
        print(f"  NOTE: above the across-layer estimate; the printed coupon decides this")


# --- body exterior overhang in the declared (neck-down) orientation -----------

def test_body_overhang_in_declared_orientation(size, d, body):
    """Every exposed downward face of the body, in print orientation, is within
    max_overhang_deg - except the declared exceptions (seat floor), which must
    be the only faces that exceed it."""
    o = d["print_orientation"]["body"]
    up = Vector(o["up"])
    first_layer = d["nozzle_d"] / 2
    ti = d["thread_interference"]
    buried = [(d["panel_core_r"] - ti, d["panel_core_r"], -d["panel_thread_len"], d["flange_h"]),
              (d["neck_core_r"] - ti, d["neck_core_r"], d["hex_top_z"], d["neck_top_z"])]
    bed_z = o["bed_z"]

    def exposed(f):
        if f.area < d["sliver_area"]:
            return False
        bb = f.bounding_box()
        # on the bed: never rises above the first layer, measured along `up`
        top = max((v.Z - bed_z) * up.Z for v in (bb.min, bb.max))
        if top <= first_layer:
            return False
        rs = [(v.X**2 + v.Y**2) ** 0.5 for v in f.vertices()]
        if rs and any(r0 - 0.01 <= min(rs) and max(rs) <= r1 + 0.01 and bb.min.Z >= z0 - 0.01 and bb.max.Z <= z1 + 0.01
                      for r0, r1, z0, z1 in buried):
            return False
        return True

    def is_exception(f):
        for name, zkey, dkey_o, dkey_i in o["overhang_exceptions"]:
            if f.geom_type == GeomType.PLANE and abs(f.center().Z - d[zkey]) < 1e-3:
                return True
        return False

    faces = body.faces().filter_by(exposed)
    worst_ok, offenders, exceptions = 0.0, [], []
    for f in faces:
        ang, _ = max_overhang_deg([f], up)
        if ang > d["max_overhang_deg"] + 0.5:
            (exceptions if is_exception(f) else offenders).append((round(ang, 1), f.geom_type.name, round(f.area, 2),
                                                                  round(f.center().Z, 2)))
        else:
            worst_ok = max(worst_ok, ang)
    print(f"\n{size} body neck-down: worst accepted overhang {worst_ok:.1f} deg; declared exceptions {exceptions}")
    assert not offenders, f"undeclared overhangs > {d['max_overhang_deg']} deg: {offenders}"
    assert exceptions, "the declared seat-floor exception was not found - orientation or exception list is wrong"
