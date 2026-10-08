r"""SEN6x enclosure: a printed PETG box for one Sensirion SEN6x air-quality module (SEN62/63C/65/66/68/69C, one
package). Two parts: a base the sensor drops into and a flat lid on four M3 screws in heat-set inserts.

The sensor's air path decides the box. It draws air in through the fan grille on its top face (the RH/T and gas
sensors breathe through the square and round openings beside it) and blows it out underneath, through a duct that
leaves by an arch in each long side. The bottom is open: the sensor is meant to sit on a flat surface that closes
the duct. So the base floor closes it, the lid has a hole over each top opening, and each long wall has a window
on the arch. Inlet on top, outlet on the sides: exhaust is not drawn back in.

The connector (ACES 51468-0064N-001) sits in the duct roof and takes a JST GHR-06V-S from below. The plug hangs
almost to the floor, so a groove in the floor gives the wires room to bend and leads them out through the -Y window.
Plug the cable in before the sensor goes into the base.

Every number is a (value, TAG, source) triple; validate() refuses an untagged one.

    STANDARD     a published standard (named)
    VENDOR       published by the vendor of the part used (sheet and page named)
    INFERRED     follows from a published number or the vendor STEP, not stated (says from what)
    DESIGN       this model's choice; the part that meets it is designed to tolerate it

Coordinates: X along the sensor's length (fan at +X), Y across it, Z up. Z=0 is the base's bed face. The sensor sits
centred on X=Y=0 with its bottom on the floor top, z = floor_t. "Sensor frame" below means the same X, Y with z=0
at the sensor's bottom face.

    section through a long wall (Y-)                plan

      lid   ====[ fan hole ]=====[o][#]====          +--------------------------------+
      wall  |  +----------------------+  |           |[i]  [#]               ____   [i]|
            |  |       SEN6x          |  |           |     [o]   ===plug=== (fan )     |
            |  |__   ________   ______|  |  window   |[i]          groove    ~~~~   [i]|
      floor |__/  \_/ plug  \_/       \__|  <- arch  +--------------------------------+
            ======== groove ======                    [i] heat-set insert, 2 per end wall

    .venv/bin/python projects/sen6x_enclosure/params.py      # prints the design
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries import materials as MAT

TAGS = ("STANDARD", "VENDOR", "INFERRED", "DESIGN")

DS = "Sensirion SEN6x datasheet v1.0 Oct 2026 (PS_DS_SEN6x.pdf)"
STEP = "Sensirion STEP PS_CD_SEN6x_D1 (175875-00), ref/SEN6x.step, probed by ray casts and planar faces 2026-10-07"
JST = "JST GH connector datasheet eGH.pdf p.3 'Housing', ref/JST_eGH.pdf"
CNC = "CNC Kitchen M3 standard insert (cacad.registries.materials)"

SPEC = MappingProxyType({
    # --- the sensor: package outline (datasheet section 5.1, Figure 8, p.56)
    "sensor_l": (55.2, "VENDOR", f"{DS} p.56: length 55.2 +0.2/-0.4"),
    "sensor_l_tol": (0.2, "VENDOR", f"{DS} p.56: +0.2"),
    "sensor_w": (25.6, "VENDOR", f"{DS} p.56: width 25.6 +0.1/-0.2"),
    "sensor_w_tol": (0.1, "VENDOR", f"{DS} p.56: +0.1"),
    "sensor_h": (21.3, "VENDOR", f"{DS} p.56: height 21.3 +/-0.5"),
    "sensor_h_tol": (0.5, "VENDOR", f"{DS} p.56: +/-0.5"),
    "sensor_corner_r": (2.8, "VENDOR", f"{DS} p.56: plan corners R2.8 (2x, -X end) and R4.3 (2x, fan end); the smaller governs"),
    "sensor_mass_g": (22.0, "VENDOR", f"{DS} p.4 Table 1: weight 18 / 20 / 22 g"),
    # --- top openings, plan dimensions from the -X end and the +Y edge (datasheet p.56), converted to centred X, Y
    "fan_x": (42.4 - 27.6, "VENDOR", f"{DS} p.56: fan centre 42.4 +/-0.3 from the -X end"),
    "fan_y": (0.0, "VENDOR", f"{DS} p.56: fan centre 12.8 +/-0.2 from the +Y edge (the centreline)"),
    "fan_d": (20.5, "VENDOR", f"{DS} p.56: fan grille dia 20.5 +/-0.3"),
    "sq_x0": (3.2 - 27.6, "VENDOR", f"{DS} p.56: square opening 3.2 to 10.2 from the -X end"),
    "sq_x1": (10.2 - 27.6, "VENDOR", f"{DS} p.56: square opening 3.2 to 10.2 from the -X end"),
    "sq_y0": (12.8 - 9.8, "VENDOR", f"{DS} p.56: square opening 2.8 to 9.8 from the +Y edge"),
    "sq_y1": (12.8 - 2.8, "VENDOR", f"{DS} p.56: square opening 2.8 to 9.8 from the +Y edge"),
    "rd_x": (6.7 - 27.6, "VENDOR", f"{DS} p.56: round opening centre 6.7 from the -X end"),
    "rd_y": (12.8 - 18.2, "VENDOR", f"{DS} p.56: round opening centre 18.2 +/-0.2 from the +Y edge"),
    "rd_d": (6.0, "VENDOR", f"{DS} p.56: round opening dia 6 +/-0.2"),
    "top_open_tol": (0.3, "VENDOR", f"{DS} p.56: largest positional tolerance on a top opening (+/-0.3)"),
    # --- outlet arch, both long sides alike: sensor-frame (x, z) of the outer face's lower edge at y = +/-12.7.
    # The datasheet gives only the flat top's ends (19 and 29.9 from the -X end = x -8.6 .. +2.3, p.56); the flanks
    # are the STEP's. Outside x -16 .. 14 the side face is closed above z 2.08.
    "arch": (((-16.0, 2.24), (-15.0, 2.83), (-14.0, 4.59), (-13.0, 7.34), (-12.0, 10.09), (-11.0, 12.28),
              (-10.0, 13.06), (-9.0, 13.36), (2.0, 13.38), (3.0, 13.28), (4.0, 12.83), (5.0, 11.81), (6.0, 10.62),
              (7.0, 9.43), (8.0, 8.23), (9.0, 7.04), (10.0, 5.85), (11.0, 4.66), (12.0, 3.47), (13.0, 2.51),
              (14.0, 2.12)), "VENDOR", f"{STEP}; flat top matches {DS} p.56 (19 / 29.9 from the -X end)"),
    # --- connector (datasheet section 3, Table 16, p.15; position from the STEP: the datasheet draws it, unpositioned)
    "socket_x": (-4.455, "VENDOR", f"{STEP}: socket shroud face x -9.83 .. 0.92"),
    "socket_y": (-6.225, "VENDOR", f"{STEP}: socket shroud face y -8.35 .. -4.10"),
    "socket_mouth_z": (6.44, "VENDOR", f"{STEP}: shroud face z 6.44 above the sensor bottom; duct roof 6.35"),
    "plug_w": (8.75, "VENDOR", f"{JST}: GHR-06V-S B = 8.75, along X (the socket's long axis, {DS} p.15 Fig. 1)"),
    "plug_t": (4.15, "VENDOR", f"{JST}: housing thickness 4.15"),
    "plug_len": (5.7, "VENDOR", f"{JST}: housing length 5.7 along the mating axis (vertical here)"),
    # --- cable: six loose crimped wires, one per pin, leaving the plug's end at the contact pitch
    "wire_n": (6, "VENDOR", f"{DS} p.15 Table 17: 6 pins (1/6 VDD, 2/5 GND, 3 SDA, 4 SCL)"),
    "wire_pitch": (1.25, "VENDOR", f"{JST}: GH pitch 1.25"),
    "pins": (("1 VDD", "2 GND", "3 SDA", "4 SCL", "5 GND/NC", "6 VDD/NC"), "VENDOR",
             f"{DS} p.15 Table 17: 1/6 and 2/5 joined inside; SDA, SCL 5 V tolerant, open drain, need pull-ups (10k, section 3.1)"),
    "pin1_at_minus_x": (True, "INFERRED", f"{DS} p.15 Fig. 1 and p.57 Fig. 9 are bottom views with the fan right and the "
                        "label below the connector; the STEP puts the fan at +X and the label at +Y, so the figure is +X right, "
                        "-Y up, and pin 1 (left) is the -X end"),
    "wire_od": (1.0, "VENDOR", "eGH.pdf p.2 contact SSHL-002T-P0.2: AWG #30-#26, insulation OD 0.76-1.0; "
                f"{DS} p.15 Table 16 asks >= AWG26, so the largest OD"),
    "wire_bend_min": (2.0, "DESIGN", "inner bend radius >= 2 x wire OD for PVC hook-up wire held in place; a fixed bend, "
                      "never flexed in service"),
    "cable_out": (30.0, "DESIGN", "length drawn outside the -Y wall, display only"),
    "cable_len_max": (500.0, "VENDOR", f"{DS} p.15 Table 16: cable <= 50 cm (and < 10 cm unshielded, section 3.1)"),
    # --- bought fasteners
    "screw_d": (3.0, "STANDARD", "ISO 4762 M3"),
    "screw_head_dk": (5.5, "STANDARD", "ISO 4762 M3: dk max 5.5"),
    "screw_head_k": (3.0, "STANDARD", "ISO 4762 M3: k max 3.0"),
    "screw_lengths": ((5, 6, 8, 10, 12, 16, 20), "STANDARD", "ISO 4762 M3 preferred lengths"),
    "screw_bore": (MAT.clearance_bore("M3"), "STANDARD", "ISO 273 medium 3.4 + DESIGN FDM allowance 0.2 (materials.clearance_bore)"),
    "insert_bore": (MAT.INSERT_BORE_M3, "VENDOR", f"{CNC}: hole 4.0"),
    "insert_len": (MAT.INSERT_LEN_M3, "VENDOR", f"{CNC}: length 5.7"),
    "insert_hole_extra": (1.0, "VENDOR", "cnckitchen.com 'Tips and tricks for heat-set inserts': hole = insert length + about 1 mm"),
    "insert_wall": (MAT.INSERT_WALL_M3, "VENDOR", f"{CNC}: minimum wall 1.6 around the hole"),
    # --- clearances
    "fit_clear": (MAT.FIT_CLEAR, "DESIGN", "radial, sensor side to pocket wall: materials.FIT_CLEAR (Prusa >= 0.3, Hubs 0.5). "
                  "The sensor is free in the pocket, never pressed"),
    "lid_gap": (0.2, "DESIGN", "sensor top at its +0.5 limit to the lid underside: one layer. A nominal sensor has 0.7 of "
                "vertical play; a sensor at -0.5 has 1.2. Free, not clamped"),
    "open_margin": (1.0, "DESIGN", "each lid hole beyond its sensor opening, past fit_clear and the opening's own tolerance, so "
                    "the lid edge never shades the grille"),
    "window_margin": (0.5, "DESIGN", "wall window inside the arch, so the wall still covers the sensor body around it"),
    "bend_room": (3.0, "DESIGN", "below the plug's lowest possible end, for the GH wires (AWG26-30, about 1 mm OD) to turn 90 deg. "
                  "The plug is taken as wholly below the mouth; seated, it ends higher"),
    "groove_side": (1.0, "DESIGN", "groove width each side of the plug"),
    # --- printed geometry
    "wall": (2.0, "DESIGN", "long walls: 5 perimeters at the 0.4 nozzle (materials.WALL is 4)"),
    "floor_min": (2.0, "DESIGN", "floor where no groove governs; stiffness of a 60 x 30 plate"),
    "floor_web": (MAT.FLOOR, "DESIGN", "materials.FLOOR: under the groove, 6 layers"),
    "lid_t": (2.0, "DESIGN", "10 layers; the lid spans 26 mm between end walls with a 23 mm hole in it"),
    "pocket_corner_r": (3.0, "DESIGN", "<= sensor_corner_r + fit_clear, so the pocket corner clears the sensor corner"),
    "outer_corner_r": (2.0, "DESIGN", "plan corners of base and lid"),
    "insert_y_inset": (3.6, "DESIGN", "insert centre in from the long outer faces: boss radius 2.0 + 1.6 wall"),
    "chamfer_top": (0.4, "DESIGN", "cosmetic lead-in on each insert bore"),
    # --- process
    "nozzle_d": (MAT.NOZZLE, "DESIGN", "materials.NOZZLE"),
    "layer": (MAT.LAYER, "DESIGN", "materials.LAYER"),
    "min_wall": (1.2, "DESIGN", "functional floor for a printed wall"),
    "bed": (MAT.BED, "VENDOR", "Bambu Lab A1 256 x 256 x 256 (materials.BED)"),
    "max_bridge": (15.0, "DESIGN", "longest unsupported bridge allowed in PETG at the A1 defaults"),
    "max_overhang_deg": (60.0, "DESIGN", "steepest unsupported face, from vertical (repo default)"),
})


def spec(key: str):
    return SPEC[key][0]


def _round_up(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 6)


def derive(**overrides) -> dict:
    """Every dimension enclosure.py, freecad_view.py and the tests need. Overrides are for what-if tables only."""
    d = {k: v[0] for k, v in SPEC.items()}
    d.update(overrides)
    c, layer = d["fit_clear"], d["layer"]

    # pocket: the sensor at its largest plus the fit clearance all round
    d["pocket_l"] = d["sensor_l"] + d["sensor_l_tol"] + 2 * c
    d["pocket_w"] = d["sensor_w"] + d["sensor_w_tol"] + 2 * c

    # floor: max() of a plain floor and the cable groove under the plug, winner recorded
    d["plug_bottom_z"] = d["socket_mouth_z"] - d["plug_len"]          # sensor frame; lowest the plug can hang
    d["groove_depth"] = _round_up(max(d["bend_room"] - d["plug_bottom_z"], 0.0), layer)
    needs = {"floor_min": d["floor_min"], "cable groove": d["groove_depth"] + d["floor_web"]}
    d["floor_governed_by"], d["floor_t"] = max(needs.items(), key=lambda kv: kv[1])
    d["floor_t"] = _round_up(d["floor_t"], layer)
    d["floor_needs"] = needs
    d["z_floor"] = d["floor_t"]                                        # sensor bottom
    d["z_groove"] = d["floor_t"] - d["groove_depth"]
    d["z_lid"] = _round_up(d["floor_t"] + d["sensor_h"] + d["sensor_h_tol"] + d["lid_gap"], layer)   # wall top / lid underside
    d["z_top"] = d["z_lid"] + d["lid_t"]

    # end walls carry the inserts: boss = bore + vendor wall both sides
    d["boss_r"] = d["insert_bore"] / 2 + d["insert_wall"]
    d["end_wall"] = 2 * d["boss_r"]
    d["outer_l"] = d["pocket_l"] + 2 * d["end_wall"]
    d["outer_w"] = d["pocket_w"] + 2 * d["wall"]
    d["insert_x"] = d["pocket_l"] / 2 + d["boss_r"]
    d["insert_y"] = d["outer_w"] / 2 - d["insert_y_inset"]
    d["inserts"] = [(sx * d["insert_x"], sy * d["insert_y"]) for sx in (-1, 1) for sy in (-1, 1)]
    d["insert_hole_depth"] = _round_up(d["insert_len"] + d["insert_hole_extra"], layer)

    # screw: the longest stocked length that stays inside the insert hole, and engages the full insert
    reach = d["lid_t"] + d["insert_hole_depth"]
    fit = [L for L in d["screw_lengths"] if d["lid_t"] + d["insert_len"] <= L <= reach]
    d["screw_len"] = max(fit) if fit else None
    d["screw_tip_z"] = d["z_top"] - d["screw_len"] if fit else None

    # lid holes: sensor opening + its tolerance + fit clearance + margin
    grow = d["top_open_tol"] + c + d["open_margin"]
    d["lid_holes"] = dict(
        fan=dict(kind="circle", c=(d["fan_x"], d["fan_y"]), d=d["fan_d"] + 2 * grow),
        round=dict(kind="circle", c=(d["rd_x"], d["rd_y"]), d=d["rd_d"] + 2 * grow),
        square=dict(kind="rect", c=((d["sq_x0"] + d["sq_x1"]) / 2, (d["sq_y0"] + d["sq_y1"]) / 2),
                    size=(d["sq_x1"] - d["sq_x0"] + 2 * grow, d["sq_y1"] - d["sq_y0"] + 2 * grow)),
    )

    # side windows: a trapezoid inscribed in the arch (inset by window_margin), from the floor top up. Flat top =
    # the arch top's lowest point, a bridge; each flank the shallowest line that stays under the arch and is no
    # shallower than the overhang limit. The -Y window also drops to the groove where the cable leaves.
    arch = [(x, z - d["window_margin"]) for x, z in d["arch"]]
    top = max(z for _, z in arch)
    zt = min(z for _, z in arch if z >= top - layer)
    d["window_top"] = zt

    def crossing(seq):   # first x along seq where the inset arch drops below zt, interpolated
        for (x0, z0), (x1, z1) in zip(seq, seq[1:]):
            if z0 >= zt > z1:
                return x0 + (x1 - x0) * (z0 - zt) / (z0 - z1)
        raise AssertionError("arch never drops below the window top")

    mid = arch.index(max(arch, key=lambda p: p[1]))
    xl1, xr1 = crossing(arch[mid::-1]), crossing(arch[mid:])
    s_min = math.tan(math.radians(90 - d["max_overhang_deg"]))    # flank slope dz/dx at the overhang limit
    sl = max([s_min] + [(zt - z) / (xl1 - x) for x, z in arch if x < xl1])
    sr = max([s_min] + [(zt - z) / (x - xr1) for x, z in arch if x > xr1])
    xl0, xr0 = xl1 - zt / sl, xr1 + zt / sr
    d["window_profile"] = [(xl0, 0.0), (xl1, zt), (xr1, zt), (xr0, 0.0)]   # sensor frame (x, z)
    d["window_x"] = (xl0, xr0)
    d["window_bridge"] = xr1 - xl1
    d["window_flank_deg"] = (math.degrees(math.atan(1 / sl)), math.degrees(math.atan(1 / sr)))   # from vertical

    # groove: from under the plug to beyond the -Y outer face
    d["groove_x"] = (d["socket_x"] - d["plug_w"] / 2 - d["groove_side"], d["socket_x"] + d["plug_w"] / 2 + d["groove_side"])
    d["groove_y"] = (-d["outer_w"] / 2 - 1.0, d["socket_y"] + d["plug_t"] / 2 + d["groove_side"])

    # cable: each wire drops out of the plug's end, turns 90 deg toward -Y and lies on the groove floor, then
    # leaves under the -Y wall. The bend uses the whole drop from the plug end to the lying wire's axis.
    sgn = 1 if d["pin1_at_minus_x"] else -1   # wire_x[0] is pin 1
    d["wire_x"] = [d["socket_x"] + sgn * (i - (d["wire_n"] - 1) / 2) * d["wire_pitch"] for i in range(d["wire_n"])]
    assert len(d["pins"]) == d["wire_n"]
    d["wire_z0"] = d["z_floor"] + d["plug_bottom_z"]                  # plug end, where the wires leave
    d["wire_zc"] = d["z_groove"] + d["wire_od"] / 2                    # axis of a wire lying on the groove floor
    d["wire_bend_r"] = d["wire_z0"] - d["wire_zc"]                     # axis radius of the 90 deg turn
    d["wire_y_end"] = -d["outer_w"] / 2 - d["cable_out"]
    d["wire_len_in_box"] = (math.pi / 2 * d["wire_bend_r"]) + (d["socket_y"] - d["wire_bend_r"] + d["outer_w"] / 2)

    # walls the printability check reads
    hole_edge = {k: (h["c"][0] + h["d"] / 2 if h["kind"] == "circle" else h["c"][0] + h["size"][0] / 2) for k, h in d["lid_holes"].items()}
    d["walls"] = {
        "long wall": d["wall"],
        "end wall: insert bore to pocket": d["insert_x"] - d["insert_bore"] / 2 - d["pocket_l"] / 2,
        "end wall: insert bore to outer face": d["outer_l"] / 2 - d["insert_x"] - d["insert_bore"] / 2,
        "end wall: insert bore to long face": d["outer_w"] / 2 - d["insert_y"] - d["insert_bore"] / 2,
        "floor under groove": d["z_groove"],
        "lid: fan hole to screw hole": d["insert_x"] - d["screw_bore"] / 2 - hole_edge["fan"],
        "lid: fan hole to long edge": d["outer_w"] / 2 - abs(d["fan_y"]) - d["lid_holes"]["fan"]["d"] / 2,
        "lid: round hole to square hole": (d["lid_holes"]["square"]["c"][1] - d["lid_holes"]["square"]["size"][1] / 2)
                                          - (d["rd_y"] + d["lid_holes"]["round"]["d"] / 2),
        "window to end wall": d["pocket_l"] / 2 - max(abs(x) for x in d["window_x"]),
    }
    d["print_orientation"] = dict(
        base=dict(up=(0, 0, 1), bed_face="floor bottom", bed_z=0.0,
                  # bridged ceilings: each window top, and the -Y wall's underside where the groove passes under it
                  exceptions=[("window top", d["z_floor"] + d["window_top"]), ("groove under -Y wall", d["z_floor"])]),
        lid=dict(up=(0, 0, -1), bed_face="lid top", bed_z=d["z_top"], exceptions=[]),
    )
    return d


def validate(**overrides) -> dict:
    """Raise AssertionError on anything not buildable or not usable. No warnings."""
    for k, v in SPEC.items():
        assert isinstance(v, tuple) and len(v) == 3 and v[1] in TAGS and v[2], f"SPEC[{k!r}] is not a tagged (value, TAG, source)"
    d = derive(**overrides)
    for name, w in d["walls"].items():
        assert w >= d["min_wall"], f"wall {name} = {w:.2f} < {d['min_wall']}"
        assert w >= 2 * d["nozzle_d"], f"wall {name} = {w:.2f} < 2 x nozzle"
    assert d["pocket_corner_r"] <= d["sensor_corner_r"] + d["fit_clear"], "pocket corner would bear on the sensor corner"
    # a stocked screw engages the whole insert and bottoms nowhere
    assert d["screw_len"] is not None, (f"no stocked M3 length in [{d['lid_t'] + d['insert_len']:.1f}, "
                                        f"{d['lid_t'] + d['insert_hole_depth']:.1f}]")
    assert d["screw_tip_z"] >= d["z_lid"] - d["insert_hole_depth"], "screw tip passes the insert hole bottom"
    assert d["z_lid"] - d["insert_hole_depth"] > 0, "insert hole breaks through the floor"
    # the plug and the wire bend fit: groove floor below the bend, above the bed
    assert d["z_floor"] + d["plug_bottom_z"] - d["bend_room"] >= d["z_groove"] - 1e-9, "groove too shallow for the wire bend"
    assert d["z_groove"] >= d["floor_web"] - 1e-9, "groove leaves less than floor_web under it"
    # the cable: wires side by side fit between their neighbours and inside the groove, and the turn is not too tight
    assert d["wire_pitch"] >= d["wire_od"], "wires wider than the contact pitch"
    bundle = (d["wire_n"] - 1) * d["wire_pitch"] + d["wire_od"]
    assert bundle <= d["groove_x"][1] - d["groove_x"][0], f"wire bundle {bundle:.2f} wider than the groove"
    inner = d["wire_bend_r"] - d["wire_od"] / 2
    assert inner >= d["wire_bend_min"] * d["wire_od"] - 1e-6, (
        f"wire bend inner radius {inner:.2f} < {d['wire_bend_min']} x OD {d['wire_od']}")
    assert d["wire_zc"] + d["wire_od"] / 2 <= d["z_floor"], "lying wires stand above the floor top, under the sensor"
    # the groove leaves through the window, not through solid wall
    assert d["window_x"][0] <= d["groove_x"][0] and d["groove_x"][1] <= d["window_x"][1], "cable groove misses the -Y window"
    # every lid hole stays inside the pocket outline, so the lid still covers the walls it sits on
    for k, h in d["lid_holes"].items():
        (cx, cy), (hx, hy) = h["c"], ((h["d"] / 2,) * 2 if h["kind"] == "circle" else (h["size"][0] / 2, h["size"][1] / 2))
        assert abs(cx) + hx <= d["pocket_l"] / 2 and abs(cy) + hy <= d["pocket_w"] / 2, f"lid hole {k} crosses the wall top"
    # the window top is a bridge, its flanks print unsupported, and it lies under the arch: the wall never opens
    # onto the sensor's closed side face
    assert d["window_bridge"] <= d["max_bridge"], f"window bridge {d['window_bridge']:.1f} > {d['max_bridge']}"
    assert max(d["window_flank_deg"]) <= d["max_overhang_deg"] + 1e-6, f"window flank {d['window_flank_deg']}"
    (xl0, _), (xl1, zt), (xr1, _), (xr0, _) = d["window_profile"]
    for x, z in d["arch"]:
        zw = 0.0 if not xl0 < x < xr0 else zt if xl1 <= x <= xr1 else zt * ((x - xl0) / (xl1 - xl0) if x < xl1 else (xr0 - x) / (xr0 - xr1))
        assert zw <= z - d["window_margin"] + 1e-6, f"window at x {x} reaches z {zw:.2f}, arch {z} - margin"
    assert all(o + 1 <= b for o, b in zip((d["outer_l"], d["outer_w"], d["z_top"]), d["bed"])), "does not fit the bed"
    return d


def report() -> str:
    d = derive()
    return "\n".join([
        f"SEN6x enclosure: outer {d['outer_l']:.2f} x {d['outer_w']:.2f} x {d['z_top']:.2f} (base {d['z_lid']:.2f} + lid {d['lid_t']:.2f})",
        f"  pocket {d['pocket_l']:.2f} x {d['pocket_w']:.2f}, sensor on the floor at z {d['z_floor']:.2f}, lid underside z {d['z_lid']:.2f}",
        f"  floor {d['floor_t']:.2f} governed by '{d['floor_governed_by']}' "
        + ", ".join(f"{k} {v:.2f}" for k, v in d["floor_needs"].items()),
        f"  plug end {d['plug_bottom_z']:.2f} above the sensor bottom; groove {d['groove_depth']:.2f} deep, "
        f"x {d['groove_x'][0]:.2f} .. {d['groove_x'][1]:.2f}, out through the -Y window",
        f"  cable: {d['wire_n']} x AWG26 (OD {d['wire_od']}) at {d['wire_pitch']} pitch, 90 deg turn on axis radius "
        f"{d['wire_bend_r']:.2f} (inner {d['wire_bend_r'] - d['wire_od'] / 2:.2f}), {d['wire_len_in_box']:.1f} mm from plug to the outer face",
        f"  windows x {d['window_x'][0]:.1f} .. {d['window_x'][1]:.1f}, top {d['window_top']:.2f} above the floor, bridge {d['window_bridge']:.1f}, "
        f"flanks {d['window_flank_deg'][0]:.0f} / {d['window_flank_deg'][1]:.0f} deg from vertical",
        f"  4 x M3 x {d['screw_len']} ISO 4762 into CNC Kitchen inserts (hole {d['insert_bore']:.2f} x {d['insert_hole_depth']:.2f}), "
        f"tip at z {d['screw_tip_z']:.2f}",
        "  lid holes " + ", ".join(f"{k} " + (f"d {h['d']:.2f}" if h["kind"] == "circle" else f"{h['size'][0]:.2f} x {h['size'][1]:.2f}")
                                  for k, h in d["lid_holes"].items()),
        "  walls " + ", ".join(f"{k} {v:.2f}" for k, v in d["walls"].items()),
    ])


if __name__ == "__main__":
    validate()
    print(report())
    print("  ok")
