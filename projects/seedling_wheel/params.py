r"""Seedling wheel: two 1020 trays on a two-gondola Ferris wheel that swaps which tray is under the light.

Two end towers each carry a gearmotor and a rotor arm. A gondola hangs from each end of the arms on plain pivots and
stays level by gravity; turning the rotor 180 deg swaps the trays. Nothing crosses the growing volume: the arms are
outboard of the tray ends, so the light above the top tray sees only plants. The ESP32 runs both motors from one
STEP/DIR pair and homes each tower on its own hall sensor (SPEC.md).

Frame: X along the rotation axis (the trays' long side), Y across, Z up. Origin on the floor, mid-length, on the
axis's vertical plane. Gondola-local frame: origin on the pivot axis, Z down to the tray floor at -h_piv.

        light bars   ===========================   z_light
                         .-- P3 + pivot --.         z_axis + R  (rotor at 0 deg: gondola A up)
        tower |  arm |  [ tray A, plants  ]  | arm | tower
              |  hub o------------------------o hub|           z_axis
              |      |  [ tray B, shaded  ]  |     |           z_axis - R
        base  =============================================    z = 0 .. a2020

Every input is a (value, TAG, source) triple (PARAMS_CONVENTION rule 5). STATUS is concept: UNVERIFIED values (tray
mass, light bar length, the gearbox and hub drawings) are allowed for ideation and named in `derive()["unverified"]`;
none of them may pass a part that has to fit.

    .venv/bin/python projects/seedling_wheel/params.py     # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.materials import FIT_CLEAR, LAYER, NOZZLE, WALL, clearance_bore

STATUS = "concept"   # concept | passes | printed | parked

TAGS = ("STANDARD", "VENDOR", "INFERRED", "DESIGN", "UNVERIFIED", "CONVENIENCE", "PLACEHOLDER")
IN = 25.4
G = 9.81

_BF = "bootstrapfarmer.com/products/extra-strength-seedling-propagation-tray (1020 Extra Strength, 2026-10-10)"
_MIS = "Misumi FA catalogue 2010 p.2239 HFS5-2020 (as cited in projects/nft_table/params.py)"
_MG = ("StepperOnline 17HS15-1584S-MG50, NEMA 17 + MG planetary 50:1; spec table as relisted by "
       "ozrobotics.com (MG series), not the maker's own sheet")
_POL = "Pololu #2693 universal aluminium mounting hub, 8 mm shaft, M3 holes (pololu.com/product/2693)"
_BAR = "Barrina T5 2 ft grow light MF10 (barrina-led.com; Amazon listing 23.1 x 0.79 x 0.79 in)"

# ---------------------------------------------------------------------------
# Bought parts.
# ---------------------------------------------------------------------------
TRAY = MappingProxyType(dict(
    L=(21.1 * IN, "VENDOR", _BF + ": outer 21.1 x 11.0 x 2.5 in"),
    W=(11.0 * IN, "VENDOR", _BF),
    D=(2.5 * IN, "VENDOR", _BF),
    floor_in=((19.9 * IN, 9.4 * IN), "VENDOR", _BF + ": inner bottom 19.9 x 9.4 in"),
    mass_loaded=(4.0, "UNVERIFIED", "estimate: 0.3 tray + 72-cell insert of wet mix ~2.7 + 1 L bottom-water reserve"),
))

EXTRUSION = MappingProxyType(dict(
    a=(20.0, "VENDOR", _MIS + ": section 20 x 20"),
    I=(0.742e4, "VENDOR", _MIS + ": Ix = Iy, mm^4"),
    m=(0.50, "VENDOR", _MIS + ": kg/m"),
    E=(69680.0, "INFERRED", "projects/nft_table: back-calculated from Misumi's load-capacity guideline, MPa"),
    slot_open=(6.0, "VENDOR", _MIS + ": slot opening"),
    slot_lip=(2.0, "VENDOR", _MIS + ": lip, surface to T-slot"),
    slot_depth=(6.0, "VENDOR", _MIS + ": surface to slot floor"),
    # Misumi HNTAJ5-5 post-assembly short nut: screw tip must pass the nut and stay off the slot floor (nft_table)
    tnut_h=(3.2, "VENDOR", "Misumi HNTAJ5-5 height 3.2 (FA 2010 p.2267)"),
    tnut_body=(2.4, "VENDOR", "Misumi HNTAJ5-5 body 2.4 (FA 2010 p.2267)"),
))

MOTOR = MappingProxyType(dict(
    part=("17HS15-1584S-MG50", "VENDOR", _MG),
    ratio=(50.0, "VENDOR", _MG),
    t_permissible=(10.0, "VENDOR", _MG + ": max permissible torque 10 Nm (MG20 and MG50)"),
    t_hold_motor=(0.36, "VENDOR", _MG + ": motor holding torque 36 Ncm"),
    efficiency=(0.90, "VENDOR", _MG + ": gearbox efficiency 90 %"),
    flange=(42.3, "STANDARD", "NEMA ICS 16: NEMA 17 frame 42.3 mm square"),
    body_len=(39.0, "UNVERIFIED", "17HS15 body length; check the maker's drawing"),
    gearbox_len=(52.0, "UNVERIFIED", "MG gearbox length to its face; check the maker's drawing"),
    shaft=((8.0, 20.0), "UNVERIFIED", "MG output shaft d x length; check the maker's drawing"),
))

HUB = MappingProxyType(dict(
    part=("Pololu #2693", "VENDOR", _POL),
    od=(25.4, "VENDOR", _POL + ": 25.4 mm dia"),
    t=(9.2, "VENDOR", _POL + ": 9.2 mm thick"),
    bore=(8.0, "VENDOR", _POL + ": 8 mm round or D shaft, two M3 set screws"),
    holes=(((9.5, 4),), "UNVERIFIED", "four M3 holes on a 19 mm circle read from memory of Pololu's dimension "
                                      "diagram (resources tab, unreachable from this session); check before printing P1"),
))

LIGHT = MappingProxyType(dict(
    part=("Barrina T5 2 ft, 10 W, linkable", "VENDOR", _BAR),
    L=(23.1 * IN, "UNVERIFIED", _BAR + ": listings disagree, 23.1 to 23.6 in"),
    section=(0.79 * IN, "UNVERIFIED", _BAR),
    count=(3, "DESIGN", "three bars across the 279 mm tray, one per third"),
    pitch=(90.0, "DESIGN", "bar spacing in Y"),
    beam=(120.0, "VENDOR", "barrina-led.com product table: beam angle 120 deg"),
    switching=("on/off through a relay", "INFERRED", "the T5 bars have a plug-in switch and no dimming input"),
))

FASTENERS = MappingProxyType(dict(
    # ISO 7379 shoulder screw, d1 8: the gondola pivot, shoulder turning in a printed bore (no bearing)
    sh_d=(8.0, "STANDARD", "ISO 7379 d1 8 (h8)"),
    sh_thread=("M6", "STANDARD", "ISO 7379 d1 8 -> d3 M6"),
    sh_thread_len=(11.0, "STANDARD", "ISO 7379 d1 8: thread length l2 11 (as tabulated by McMaster/Misumi)"),
    sh_head=((13.0, 5.5), "STANDARD", "ISO 7379 d1 8: head d2 13, k 5.5"),
    sh_lengths=((10, 12, 16, 20, 25, 30, 40, 50), "STANDARD", "ISO 7379 d1 8 shoulder lengths"),
    washer8=((8.4, 16.0, 1.6), "STANDARD", "ISO 7089 size 8: d1 8.4, d2 16, h 1.6"),
    nut_M6=((10.0, 5.2), "STANDARD", "ISO 4032 M6: s 10, m 5.2"),
    nut_M3=((5.5, 2.4), "STANDARD", "ISO 4032 M3: s 5.5, m 2.4"),
    M5_head=((8.5, 5.0), "STANDARD", "ISO 4762 M5: dk 8.5, k 5.0"),
    M3_head=((5.5, 3.0), "STANDARD", "ISO 4762 M3: dk 5.5, k 3.0"),
    shcs_lengths=((6, 8, 10, 12, 16, 20, 25, 30), "STANDARD", "ISO 4762 preferred lengths"),
))

# ---------------------------------------------------------------------------
# Design rules and choices.
# ---------------------------------------------------------------------------
COMMON = MappingProxyType(dict(
    # --- growing volume ---
    headroom=(150.0, "DESIGN", "owner's choice: plant tops this far above the tray rim (transplant-size seedlings)"),
    tray_clear=(4.0, "DESIGN", "tray rim to a locating fence, each side: the tray drops in free (never pressed)"),
    fence_t=(3.0, "DESIGN", "P4 fence thickness (envelope only this round)"),
    # the tray drops between P4 fences: end_clear = tray_clear + fence_t puts the end fence on the crossbar's face
    # --- gondola ---
    rail_y=(90.0, "DESIGN", "long rails' centres: under the tray's inner floor, so they carry it whatever its taper"),
    post_top_gap=(12.0, "DESIGN", "pivot axis to the post top: the washer (r 8) clears the post with 4 to spare"),
    post_engage=(50.0, "DESIGN", "P3 overlap on the post: two M5 into the post's slot"),
    p3_w=(24.0, "DESIGN", "P3 width; its top is a half-round of this diameter about the pivot"),
    sh_play=(0.4, "DESIGN", "axial play of the pivot stack: P3 turns between two washers, never clamped"),
    pivot_fit=(FIT_CLEAR, "DESIGN", "materials.FIT_CLEAR, radial: the shoulder turns in P3's printed bore"),
    pivot_mu=(0.30, "UNVERIFIED", "steel on PETG, dry: order-of-magnitude for the pivot friction; grease it"),
    # --- rotor ---
    sweep_gap=(15.0, "DESIGN", "least clearance between the two gondola envelopes anywhere in the turn"),
    arm_end=(25.0, "DESIGN", "arm beyond the pivot: P2's outer screw sits on the arm end's centre"),
    p2_screw_r=(15.0, "DESIGN", "P2's two M5 either side of the pivot along the arm"),
    p2_web=(3.2, "DESIGN", "P2 floor between the shoulder face and the M6 nut: 16 layers"),
    nut_clear=(0.3, "DESIGN", "hex pocket across flats over the nut (standoff_plate); captive, not pressed"),
    thread_past_nut=(1.0, "DESIGN", "pivot thread beyond the nut's far face"),
    p1_d=(60.0, "DESIGN", "P1 hub disc diameter"),
    p1_t=(10.0, "DESIGN", "P1 thickness"),
    p1_screw_r=(21.0, "DESIGN", "P1's two M5 into the arm's slot, either side of the axis"),
    key=((5.6, 1.8), "DESIGN", "P1 key into the arm's slot, W x H: takes the drive torque in shear, not friction"),
    key_gap=(14.0, "DESIGN", "key interrupted within this of the axis: clear of the M3 nut pockets"),
    cb_clear=(1.0, "DESIGN", "counterbore diameter over the head; depth k + 0.4 so heads sit below the face"),
    # --- tower, base, light ---
    ground_gap=(25.0, "DESIGN", "lowest point of the sweep above the base rails"),
    light_gap=(40.0, "DESIGN", "highest point of the sweep to the light bars' underside"),
    tower_y=(100.0, "DESIGN", "tower verticals' centres"),
    base_y=(260.0, "DESIGN", "base long rails' centres: the footprint"),
    motor_plate_t=(6.0, "DESIGN", "P5 plate the gearbox face bolts to"),
    hub_gap=(2.0, "DESIGN", "hub to P5"),
    # --- motion ---
    t_swap=(40.0, "DESIGN", "seconds for the 180 deg swap"),
    t_ramp=(5.0, "DESIGN", "S-curve ramp at each end, s"),
    torque_sf=(1.5, "DESIGN", "least margin of the gearbox's permissible torque over the worst imbalance"),
    # --- print ---
    nozzle_d=(NOZZLE, "DESIGN", "materials.NOZZLE"),
    layer=(LAYER, "DESIGN", "materials.LAYER"),
    min_wall=(WALL, "DESIGN", "materials.WALL"),
    max_overhang_deg=(60.0, "DESIGN", "repo default"),
))

PRINT_ORIENTATION = MappingProxyType(dict(
    # bed_z names a derived key or is a number; every part is a flat plate, bores vertical
    p1_hub=dict(up=(0, 0, 1), bed_face="hub face (Pololu side)", bed_z="0",
                known_overhangs=["M5 counterbore ceilings (bridged annuli)"], overhang_exceptions="p1_cb_ceiling"),
    p2_pivot=dict(up=(0, 0, 1), bed_face="arm face", bed_z="0",
                  known_overhangs=["M6 nut pocket ceiling (bridged hex)"], overhang_exceptions="p2_pocket_ceiling"),
    p3_hanger=dict(up=(0, 0, 1), bed_face="post face", bed_z="0", known_overhangs=[], overhang_exceptions=None),
))

SIZES = {"T1020": dict()}    # one size: the 1020 flat
ACTIVE_SIZES = ("T1020",)


def _check_tags(table, name):
    for k, v in table.items():
        assert isinstance(v, tuple) and len(v) == 3 and v[1] in TAGS, f"{name}.{k}: untagged {v!r}"


def val(table, key):
    return table[key][0]


def derive(size: str = "T1020", **overrides) -> dict:
    """Every dimension the build scripts need. Overrides are for what-if tables only."""
    c = {k: v[0] for k, v in COMMON.items()}
    c.update(SIZES[size])
    c.update(overrides)
    t = {k: v[0] for k, v in TRAY.items()}
    x = {k: v[0] for k, v in EXTRUSION.items()}
    f = {k: v[0] for k, v in FASTENERS.items()}
    m = {k: v[0] for k, v in MOTOR.items()}
    a = x["a"]
    d = dict(size=size, c=c, tray=t, ext=x, fas=f, motor=m, hub={k: v[0] for k, v in HUB.items()},
             light={k: v[0] for k, v in LIGHT.items()})

    # --- gondola (local: pivot at origin) ---
    d["h_plants"] = t["D"] + c["headroom"]
    d["h_piv"] = d["h_plants"]                          # pivot level with the plant tops: as low as the plants allow
    d["z_floor"] = -d["h_piv"]
    d["x_end0"] = t["L"] / 2 + c["tray_clear"] + c["fence_t"]           # end crossbar / post inner face
    d["x_post1"] = d["x_end0"] + a                      # post outer face = P3's bed face
    d["rail_len"] = 2 * d["x_post1"]
    d["xbar_len"] = t["W"] + 2 * (c["tray_clear"] + c["fence_t"])     # the side fences stand on its ends
    d["post_z"] = (d["z_floor"] - a, -c["post_top_gap"])
    d["w_gondola"] = max(t["W"] + 2 * (c["tray_clear"] + c["fence_t"]), d["xbar_len"])
    d["env_top"] = c["p3_w"] / 2                        # P3's half-round above the pivot
    d["env_bot"] = d["z_floor"] - 2 * a                 # under the end crossbars
    d["h_gondola"] = d["env_top"] - d["env_bot"]

    # --- pivot stack along +X: head | washer | P3 | washer | P2 | arm ---
    wt = f["washer8"][2]
    sh_need = wt + 0 + wt + c["sh_play"]
    d["sh_len"] = min(L for L in f["sh_lengths"] if L >= sh_need + 10.0)   # P3 at least 10 thick
    d["p3_t"] = d["sh_len"] - 2 * wt - c["sh_play"]
    d["p3_bore"] = f["sh_d"] + 2 * c["pivot_fit"]
    d["x_p3"] = (d["x_post1"], d["x_post1"] + d["p3_t"])
    d["p2_pocket"] = (f["nut_M6"][0] + c["nut_clear"], f["nut_M6"][1])
    d["p2_t"] = math.ceil((f["sh_thread_len"] + 0.6) / LAYER) * LAYER      # tip stays inside P2
    d["p2_pocket_depth"] = d["p2_t"] - c["p2_web"]
    d["thread_past_nut"] = f["sh_thread_len"] - c["p2_web"] - f["nut_M6"][1]
    d["p2_bore"] = clearance_bore("M6")
    d["x_p2"] = (d["x_p3"][1] + wt + c["sh_play"], d["x_p3"][1] + wt + c["sh_play"] + d["p2_t"])
    d["x_arm"] = (d["x_p2"][1], d["x_p2"][1] + a)
    d["x_p1"] = (d["x_arm"][1], d["x_arm"][1] + c["p1_t"])
    d["x_hub"] = (d["x_p1"][1], d["x_p1"][1] + d["hub"]["t"])
    d["x_p5"] = (d["x_hub"][1] + c["hub_gap"], d["x_hub"][1] + c["hub_gap"] + c["motor_plate_t"])
    d["x_tower"] = (d["x_p5"][1], d["x_p5"][1] + a)     # tower verticals and motor rails, inboard face on P5
    d["shaft_need"] = c["motor_plate_t"] + c["hub_gap"] + d["hub"]["t"] * 0.75
    d["length"] = 2 * d["x_tower"][1]

    # M5 screw stacks into the HFS5 slot (nft_table rule): tip past the T-nut, off the slot floor
    k5 = f["M5_head"][1]
    d["cb_depth5"] = k5 + 0.4
    d["cb_d5"] = f["M5_head"][0] + c["cb_clear"]
    d["bore5"] = clearance_bore("M5")
    d["slot_p"] = (x["slot_lip"] - (x["tnut_h"] - x["tnut_body"]) + x["tnut_h"], x["slot_depth"])
    d["screws5"] = {}
    for part, t_plate in (("P3", d["p3_t"]), ("P2", d["p2_t"]), ("P1", c["p1_t"])):
        under = t_plate - d["cb_depth5"]
        L = min(L for L in f["shcs_lengths"] if L - under >= d["slot_p"][0])
        d["screws5"][part] = dict(L=L, under_head=under, into_slot=L - under)

    # --- rotor: least radius so the two gondolas pass at every angle (two W x H boxes, centres 2R apart) ---
    d["R_min"] = math.hypot(d["w_gondola"], d["h_gondola"]) / 2
    d["R"] = math.ceil(d["R_min"] + c["sweep_gap"] / 2)
    d["arm_len"] = 2 * (d["R"] + c["arm_end"])
    d["sweep_r_arm"] = math.hypot(d["R"] + c["arm_end"], a / 2)

    # --- frame heights ---
    d["z_axis"] = a + c["ground_gap"] - d["env_bot"] + d["R"]
    d["sweep_top"] = d["z_axis"] + d["R"] + d["env_top"]
    d["sweep_bot"] = d["z_axis"] - d["R"] + d["env_bot"]
    d["z_light"] = d["sweep_top"] + c["light_gap"]       # bar underside
    d["z_top_rail"] = d["z_light"] + d["light"]["section"] + 10.0   # bars clip under the tower top rails' P7
    d["height"] = d["z_top_rail"] + a
    d["sweep_y"] = d["R"] + d["w_gondola"] / 2
    d["width"] = max(2 * c["base_y"] + a, 2 * d["sweep_y"])
    d["light_to_floor"] = d["z_light"] - (d["z_axis"] + d["R"] + d["z_floor"])
    d["light_to_tops"] = d["light_to_floor"] - d["h_plants"]

    # --- masses, torque, motion ---
    len_2020 = 2 * d["rail_len"] + 2 * d["xbar_len"] + 2 * (d["post_z"][1] - d["post_z"][0])
    d["m_gondola"] = len_2020 / 1000 * x["m"] + 0.15     # + printed parts and screws, UNVERIFIED
    d["m_loaded"] = d["m_gondola"] + t["mass_loaded"]
    d["imbalance"] = t["mass_loaded"] * G * d["R"] / 1000     # one tray loaded, the other empty: N m
    d["torque_per_end"] = d["imbalance"] / 2
    d["torque_sf"] = val(MOTOR, "t_permissible") / d["torque_per_end"]
    d["torque_avail"] = m["t_hold_motor"] * m["ratio"] * m["efficiency"]
    w = math.pi / (c["t_swap"] - c["t_ramp"])           # cruise rad/s with linear ramps at each end
    d["omega"] = w
    d["motor_rpm"] = w / (2 * math.pi) * 60 * m["ratio"]
    d["a_tan"] = w / c["t_ramp"] * d["R"] / 1000         # m/s^2 at the pivot during the ramp
    d["swing_deg"] = math.degrees(d["a_tan"] / G)        # quasi-static tilt bound
    cg_below = d["h_piv"] - 30.0                          # loaded tray CG ~30 above its floor, UNVERIFIED
    d["pendulum_s"] = 2 * math.pi * math.sqrt(cg_below / 1000 / G)
    d["pivot_tilt_deg"] = math.degrees(c["pivot_mu"] * f["sh_d"] / 2 / cg_below)
    sig = (d["m_loaded"] / 2 * G) * d["R"] * (a / 2) / x["I"]                 # arm root bending, MPa
    d["arm_stress"] = sig
    wl = t["mass_loaded"] * G / 2 / d["rail_len"]                               # N/mm per long rail
    d["rail_sag"] = 5 * wl * d["rail_len"] ** 4 / (384 * x["E"] * x["I"])
    # tip-over: one loaded gondola at the side, the rest centred, over the base rails
    m_frame = 6.0                                                               # UNVERIFIED frame + motors + light
    m_tot = m_frame + 2 * d["m_gondola"] + t["mass_loaded"]
    d["cg_offset"] = t["mass_loaded"] * d["R"] / m_tot
    d["unverified"] = [f"{tb}.{k}" for tb, T in (("TRAY", TRAY), ("MOTOR", MOTOR), ("HUB", HUB), ("LIGHT", LIGHT),
                                                 ("COMMON", COMMON)) for k, v in T.items() if v[1] == "UNVERIFIED"]

    # --- printed parts ---
    hub_r = d["hub"]["holes"][0][0]
    d["p1"] = dict(d=c["p1_d"], t=c["p1_t"], bore=d["hub"]["bore"] + 2 * FIT_CLEAR, hub_r=hub_r, n_hub=4,
                   bore3=clearance_bore("M3"), nut3=f["nut_M3"][0] + c["nut_clear"], nut3_depth=f["nut_M3"][1] + 0.6,
                   screws5=(-c["p1_screw_r"], c["p1_screw_r"]), key=c["key"], key_gap=c["key_gap"])
    d["p1_cb_ceiling"] = d["cb_depth5"]
    d["p2"] = dict(len=2 * (c["p2_screw_r"] + a / 2), w=a, t=d["p2_t"], screw_r=c["p2_screw_r"])
    d["p2_pocket_ceiling"] = d["p2_pocket_depth"]
    d["p3"] = dict(w=c["p3_w"], t=d["p3_t"], top=c["p3_w"] / 2,
                   bot=-(c["post_top_gap"] + c["post_engage"]),
                   screws=(-(c["post_top_gap"] + 15.0), -(c["post_top_gap"] + c["post_engage"] - 12.0)))

    d["walls"] = {
        "P3 bore to edge": (c["p3_w"] - d["p3_bore"]) / 2,
        "P2 nut pocket to edge": (a - d["p2_pocket"][0]) / 2,
        "P2 pocket corner to M5 bore": c["p2_screw_r"] - d["p2_pocket"][0] / math.sqrt(3) - d["bore5"] / 2,
        "P2 web": c["p2_web"],
        "P1 hub bore to M3 bore": hub_r - d["p1"]["bore"] / 2 - d["p1"]["bore3"] / 2,
        "P1 M5 counterbore to disc edge": c["p1_d"] / 2 - c["p1_screw_r"] - d["cb_d5"] / 2,
        "P3 M5 counterbore to edge": (c["p3_w"] - d["cb_d5"]) / 2,
    }
    d["print_orientation"] = {
        k: dict(v, bed_z=float(v["bed_z"]),
                overhang_exceptions=[] if v["overhang_exceptions"] is None else [(v["overhang_exceptions"],
                                                                                  d[v["overhang_exceptions"]])])
        for k, v in PRINT_ORIENTATION.items()}
    d.update({k: c[k] for k in ("nozzle_d", "min_wall", "max_overhang_deg")})
    d["bbox_tol"] = 0.05
    return d


def validate(size: str = "T1020") -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    for name, table in (("TRAY", TRAY), ("EXTRUSION", EXTRUSION), ("MOTOR", MOTOR), ("HUB", HUB), ("LIGHT", LIGHT),
                        ("FASTENERS", FASTENERS), ("COMMON", COMMON)):
        _check_tags(table, name)
        for k, v in table.items():
            assert v[1] not in ("PLACEHOLDER", "CONVENIENCE"), f"{name}.{k} is {v[1]}"
    d = derive(size)
    c, t, f, a = d["c"], d["tray"], d["fas"], d["ext"]["a"]
    from cacad.registries.materials import BED

    # the gondola carries the tray on its floor, whatever the tray's taper
    assert c["rail_y"] + a / 2 < t["floor_in"][1] / 2, "long rails outside the tray's inner floor"
    assert abs(d["x_p2"][0] - (d["x_post1"] - f["washer8"][2] + d["sh_len"])) < 1e-9, "shoulder does not land on P2"
    # the turn: two boxes 2R apart never overlap, with the gap (closed form; tests sweep it too)
    assert 2 * d["R"] >= math.hypot(d["w_gondola"], d["h_gondola"]) + c["sweep_gap"] - 1e-9, "gondolas collide in the turn"
    assert d["R"] > d["w_gondola"] / 2 and 2 * d["R"] > d["h_gondola"], "gondolas collide stacked or side by side"
    assert d["sweep_bot"] >= a + c["ground_gap"] - 1e-9, "sweep hits the base"
    assert d["light_to_tops"] >= c["light_gap"] - 1e-9, "plant tops reach the light"
    assert d["light"]["L"] / 2 < d["x_arm"][0], "light bars reach into the arms' sweep"
    assert d["sweep_r_arm"] < d["z_axis"] - a, "arm sweep hits the base"
    # the pivot stack
    assert d["sh_len"] in f["sh_lengths"], "shoulder length not stocked"
    assert d["thread_past_nut"] >= c["thread_past_nut"], f"pivot thread past the nut {d['thread_past_nut']:.2f}"
    assert f["sh_thread_len"] <= d["p2_t"], "pivot screw tip reaches the arm"
    assert d["p2_pocket_depth"] >= f["nut_M6"][1], "M6 nut does not fit its pocket"
    assert c["post_top_gap"] >= f["washer8"][1] / 2 + 2.0, "pivot washer hits the post top"
    # M5 stacks into the slot
    for part, s in d["screws5"].items():
        assert d["slot_p"][0] <= s["into_slot"] <= d["slot_p"][1], f"{part} M5 x {s['L']}: {s['into_slot']:.1f} into slot"
    # drive
    assert d["torque_sf"] >= c["torque_sf"], f"gearbox margin {d['torque_sf']:.2f} < {c['torque_sf']}"
    assert d["torque_avail"] >= d["torque_per_end"] * c["torque_sf"], "motor cannot lift the imbalance"
    assert d["shaft_need"] <= d["motor"]["shaft"][1], "gearbox shaft too short for P5 + hub"
    assert d["swing_deg"] < 0.5, f"swap swings the trays {d['swing_deg']:.2f} deg"
    assert d["arm_stress"] < 30.0, f"arm root {d['arm_stress']:.1f} MPa"
    assert d["rail_sag"] < 1.0, f"tray rails sag {d['rail_sag']:.2f}"
    assert d["cg_offset"] < c["base_y"] / 2, "tips with one loaded tray at the side"
    # printability
    for name, w in d["walls"].items():
        assert w >= d["min_wall"] and w >= 2 * d["nozzle_d"], f"wall {name} = {w:.2f}"
    for part, dim in (("P1", c["p1_d"]), ("P2", d["p2"]["len"]), ("P3", d["p3"]["top"] - d["p3"]["bot"])):
        assert dim <= BED[0], f"{part} {dim} exceeds the bed"
    assert STATUS in ("concept", "passes", "printed", "parked")
    return d


if __name__ == "__main__":
    for size in SIZES:
        try:
            d = validate(size)
        except AssertionError as e:
            print(f"{size}: FAIL: {e}")
            continue
        print(f"{size}: ok")
        print(f"  overall          {d['length']:.0f} L x {d['width']:.0f} W x {d['height']:.0f} H mm")
        print(f"  gondola envelope {d['w_gondola']:.1f} W x {d['h_gondola']:.1f} H; R_min {d['R_min']:.1f} -> R {d['R']}")
        print(f"  axis z {d['z_axis']:.1f}; sweep {d['sweep_bot']:.1f} .. {d['sweep_top']:.1f}; light {d['z_light']:.1f}")
        print(f"  light to tray floor {d['light_to_floor']:.0f}, to plant tops at full growth {d['light_to_tops']:.0f}")
        print(f"  pivot: ISO 7379 8 x {d['sh_len']}, P3 {d['p3_t']:.1f} thick, P2 {d['p2_t']:.1f}, "
              f"thread past nut {d['thread_past_nut']:.1f}")
        for p, s in d["screws5"].items():
            print(f"  {p}: ISO 4762 M5 x {s['L']}, {s['into_slot']:.1f} into the slot (window {d['slot_p'][0]:.1f}..{d['slot_p'][1]:.1f})")
        print(f"  imbalance {d['imbalance']:.2f} N m, {d['torque_per_end']:.2f} per end; gearbox margin "
              f"{d['torque_sf']:.2f}; motor can give {d['torque_avail']:.1f}")
        print(f"  swap {d['c']['t_swap']:.0f} s, motor {d['motor_rpm']:.0f} rpm; ramp tilt {d['swing_deg']:.3f} deg; "
              f"pendulum {d['pendulum_s']:.2f} s; pivot stick-slip ~{d['pivot_tilt_deg']:.2f} deg")
        print(f"  gondola {d['m_gondola']:.2f} kg empty; arm root {d['arm_stress']:.1f} MPa; rail sag {d['rail_sag']:.2f} mm; "
              f"tip CG offset {d['cg_offset']:.0f} mm")
        print(f"  walls: " + ", ".join(f"{k} {v:.2f}" for k, v in d["walls"].items()))
        print(f"  UNVERIFIED: {', '.join(d['unverified'])}")
