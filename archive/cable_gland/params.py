"""Single source of truth for the cable-gland family.

Axis convention (all parts, all sizes):
    Z is the gland axis. Z=0 is the panel's outer face = the compression-stop
    foot face. The gasket sits in a recess above it (z 0..standoff). The
    panel thread points to -Z, the nut sits at +Z.

Everything downstream (body.py, nut.py, collet.py, insert.py, assembly.py,
coupon.py, tests) reads from `derive(size)`; nothing is hardcoded outside
this file.

Per-size values marked UNVERIFIED are starting points and must be checked
against a real gland (Lapp SKINTOP / Hummel HSK-K catalogue sheets) before
they are trusted. Only M16 has been built and checked so far.

Parts and how they load each other (nut seated = first contact, `nut_travel`
of tightening left):
    body    panel thread, gasket flange with recess + compression-stop foot,
            hex (neck side chamfered self-supporting), neck thread, collet seat
    collet  rigid seat for the insert: base ring in the body seat, straight
            fingers, short 15 deg taper at the tip. Not a clamp.
    insert  TPU sleeve on the collet's base-ring ledge; the nut's flat ledge
            squeezes it axially so it bulges onto the cable. This is the seal.
    nut     internal thread, relief bore, cone (preloads the collet fingers
            onto the insert), flat ledge (compresses the insert), exit bore
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.geometry import clamp_force_n, hex_across_corners, iso_core_radius  # noqa: F401  (re-exported for callers)

MM = 1.0

# ---------------------------------------------------------------------------
# Family-wide values
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(
    dict(
        # --- named clearances (diametral, mm) ---
        thread_clearance=0.3,         # nut internal thread major - body neck major
        collet_slide_clearance=0.2,   # seat bore - collet base OD; nut cone - collet taper; cone top - insert OD
        panel_hole_clearance=0.3,     # panel hole - panel thread major (DIN 46320 lands at 0.2-0.5)
        cable_clearance=0.5,          # body bore / nut exit bore - max cable OD
        insert_clearance=0.2,         # collet finger bore - insert OD
        # --- geometry rules ---
        taper_deg=15.0,               # half-angle of collet tip taper and nut cone
        shoulder_inset=1.0,           # nut dome base sits this far inside the nut flats (avoids tangent faces)
        min_wall=1.2,                 # asserted everywhere it matters (rigid parts)
        chamfer_hex=0.8,
        chamfer_edge=0.5,
        chamfer_fallbacks=(0.6, 0.4, 0.25),
        # --- collet as a seat ---
        # Radial finger deflection that just seats the insert: half the insert
        # clearance to close the gap, plus 0.2 preload. Minimum, not the actual;
        # the actual is nut_travel * tan(taper) once the insert stroke governs.
        collet_seat_deflection=0.3,
        # --- insert (TPU 95A) ---
        # Axial compression that seals: assumption 10-15 %% for TPU 95A on a
        # sleeve constrained on its OD; design point 12 %%. The bulge model in
        # derive() is volume conservation (near-incompressible), uniform along
        # the length. Real bulge is barrel-shaped, larger mid-length, so the
        # coverage numbers are on the conservative side. UNVERIFIED until a
        # printed insert is squeezed.
        insert_axial_compression=0.12,   # MINIMUM; the actual is nut_travel / insert_len (reported)
        insert_id_step=0.1,           # derived insert IDs are rounded down to this
        # --- panel side ---
        panel_max=3.0,                # thickest panel the panel thread must serve
        spare_engagement_min=2.0,     # thread left beyond the locknut, worst case
        panel_thread_round=0.5,       # derived panel thread length is rounded up to this
        # flat gasket in a recess under the flange; a foot ring outside the recess
        # stands on the panel and stops compression at the recess depth
        gasket_t=1.5,                 # uncompressed
        gasket_compression=0.25,      # target; recess depth (standoff) = gasket_t * (1 - this)
        gasket_hole_deburr=0.5,       # radial allowance for the panel hole edge
        gasket_groove_fill_max=0.90,  # gasket volume / recess volume at full compression (open-ID groove)
        gasket_seal_width_min_t=2.0,  # radial seal width >= this x gasket_t
        foot_w=1.2,                   # compression-stop ring width (= min_wall)
        flange_web=1.2,               # flange material above the recess floor
        flange_hex_inset=0.1,         # frustum top sits this far inside the hex flats (no tangent faces)
        self_support_deg=45.0,        # transitions that must print unsupported are cut to this
        # flat ring on the hex top, just outside the nut bore, that the nut's bottom face lands on
        # (the hard stop). It is the one deliberate ceiling on the body's neck side; 1 mm wide.
        hex_stop_ring_w=1.0,
        # printed-locknut derivation, kept for reference (not the chosen option)
        printed_thread_shear_mpa=12.5,   # PETG bulk ~25, halved across layers
        printed_locknut_sf=1.5,
        # Clamp force from torque: F = T / (K d). K = 0.2 for dry nylon on nylon.
        torque_nominal_nm=1.5,        # hand-tight
        torque_abuse_nm=5.0,          # hand over-tightening on a 24 AF wrench, no torque wrench
        thread_friction_k=0.2,
        # --- bd_warehouse IsoThread specifics ---
        # Threads are NOT fused onto their core. Fusing leaves seam slivers and
        # InvalidCurveOnSurface flags where the sweep seams cross the core
        # (2026-09-16, FreeCAD 1.1.3 / OCC 7.8.1); clean(), fix(),
        # BRepLib.SameParameter, glue fuse and groove-cutting were all tried.
        # Each part is a Compound of its core solid plus separate thread solids
        # that overlap the core by `thread_interference`, so the slicer unions
        # them. 0.2 rather than 0 so the overlap survives mesh tolerance.
        thread_interference=0.2,
        # Mating rule for bd_warehouse IsoThread internal-on-external, both
        # built at their own z=0 and the internal one moved up by dz:
        #     rotate internal about Z by  +(dz / pitch) * 360 + thread_phase_offset_deg
        # 180 = tooth sits in groove. Verified 2026-09-16 on the M16 parts at
        # three dz values: zero interference over ~160-200 deg with 0.3 mm
        # clearance, independent of major diameter and end_finishes.
        thread_phase_offset_deg=180.0,
        panel_thread_finish=("chamfer", "fade"),  # local z=0 is the free (panel) end
        neck_thread_finish=("fade", "chamfer"),   # local z=0 is the hex top
        nut_thread_finish=("chamfer", "fade"),    # local z=0 is the nut's bottom face
        slot_count=6,
        slot_width=1.0,
        bbox_tol=0.05,                # mm, assertion tolerance on bounding boxes
        volume_tol=1e-3,              # mm^3, "no interference" threshold
        # --- FDM manufacturing rules ---
        nozzle_d=0.4,                 # every wall >= 2 * nozzle, every slot >= 1 * nozzle
        sliver_area=0.16,             # faces below nozzle^2 are not resolved by a slicer
        max_overhang_deg=60.0,        # from vertical, unsupported. ISO 60 deg flank = 60 deg overhang,
                                      # accepted because each flank spans < 1 mm (see test_printability)
        collet_material="PETG",       # key into MATERIAL_MAX_BENDING_STRAIN
        # The collet prints axis-vertical, so the finger root bends across
        # layer lines where interlayer adhesion governs, not bulk strength.
        # Effective allowable strain ~ bulk * this factor. Reported alongside
        # the bulk number so the margin is not read as larger than it is.
        layer_adhesion_factor=0.5,
    )
)

# Allowable bending strain at the finger root, by material: BULK yield-class
# numbers for FDM parts, not datasheet elongation-at-break, and not across
# layer lines (see layer_adhesion_factor). UNVERIFIED against a printed
# coupon; PLA is listed to document why it is excluded.
MATERIAL_MAX_BENDING_STRAIN = MappingProxyType(dict(
    PLA=0.020,
    PETG=0.045,
    PA12=0.080,
    TPU95A=0.500,
))

# Declared print orientation per part. `up` is the build direction in the
# part's own frame; `bed_face` names the planar face on the bed (z in part
# frame, normal opposite to `up`). Known overhangs are listed, not hidden.
PRINT_ORIENTATION = MappingProxyType(dict(
    # neck-down: the sealing faces (recess floor, foot) print facing up, never on support.
    # The hex neck-side and the flange are cut to self_support_deg. The one
    # remaining ceiling is the collet-seat floor, 2 mm above the bed inside the
    # seat pocket: support there, it is not a sealing face.
    body=dict(up=(0, 0, -1), bed_face="neck top face", bed_z="neck_top_z",   # hex_h must cover hex_cone_h_at_flats + 4 mm
              known_overhangs=["collet seat floor (z=seat_floor_z): flat ring seat_d - bore_d wide, 2 mm above the bed, support inside the pocket",
                               "nut hard-stop ring on the hex top (z=hex_top_z): flat ring from the neck thread OD to hex_stop_r, ~1.35 mm wide, prints unsupported"],
              overhang_exceptions=[("seat floor", "seat_floor_z", "seat_d", "bore_d"),
                                   ("hex stop ring", "hex_top_z", "hex_stop_r", "neck_core_r")],
              note="stands on the neck-top annulus; use a brim"),
    nut=dict(up=(0, 0, 1), bed_face="open threaded face", bed_z="0",
             known_overhangs=["internal shoulder (z=nut_hex_h): flat ring nut_bore_r - cone_base_d/2 wide, bridges the relief bore",
                              "insert ledge (z=nut_hex_h+cone_h): flat ring cone_top_d - bore_d wide"]),
    collet=dict(up=(0, 0, 1), bed_face="base ring bottom", bed_z="0",
                known_overhangs=["ledge for the insert (z=collet_base_ring_h): flat ring, finger bore - body bore wide, faces up - none"]),
    insert=dict(up=(0, 0, 1), bed_face="bottom face", bed_z="0", known_overhangs=[]),
))

# ---------------------------------------------------------------------------
# Family axis. Values are UNVERIFIED unless noted.
# ---------------------------------------------------------------------------
SIZES = {
    "M12": dict(  # UNVERIFIED - not built yet
        thread_major=12.0, pitch=1.5,
        cable_od_min=3.0, cable_od_max=6.5,
        locknut="DIN 439 B M12x1.5", locknut_h=6.0,
        gasket_recess_od=22.0, hex_af=20.0, hex_h=5.0,
        neck_major=16.0, nut_thread_len=5.0, seat_depth=2.0,
        collet_base_od=11.7, collet_cyl_len=7.3, collet_taper_len=0.7, collet_finger_t=1.40,
        collet_tip_deflection=0.60,
        nut_af=20.0, nut_top_wall=2.0, nut_exit_len=2.0,
    ),
    "M16": dict(  # built + tested; dims still UNVERIFIED against a catalogue part
        thread_major=16.0, pitch=1.5,
        cable_od_min=5.0, cable_od_max=10.0,
        locknut="DIN 439 B M16x1.5", locknut_h=8.0,   # m = 8 for M16 thin nut; buyable
        gasket_recess_od=26.0,                        # = the flange OD you chose; foot ring sits outside it
        hex_af=24.0, hex_h=5.0,                       # 4.35 mm wrench flat after the 45 deg cone from the stop ring
        neck_major=20.0, nut_thread_len=6.0, seat_depth=2.0,
        # fingers: L = cyl + taper = 8.0, t = 1.40 -> 2 inserts inside the height budget
        # (finger_tradeoff_table). delta 0.66 sits 0.1 %% under the across-layer strain limit.
        collet_base_od=15.7, collet_cyl_len=7.3, collet_taper_len=0.7, collet_finger_t=1.40,
        collet_tip_deflection=0.66,
        nut_af=24.0, nut_top_wall=2.0, nut_exit_len=2.0,
    ),
    "M20": dict(  # UNVERIFIED - not built yet
        thread_major=20.0, pitch=1.5,
        cable_od_min=6.0, cable_od_max=12.0,
        locknut="DIN 439 B M20x1.5", locknut_h=10.0,
        gasket_recess_od=30.0, hex_af=28.0, hex_h=5.5,
        neck_major=24.0, nut_thread_len=6.0, seat_depth=2.5,
        collet_base_od=19.7, collet_cyl_len=7.3, collet_taper_len=0.7, collet_finger_t=1.40,
        collet_tip_deflection=0.60,
        nut_af=28.0, nut_top_wall=2.0, nut_exit_len=3.0,
    ),
}

# Sizes that build.py and tests actually run. Extend after M16 is confirmed.
ACTIVE_SIZES = ("M16",)


def derive(size: str, **overrides) -> dict:
    """Return every dimension the build scripts need, computed from SIZES + COMMON.
    `overrides` replace SIZES/COMMON entries for what-if tables; the build
    scripts never pass any."""
    s = dict(SIZES[size])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    tan_t = math.tan(math.radians(c["taper_deg"]))

    d = dict(size=size, **s, **c)

    # --- bores ---
    d["bore_d"] = s["cable_od_max"] + c["cable_clearance"]      # body bore, collet base-ring bore, nut exit
    d["collet_finger_bore_d"] = s["collet_base_od"] - 2 * s["collet_finger_t"]
    d["insert_od"] = d["collet_finger_bore_d"] - c["insert_clearance"]
    s["insert_od"] = d["insert_od"]
    d["collet_bore_d"] = d["collet_finger_bore_d"]              # the bore the cable/insert passes
    d["panel_hole_d"] = s["thread_major"] + c["panel_hole_clearance"]

    # --- thread cores (what the thread solids overlap) ---
    d["panel_core_r"] = iso_core_radius(s["thread_major"], s["pitch"])
    d["neck_core_r"] = iso_core_radius(s["neck_major"], s["pitch"])
    d["nut_thread_major"] = s["neck_major"] + c["thread_clearance"]
    d["nut_bore_r"] = d["nut_thread_major"] / 2                  # internal thread overlaps into this wall

    # --- collet (rigid seat) ---
    d["seat_d"] = s["collet_base_od"] + c["collet_slide_clearance"]
    d["collet_tip_od"] = s["collet_base_od"] - 2 * s["collet_taper_len"] * tan_t
    d["collet_base_ring_h"] = s["seat_depth"]                    # slots stop here; insert ledge is its top
    d["collet_protrusion"] = s["collet_cyl_len"] + s["collet_taper_len"]
    d["collet_h"] = s["seat_depth"] + d["collet_protrusion"]

    # --- nut interior ---
    d["cone_base_d"] = d["seat_d"]
    d["cone_top_d"] = s["insert_od"] + 2 * c["collet_slide_clearance"]   # cone stops clear of the insert
    d["cone_h"] = (d["cone_base_d"] - d["cone_top_d"]) / (2 * tan_t)
    d["nut_relief_len"] = s["collet_cyl_len"]                    # straight fingers sit in the wide bore
    d["ledge_w"] = (d["cone_top_d"] - d["bore_d"]) / 2           # flat ring that pushes the insert

    # --- nut travel: the larger of the two strokes ---
    d["insert_len"] = s["collet_cyl_len"] + d["cone_h"]          # collet ledge (neck top) to nut ledge, seated
    d["insert_compression_travel"] = c["insert_axial_compression"] * d["insert_len"]
    d["collet_seat_travel"] = c["collet_seat_deflection"] / tan_t           # minimum that seats the insert
    d["collet_closure_travel"] = s["collet_tip_deflection"] / tan_t         # design closure (range mechanism)
    d["nut_travel"] = max(d["collet_seat_travel"], d["collet_closure_travel"], d["insert_compression_travel"])
    d["nut_travel_governed_by"] = max(
        (("collet closure", d["collet_closure_travel"]), ("insert compression", d["insert_compression_travel"]),
         ("collet seating", d["collet_seat_travel"])), key=lambda kv: kv[1])[0]
    d["collet_tip_deflection"] = d["nut_travel"] * tan_t         # actual, at the hard stop
    d["insert_axial_compression_actual"] = d["nut_travel"] / d["insert_len"]

    # --- panel side: compression stop, gasket recess, thread length ---
    d["standoff"] = c["gasket_t"] * (1 - c["gasket_compression"])   # recess depth = compressed gasket
    d["recess_id"] = s["thread_major"]                                # gasket slides over the thread
    d["recess_od"] = s["gasket_recess_od"]
    d["foot_od"] = d["recess_od"] + 2 * c["foot_w"]
    d["shoulder_d"] = d["foot_od"]                                    # widest flange feature (bbox)
    d["flange_h"] = d["standoff"] + c["flange_web"]
    d["flange_top_d"] = s["hex_af"] - 2 * c["flange_hex_inset"]        # frustum top, inside the hex flats
    d["flange_cone_deg"] = math.degrees(math.atan((d["foot_od"] - d["flange_top_d"]) / 2 / d["flange_h"]))
    # neck side of the hex: a flat stop ring for the nut's bottom face, then a
    # self_support_deg cone out to the corners (an edge chamfer would leave a
    # wide ceiling; a cone from the neck core would leave no hard stop)
    tan_ss = math.tan(math.radians(c["self_support_deg"]))
    d["hex_ac"] = hex_across_corners(s["hex_af"])
    d["hex_stop_r"] = d["nut_bore_r"] + c["thread_interference"] + c["hex_stop_ring_w"]
    d["hex_stop_ring_w_actual"] = d["hex_stop_r"] - s["neck_major"] / 2     # flat ring beyond the neck thread OD
    d["hex_cone_h"] = (d["hex_ac"] / 2 - d["hex_stop_r"]) / tan_ss
    d["hex_cone_h_at_flats"] = (s["hex_af"] / 2 - d["hex_stop_r"]) / tan_ss
    d["hex_wrench_flat"] = s["hex_h"] - d["hex_cone_h_at_flats"]
    required = c["panel_max"] + s["locknut_h"] + c["spare_engagement_min"]
    d["panel_thread_len"] = math.ceil(required / c["panel_thread_round"] - 1e-9) * c["panel_thread_round"]
    s["panel_thread_len"] = d["panel_thread_len"]
    d["spare_engagement"] = d["panel_thread_len"] - c["panel_max"] - s["locknut_h"]
    d["printed_locknut_h"] = _printed_locknut_h(d)

    # --- body Z levels ---
    d["shoulder_h"] = d["flange_h"]
    s["shoulder_h"] = d["flange_h"]
    d["hex_top_z"] = d["flange_h"] + s["hex_h"]
    d["neck_len"] = s["nut_thread_len"] + d["nut_travel"]        # full engagement at seated and at hard stop
    d["neck_top_z"] = d["hex_top_z"] + d["neck_len"]
    d["seat_floor_z"] = d["neck_top_z"] - s["seat_depth"]
    d["body_len"] = s["panel_thread_len"] + d["neck_top_z"]
    d["hex_ac"] = hex_across_corners(s["hex_af"])

    # --- nut outside ---
    d["nut_hex_h"] = s["nut_thread_len"] + d["nut_relief_len"]
    d["nut_dome_h"] = d["cone_h"] + s["nut_exit_len"]
    d["nut_h"] = d["nut_hex_h"] + d["nut_dome_h"]
    d["nut_ledge_z_local"] = d["nut_hex_h"] + d["cone_h"]
    d["nut_dome_base_d"] = s["nut_af"] - 2 * c["shoulder_inset"]
    d["nut_top_od"] = d["bore_d"] + 2 * s["nut_top_wall"]
    d["nut_ac"] = hex_across_corners(s["nut_af"])

    # --- assembly (nut seated = first contact with nut_travel remaining) ---
    d["collet_z"] = d["seat_floor_z"]
    d["insert_z"] = d["neck_top_z"]                              # on the collet base-ring ledge
    d["nut_z"] = d["hex_top_z"] + d["nut_travel"]
    d["stack_length"] = s["panel_thread_len"] + d["nut_z"] + d["nut_h"]
    d["stack_length_tight"] = s["panel_thread_len"] + d["hex_top_z"] + d["nut_h"]   # nut bottom on hex top
    d["height_above_panel"] = d["stack_length"] - s["panel_thread_len"]
    dz = d["nut_z"] - d["hex_top_z"]
    d["nut_phase_deg"] = (dz / s["pitch"]) * 360 + c["thread_phase_offset_deg"]

    # --- gasket seal in the recess ---
    d["gasket"] = _gasket_report(d)

    # --- insert set: greedy from the largest cable down, each insert sealing
    #     from its ID down to what the bulge closes it to ---
    d["insert_ids"], d["insert_coverage"] = _insert_set(d)

    # --- FDM rules ---
    d["min_printable_wall"] = 2 * c["nozzle_d"]
    d["min_slot_width"] = c["nozzle_d"]
    d["material_max_strain"] = MATERIAL_MAX_BENDING_STRAIN[c["collet_material"]]
    d["material_max_strain_across_layers"] = d["material_max_strain"] * c["layer_adhesion_factor"]
    d["print_orientation"] = {k: dict(v, bed_z=_eval_z(v["bed_z"], d)) for k, v in PRINT_ORIENTATION.items()}

    # --- collet finger as a cantilever from the base ring ---
    # eps = 3 * delta * t / (2 * L^2) for a tip-loaded cantilever.
    finger_len = d["collet_protrusion"]
    finger_t = (s["collet_base_od"] - d["collet_finger_bore_d"]) / 2
    tip_deflection = d["collet_tip_deflection"]
    d["collet_finger"] = dict(
        length=finger_len, root_thickness=finger_t, tip_deflection=tip_deflection,
        deflection_to_thickness=tip_deflection / finger_t,
        deflection_to_length=tip_deflection / finger_len,
        root_strain=3 * tip_deflection * finger_t / (2 * finger_len**2),
        material=c["collet_material"],
        material_max_strain=d["material_max_strain"],
        material_max_strain_across_layers=d["material_max_strain_across_layers"],
    )

    # --- walls that matter ---
    outer_r_at_cone_top = _dome_outer_r(d, d["nut_hex_h"] + d["cone_h"])
    d["walls"] = {
        "body.panel_core_to_bore": d["panel_core_r"] - d["bore_d"] / 2,
        "body.neck_core_to_seat": d["neck_core_r"] - d["seat_d"] / 2,
        "body.hex_flat_to_neck_thread": s["hex_af"] / 2 - s["neck_major"] / 2,
        "body.flange_web_over_recess": c["flange_web"],
        "body.foot_ring": c["foot_w"],
        "collet.base_ring": (s["collet_base_od"] - d["bore_d"]) / 2,
        "collet.finger_root": finger_t,
        "collet.tip": (d["collet_tip_od"] - d["collet_finger_bore_d"]) / 2,
        "nut.hex_flat_to_thread": s["nut_af"] / 2 - (d["nut_bore_r"] + c["thread_interference"]),
        "nut.top": s["nut_top_wall"],
        "nut.at_cone_top": outer_r_at_cone_top - d["cone_top_d"] / 2,
        "nut.dome_base_to_cone_base": d["nut_dome_base_d"] / 2 - d["cone_base_d"] / 2,
    }
    # the insert is TPU: printable-wall rule only, min_wall does not apply
    d["insert_walls"] = {f"insert.ID{i:.1f}": (s["insert_od"] - i) / 2 for i in d["insert_ids"]}
    return d


def _gasket_report(d: dict) -> dict:
    """Flat gasket in the flange recess, compression stopped by the foot ring.

    Compression is set by geometry (recess depth = gasket_t * (1 - target)),
    not by torque, once the clamp force exceeds what the gasket needs to reach
    that depth. Gasket: ID slides over the thread, OD is the largest that
    keeps groove fill <= gasket_groove_fill_max at full compression. The seal
    on the panel runs from the hole edge + deburr to the gasket OD.
    Gasket force at target compression from an unbonded rubber ring:
    E_c = E * (1 + 0.5 k S^2). Model, not measurement.
    """
    c = d
    gasket_id = d["thread_major"] + 0.5
    inner_seal_d = d["panel_hole_d"] + 2 * c["gasket_hole_deburr"]
    recess_area = math.pi / 4 * (d["recess_od"]**2 - d["recess_id"]**2)
    recess_vol = recess_area * d["standoff"]
    gasket_area_max = c["gasket_groove_fill_max"] * recess_vol / c["gasket_t"]
    gasket_od = math.floor(math.sqrt(gasket_area_max * 4 / math.pi + gasket_id**2) * 10) / 10
    gasket_area = math.pi / 4 * (gasket_od**2 - gasket_id**2)
    seal_width = (gasket_od - inner_seal_d) / 2
    free_area = math.pi * (gasket_od + gasket_id) * c["gasket_t"]
    shape_factor = gasket_area / free_area
    foot_area = math.pi / 4 * (d["foot_od"]**2 - d["recess_od"]**2)
    rep = dict(gasket_id=gasket_id, gasket_od=gasket_od, inner_seal_d=inner_seal_d,
               radial_seal_width=seal_width, seal_width_over_thickness=seal_width / c["gasket_t"],
               groove_fill=gasket_area * c["gasket_t"] / recess_vol, compression=c["gasket_compression"],
               standoff=d["standoff"], foot_area_mm2=foot_area, gasket_force_n={}, cases={})
    moduli = {"NBR 60A": (4.4, 0.55), "NBR 70A": (6.4, 0.6)}
    for mat, (e_mod, k) in moduli.items():
        e_c = e_mod * (1 + 0.5 * k * shape_factor**2)
        rep["gasket_force_n"][mat] = e_c * c["gasket_compression"] * gasket_area
    for case, torque in (("nominal", c["torque_nominal_nm"]), ("abuse", c["torque_abuse_nm"])):
        force = clamp_force_n(torque, d["thread_major"], c["thread_friction_k"])
        per_mat = {}
        for mat, f_g in rep["gasket_force_n"].items():
            bottomed = force >= f_g
            into_foot = max(0.0, force - f_g)
            per_mat[mat] = dict(bottomed=bottomed, foot_load_n=into_foot, foot_stress_mpa=into_foot / foot_area,
                                compression=c["gasket_compression"] if bottomed else c["gasket_compression"] * force / f_g)
        rep["cases"][case] = dict(torque_nm=torque, force_n=force, per_material=per_mat)
    return rep


def _printed_locknut_h(d: dict) -> float:
    """Height a printed locknut would need: thread shear across layers at the
    abuse clamp load. Reference only; the chosen locknut is bought."""
    force = clamp_force_n(d["torque_abuse_nm"], d["thread_major"], d["thread_friction_k"]) * d["printed_locknut_sf"]
    minor_d = 2 * iso_core_radius(d["thread_major"], d["pitch"])
    area_per_turn = math.pi * minor_d * d["pitch"] / 2
    turns = math.ceil(force / (d["printed_thread_shear_mpa"] * area_per_turn))
    return turns * d["pitch"] + 2 * d["chamfer_edge"]


def finger_tradeoff_table(size: str, lengths=(6.5, 8.0, 10.0, 12.0), thicknesses=(1.65, 1.5, 1.4),
                          strain_limit: float | None = None) -> list[dict]:
    """What the collet fingers buy: for each finger length L and root thickness
    t, the largest tip deflection that holds the across-layer strain limit,
    the resulting nut travel, insert count and height above the panel.
    Thinner t needs a shorter taper to keep the tip wall >= min_wall."""
    base = derive(size)
    eps = strain_limit if strain_limit is not None else base["material_max_strain_across_layers"]
    tan_t = math.tan(math.radians(base["taper_deg"]))
    rows = []
    for L in lengths:
        for t in thicknesses:
            taper_len = min(base["collet_taper_len"], (t - base["min_wall"]) / tan_t)
            if taper_len < 0.5:
                continue
            delta = 2 * eps * L**2 / (3 * t)
            d = derive(size, collet_cyl_len=L - taper_len, collet_taper_len=taper_len, collet_finger_t=t,
                       collet_tip_deflection=delta)
            rows.append(dict(L=L, t=t, taper_len=taper_len, delta=d["collet_tip_deflection"],
                             strain=d["collet_finger"]["root_strain"], nut_travel=d["nut_travel"],
                             governed_by=d["nut_travel_governed_by"], insert_od=d["insert_od"],
                             inserts=len(d["insert_ids"]), insert_ids=d["insert_ids"],
                             height_above_panel=d["height_above_panel"], tip_wall=d["walls"]["collet.tip"]))
    return rows


def _insert_set(d: dict) -> tuple[tuple[float, ...], list[dict]]:
    """Insert IDs that cover [cable_od_min, cable_od_max] end to end.

    Each insert: ID = largest cable it takes (slides on with zero clearance,
    TPU complies). Under `insert_axial_compression` with the OD held by the
    collet fingers (and squeezed by the finger preload), volume conservation
    closes the bore to r_i' = sqrt(r_o'^2 - (r_o^2 - r_i^2) / (1 - eps)).
    The next insert's ID is that closed diameter, rounded down.
    """
    c = COMMON
    eps = d["insert_axial_compression_actual"]
    r_o = d["insert_od"] / 2
    od_squeeze = max(0.0, d["collet_tip_deflection"] - c["insert_clearance"] / 2)
    r_o2 = r_o - od_squeeze
    ids, cov = [], []
    top = d["cable_od_max"]
    while top > d["cable_od_min"] + 1e-9 and len(ids) < 12:
        r_i = top / 2
        inside = r_o2**2 - (r_o**2 - r_i**2) / (1 - eps)
        closed = 2 * math.sqrt(inside) if inside > 0 else 0.0
        ids.append(round(top, 3))
        cov.append(dict(id=round(top, 3), seals_down_to=round(closed, 3), wall=(d["insert_od"] - top) / 2,
                        radial_closure=(top - closed) / 2))
        top = math.floor(closed / c["insert_id_step"] - 1e-9) * c["insert_id_step"]
    return tuple(ids), cov


def _eval_z(expr: str, d: dict) -> float:
    """bed_z expressions are tiny: a number or '-<key>'."""
    expr = expr.strip()
    if expr.startswith("-"):
        return -d[expr[1:]]
    return float(expr) if expr.replace(".", "").isdigit() else d[expr]


def _dome_outer_r(d: dict, z: float) -> float:
    """Outer radius of the nut dome frustum at nut-local height z."""
    z0, z1 = d["nut_hex_h"], d["nut_h"]
    r0, r1 = d["nut_dome_base_d"] / 2, d["nut_top_od"] / 2
    return r0 + (r1 - r0) * (z - z0) / (z1 - z0)


def validate(size: str) -> dict:
    """Arithmetic sanity of a size, no geometry. Raises AssertionError."""
    d = derive(size)
    c = COMMON
    for name, w in d["walls"].items():
        assert w >= c["min_wall"], f"{size}: wall {name} = {w:.2f} < {c['min_wall']}"
        assert w >= d["min_printable_wall"], f"{size}: wall {name} = {w:.2f} < 2 x nozzle"
    for name, w in d["insert_walls"].items():
        assert w >= d["min_printable_wall"], f"{size}: {name} wall {w:.2f} < 2 x nozzle"
    assert c["slot_width"] >= d["min_slot_width"], f"{size}: slot narrower than nozzle"
    assert d["collet_bore_d"] >= d["cable_od_min"], f"{size}: collet bore < min cable OD"
    assert d["collet_tip_od"] > d["collet_finger_bore_d"], f"{size}: collet taper cuts through bore"
    assert d["cone_base_d"] < d["nut_thread_major"], f"{size}: nut cone base wider than thread bore"
    assert d["cone_top_d"] > d["bore_d"], f"{size}: no ledge to push the insert"
    assert d["cone_top_d"] > d["insert_od"], f"{size}: cone would pinch the insert"
    assert d["collet_protrusion"] < d["cone_h"] + d["collet_cyl_len"] - d["nut_travel"], \
        f"{size}: collet tip reaches the nut ledge at the hard stop"
    assert d["nut_thread_len"] >= 2 * d["pitch"], f"{size}: < 2 turns of nut engagement"
    assert d["seat_d"] < 2 * d["neck_core_r"], f"{size}: seat wider than neck core"
    assert d["nut_dome_base_d"] < d["nut_af"], f"{size}: dome base must sit inside nut flats"
    assert d["recess_od"] > d["hex_af"], f"{size}: gasket recess is meant to be proud of the hex flats"
    assert d["flange_top_d"] < d["hex_af"], f"{size}: frustum top must sit inside the hex flats"
    assert d["flange_cone_deg"] <= c["self_support_deg"] + 1e-9, f"{size}: flange cone {d['flange_cone_deg']:.1f} deg not self-supporting"
    assert d["hex_wrench_flat"] >= 4.0, f"{size}: only {d['hex_wrench_flat']:.1f} mm of wrench flat left after the self-support chamfer"
    g = d["gasket"]
    assert g["seal_width_over_thickness"] >= c["gasket_seal_width_min_t"], (
        f"{size}: gasket seal width {g['radial_seal_width']:.2f} < {c['gasket_seal_width_min_t']} x t")
    assert g["groove_fill"] <= c["gasket_groove_fill_max"] + 1e-9, f"{size}: gasket does not fit its recess"
    # panel side: the gasket sits above the panel face, so it costs no thread
    assert d["spare_engagement"] >= c["spare_engagement_min"] - 1e-9, (
        f"{size}: panel thread {d['panel_thread_len']} - panel {c['panel_max']} - locknut {d['locknut_h']} "
        f"= {d['spare_engagement']:.2f} < {c['spare_engagement_min']} spare")
    # sealing stroke is preserved
    assert d["nut_travel"] >= d["insert_compression_travel"] - 1e-9, f"{size}: sealing stroke removed"
    assert d["insert_axial_compression_actual"] <= 0.30, f"{size}: insert compressed {d['insert_axial_compression_actual']:.0%}, past what TPU 95A tolerates"
    assert d["nut_travel"] >= d["collet_seat_travel"] - 1e-9, f"{size}: collet never seats"
    assert d["insert_ids"][0] == d["cable_od_max"] and d["insert_coverage"][-1]["seals_down_to"] <= d["cable_od_min"] + 1e-9, \
        f"{size}: insert set does not cover the cable range"
    f = d["collet_finger"]
    assert f["root_strain"] <= f["material_max_strain_across_layers"] + 1e-9, (
        f"{size}: collet finger root strain {f['root_strain']:.3%} > {f['material']} across-layer allowable "
        f"{f['material_max_strain_across_layers']:.1%}")
    assert d["collet_tip_deflection"] >= c["collet_seat_deflection"] - 1e-9, f"{size}: fingers never seat the insert"
    return d


if __name__ == "__main__":
    for size in SIZES:
        try:
            d = validate(size)
            status = "ok"
        except AssertionError as e:
            d = derive(size)
            status = f"FAIL: {e}"
        print(f"{size}: {status}")
        for k in ("panel_thread_len", "spare_engagement", "printed_locknut_h", "standoff", "flange_h", "foot_od",
                  "flange_cone_deg", "hex_stop_r", "hex_cone_h", "hex_wrench_flat", "bore_d", "collet_finger_bore_d", "insert_od",
                  "seat_d", "collet_tip_od", "collet_h", "cone_h", "cone_top_d", "insert_len",
                  "insert_compression_travel", "collet_seat_travel", "collet_closure_travel", "nut_travel", "neck_len",
                  "nut_h", "body_len", "stack_length", "stack_length_tight", "height_above_panel"):
            print(f"  {k:26s} {d[k]:8.3f}")
        print(f"  nut_travel governed by: {d['nut_travel_governed_by']}; insert axial compression actual "
              f"{d['insert_axial_compression_actual']:.1%} (min {d['insert_axial_compression']:.0%})")
        for k, w in d["walls"].items():
            print(f"  wall {k:32s} {w:6.2f}")
        f = d["collet_finger"]
        print(f"  collet finger: L={f['length']:.2f} t={f['root_thickness']:.2f} tip defl={f['tip_deflection']:.3f} "
              f"d/t={f['deflection_to_thickness']:.3f} root strain={f['root_strain']:.2%} "
              f"({f['material']} bulk {f['material_max_strain']:.1%}, across layers ~{f['material_max_strain_across_layers']:.1%})")
        print(f"  inserts (ID -> seals down to, wall):")
        for cv in d["insert_coverage"]:
            print(f"    {cv['id']:5.1f} -> {cv['seals_down_to']:5.2f}   wall {cv['wall']:.2f}  closure {cv['radial_closure']:.2f}")
        g = d["gasket"]
        print(f"  gasket {g['gasket_id']:.1f} x {g['gasket_od']:.1f} x {d['gasket_t']} in recess {d['recess_id']:.0f}..{d['recess_od']:.0f} "
              f"x {g['standoff']:.3f} deep (fill {g['groove_fill']:.0%}); seal {g['inner_seal_d']:.1f}..{g['gasket_od']:.1f} "
              f"= {g['radial_seal_width']:.2f} wide ({g['seal_width_over_thickness']:.1f} x t); foot ring {g['foot_area_mm2']:.0f} mm2")
        print(f"  gasket force at {g['compression']:.0%}: " + ", ".join(f"{m} {f:.0f} N" for m, f in g["gasket_force_n"].items()))
        for case, v in g["cases"].items():
            per = "; ".join(f"{m}: {'bottomed' if r['bottomed'] else f'{r[chr(99)+chr(111)+chr(109)+chr(112)+chr(114)+chr(101)+chr(115)+chr(115)+chr(105)+chr(111)+chr(110)]:.0%} only'}, "
                            f"foot {r['foot_load_n']:.0f} N = {r['foot_stress_mpa']:.1f} MPa" for m, r in v["per_material"].items())
            print(f"    {case:8s} {v['torque_nm']:.1f} Nm -> {v['force_n']:.0f} N: {per}")
