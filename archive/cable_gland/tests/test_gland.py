"""Mating checks for each active size. Parts are built once per session."""
from build123d import Axis, Compound

import params
from assembly import place_collet, place_insert, place_nut
from body import check_body
from collet import check_collet
from build123d import Location

from cacad import cylindrical_faces, interference_pieces, interference_volume
from insert import check_insert
from nut import check_nut


def test_params_arithmetic(size):
    params.validate(size)


def test_parts_pass_own_checks(size, body, collet, nut, inserts):
    check_body(body, size)
    check_collet(collet, size)
    check_nut(nut, size)
    for i, ins in inserts.items():
        check_insert(ins, size, i)


def test_nut_threads_onto_body(size, d, body, nut):
    """No interference at the seated position (nominal + thread_clearance)."""
    seated = place_nut(nut, d)
    assert interference_volume(body, seated) <= d["volume_tol"]
    # and the check is sensitive: a half-turn out of phase must collide
    assert interference_volume(body, seated.rotate(Axis.Z, 180)) > 1.0


def test_nut_threads_through_full_travel(size, d, body, nut):
    """Body and nut stay clearance-free from seated down to the hard stop."""
    for frac in (0.5, 1.0):
        tight = place_nut(nut, d, extra_travel=frac * d["nut_travel"])
        assert interference_volume(body, tight) <= d["volume_tol"], f"interference at {frac:.0%} travel"


def test_collet_fits_seat(size, d, body, collet):
    placed = place_collet(collet, d)
    assert interference_volume(body, placed) <= d["volume_tol"]
    seat_r = cylindrical_faces(body, d["seat_d"] / 2)[0].radius
    base_r = cylindrical_faces(collet, d["collet_base_od"] / 2)[0].radius
    assert abs(2 * (seat_r - base_r) - d["collet_slide_clearance"]) < 1e-6
    bb = placed.bounding_box()
    assert abs(bb.min.Z - d["seat_floor_z"]) < d["bbox_tol"]
    assert abs(bb.max.Z - (d["neck_top_z"] + d["collet_protrusion"])) < d["bbox_tol"]


def test_insert_sits_on_collet_ledge_and_fits_bore(size, d, body, collet, inserts):
    placed_collet = place_collet(collet, d)
    for i, ins in inserts.items():
        placed = place_insert(ins, d)
        assert interference_volume(placed_collet, placed) <= d["volume_tol"], f"ID{i}: insert hits collet"
        assert interference_volume(body, placed) <= d["volume_tol"], f"ID{i}: insert hits body"
        bore_r = cylindrical_faces(collet, d["collet_finger_bore_d"] / 2)[0].radius
        od_r = cylindrical_faces(ins, d["insert_od"] / 2)[0].radius
        assert abs(2 * (bore_r - od_r) - d["insert_clearance"]) < 1e-6
        bb = placed.bounding_box()
        assert abs(bb.min.Z - d["neck_top_z"]) < d["bbox_tol"], "insert bottom is not on the collet ledge"
        # dropping it 0.1 mm would hit the ledge: the ledge really supports it
        assert interference_volume(placed_collet, placed.moved(Location((0, 0, -0.1)))) > 0.01


def test_collet_and_insert_clear_nut_when_seated(size, d, collet, nut, inserts):
    seated = place_nut(nut, d)
    assert interference_volume(seated, place_collet(collet, d)) <= d["volume_tol"]
    for i, ins in inserts.items():
        placed = place_insert(ins, d)
        assert interference_volume(seated, placed) <= d["volume_tol"], f"ID{i}: nut hits insert when seated"
        # the nut ledge is exactly on the insert top: first contact
        assert abs(placed.bounding_box().max.Z - (d["nut_z"] + d["nut_ledge_z_local"])) < d["bbox_tol"]


def test_sealing_stroke_is_axial_squeeze(size, d, collet, nut, inserts):
    """At the hard stop the nut ledge has advanced nut_travel into the insert
    (axial squeeze = the seal) and the cone preloads the collet fingers."""
    tight = place_nut(nut, d, extra_travel=d["nut_travel"])
    assert interference_volume(tight, place_collet(collet, d)) > 0.1, "cone never touches the fingers"
    ins = place_insert(inserts[d["insert_ids"][0]], d)
    pieces = interference_pieces(tight, ins)
    assert sum(p.volume for p in pieces) > 0.1, "nut never squeezes the insert"
    # the ledge's position inside the undeformed insert is the axial squeeze
    ledge_z = min(p.bounding_box().min.Z for p in pieces)
    insert_top = d["insert_z"] + d["insert_len"]
    depth = insert_top - ledge_z
    assert abs(depth - d["nut_travel"]) < d["bbox_tol"], f"axial squeeze {depth:.3f} != nut_travel {d['nut_travel']:.3f}"
    assert d["nut_travel"] >= d["insert_compression_travel"] - 1e-9
    assert depth / d["insert_len"] >= d["insert_axial_compression"] - 1e-9, "insert compressed less than the sealing minimum"


def test_assembled_stack_length(size, d, body, collet, nut, inserts):
    asm = Compound(children=[body, place_collet(collet, d), place_insert(inserts[d["insert_ids"][0]], d), place_nut(nut, d)])
    bb = asm.bounding_box()
    assert abs((bb.max.Z - bb.min.Z) - d["stack_length"]) < d["bbox_tol"]
    assert abs(bb.min.Z + d["panel_thread_len"]) < d["bbox_tol"]
    assert max(bb.size.X, bb.size.Y) <= max(d["hex_ac"], d["nut_ac"], d["shoulder_d"]) + d["bbox_tol"]


def test_panel_side_engagement(size, d):
    """The gasket sits in the recess above the panel face, so only the panel
    and the locknut consume panel thread. locknut_h must be a catalogue height."""
    assert d["locknut"].startswith("DIN 439"), "locknut must name a buyable part"
    spare = d["panel_thread_len"] - d["panel_max"] - d["locknut_h"]
    assert abs(spare - d["spare_engagement"]) < 1e-9
    assert spare >= d["spare_engagement_min"] - 1e-9
    assert abs(d["standoff"] - d["gasket_t"] * (1 - d["gasket_compression"])) < 1e-9


def test_compression_stop_geometry(size, d, body):
    """Foot face on z=0, recess floor exactly one compressed gasket above it."""
    from build123d import Vector
    from cacad import planar_faces_with_normal
    assert planar_faces_with_normal(body, Vector(0, 0, -1), 0.0)
    assert planar_faces_with_normal(body, Vector(0, 0, -1), d["standoff"])
    g = d["gasket"]
    assert g["radial_seal_width"] >= d["gasket_seal_width_min_t"] * d["gasket_t"]
    assert g["groove_fill"] <= d["gasket_groove_fill_max"] + 1e-9
