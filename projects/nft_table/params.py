r"""NFT table v2: one level of six Growrilla 100x50 channels on a 2040/2020 table, an HDX 27 gal tote under the low
end, standard PVC plumbing (ASTM D1785 pipe, D2466 Sch 40 fittings, Spears catalogue Dec 2025) and printed PETG
parts for every interface nobody publishes. Supersedes archive/nft_rack_v1.

Everything downstream (shapes.py, build.py, the part files, table.py, freecad_view.py, tests) reads `derive()`.
Every number here is a (value, TAG, source) triple; validate() refuses an untagged one and fails by name on any
load-bearing PLACEHOLDER (cad-design-review rule 2: unbuyable or unsourced = failing test).

    STANDARD     a published standard (named)
    VENDOR       published by the vendor of the part used (sheet and page named)
    VAULT        from the T1TRTA grow-system notes (file named)
    INFERRED     follows from a published number or drawing, not stated (says from what)
    DESIGN       this model's choice; the part that meets it is designed to tolerate it
    CONVENIENCE  set to draw the model, awaits derivation (design review rule 1)
    PLACEHOLDER  drawn for a part whose geometry is unknown

Coordinates: origin on the floor at the front-left leg's outer corner. +X right across the six channels, +Y back
(downhill), +Z up. Channels run along +Y and fall toward the back: feed at the front (high) end, drain at the back.

    side view (channel centre)                         plan

     feed line   P2 _____lid____________ P3            y ^  collector (level) -- tee -- 2 in drop to the tote
        ___     [|_______channel________|]             |   +--P4-P4-P4-+-P4-P4-P4--+     back rail (2040)
       /   \     ^P1        ^P1       ^P1 \  spout     |   |   [ tote under the low end, centred in X ] |
      P5 tap   front rail  mid rail  back rail  O      |   +--------------------------+     mid rail (2040)
      =manifold (under the front rail)          coll.  |   |  C1  C2  C3  C4  C5  C6  |
                                                       |   +--------------------------+     front rail (2040)
                                                       |   Y-run | manifold under the front rail ---- cap
                                                       +-----------------------------------> x
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad import plumbing as P
from cacad.lumber import cut_plan
from cacad.registries import materials as MAT
from cacad.registries.reservoirs import RESERVOIRS
from projects.nft_table import shapes as S

IN = 25.4
G = 9.80665
TAGS = ("STANDARD", "VENDOR", "VAULT", "INFERRED", "DESIGN", "CONVENIENCE", "PLACEHOLDER")


def _i(x):
    return x * IN


SPEARS = "Spears 'Schedule 40 Fittings Technical' Dec 2025 (SCH40TECH_40-1_T), ref/vendor_sheets/pvc"
SPEARS_VALVE = "Spears Valves Technical 'Compact Ball Valves' Dec 2024 p.5 (VALTECH), ref/vendor_sheets/pvc"
MISUMI = "Misumi FA catalogue 2010 (us.misumi-ec.com/pdf/fa/2010), ref/vendor_sheets/frame"
MISUMI19 = "Misumi US catalogue 2019 p.2686 'Aluminum Extrusions (HFS5 Series)', ref/vendor_sheets/frame"
LG = "Little Giant spec sheet 995110 'PE-2.5F Series' (fele.widen.net), ref/vendor_sheets/pump"
GROWRILLA = "Growrilla 'Hydroponics NFT channel 100x50mm length 2 meters' (vault clipping 2025-05-04 and live EN page)"
HARVEL = "GF Harvel 'Engineering & Design Data' (c)2012, 'Average Friction Loss for PVC and CPVC Fittings in Equivalent Feet'"
PARKER = "Parker O-Ring Handbook ORD 5700A/US (2001), Design Chart 4-2 'Face Type Seals' p.4-14 and Table 4-1"
ETB = "Engineering ToolBox"

# ---------------------------------------------------------------------------
# Facts and rules: key -> (value, tag, source)
# ---------------------------------------------------------------------------
SPEC = MappingProxyType({
    # Growrilla channel
    "channel_w": (100.0, "VENDOR", f"{GROWRILLA}: width 100 mm"),
    "channel_h": (48.0, "VENDOR", f"{GROWRILLA}: height 48 mm (also Growrilla IT page). Taken as the body without the "
                  "lid. The floor profile ('special design') is not published: P1 bears on the walls and corners only"),
    "channel_t": (2.5, "VENDOR", f"{GROWRILLA}: thickness 2.5 mm"),
    "channel_len": (2000.0, "VENDOR", f"{GROWRILLA}: length 2 m, used uncut"),
    "channel_mass": (4.0, "VENDOR", f"{GROWRILLA}: 4 kg per 2 m channel"),
    "lid_t": (2.5, "INFERRED", "lid thickness not published; drawn at the 2.5 mm channel thickness. Nothing printed "
              "touches the lid: P2 and P3 stop below the lid line"),
    "site_hole_d": (48.0, "VENDOR", f"{GROWRILLA}: 48 mm holes for 5 cm net pots. CONFLICT: Growrilla's IT channel page "
                    "(ref/vendor_sheets/pp_grommets_tote_pump/growrilla_canalina_100x50_2m.html) says 'Diametro fori "
                    "40mm'. 48 kept as instructed"),
    "site_pitch": (250.0, "VENDOR", f"{GROWRILLA}: holes at 250 mm (8 per 2 m)"),
    "n_sites": (8, "VENDOR", f"{GROWRILLA}: 8 holes per 2 m at 250 mm"),
    # vault rules
    "slope_min": (1 / 40, "VAULT", "NFT/vinylDOwn.md 'Slope': 1:30 to 1:40"),
    "slope_max": (1 / 30, "VAULT", "NFT/vinylDOwn.md 'Slope': 1:30 to 1:40"),
    "flow_min_lpm": (1.0, "VAULT", "NFT/vinylDOwn.md 'Optimal Flow Rates': 1 to 2 L/min per channel"),
    "flow_max_lpm": (2.0, "VAULT", "NFT/vinylDOwn.md 'Optimal Flow Rates': 1 to 2 L/min per channel"),
    "film_depth": (_i(0.25), "VAULT", "multiLVLRack.md: film depth 1/8-1/4 in; the deeper end is the operating load"),
    # frame: Misumi HFS5
    "a2020": (20.0, "VENDOR", f"HFS5-2020 section 20 x 20 ({MISUMI} p.2239)"),
    "I2020": (0.742e4, "VENDOR", f"HFS5-2020 Ix = Iy = 0.742e4 mm^4 ({MISUMI} p.2239; {MISUMI19})"),
    "m2020": (0.50, "VENDOR", f"HFS5-2020 0.50 kg/m ({MISUMI} p.2239)"),
    "I2040_edge": (5.13e4, "VENDOR", f"HFS5-2040 Iy = 5.13e4 mm^4, the strong axis: 40 mm vertical ({MISUMI19}; Ix = 1.358e4)"),
    "m2040": (0.88, "VENDOR", f"HFS5-2040 0.88 kg/m ({MISUMI19})"),
    "E_al": (69680.0, "INFERRED", f"{MISUMI} p.2433 'Load Capacity Guideline': HFS5-2020 allowable 99 N at L 500 mm for a "
             "L/1000 deflection under a central load, I 0.74e4: E = F L^3 / (48 (L/1000) I) = 69,680 N/mm^2"),
    "slot_open": (6.0, "VENDOR", f"HFS5 slot opening 6 ({MISUMI} p.2239 'Details of slot')"),
    "slot_lip": (2.0, "VENDOR", f"HFS5 slot lip 2 mm, surface to T-slot ({MISUMI} p.2239 'Details of slot')"),
    "slot_depth": (6.0, "VENDOR", f"HFS5 T-slot 4 mm under the 2 mm lip: surface to slot floor 6 ({MISUMI} p.2239)"),
    # loads
    "rho_water": (1.0e-6, "STANDARD", "water 1000 kg/m^3 = 1e-6 kg/mm^3"),
    "plant_mass": (0.5, "DESIGN", "one grown plant with net pot and medium per site, kg (lettuce-class crop)"),
    # PVC
    "E_pvc": (2758.0, "STANDARD", "ASTM D1784 cell class 12454 (PVC 1120, the D1785 pipe compound): tensile modulus "
              "400,000 psi = 2758 N/mm^2"),
})


def spec(key: str):
    return SPEC[key][0]


# ---------------------------------------------------------------------------
# Bought parts. Each row: what, ref (standard or catalogue page), and fields (value mm, tag, source).
# ---------------------------------------------------------------------------
BOUGHT = MappingProxyType({
    # ---- pipe, ASTM D1785 Sch 40 (Spears p.4 table)
    "pvc12": dict(what="1/2 in PVC Sch 40 IPS size (the 438-073 spigot)", ref=f"ASTM D1785, {SPEARS} p.4",
                  od=(_i(0.840), "STANDARD", "D1785 1/2: mean OD .840 in +/- .004"),
                  wall=(_i(0.109), "STANDARD", "D1785 1/2 Sch 40: min wall .109 in")),
    "pvc34": dict(what="3/4 in PVC Sch 40 pipe: riser, runs, manifold, bypass", ref=f"ASTM D1785, {SPEARS} p.4",
                  od=(_i(1.050), "STANDARD", "D1785 3/4: mean OD 1.050 in"),
                  od_tol=(_i(0.004), "STANDARD", "D1785 3/4: OD tolerance +/- .004 in"),
                  wall=(_i(0.113), "STANDARD", "D1785 3/4 Sch 40: min wall .113 in"),
                  stick=(_i(120.0), "VENDOR", "sold in 10 ft sticks (Charlotte DC-PR p.27: Sch 40 pipe in 10 and 20 ft)")),
    "pvc2": dict(what="2 in PVC Sch 40 pipe: collector and return drop", ref=f"ASTM D1785, {SPEARS} p.4",
                 od=(_i(2.375), "STANDARD", "D1785 2: mean OD 2.375 in"),
                 od_tol=(_i(0.006), "STANDARD", "D1785 2: OD tolerance +/- .006 in"),
                 wall=(_i(0.154), "STANDARD", "D1785 2 Sch 40: min wall .154 in"),
                 stick=(_i(120.0), "VENDOR", "sold in 10 ft sticks (Charlotte DC-PR p.27)")),
    # ---- D2466 socket minimums (Spears p.4)
    "d2466": dict(what="ASTM D2466 Sch 40 socket length C minimum", ref=f"ASTM D2466, {SPEARS} p.4",
                  c12=(_i(0.688), "STANDARD", "1/2: C .688 in"),
                  c34=(_i(0.719), "STANDARD", "3/4: C .719 in"),
                  c2=(_i(1.156), "STANDARD", "2: C 1.156 in")),
    "npt38": dict(what="3/8 NPT thread, the pump discharge into the 438-073", ref="ANSI/ASME B1.20.1 (Spears p.4 table)",
                  od=(_i(0.675), "STANDARD", "3/8 NPT: pipe OD .675 in (D1785 3/8 table, Spears p.4)"),
                  L2=(_i(0.4078), "STANDARD", "3/8 NPT effective thread length L .4078 in (Spears p.4, B1.20.1)")),
    # ---- fittings, Spears Sch 40
    "tee34": dict(what="3/4 in PVC Sch 40 tee S x S x S (bypass)", ref=f"Spears 401-007, {SPEARS} p.8",
                  G=(_i(9 / 16), "VENDOR", "G: centre lines to socket bottom (run)"),
                  H=(_i(1 + 9 / 16), "VENDOR", "H: centre lines to face (run)"),
                  G1=(_i(9 / 16), "VENDOR", "G1: centre to branch socket bottom"),
                  H1=(_i(1 + 9 / 16), "VENDOR", "H1: centre to branch face"),
                  M=(_i(1 + 5 / 16), "VENDOR", "M: hub OD")),
    "tee2": dict(what="2 in PVC Sch 40 tee S x S x S (collector centre, drop on the branch)", ref=f"Spears 401-020, {SPEARS} p.8",
                 G=(_i(1 + 3 / 8), "VENDOR", "G"), H=(_i(2 + 3 / 4), "VENDOR", "H"),
                 G1=(_i(1 + 3 / 8), "VENDOR", "G1"), H1=(_i(2 + 3 / 4), "VENDOR", "H1"),
                 M=(_i(2 + 3 / 4), "VENDOR", "M: hub OD")),
    "ell34": dict(what="3/4 in PVC Sch 40 90 deg elbow S x S", ref=f"Spears 406-007, {SPEARS} p.21",
                  G=(_i(9 / 16), "VENDOR", "G: centre lines to socket bottom"),
                  H=(_i(1 + 1 / 2), "VENDOR", "H: centre lines to face"),
                  M=(_i(1 + 5 / 16), "VENDOR", "M: hub OD (2019 edition: 1-11/32)")),
    "cap34": dict(what="3/4 in PVC Sch 40 socket cap, manifold end", ref=f"Spears 447-007, {SPEARS} p.60",
                  M=(_i(1 + 5 / 16), "VENDOR", "M: hub OD"),
                  W=(_i(1 + 5 / 16), "VENDOR", "W: cap height (2019 edition: 1-9/32)")),
    "cap2": dict(what="2 in PVC Sch 40 socket cap, collector ends", ref=f"Spears 447-020, {SPEARS} p.60",
                 M=(_i(2 + 23 / 32), "VENDOR", "M: hub OD"),
                 W=(_i(2 + 1 / 32), "VENDOR", "W: cap height")),
    "union34": dict(what="3/4 in PVC Sch 40 union, socket ends (pump removal)", ref=f"Spears 457-007 (Buna) / 497-007 (EPDM), {SPEARS} p.68",
                    L=(_i(2 + 3 / 16), "VENDOR", "L: overall length"),
                    N=(_i(11 / 32), "VENDOR", "N: socket bottom to socket bottom"),
                    nut=(_i(2.0), "VENDOR", "nut OD 2 in (2019/2012 editions: 1-31/32). The union is drawn as a cylinder "
                         "of the nut OD over its full length: an upper-bound envelope")),
    "bush38": dict(what="1/2 x 3/8 PVC reducer bushing, flush, spigot x FIPT (onto the pump's 3/8 MNPT)",
                   ref=f"Spears 438-073, {SPEARS} p.56",
                   L=(_i(1.0), "VENDOR", "L: overall length; spigot = 1/2 pipe OD"),
                   N=(_i(13 / 32), "VENDOR", "N (drawing): spigot end to the bottom of the FIPT; thread depth L - N")),
    "bush12": dict(what="3/4 x 1/2 PVC reducer bushing, flush, spigot x socket", ref=f"Spears 437-101, {SPEARS} p.54",
                   L=(_i(1 + 1 / 16), "VENDOR", "L: overall length; spigot = 3/4 pipe OD"),
                   N=(_i(9 / 32), "VENDOR", "N (drawing): spigot face to socket bottom; socket depth L - N")),
    "valve34": dict(what="3/4 in PVC compact ball valve, socket ends (bypass throttle)", ref=f"Spears 2122-007 (EPDM), {SPEARS_VALVE}",
                    A=(_i(1 + 15 / 16), "VENDOR", "A: end diameter"),
                    B=(_i(1 + 3 / 4), "VENDOR", "B socket: lay length between socket bottoms"),
                    C=(_i(3 + 7 / 8), "VENDOR", "C: overall end to end"),
                    D=(_i(2 + 11 / 16), "VENDOR", "D: valve centre line to handle top"),
                    E=(_i(3 + 1 / 4), "VENDOR", "E: handle length. The handle width is not published: the handle is drawn "
                       "as the disc it sweeps, radius E about the stem, from the body to D (an upper bound)"),
                    Cv=(74.0, "VENDOR", "Cv 74 (socket/threaded), gpm at 1 psi loss")),
    # ---- pump
    "pump": dict(what="Little Giant PE-2.5F submersible pump, item 518600", ref=LG,
                 body_w=(_i(2.9), "VENDOR", "front view: body width 2.9 in"),
                 body_d=(_i(4.6), "VENDOR", "side view: body depth 4.6 in"),
                 depth_screen=(_i(5.6), "VENDOR", "side view: 5.6 in over the inlet screen"),
                 body_h=(_i(4.0), "VENDOR", "front view: height 4.0 in"),
                 reach=(_i(4.0), "VENDOR", "front view: 4.0 in from the body's left side to the discharge tip"),
                 outlet_z=(_i(2.24), "INFERRED", "discharge axis height scaled from the 995110 drawing (175 px = 4.0 in): "
                           "not dimensioned. Nothing depends on it: the pump stands free on the tote floor and the riser "
                           "is cut to fit (cut list)"),
                 outlet_y=(_i(0.0), "INFERRED", "discharge axis taken on the body's depth centre; not dimensioned, same "
                           "as outlet_z"),
                 thread=("3/8 MNPT", "VENDOR", "'3/8-inch MNPT discharge'"),
                 cord=(_i(72.0), "VENDOR", "cord 6 ft (1.8 m)"),
                 curve=(((1.0, 475.0), (3.0, 440.0), (5.0, 395.0), (10.0, 205.0), (13.4, 0.0)), "VENDOR",
                        "GPH at 1/3/5/10 ft and shut-off 13.4 ft (series specifications table)"),
                 watts=(80.0, "VENDOR", "80 W, 1.4 A, 115 V")),
    # ---- feed line
    "tube": dict(what="1/4 in ID x 3/8 in OD clear PVC tubing, manifold tap to feed cap", ref=(
        "Kuriyama Kuri Tec K010-0406X100 (products.kuriyama.com, ref/vendor_sheets/pvc/kuriyama_K010-0406X100_page.html)"),
                 id=(_i(0.25), "VENDOR", "Nominal ID 1/4 in"),
                 od=(_i(0.375), "VENDOR", "Nominal OD 3/8 in; wall 1/16 in; 55 psi at 70 F"),
                 bend_r=(3 * _i(0.375), "DESIGN", "K010 bend radius not published; 3 x OD, the Excelon RNT rule used in v1 "
                         "(US Plastic 59022: 'minimum bend radius of 3x diameter')")),
    # ---- frame hardware, Misumi HFS5
    "bracket": dict(what="Misumi HBLFSN5 reversal tabbed bracket, 20 x 30 x 30, for HFS5", ref=f"{MISUMI} p.2245",
                    w=(20.0, "VENDOR", "width 20"), leg=(30.0, "VENDOR", "legs 30 x 30"),
                    t=(4.5, "VENDOR", "base 4.5"), load=(1176.0, "VENDOR", "allowable load 1176 N"),
                    screw=("CBM5-10 + HNTT5-5, 2 each", "VENDOR", "applicable screw / T-nut")),
    "tnut": dict(what="Misumi HNTAJ5-5 post-assembly insertion short nut, M5, for HFS5 (printed parts)", ref=f"{MISUMI} p.2267",
                 L=(10.0, "VENDOR", "length 10"), W=(8.0, "VENDOR", "body width 8"),
                 neck=(5.8, "VENDOR", "neck 5.8 (through the 6 mm slot)"),
                 h=(3.2, "VENDOR", "height 3.2 (drawing; read as the overall height under the lip)"),
                 h_body=(2.4, "VENDOR", "body height 2.4 (drawing)")),
    # ---- fasteners
    "shcs": dict(what="socket head cap screws, ISO 4762 (Misumi CBM)", ref="ISO 4762",
                 dk_M4=(7.0, "STANDARD", "M4 head dia dk max 7.0"), k_M4=(4.0, "STANDARD", "M4 head height k 4.0"),
                 dk_M5=(8.5, "STANDARD", "M5 head dia dk max 8.5"), k_M5=(5.0, "STANDARD", "M5 head height k 5.0"),
                 lengths=((6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50), "STANDARD", "ISO 4762 preferred lengths")),
    "nut": dict(what="hex nuts, ISO 4032", ref="ISO 4032",
                s_M4=(7.0, "STANDARD", "M4 across flats s 7"), m_M4=(3.2, "STANDARD", "M4 height m 3.2")),
    "insert": dict(what="heat-set insert, CNC Kitchen standard", ref="cacad.registries.materials (CNC Kitchen / Ruthex)",
                   bore_M4=(MAT.INSERT_BORE_M4, "VENDOR", "M4 x 8.1: hole 5.6"),
                   len_M4=(MAT.INSERT_LEN_M4, "VENDOR", "insert length 8.1"),
                   wall_M4=(MAT.INSERT_WALL_M4, "VENDOR", "minimum wall 2.1")),
    # ---- seals and cutters
    "oring": dict(what="AS568-205 O-ring, nitrile (manifold tap)", ref=f"AS568, {PARKER} Table 4-1 / size tables",
                  id=(_i(0.421), "STANDARD", "-205: ID .421 +/- .005 in (groove ID 8.3 leaves 1.0 mm of wall around the 6.35 passage)"),
                  cs=(_i(0.139), "STANDARD", "-2xx: cross-section .139 +/- .004 in"),
                  cs_tol=(_i(0.004), "STANDARD", "cross-section tolerance +/- .004 in")),
    "gland": dict(what="face-seal gland for a 1/8 in (.139) cross-section, sizes 201-284", ref=PARKER,
                  depth=((_i(0.101), _i(0.107)), "VENDOR", "gland depth L .101-.107 in"),
                  width=((_i(0.177), _i(0.187)), "VENDOR", "groove width G .177-.187 in (liquids)"),
                  squeeze=((0.20, 0.30), "VENDOR", "squeeze 20-30 %"),
                  od_rule=(0.99, "VENDOR", "internal pressure: groove OD = O-ring OD less 1 % (p.4-14 text)")),
    "holesaw": dict(what="1 in bi-metal hole saw (collector inlet holes)", ref="Lenox Speed Slot 1 in (cutwithlenox.com); "
                    "Milwaukee Hole Dozer 1 in",
                    d=(_i(1.0), "VENDOR", "1 in = 25.4 mm")),
    "drill": dict(what="1/4 in jobber drill (manifold tap holes)", ref="ANSI B94.11M fractional series",
                  d=(_i(0.25), "STANDARD", "1/4 in = 6.35 mm")),
    # ---- tote
    "tote": dict(what=RESERVOIRS["HDX_27GAL"].model, ref="cacad.registries.reservoirs.HDX_27GAL",
                 ext=(RESERVOIRS["HDX_27GAL"].exterior_top, "VENDOR", "exterior at top L x W x H (H overall, lid on)"),
                 int_bot=(RESERVOIRS["HDX_27GAL"].interior_bottom, "VENDOR", "interior at bottom L x W x H"),
                 lid_t_range=(RESERVOIRS["HDX_27GAL"].lid_t_range, "DESIGN", "any lid 1.5-5 mm thick: P6 accepts it"),
                 fill_depth=(RESERVOIRS["HDX_27GAL"].fill_depth, "DESIGN", "working waterline 8 in above the inside floor"),
                 freeboard=(RESERVOIRS["HDX_27GAL"].freeboard, "DESIGN", "least air under the lid after drain-back")),
})


def bv(row: str, key: str):
    return BOUGHT[row][key][0]


# ---------------------------------------------------------------------------
# Hydraulics and structure constants
# ---------------------------------------------------------------------------
HYD = MappingProxyType({
    "C_hw": (150.0, "VENDOR", f"Hazen-Williams C = 150 for PVC ({HARVEL}; {ETB} 'Hazen-Williams coefficients')"),
    "eq_tee_run": (1.4 * 304.8, "VENDOR", f"3/4 tee, flow through run: 1.4 ft ({HARVEL})"),
    "eq_tee_branch": (4.9 * 304.8, "VENDOR", f"3/4 tee, flow through branch: 4.9 ft ({HARVEL})"),
    "eq_ell": (2.0 * 304.8, "VENDOR", f"3/4 90 deg elbow: 2.0 ft ({HARVEL})"),
    "eq_union": (1.5 * 304.8, "DESIGN", f"union equivalent length not found; taken as {ETB}'s 3/4 male/female adapter 1.5 ft"),
    "eq_bushing": (1.5 * 304.8, "DESIGN", f"reducer bushing taken as {ETB}'s 3/4 adapter 1.5 ft each, at the 3/4 size"),
    "nu": (1.004e-6, "STANDARD", "kinematic viscosity of water at 20 C, m^2/s"),
    "K_entry": (0.5, "VENDOR", f"sharp-edged entrance K 0.5 ({ETB} 'Minor or dynamic loss coefficients')"),
    "K_exit": (1.0, "VENDOR", f"exit to a large volume K 1.0 ({ETB}, same page)"),
    "K_contract": (0.2, "DESIGN", "sudden contraction tube -> barb bore, area ratio about 0.5: K 0.2 (ETB table range "
                   "0.1-0.4); the Borda-Carnot expansion is computed"),
    "Cd_orifice": (0.61, "VENDOR", f"sharp-edged orifice discharge coefficient 0.61 ({ETB} 'Orifice, nozzle and venturi')"),
    "beij": (math.sqrt(3.0), "VENDOR", "level gutter with free outfall and uniform lateral inflow: upstream depth = sqrt(3) "
             "x critical depth at the outlet (Beij, 'Flow in roof gutters', J. Res. NBS 12, 1934)"),
    "beij_sf": (1.5, "DESIGN", "factor on Beij's frictionless result for the circular section and friction"),
    "K_bend90": (1.1, "VENDOR", f"sharp 90 deg turn (drilled passage into a bore) K 1.1 ({ETB} 'Minor or dynamic loss coefficients')"),
    "K_bend_smooth": (0.17, "VENDOR", f"smooth 90 deg bend, R/D about 4.5: K 0.17 ({ETB}, same page)"),
})


def hv(key: str):
    return HYD[key][0]


# ---------------------------------------------------------------------------
# Layout and printed-part inputs: key -> (value, tag, source). derive(**overrides) replaces values by key.
# ---------------------------------------------------------------------------
_SPEC_PROMPT = "owner's v2 spec (2026-10-01)"
LAYOUT = MappingProxyType({
    # ---- channels and frame
    "slope": (1 / 40, "DESIGN", f"{_SPEC_PROMPT}: 1:40, inside the vault's 1:30-1:40"),
    "z_hi": (_i(36.0), "DESIGN", f"{_SPEC_PROMPT}: channel floor 36 in at the high end (underside at the high tip)"),
    "n_ch": (6, "DESIGN", f"{_SPEC_PROMPT}: 6 channels"),
    "pitch_x": (250.0, "DESIGN", f"{_SPEC_PROMPT}: 250 mm apart across"),
    "s_front": (100.0, "DESIGN", "front rail centre from the channel's high tip, along the channel: P2 sleeve, P1 and the "
                "feed line's forward run (two bend radii) fit in front of it"),
    "s_back": (100.0, "DESIGN", "back rail centre from the channel's low tip: P1 and the P3 sleeve fit behind it"),
    "x_run_clear": (30.0, "DESIGN", "left leg inner face to the Y-run elbow's hub: the P7 under the mid rail clears the HBLFSN5 (30 along the rail)"),
    "d_run": (125.0, "DESIGN", "Y-run axis to channel 1's centre: C1's feed line rises clear of the manifold inlet elbow (H 38.1 + hub)"),
    "right_clear": (10.0, "DESIGN", "manifold cap end to the right leg's inner face"),
    "hang": (55.0, "DESIGN", "rail underside to the supply pipe axis: the pipe and its elbows pass under the HBLFSN5 "
             "brackets (30 mm down the leg); P5 ears clear the rail"),
    # ---- structure
    "defl_op": (360.0, "DESIGN", "operating load: rail deflection limit L/360"),
    "defl_flood": (200.0, "DESIGN", "flooded (drain blocked) load: rail deflection limit L/200 (owner's decision 2026-10-01: "
                   "six legs, the flooded load gated)"),
    "fall_margin": (1.0, "DESIGN", "under the flooded load the channel floor still falls at least this much between rails"),
    "leg_K": (2.0, "DESIGN", "leg effective length factor: fixed base, free top (no credit for the frame)"),
    "leg_sf": (3.0, "DESIGN", "least Euler buckling safety factor for a leg"),
    # ---- plumbing layout
    "x_riser_off": (62.0, "DESIGN", "riser axis left of the 2 in drop axis: the two P6 collars clear by 12.9 and P6 fits the A1 bed"),
    "exposed": (8.0, "DESIGN", "least bare pipe between two fitting faces"),
    "valve_clear": (15.0, "DESIGN", "valve handle sweep above the P6 collar tops"),
    "drop_above_wl": (50.0, "DESIGN", "2 in drop end above the working waterline (free fall, aerates)"),
    "bypass_above_wl": (60.0, "DESIGN", "bypass end above the working waterline"),
    "pump_wall_gap": (15.0, "DESIGN", "least air between the pump envelope and the tote's bottom interior outline"),
    "lid_t_draw": (3.0, "DESIGN", "lid drawn this thick (mid of the DESIGN 1.5-5 range); P6 is checked at both ends"),
    "tote_wall_draw": (3.0, "DESIGN", "tote wall drawn this thick at the rim (envelope); not published"),
    "tip_in": (12.0, "DESIGN", "P3 spout tip below the collector's inner crown"),
    "tip_air": (5.0, "DESIGN", "least air between a spout tip and the collector's computed water surface"),
    "coll_end": (40.0, "DESIGN", "collector pipe past the outermost P4 to the cap socket bottom"),
    "feed_dx": (75.0, "DESIGN", "feed line rises this far left of its channel's centre (between channels and P1s)"),
    "feed_top_clear": (5.0, "DESIGN", "feed line's top run above the bend it needs over the P2 barb"),
    "pipe_end_trim": (25.0, "DESIGN", "trim off each 10 ft stick before cutting"),
    "pipe_kerf": (3.0, "DESIGN", "saw kerf, PVC"),
    "feed_flow_check": (2.0, "DESIGN", "per-channel flow the feed is checked at (the vault's maximum), L/min, bypass closed"),
    "spout_capacity_x": (2.0, "DESIGN", f"{_SPEC_PROMPT}: P3 spout carries 2 x the maximum channel flow"),
    # ---- printed: shared
    "fit": (MAT.FIT_CLEAR, "DESIGN", "printed-to-bought radial clearance (cacad.registries.materials.FIT_CLEAR)"),
    "label_h": (6.0, "DESIGN", "embossed label cap height, bold (F22: >= 4 mm)"),
    "label_t": (3 * MAT.LAYER, "DESIGN", "embossed label height: three 0.2 mm layers (F22)"),
    "barb_tip_d": (_i(0.25), "DESIGN", "barb tip at the tube ID: the tube starts over it"),
    "barb_ridge_d": (7.4, "DESIGN", "barb ridge 1.05 mm over the 6.35 tube ID (16 % stretch); hose-barb practice, not a "
                     "published fit for K010: the tube is retained by the ridges, sealed by stretch"),
    "barb_ridge_len": (5.0, "DESIGN", "insertion taper per ridge"),
    "barb_n": (2, "DESIGN", "ridges per barb"),
    "barb_bore": (4.6, "DESIGN", "barb bore: wall (6.35 - 4.6)/2 = 0.875 at the tip >= 2 x nozzle"),
    "barb_base_d": (10.0, "DESIGN", "barb shank OD at its base"),
    "barb_base_h": (4.0, "DESIGN", "barb shank height"),
    # ---- P1 channel saddle
    "p1_len": (40.0, "DESIGN", "saddle length along the channel (rail top is 20)"),
    "p1_cheek_t": (4.0, "DESIGN", "cheek wall, 10 perimeters"),
    "p1_cheek_rise": (25.0, "DESIGN", "cheek top above the channel underside"),
    "p1_ledge_w": (12.0, "DESIGN", "corner ledge under the channel, inside its wall"),
    "p1_rib_w": (10.0, "DESIGN", "outer gusset run on the base"),
    "p1_rib_t": (3.2, "DESIGN", "gusset thickness, 8 perimeters"),
    "p1_screw_x": (30.0, "DESIGN", "M5 screws at +/- this x along the rail slot, under the channel floor: heads clear the ledges"),
    "p1_screw_L": (12.0, "STANDARD", "ISO 4762 M5 x 12"),
    "p1_head_clear": (1.2, "DESIGN", "screw head top to the channel underside"),
    # ---- P2 / P3 sleeves
    "sl_len": (40.0, "DESIGN", "sleeve length over the channel end"),
    "sl_wall": (3.2, "DESIGN", "sleeve side wall"),
    "sl_floor": (3.2, "DESIGN", "sleeve floor"),
    "sl_lid_gap": (5.0, "DESIGN", "sleeve walls stop this far below the channel top: the lid profile is not published"),
    "end_gap": (1.0, "DESIGN", "channel tip to the cap's end wall"),
    "groove_s": (20.0, "DESIGN", "sealant groove centre from the channel tip"),
    "groove_w": (6.0, "DESIGN", "sealant groove width (one silicone bead)"),
    "groove_d": (1.2, "DESIGN", "sealant groove depth into the sleeve"),
    "p2_end_t": (10.0, "DESIGN", "P2 end wall: holds the barb's vertical bore"),
    "p2_slot_w": (5.0, "DESIGN", "P2 outlet slot width, open to the channel, under the bore"),
    "p3_end_t": (8.0, "DESIGN", "P3 end wall: carries the label on its top"),
    "sump_len": (30.0, "DESIGN", "P3 chamber length past the channel tip"),
    "sump_d": (20.0, "DESIGN", "P3 chamber floor below the channel underside: the orifice head"),
    "spout_hole_clear": (1.5, "DESIGN", "spout OD below the 1 in hole saw, radial: the spout tilts 1:40 with the channel"),
    "spout_wall": (3.0, "DESIGN", "spout wall"),
    "spout_len": (40.0, "DESIGN", "spout below the chamber floor"),
    # ---- P4 collector saddle
    "p4_len": (42.0, "DESIGN", "P4 length along the collector: holds the hole-saw guide's teardrop (r 13.1, apex r x 1.414)"),
    "p4_shell": (4.0, "DESIGN", "clamp shell"),
    "p4_ear": (12.0, "DESIGN", "clamp ear run past the shell"),
    "p4_gap": (1.0, "DESIGN", "clamp split gap at nominal OD (closes by OD_max - OD_min = 0.30 at worst)"),
    "p4_ring_h": (10.0, "DESIGN", "guide ring height above the shell"),
    "p4_ring_wall": (3.0, "DESIGN", "guide ring wall"),
    "p4_arm_t": (6.0, "DESIGN", "hanger arm thickness"),
    "p4_plate_t": (6.8, "DESIGN", "hanger plate under the M5 heads: ISO 4762 M5 x 12 - 5.2 mm in the slot"),
    "p4_screw_L": (12.0, "STANDARD", "ISO 4762 M4 x 12, clamp: from below, nut in a side-entry trap in the upper ear"),
    # ---- P5 manifold tap
    "p5_len": (36.0, "DESIGN", "tap length along the manifold"),
    "p5_t": (12.0, "DESIGN", "tap half beyond the seat at the crown: the barb bore clears the gland (2.64 + bore 2.3 + 0.8) and the barb base fits"),
    "p5_back_t": (6.0, "DESIGN", "back half beyond the seat"),
    "p5_ear": (10.0, "DESIGN", "ear run past the seat"),
    "p5_gap": (1.0, "DESIGN", "split gap at OD_max; closes by OD_max - OD_min = 0.20 at worst"),
    "p5_barb_x": (5.0, "DESIGN", "barb axis inside the tap half's outer face"),
    "p5_screw_L": (20.0, "STANDARD", "ISO 4762 M4 x 20 through both 6 mm ears, nut in the back ear"),
    "p5_pilot_under": (0.6, "DESIGN", "printed passage pilot this much under the 1/4 in drill: its teardrop apex stays "
                       "inside the gland's 1 mm land; drilled to size after printing"),
    # ---- P6 service plate
    "p6_cut": (8.0, "DESIGN", "rough-cut window edge past each pipe"),
    "p6_overlap": (20.0, "DESIGN", "plate past the window on every side (screws, light)"),
    "p6_win_tol": (4.0, "DESIGN", "window may be cut this much oversize; the backing frame opening allows it"),
    "p6_t_low": (4.0, "DESIGN", "plate thickness at its low (back) edge"),
    "p6_pitch_deg": (2.0, "DESIGN", "plate top falls this many degrees toward its back edge: sheds"),
    "p6_collar_h": (15.0, "DESIGN", "collar above the plate top (light-tight annulus length)"),
    "p6_collar_wall": (2.4, "DESIGN", "collar wall"),
    "p6_frame_t": (10.0, "DESIGN", "backing frame: insert 8.1 + 1 + skin"),
    "p6_screw_L": (25.0, "STANDARD", "ISO 4762 M4 x 25: engages 6 at the thick edge with a 5 mm lid"),
    "p6_engage_min": (6.0, "DESIGN", "least M4 thread in the insert: 1.5 d"),
    "p6_port_d": (20.0, "DESIGN", "spare sensor port bore"),
    "p6_cord_d": (36.0, "DESIGN", "cord port: passes the pump plug (plug size not published)"),
    "p6_cord_slot": (7.0, "DESIGN", "cord clamp slot width (cord OD not published; the clamp's slot is closed by screws)"),
    # ---- P7 pipe clip
    "p7_w": (20.0, "DESIGN", "clip width along the pipe"),
    "p7_plate_t": (6.8, "DESIGN", "plate under the M5 head: ISO 4762 M5 x 12 - 5.2 in the slot"),
    "p7_ring": (3.0, "DESIGN", "ring wall"),
    "p7_open": (0.84, "DESIGN", "snap opening chord / pipe OD"),
    "p7_screw_off": (14.0, "DESIGN", "screw from the clip's centre, along the slot"),
})


ACTIVE = ("nft_table",)
COMMON = MappingProxyType(dict(bbox_tol=0.05, vol_rel=1e-3))

NOT_MODELLED = (
    "slots, end caps and screws of the extrusions (sections drawn solid; brackets drawn as their 30 x 30 x 20 envelope)",
    "T-nuts and screws (their lengths and slot engagement are checked in validate(), not drawn)",
    "the channel floor's unpublished profile (drawn flat), lid snap profile (drawn as a flat plate), net pots, plants",
    "tote lid ribs and rim lip (lid drawn flat at lid_t_draw), screw holes drilled in the lid",
    "the O-ring itself and the sealant beads (glands and grooves are drawn)",
    "the pump's power cord and plug, zip tie",
    "the feed tube's stretch over the barbs (each tube is drawn from barb tip to barb tip)",
)


def lay(d, key):
    return d["L"][key]


# ---------------------------------------------------------------------------
# frames and small helpers
# ---------------------------------------------------------------------------
def _pipe_r(row):
    od, wall = bv(row, "od"), bv(row, "wall")
    return od / 2, od / 2 - wall


def _pipe(name_kind, p0, p1, row):
    ro, ri = _pipe_r(row)
    o = tuple(b - a for a, b in zip(p0, p1))
    ln = math.sqrt(sum(x * x for x in o))
    e = P.legs_expect(name_kind, P.straight(p0, o, [(ln, ro, ri)]))
    e["length"] = ln
    e["row"] = row
    return e


def _ell(c, o1, o2, row_f, row_p):
    G, H, M = bv(row_f, "G"), bv(row_f, "H"), bv(row_f, "M")
    ro_p, ri_p = _pipe_r(row_p)
    secs = [(None, G, M / 2, ri_p), (G, H, M / 2, ro_p)]
    return P.legs_expect("fitting", P.elbow(c, o1, secs, o2, secs))


def _tee(c, run, branch, row_f, row_p):
    G, H, G1, H1, M = (bv(row_f, k) for k in ("G", "H", "G1", "H1", "M"))
    ro_p, ri_p = _pipe_r(row_p)
    run_secs = [(-H, -G, ro_p), (-G, G, ri_p), (G, H, ro_p)]
    br_secs = [(0.0, G1, ri_p), (G1, H1, ro_p)]
    return S.tee_expect("fitting", c, run, branch, M / 2, run_secs, br_secs, ri_p)


def _cap(mouth, o, row_cap, row_p, depth):
    M, W = bv(row_cap, "M"), bv(row_cap, "W")
    ro_p, _ = _pipe_r(row_p)
    return P.legs_expect("fitting", P.straight(mouth, o, [(depth, M / 2, ro_p), (W - depth, M / 2, 0.0)]))


def _add(p, o, k):
    return tuple(p[i] + k * o[i] for i in range(3))


def _rot_cols(*cols):
    return tuple(tuple(float(x) for x in c) for c in cols)


# ---------------------------------------------------------------------------
# printed part descriptions (each in its print frame: bed at z = 0, up +z)
# ---------------------------------------------------------------------------
def _barb(d, base, axis, base_on_flat=True):
    """Barb from base point along axis: shank, then ridges (insertion taper up, 45 deg back-taper down), tip at the tube
    ID. Returns (adds, tip point, bore length from base)."""
    L = d["L"]
    a = P.unit(axis)
    rb, hb = L["barb_base_d"] / 2, L["barb_base_h"]
    rr, rt, lr = L["barb_ridge_d"] / 2, L["barb_tip_d"] / 2, L["barb_ridge_len"]
    adds = [("cyl", base, a, hb, rb)]
    s = hb
    for k in range(int(L["barb_n"])):
        if k > 0:
            adds.append(("cone", _add(base, a, s), a, 1.25 * (rr - rt), rt, rr))   # back-taper, 39 deg from the axis
            s += 1.25 * (rr - rt)
        adds.append(("cone", _add(base, a, s), a, lr, rr, rt))            # insertion taper
        s += lr
    return adds, _add(base, a, s), s


def _label(d, text, c, n, up):
    L = d["L"]
    return dict(text=text, c=tuple(c), n=tuple(n), up=tuple(up), h=L["label_h"], t=L["label_t"])


def p1_desc(d, h, letter):
    """P1 channel saddle in its print frame (x across the channel, y along it (+ downhill), z up; bed on the rail
    top). h: seat height at y = 0 above the rail top."""
    L = d["L"]
    cw, c, tn = spec("channel_w"), L["fit"], d["tan"]
    t_b = d["p1_t_base"]
    wi = cw / 2 + c
    wo = wi + L["p1_cheek_t"]
    wb = wo + L["p1_rib_w"]
    y2 = L["p1_len"] / 2
    ztop = h + L["p1_cheek_rise"]
    rt = L["p1_rib_t"]
    rib_h = ztop - t_b - 2.0
    xl = cw / 2 - L["p1_ledge_w"]
    seat = [(-y2, t_b), (y2, t_b), (y2, h - y2 * tn), (-y2, h + y2 * tn)]
    add = [("box", (-wb, -y2, 0.0), (wb, y2, t_b)),
           ("box", (-wo, -y2, t_b), (-wi, y2, ztop)), ("box", (wi, -y2, t_b), (wo, y2, ztop)),
           ("prism", "x", seat, -wi, -xl), ("prism", "x", seat, xl, wi)]
    for sx in (1, -1):
        tri = [(sx * wo, t_b), (sx * wb, t_b), (sx * wo, t_b + rib_h)]
        if sx < 0:
            tri = tri[::-1]
        add += [("prism", "y", tri, -y2, -y2 + rt), ("prism", "y", tri, y2 - rt, y2)]
    rh = MAT.clearance_bore("M5") / 2
    sub = [("cyl", (sx * L["p1_screw_x"], 0.0, 0.0), (0, 0, 1), t_b, rh) for sx in (1, -1)]
    lab = _label(d, letter, ((wo + wb) / 2, 0.0, t_b), (0, 0, 1), (-1, 0, 0))
    return dict(add=add, sub=sub, corr=[], label=lab, seat=seat, ztop=ztop, t_b=t_b, wi=wi, wo=wo, xl=xl)


def _sleeve(d, y_lo, y_hi, z_fl0, z_cu, z_wt):
    """Sleeve walls over the channel end: floor (z_fl0..z_cu), side walls (z_cu..z_wt) over y_lo..y_hi."""
    L = d["L"]
    wi = spec("channel_w") / 2 + L["fit"]
    wo = wi + L["sl_wall"]
    add = [("box", (-wo, y_lo, z_fl0), (wo, y_hi, z_cu)),
           ("box", (-wo, y_lo, z_cu), (-wi, y_hi, z_wt)), ("box", (wi, y_lo, z_cu), (wo, y_hi, z_wt))]
    return add, wi, wo


def _groove(d, y_c, z_cu, z_wt, wi):
    L = d["L"]
    w, g = L["groove_w"], L["groove_d"]
    y0, y1 = y_c - w / 2, y_c + w / 2
    return [("box", (-wi, y0, z_cu - g), (wi, y1, z_cu)),
            ("box", (-wi - g, y0, z_cu - g), (-wi, y1, z_wt)), ("box", (wi, y0, z_cu - g), (wi + g, y1, z_wt))]


def p2_desc(d):
    """P2 feed cap, print frame = channel frame shifted down by the floor: x across, y along the channel from the high
    tip (+ downhill), z up from the bed (sleeve floor bottom). The channel underside sits on the floor top."""
    L = d["L"]
    th = d["theta"]
    z_cu = L["sl_floor"]
    z_wt = z_cu + spec("channel_h") - L["sl_lid_gap"]
    eg, te = L["end_gap"], L["p2_end_t"]
    y_lo = -eg - te
    add, wi, wo = _sleeve(d, y_lo, L["sl_len"], 0.0, z_cu, z_wt)
    add.append(("box", (-wi, y_lo, z_cu), (wi, -eg, z_wt)))                       # end wall
    sub = _groove(d, L["groove_s"], z_cu, z_wt, wi)
    # barb, world-vertical: local axis (0, -sin th, cos th); shank sunk until its base disc is inside the wall
    a = (0.0, -math.sin(th), math.cos(th))
    rb = L["barb_base_d"] / 2
    yb = y_lo + te / 2
    sink = rb * math.tan(th) + 0.2
    base = _add((0.0, yb, z_wt), a, -sink)
    badd, tip, s_tip = _barb(d, base, a)
    add += badd
    corr = [-math.pi * rb * rb * sink]                                              # shank inside the wall
    # bore down from the tip into the wall, then a slot open to the channel, down to 1 mm over the floor
    rbo = L["barb_bore"] / 2
    z_bend = z_cu + 6.0
    bore_len = (tip[2] - z_bend) / math.cos(th)
    bore0 = _add(tip, a, -bore_len)
    sub.append(("cyl", bore0, a, bore_len, rbo))
    sw = L["p2_slot_w"]
    sub.append(("box", (-sw / 2, yb - rbo, z_cu + 1.0), (sw / 2, -eg, bore0[2])))
    lab = _label(d, "FEED", (wi / 2 + 3.0, y_lo + te / 2, z_wt), (0, 0, 1), (0, 1, 0))
    return dict(add=add, sub=sub, corr=corr, label=lab, z_cu=z_cu, z_wt=z_wt, tip=tip, axis=a, wi=wi, wo=wo, base=base,
                y_lo=y_lo, slot_bottom=z_cu + 1.0, bore_len=bore_len, s_tip=s_tip)


def p3_desc(d):
    """P3 drain cap, print frame: x across, y along the channel with 0 at the low tip (+ beyond it), z up from the
    bed (the spout tip). The channel underside sits on the sleeve floor top at z_cu."""
    L = d["L"]
    eg = L["end_gap"]
    tf, sd, sl = L["sl_floor"], L["sump_d"], L["spout_len"]
    z_cf_bot = sl
    z_cf_top = sl + tf
    z_cu = z_cf_top + sd
    z_wt = z_cu + spec("channel_h") - L["sl_lid_gap"]
    yce = L["sump_len"]
    te = L["p3_end_t"]
    wi = spec("channel_w") / 2 + L["fit"]
    wo = wi + L["sl_wall"]
    tcw = L["sl_wall"]
    add = [("box", (-wo, -L["sl_len"], z_cu - tf), (wo, eg, z_cu)),                  # sleeve floor, under the stop too
           ("box", (-wo, -L["sl_len"], z_cu), (-wi, eg, z_wt)), ("box", (wi, -L["sl_len"], z_cu), (wo, eg, z_wt)),
           ("box", (-wo, eg - tcw, z_cf_bot), (wo, eg, z_cu - tf)),                   # chamber front wall
           ("box", (-wo, eg, z_cf_bot), (wo, eg + yce, z_cf_top)),                    # chamber floor
           ("box", (-wo, eg, z_cf_top), (-wi, eg + yce, z_wt)), ("box", (wi, eg, z_cf_top), (wo, eg + yce, z_wt)),
           ("box", (-wo, eg + yce, z_cf_bot), (wo, eg + yce + te, z_wt)),             # end wall
           ("box", (-wi, 0.0, z_cu), (wi, eg, z_cu + 2.0))]                           # tip stop, below the floor top
    r_sp = d["spout_od"] / 2
    y_sp = eg + yce / 2
    add.append(("cyl", (0.0, y_sp, 0.0), (0, 0, 1), sl, r_sp))
    sub = _groove(d, -L["groove_s"], z_cu, z_wt, wi)
    sub.append(("cyl", (0.0, y_sp, 0.0), (0, 0, 1), z_cf_top, d["spout_bore"] / 2))
    lab = _label(d, "DRAIN", (0.0, eg + yce + te / 2, z_wt), (0, 0, 1), (0, 1, 0))
    return dict(add=add, sub=sub, corr=[], label=lab, z_cu=z_cu, z_wt=z_wt, z_cf_top=z_cf_top, y_sp=y_sp, wi=wi,
                wo=wo, overhang_z=[z_cu - tf, z_cf_bot])


def _clamp_block(d, R_s, g, x_out, ear, ear_t, ylen, sign):
    """Half of a split clamp in a frame with the pipe axis along z: central block |y| <= R_s + 2 from the split face
    (x = sign g/2) to x = sign x_out, ears from the split face ear_t thick out to |y| = R_s + 2 + ear. The seat
    (radius R_s about the z axis) is cut by a raw half-disc segment."""
    xs = sign * g / 2
    x0, x1 = sorted((xs, sign * x_out))
    yc = R_s + 2.0
    e0, e1 = sorted((xs, xs + sign * ear_t))
    add = [("box", (x0, -yc, 0.0), (x1, yc, ylen)),
           ("box", (e0, yc, 0.0), (e1, yc + ear, ylen)), ("box", (e0, -yc - ear, 0.0), (e1, -yc, ylen))]
    seat_vol = S.segment_area(R_s, g / 2) * ylen
    sub = [("raw", ("cyl", (0.0, 0.0, 0.0), (0, 0, 1), ylen, R_s), seat_vol)]
    return add, sub, yc, (e0, e1)


def p5_desc(d, half):
    """P5 manifold tap, print frame: z along the manifold (print up), x toward the tap (the front), y = z x x.
    The seat axis is the z axis. half: 'tap' or 'back'."""
    L = d["L"]
    R_s = d["p5_Rs"]
    g, ear, L5 = L["p5_gap"], L["p5_ear"], L["p5_len"]
    et = 6.0
    if half == "tap":
        x_out = R_s + L["p5_t"]
        add, sub, yc, (e0, e1) = _clamp_block(d, R_s, g, x_out, ear, et, L5, +1)
        zc = L5 / 2
        Lg, (ri, ro) = d["gland_L"], d["gland_r"]
        sub.append(("raw", ("gland", (R_s, 0.0, zc), Lg, ri, ro), S.gland_volume(R_s, Lg, ri, ro)))
        x_b = x_out - L["p5_barb_x"] - 0.5
        rp = bv("drill", "d") / 2
        rbo = L["barb_bore"] / 2
        x_end = x_b + rbo
        pilot = S.teardrop_poly(rp - L["p5_pilot_under"] / 2, 96, (0.0, zc))       # (y, z): drilled round after printing
        sub.append(("raw", ("prism", "x", pilot, 0.0, x_end), S.prism_above_seat(pilot, x_end, R_s, 0.0)))
        badd, tip, _ = _barb(d, (x_b, 0.0, L5), (0, 0, 1))
        add += badd
        sub.append(("cyl", (x_b, 0.0, zc), (0, 0, 1), tip[2] - zc, rbo))
        corr = [S.bore_over_poly(rbo, pilot, zc)]                                  # bore and pilot share it
        head_x = e1
        lab = _label(d, "T", ((e0 + e1) / 2, yc + ear / 2, L5), (0, 0, 1), (0, 1, 0))
    else:
        x_out = R_s + L["p5_back_t"]
        add, sub, yc, (e0, e1) = _clamp_block(d, R_s, g, x_out, ear, et, L5, -1)
        corr, tip, x_b = [], None, None
        lab = _label(d, "B", ((e0 + e1) / 2, yc + ear / 2, L5), (0, 0, 1), (0, 1, 0))
    # M4 screws through the ears along x, teardrop holes (horizontal in print), nut pockets on the back
    rh = MAT.clearance_bore("M4") / 2
    for sy in (1, -1):
        yh = sy * (yc + ear / 2)
        if half == "back":
            s_af, m = bv("nut", "s_M4") + 2 * 0.15, bv("nut", "m_M4") + 0.4
            sub.append(("hex", (e0, yh, L5 / 2), (1, 0, 0), m, s_af, math.pi / 6))
            sub.append(("prism", "x", S.teardrop_poly(rh, 96, (yh, L5 / 2)), e0 + m, e1))
        else:
            sub.append(("prism", "x", S.teardrop_poly(rh, 96, (yh, L5 / 2)), e0, e1))
    return dict(add=add, sub=sub, corr=corr, label=lab, R_s=R_s, x_out=x_out, tip=tip, x_b=x_b, ears=(e0, e1), yc=yc)


def p4_desc(d, half):
    """P4 collector saddle, print frame: z along the collector (print up), x toward the back (+Y world), y up (+Z
    world). Seat axis = z axis. 'up': block, guide ring for the 1 in hole saw, hanger to the back rail; 'lo': cradle."""
    L = d["L"]
    R_s = d["p4_Rs"]
    g, ear, L4 = L["p4_gap"], L["p4_ear"], L["p4_len"]
    et = 6.0
    sh = L["p4_shell"]
    yc = R_s + 2.0
    # in this frame the split plane is y = 0 (horizontal in the world): build with the generic block in a rotated
    # sense: x <-> y swapped by constructing directly
    if half == "up":
        y_top = g / 2 + R_s + sh
        add = [("box", (-yc, g / 2, 0.0), (yc, y_top, L4)),
               ("box", (yc, g / 2, 0.0), (yc + ear, g / 2 + et, L4)), ("box", (-yc - ear, g / 2, 0.0), (-yc, g / 2 + et, L4))]
        sub = [("raw", ("cyl", (0.0, 0.0, 0.0), (0, 0, 1), L4, R_s), S.segment_area(R_s, g / 2) * L4)]
        # guide ring block on top, the hole through it and the shell down to the seat
        r_ring_i = d["ring_id"] / 2
        r_ring_o = r_ring_i + L["p4_ring_wall"]
        y_ring = y_top + L["p4_ring_h"]
        add.append(("box", (-r_ring_o, y_top, 0.0), (r_ring_o, y_ring, L4)))
        hole = S.teardrop_poly(r_ring_i, 96, (0.0, L4 / 2))
        hole_xz = hole                                                           # (x, z) polygon, prism along y
        sub.append(("raw", ("prism", "y", hole_xz, g / 2, y_ring),
                    S.prism_above_seat(hole_xz, y_ring, R_s, 0.0)))
        # hanger toward the back rail (-x), web and plate
        x_web0 = -d["p4_web_x"]
        add.append(("box", (x_web0, d["p4_web_y0"], 0.0), (-yc, d["p4_web_y1"], L4)))
        add.append(("box", (x_web0 - L["p4_plate_t"], d["p4_plate_y0"], 0.0), (x_web0, d["p4_plate_y1"], L4)))
        rh = MAT.clearance_bore("M5") / 2
        sub.append(("prism", "x", S.teardrop_poly(rh, 96, (d["p4_slot_y"], L4 / 2)), x_web0 - L["p4_plate_t"], x_web0))
        # clamp screws from below: clearance through the ear up to a side-entry nut trap, then through the skin
        rhc = MAT.clearance_bore("M4") / 2
        s_af, m = bv("nut", "s_M4") + 2 * 0.15, bv("nut", "m_M4") + 0.4
        y_t0 = g / 2 + 1.6
        for sx in (1, -1):
            xh = sx * (yc + ear / 2)
            sub.append(("prism", "y", S.teardrop_poly(rhc, 96, (xh, L4 / 2)), g / 2, y_t0))
            xa, xb = sorted((xh - sx * s_af / 2, sx * (yc + ear)))
            sub.append(("box", (xa, y_t0, L4 / 2 - s_af / 2), (xb, y_t0 + m, L4 / 2 + s_af / 2)))
            sub.append(("prism", "y", S.teardrop_poly(rhc, 96, (xh, L4 / 2)), y_t0 + m, g / 2 + et))
        lab = _label(d, "P4", ((x_web0 - yc) / 2, (d["p4_web_y0"] + d["p4_web_y1"]) / 2, L4), (0, 0, 1), (-1, 0, 0))
        corr = []
    else:
        y_bot = -(g / 2 + R_s + sh)
        add = [("box", (-yc, y_bot, 0.0), (yc, -g / 2, L4)),
               ("box", (yc, -g / 2 - et, 0.0), (yc + ear, -g / 2, L4)), ("box", (-yc - ear, -g / 2 - et, 0.0), (-yc, -g / 2, L4))]
        sub = [("raw", ("cyl", (0.0, 0.0, 0.0), (0, 0, 1), L4, R_s), S.segment_area(R_s, g / 2) * L4)]
        rhc = MAT.clearance_bore("M4") / 2
        for sx in (1, -1):
            xh = sx * (yc + ear / 2)
            sub.append(("prism", "y", S.teardrop_poly(rhc, 96, (xh, L4 / 2)), -g / 2 - et, -g / 2))
        lab = _label(d, "P4", (yc - 6.0, y_bot + 5.0, L4), (0, 0, 1), (0, 1, 0))
        corr = []
    return dict(add=add, sub=sub, corr=corr, label=lab, R_s=R_s, yc=yc)


def p7_desc(d, variant):
    """P7 pipe clip, print frame: z along the pipe (print up), y toward the rail (+Z world), x = y x z.
    variant 'along': the pipe runs along the rail slot (screw offset along the pipe);
    'across': the pipe crosses the rail (screw offset across, along x)."""
    L = d["L"]
    ri = d["p7_ri"]
    ro = ri + L["p7_ring"]
    w = L["p7_w"]
    hang = L["hang"]
    tp = L["p7_plate_t"]
    beta = math.asin(L["p7_open"] * bv("pvc34", "od") / 2 / ri)
    a0, a1 = -math.pi / 2 + beta, 3 * math.pi / 2 - beta
    st = 8.0
    add = [("ring", (0.0, 0.0, 0.0), "z", 0.0, w, ri, ro, a0, a1),
           ("box", (-st / 2, ri, 0.0), (st / 2, hang - tp, w))]
    corr = [-(S.chord_integral(ro, st / 2) - 2 * (st / 2) * ri) * w]               # stem inside the ring wall
    off = L["p7_screw_off"]
    rh = MAT.clearance_bore("M5") / 2
    if variant == "along":
        add.append(("box", (-10.0, hang - tp, 0.0), (10.0, hang, w + off + 6.0)))
        sub = [("prism", "y", S.teardrop_poly(rh, 96, (0.0, w + off)), hang - tp, hang)]
        screw = (0.0, hang, w + off)
    else:
        add.append(("box", (-10.0, hang - tp, 0.0), (off + 8.0, hang, w)))
        sub = [("prism", "y", S.teardrop_poly(rh, 96, (off, w / 2)), hang - tp, hang)]
        screw = (off, hang, w / 2)
    if variant == "along":
        lab = _label(d, "P7", (0.0, hang - tp / 2, w + off + 6.0), (0, 0, 1), (0, 1, 0))
    else:
        lab = _label(d, "P7", (off - 4.0, hang - tp / 2, w), (0, 0, 1), (0, 1, 0))
    return dict(add=add, sub=sub, corr=corr, label=lab, screw=screw, ri=ri, ro=ro, a0=a0, a1=a1)


# ---------------------------------------------------------------------------
# derive
# ---------------------------------------------------------------------------
def derive(**overrides) -> dict:
    unknown = [k for k in overrides if k not in LAYOUT]
    assert not unknown, f"derive: unknown overrides {unknown}"
    L = {k: v[0] for k, v in LAYOUT.items()}
    L.update(overrides)
    d = dict(L=L, expect={}, joints=[], notes=[])
    th = math.atan(L["slope"])
    d.update(theta=th, tan=math.tan(th), sin=math.sin(th), cos=math.cos(th))
    _derive_fasteners(d)
    _derive_frame(d)
    _derive_channels(d)
    _derive_structure(d)
    d["p6_t_hi_est"] = L["p6_t_low"] + MAT.BED[1] * math.tan(math.radians(L["p6_pitch_deg"]))
    _derive_tote(d)
    _derive_return(d)
    _derive_supply(d)
    _derive_p6(d)
    _derive_feed(d)
    _derive_hydraulics(d)
    _derive_buy(d)
    lo = tuple(min(e["lo"][i] for e in d["expect"].values()) for i in range(3))
    hi = tuple(max(e["hi"][i] for e in d["expect"].values()) for i in range(3))
    d["bbox"] = (lo, hi)
    return d


def _derive_fasteners(d):
    """Screw stacks into the HFS5 slot: an HNTAJ5 sits under the 2 mm lip with 0.8 of its 3.2 in the lip (neck); the
    screw tip must pass the nut fully (lip - neck + h) and stay off the slot floor (slot_depth)."""
    tn = BOUGHT["tnut"]
    p_min = spec("slot_lip") - (bv("tnut", "h") - bv("tnut", "h_body")) + bv("tnut", "h")
    p_max = spec("slot_depth")
    d["slot_p"] = (p_min, p_max)
    d["slot_p_mid"] = (p_min + p_max) / 2
    d["p1_t_base"] = d["L"]["p1_screw_L"] - d["slot_p_mid"]
    L = d["L"]
    d["spout_od"] = bv("holesaw", "d") - 2 * L["spout_hole_clear"]
    d["spout_bore"] = d["spout_od"] - 2 * L["spout_wall"]
    d["p7_t_check"] = d["L"]["p7_plate_t"]
    d["p4_plate_check"] = d["L"]["p4_plate_t"]
    del tn


def _derive_frame(d):
    L = d["L"]
    a = spec("a2020")
    cw = spec("channel_w")
    # x: left leg at 0..a, Y-run, channel 1, ..., channel 6, right leg
    x_run = a + L["x_run_clear"] + bv("ell34", "M") / 2
    xc = [x_run + L["d_run"] + i * L["pitch_x"] for i in range(L["n_ch"])]
    d.update(x_run=x_run, xc=xc, x_mid=(xc[0] + xc[-1]) / 2)
    # rails along the channel at s_F, s_M, s_B (channel coordinate of the underside contact)
    Lc = spec("channel_len")
    s_rail = dict(F=L["s_front"], M=(L["s_front"] + Lc - L["s_back"]) / 2, B=Lc - L["s_back"])
    # front leg front face at y = 0: front rail centre y = 10
    y_F = a / 2
    y_ch0 = y_F - s_rail["F"] * d["cos"]
    d.update(s_rail=s_rail, y_ch0=y_ch0)
    d["y_rail"] = {k: y_ch0 + s * d["cos"] for k, s in s_rail.items()}
    z_u = {k: L["z_hi"] - s * d["sin"] for k, s in s_rail.items()}
    # P1 at the back rail is the lowest: seat = base + M5 head + clearance
    h_min = d["p1_t_base"] + bv("shcs", "k_M5") + L["p1_head_clear"]
    z_rt = z_u["B"] - h_min
    d.update(z_rt=z_rt, z_under_rail=z_u)
    d["saddle_h"] = {k: z_u[k] - z_rt for k in s_rail}
    d["frame_W"] = None   # set after the manifold end is known (_derive_supply)
    d["z_sup"] = z_rt - 40.0 - L["hang"]


def _frame_parts(d, W):
    """Legs, rails, side members and brackets once the width is known."""
    a = spec("a2020")
    e = d["expect"]
    zt = d["z_rt"]
    yr = d["y_rail"]
    for k in ("F", "M", "B"):
        for side, x0 in (("L", 0.0), ("R", W - a)):
            lo, hi = (x0, yr[k] - a / 2, 0.0), (x0 + a, yr[k] + a / 2, zt)
            e[f"LEG-{k}{side}"] = S.expect_prims("frame", dict(add=[("box", lo, hi)]), (S.IDENTITY, (0, 0, 0)), stock="2020")
        lo, hi = (a, yr[k] - a / 2, zt - 40.0), (W - a, yr[k] + a / 2, zt)
        e[f"RAIL-{k}"] = S.expect_prims("frame", dict(add=[("box", lo, hi)]), (S.IDENTITY, (0, 0, 0)), stock="2040")
    for side, x0 in (("L", 0.0), ("R", W - a)):
        for k0, k1 in (("F", "M"), ("M", "B")):
            lo, hi = (x0, yr[k0] + a / 2, zt - a), (x0 + a, yr[k1] - a / 2, zt)
            e[f"SIDE-{side}{k0}{k1}"] = S.expect_prims("frame", dict(add=[("box", lo, hi)]), (S.IDENTITY, (0, 0, 0)), stock="2020")
    # HBLFSN5 envelopes: under each rail end against the leg, and under each side member end against its leg
    bl = bv("bracket", "leg")
    bw = bv("bracket", "w")
    for k in ("F", "M", "B"):
        for side, xf, sx in (("L", a, 1), ("R", W - a, -1)):
            tri = [(xf, zt - 40.0), (xf + sx * bl, zt - 40.0), (xf, zt - 40.0 - bl)]
            if sx < 0:
                tri = tri[::-1]
            e[f"BRK-R{k}{side}"] = S.expect_prims("bracket", dict(add=[("prism", "y", tri, yr[k] - bw / 2, yr[k] + bw / 2)]),
                                                  (S.IDENTITY, (0, 0, 0)))
    for side, x0 in (("L", 0.0), ("R", W - a)):
        for k0, k1 in (("F", "M"), ("M", "B")):
            for end, yf, sy in (("0", yr[k0] + a / 2, 1), ("1", yr[k1] - a / 2, -1)):
                tri = [(yf, zt - a), (yf + sy * bl, zt - a), (yf, zt - a - bl)]
                if sy < 0:
                    tri = tri[::-1]
                e[f"BRK-S{side}{k0}{k1}{end}"] = S.expect_prims(
                    "bracket", dict(add=[("prism", "x", tri, x0, x0 + bw)]), (S.IDENTITY, (0, 0, 0)))


def _channel_frame(d, xc):
    """Channel-local (x across, s along downhill, z up from the underside) -> world: rotation about X by -theta."""
    return (S.rot_x(-d["theta"]), (xc, d["y_ch0"], d["L"]["z_hi"]))


def _derive_channels(d):
    L = d["L"]
    e = d["expect"]
    cw, ch, ct, lt = spec("channel_w"), spec("channel_h"), spec("channel_t"), spec("lid_t")
    Lc = spec("channel_len")
    sites = [spec("site_pitch") / 2 + k * spec("site_pitch") for k in range(spec("n_sites"))]
    d["sites"] = sites
    d["channels"] = []
    p1h = {k: d["saddle_h"][k] for k in ("F", "M", "B")}
    d["p1"] = {k: p1_desc(d, h, k) for k, h in p1h.items()}
    d["p2"] = p2_desc(d)
    d["p3"] = p3_desc(d)
    for i, xc in enumerate(d["xc"]):
        n = f"C{i + 1}"
        F = _channel_frame(d, xc)
        body = dict(add=[("box", (-cw / 2, 0.0, 0.0), (cw / 2, Lc, ch))],
                    sub=[("box", (-cw / 2 + ct, 0.0, ct), (cw / 2 - ct, Lc, ch))])
        lid = dict(add=[("box", (-cw / 2, 0.0, ch), (cw / 2, Lc, ch + lt))],
                   sub=[("cyl", (0.0, s_, ch), (0, 0, 1), lt, spec("site_hole_d") / 2) for s_ in sites])
        e[f"{n}-body"] = S.expect_prims("channel", body, F)
        e[f"{n}-lid"] = S.expect_prims("lid", lid, F)
        for k in ("F", "M", "B"):
            pl = (S.IDENTITY, (xc, d["y_rail"][k], d["z_rt"]))
            e[f"P1-{n}-{k}"] = S.expect_prims("printed", d["p1"][k], pl, part=f"P1-{k}")
        # P2: print frame origin = channel-local (0, 0, -floor)
        p2_pl = (F[0], S.to_world(F, (0.0, 0.0, -L["sl_floor"])))
        e[f"P2-{n}"] = S.expect_prims("printed", d["p2"], p2_pl, part="P2")
        # P3: print frame origin = channel-local (0, Lc, -z_cu)
        p3_pl = (F[0], S.to_world(F, (0.0, Lc, -d["p3"]["z_cu"])))
        e[f"P3-{n}"] = S.expect_prims("printed", d["p3"], p3_pl, part="P3")
        spout_tip = S.to_world(p3_pl, (0.0, d["p3"]["y_sp"], 0.0))
        spout_top = S.to_world(p3_pl, (0.0, d["p3"]["y_sp"], d["p3"]["z_cf_top"]))
        floor_end = S.to_world(F, (0.0, Lc, ct))
        p2_tip = S.to_world(p2_pl, d["p2"]["tip"])
        d["channels"].append(dict(name=n, xc=xc, frame=F, p2_pl=p2_pl, p3_pl=p3_pl, spout_tip=spout_tip,
                                  spout_top=spout_top, floor_end=floor_end, p2_tip=p2_tip))


def _derive_structure(d):
    """Channel reactions on the three rails (continuous beam with overhangs, unit-load compatibility), rail
    deflection under six point loads plus self weight, side members and legs."""
    L = d["L"]
    g = G
    Lc = spec("channel_len")
    sF, sM, sB = d["s_rail"]["F"], d["s_rail"]["M"], d["s_rail"]["B"]
    cw, ct = spec("channel_w"), spec("channel_t")
    wi = cw - 2 * ct
    rho = spec("rho_water")

    def loads(case):
        """Point loads (s, N) along one channel."""
        pts = []
        n = 400
        ds = Lc / n
        m_body = spec("channel_mass")
        for k in range(n):
            s_ = (k + 0.5) * ds
            m = m_body / n
            if case == "operating":
                m += rho * wi * spec("film_depth") * ds
            else:
                # drain blocked: water to the P3 wall top at the low end, a wedge falling 1:slope uphill
                depth = (d["p3"]["z_wt"] - d["p3"]["z_cu"] - ct) - (Lc - s_) * d["tan"]
                m += rho * wi * max(0.0, depth) * ds
            pts.append((s_, m * g))
        for s_ in d["sites"]:
            pts.append((s_, spec("plant_mass") * g))
        return pts

    def reactions(pts):
        # statically determinate on F and B; unit load at M; compatibility: R_M = d_M(loads) / d_M(unit)
        Ls = sB - sF
        def m_simple(x, P_list):
            # bending moment at x (F <= x <= B) of a beam on supports F, B with loads anywhere (overhangs incl.)
            RB = sum(P * (s_ - sF) for s_, P in P_list) / Ls
            RF = sum(P for _, P in P_list) - RB
            m = RF * (x - sF)
            for s_, P in P_list:
                if s_ < x:
                    m -= P * (x - s_)
            return m
        def m_unit(x):
            a_ = sM - sF
            return (Ls - a_) * (x - sF) / Ls - (x - sM if x > sM else 0.0)
        num = S.quad(lambda x: m_simple(x, pts) * m_unit(x), sF, sM, 24, 8) + \
            S.quad(lambda x: m_simple(x, pts) * m_unit(x), sM, sB, 24, 8)
        den = S.quad(lambda x: m_unit(x) ** 2, sF, sM, 24, 8) + S.quad(lambda x: m_unit(x) ** 2, sM, sB, 24, 8)
        RM = num / den
        tot = sum(P for _, P in pts)
        mom_F = sum(P * (s_ - sF) for s_, P in pts) - RM * (sM - sF)
        RB = mom_F / Ls
        RF = tot - RM - RB
        return dict(F=RF, M=RM, B=RB, total=tot)

    E = spec("E_al")
    d["structure"] = {}
    xs = d["xc"]
    for case in ("operating", "flooded"):
        R = reactions(loads(case))
        out = dict(reactions=R)
        rails = {}
        for k in ("F", "M", "B"):
            # rail span between leg centres (conservative over the inner faces)
            # (W known after _derive_supply; use a closure evaluated later)
            rails[k] = R[k]
        out["per_saddle"] = rails
        d["structure"][case] = out
    d["structure"]["E"] = E


def _rail_deflection(d, W):
    """Simply supported between leg centres, six saddle point loads + self weight: max deflection by superposition."""
    a = spec("a2020")
    Ls = W - a
    E, I = spec("E_al"), spec("I2040_edge")
    w_self = spec("m2040") * G / 1000.0     # N/mm
    xs = [x - a / 2 for x in d["xc"]]       # from the left leg centre
    res = {}
    for case in ("operating", "flooded"):
        per = d["structure"][case]["per_saddle"]
        out = {}
        for k in ("F", "M", "B"):
            P_ = per[k]
            def defl(x):
                v = w_self * x * (Ls ** 3 - 2 * Ls * x * x + x ** 3) / (24 * E * I)
                for a_ in xs:
                    b_ = Ls - a_
                    if x <= a_:
                        v += P_ * b_ * x * (Ls * Ls - b_ * b_ - x * x) / (6 * E * I * Ls)
                    else:
                        v += P_ * a_ * (Ls - x) * (2 * Ls * x - x * x - a_ * a_) / (6 * E * I * Ls)
                return v
            samples = [Ls * j / 400 for j in range(401)]
            dmax = max(defl(x) for x in samples)
            at_saddles = [defl(x) for x in xs]
            end_reaction = (6 * P_ + w_self * Ls) / 2
            out[k] = dict(max=dmax, saddles=at_saddles, span=Ls, end_reaction=end_reaction, P=P_)
        res[case] = out
    # legs: the heaviest rail end, Euler with K
    z_leg = d["z_rt"]
    Pcr = math.pi ** 2 * spec("E_al") * spec("I2020") / (d["L"]["leg_K"] * z_leg) ** 2
    worst = max(res["flooded"][k]["end_reaction"] for k in ("F", "M", "B"))
    res["leg"] = dict(P=worst, Pcr=Pcr, sf=Pcr / worst, L=z_leg)
    return res


def _pipe_prims(kind, p0, p1, row, holes=()):
    """A pipe as primitives (outer cylinder minus bore), with drilled holes through one wall. Each hole:
    (s along the pipe from p0, unit direction from the axis through the wall, radius). The removed wall volume is
    integrated: over the hole's disc, sqrt(ro^2 - u^2) - sqrt(ri^2 - u^2), u across the pipe."""
    ro, ri = _pipe_r(row)
    o = P.unit(tuple(b - a for a, b in zip(p0, p1)))
    ln = math.dist(p0, p1)
    add = [("cyl", tuple(p0), o, ln, ro)]
    sub = [("cyl", tuple(p0), o, ln, ri)]
    for s_, n_, r in holes:
        c = _add(p0, o, s_)
        vol = S.quad(lambda u: 2 * math.sqrt(max(0.0, r * r - u * u)) * (math.sqrt(ro * ro - u * u) - math.sqrt(ri * ri - u * u)),
                     -r, r, 48, 4)
        sub.append(("raw", ("cyl", c, n_, ro + 1.0, r), vol))
    desc = dict(add=add, sub=sub)
    e = S.expect_prims(kind, desc, (S.IDENTITY, (0.0, 0.0, 0.0)), length=ln, row=row,
                       axis=dict(p0=tuple(p0), p1=tuple(p1)))
    return e


def _derive_tote(d):
    L = d["L"]
    ext, ib = bv("tote", "ext"), bv("tote", "int_bot")
    H = ext[2]
    z_rim = H - L["lid_t_draw"]
    z_fi = z_rim - ib[2]
    z_w = z_fi + bv("tote", "fill_depth")
    d["tote_z"] = dict(top=H, rim=z_rim, floor_in=z_fi, waterline=z_w,
                       floor_in_range=tuple(H - t - ib[2] for t in bv("tote", "lid_t_range")))


def _derive_return(d):
    L = d["L"]
    e = d["expect"]
    ro2, ri2 = _pipe_r("pvc2")
    tip = d["channels"][0]["spout_tip"]
    y_coll = tip[1]
    z_coll = tip[2] + L["tip_in"] - ri2
    d.update(y_coll=y_coll, z_coll=z_coll)
    d["p4_Rs"] = (bv("pvc2", "od") + 2 * bv("pvc2", "od_tol")) / 2
    d["ring_id"] = bv("holesaw", "d") + 2 * L["fit"]
    a = spec("a2020")
    # hanger: plate on the back rail's back face over its lower slot (z_rt - 30)
    yc = d["p4_Rs"] + 2.0
    x_face = (d["y_rail"]["B"] + a / 2) - y_coll                        # print x of the rail's back face
    d["p4_web_x"] = -(x_face + L["p4_plate_t"])
    y_slot = (d["z_rt"] - 30.0) - z_coll
    d["p4_slot_y"] = y_slot
    d["p4_plate_y0"], d["p4_plate_y1"] = y_slot - 10.0, min(y_slot + 10.0, d["z_rt"] - z_coll)
    y_top = L["p4_gap"] / 2 + d["p4_Rs"] + L["p4_shell"]
    d["p4_web_y0"] = L["p4_gap"] / 2 + 6.0
    d["p4_web_y1"] = max(d["p4_plate_y1"], y_top)
    d["p4"] = {h: p4_desc(d, h) for h in ("up", "lo")}
    L4 = L["p4_len"]
    R4 = _rot_cols((0, 1, 0), (0, 0, 1), (1, 0, 0))
    # each half drawn closed onto the nominal pipe: seats are R_s (OD max / 2), the pipe is drawn at nominal OD
    dl4 = d["p4_Rs"] - bv("pvc2", "od") / 2
    for c in d["channels"]:
        pl = (R4, (c["xc"] - L4 / 2, y_coll, z_coll))
        for h, sg in (("up", -1.0), ("lo", 1.0)):
            plh = (R4, _add(pl[1], R4[1], sg * dl4))
            e[f"P4-{c['name']}-{h}"] = S.expect_prims("printed", d["p4"][h], plh, part=f"P4-{h}")
        c["p4_pl"] = pl
    # collector: two 2 in pipes, level, into a centre tee; caps at both ends; holes under each spout
    Gt, G1 = bv("tee2", "G"), bv("tee2", "G1")
    xm = d["x_mid"]
    c2 = bv("d2466", "c2")
    x_left = d["xc"][0] - L4 / 2 - L["coll_end"]
    x_right = d["xc"][-1] + L4 / 2 + L["coll_end"]
    up = (0.0, 0.0, 1.0)
    rh = bv("holesaw", "d") / 2
    left_holes = [(c["xc"] - x_left, up, rh) for c in d["channels"] if c["xc"] < xm]
    right_holes = [(c["xc"] - (xm + Gt), up, rh) for c in d["channels"] if c["xc"] > xm]
    e["RET-coll-L"] = _pipe_prims("pipe", (x_left, y_coll, z_coll), (xm - Gt, y_coll, z_coll), "pvc2", left_holes)
    e["RET-coll-R"] = _pipe_prims("pipe", (xm + Gt, y_coll, z_coll), (x_right, y_coll, z_coll), "pvc2", right_holes)
    e["RET-tee"] = _tee((xm, y_coll, z_coll), (1, 0, 0), (0, 0, -1), "tee2", "pvc2")
    e["RET-cap-L"] = _cap((x_left + c2, y_coll, z_coll), (-1, 0, 0), "cap2", "pvc2", c2)
    e["RET-cap-R"] = _cap((x_right - c2, y_coll, z_coll), (1, 0, 0), "cap2", "pvc2", c2)
    z_drop_end = d["tote_z"]["waterline"] + L["drop_above_wl"]
    e["RET-drop"] = _pipe("pipe", (xm, y_coll, z_coll - G1), (xm, y_coll, z_drop_end), "pvc2")
    H2, H21 = bv("tee2", "H"), bv("tee2", "H1")
    d["joints"] += [
        ("RET-coll-L", "RET-tee", ro2, H2 - Gt, c2, "collector L into the 2 in tee"),
        ("RET-coll-R", "RET-tee", ro2, H2 - Gt, c2, "collector R into the 2 in tee"),
        ("RET-coll-L", "RET-cap-L", ro2, c2, c2, "collector L into its cap (cap socket depth not published: D2466 C)"),
        ("RET-coll-R", "RET-cap-R", ro2, c2, c2, "collector R into its cap"),
        ("RET-drop", "RET-tee", ro2, H21 - G1, c2, "drop into the tee branch"),
    ]
    d["drop_end"] = (xm, y_coll, z_drop_end)
    d["coll_len"] = x_right - x_left


def _derive_supply(d):
    L = d["L"]
    e = d["expect"]
    a = spec("a2020")
    ro, ri = _pipe_r("pvc34")
    G, H = bv("ell34", "G"), bv("ell34", "H")
    Gt, Ht, G1, H1 = bv("tee34", "G"), bv("tee34", "H"), bv("tee34", "G1"), bv("tee34", "H1")
    c34, c12 = bv("d2466", "c34"), bv("d2466", "c12")
    ex = L["exposed"]
    xm = d["x_mid"]
    x_r = xm - L["x_riser_off"]
    y_r = d["y_rail"]["B"]
    y_F = d["y_rail"]["F"]
    z_sup = d["z_sup"]
    tz = d["tote_z"]
    pu = BOUGHT["pump"]
    z_out = tz["floor_in"] + bv("pump", "outlet_z")
    # ---- pump chain along +X into ELL-1 under the riser
    Lu, Nu = bv("union34", "L"), bv("union34", "N")
    du = (Lu - Nu) / 2
    la = (H - G) + du + ex
    b1 = x_r - G - la                       # union's far socket bottom
    b0 = b1 - Nu
    face0 = b0 - du
    L437, N437 = bv("bush12", "L"), bv("bush12", "N")
    L438, N438 = bv("bush38", "L"), bv("bush38", "N")
    x437 = b0 - L437                        # 437's socket face
    x438_end = b0 - N437                    # 438's spigot end at 437's socket bottom
    x_f = x438_end - L438                   # 438's FIPT face
    L2 = bv("npt38", "L2")
    x_tip = x_f + L2
    nip = bv("pump", "reach") - bv("pump", "body_w")
    x_body1 = x_tip - nip
    x_body0 = x_body1 - bv("pump", "body_w")
    bd, bds = bv("pump", "body_d"), bv("pump", "depth_screen")
    y_b0, y_b1 = y_r - bd / 2 - (bds - bd), y_r + bd / 2           # inlet screen toward the front
    r_npt = bv("npt38", "od") / 2
    pump = dict(add=[("box", (x_body0, y_b0, tz["floor_in"]), (x_body1, y_b1, tz["floor_in"] + bv("pump", "body_h"))),
                     ("cyl", (x_body1, y_r, z_out), (1, 0, 0), nip, r_npt)])
    e["PUMP"] = S.expect_prims("pump", pump, (S.IDENTITY, (0, 0, 0)))
    ro12, ri12 = _pipe_r("pvc12")
    bore438 = bv("npt38", "od") / 2 - _i(0.091)                     # 3/8 Sch 40 ID: INFERRED, through bore
    e["SUP-bush38"] = P.legs_expect("fitting", P.straight((x_f, y_r, z_out), (1, 0, 0),
                                    [(L438 - N438, ro12, r_npt), (N438, ro12, bore438)]))
    e["SUP-bush12"] = P.legs_expect("fitting", P.straight((x437, y_r, z_out), (1, 0, 0),
                                    [(L437 - N437, ro, ro12), (N437, ro, ri12)]))
    nut = bv("union34", "nut") / 2
    e["SUP-union"] = P.legs_expect("fitting", P.straight((face0, y_r, z_out), (1, 0, 0),
                                   [(du, nut, ro), (Nu, nut, ri), (du, nut, ro)]))
    e["SUP-pipe-a"] = _pipe("pipe", (b1, y_r, z_out), (x_r - G, y_r, z_out), "pvc34")
    e["SUP-ell-1"] = _ell((x_r, y_r, z_out), (-1, 0, 0), (0, 0, 1), "ell34", "pvc34")
    # ---- valve height from the P6 collar tops and the handle sweep; tee above it
    A_, B_, C_, D_, E_ = (bv("valve34", k) for k in ("A", "B", "C", "D", "E"))
    sd = (C_ - B_) / 2
    p6_top_est = tz["top"] + d["p6_t_hi_est"] + L["p6_collar_h"] + 4.0
    z_v = p6_top_est + E_ + L["valve_clear"]
    lb2 = (H - G) + sd + ex
    z_tee = z_v + B_ / 2 + lb2 + G
    lb1 = (H1 - G1) + (H - G) + ex
    x_bp = x_r - G1 - lb1 - G
    e["SUP-riser"] = _pipe("pipe", (x_r, y_r, z_out + G), (x_r, y_r, z_tee - Gt), "pvc34")
    e["SUP-tee"] = _tee((x_r, y_r, z_tee), (0, 0, 1), (-1, 0, 0), "tee34", "pvc34")
    e["SUP-bp-1"] = _pipe("pipe", (x_r - G1, y_r, z_tee), (x_bp + G, y_r, z_tee), "pvc34")
    e["SUP-bp-ell"] = _ell((x_bp, y_r, z_tee), (1, 0, 0), (0, 0, -1), "ell34", "pvc34")
    e["SUP-bp-2"] = _pipe("pipe", (x_bp, y_r, z_tee - G), (x_bp, y_r, z_v + B_ / 2), "pvc34")
    e["SUP-valve"] = P.legs_expect("fitting", P.straight((x_bp, y_r, z_v + C_ / 2), (0, 0, -1),
                                   [(sd, A_ / 2, ro), (B_, A_ / 2, ri), (sd, A_ / 2, ro)]))
    e["SUP-valve-handle"] = S.expect_prims("sweep", dict(add=[("cyl", (x_bp - A_ / 2, y_r, z_v), (-1, 0, 0), D_ - A_ / 2, E_)]),
                                           (S.IDENTITY, (0, 0, 0)))
    z_bp_end = tz["waterline"] + L["bypass_above_wl"]
    e["SUP-bp-3"] = _pipe("pipe", (x_bp, y_r, z_v - B_ / 2), (x_bp, y_r, z_bp_end), "pvc34")
    # ---- up to the back rail, X-run, Y-run, manifold
    e["SUP-up"] = _pipe("pipe", (x_r, y_r, z_tee + Gt), (x_r, y_r, z_sup - G), "pvc34")
    e["SUP-ell-2"] = _ell((x_r, y_r, z_sup), (0, 0, -1), (-1, 0, 0), "ell34", "pvc34")
    x_run = d["x_run"]
    y_B = d["y_rail"]["B"]
    e["SUP-xrun"] = _pipe("pipe", (x_r - G, y_r, z_sup), (x_run + G, y_r, z_sup), "pvc34")
    e["SUP-ell-3"] = _ell((x_run, y_B, z_sup), (1, 0, 0), (0, -1, 0), "ell34", "pvc34")
    e["SUP-yrun"] = _pipe("pipe", (x_run, y_B - G, z_sup), (x_run, y_F + G, z_sup), "pvc34")
    e["SUP-ell-4"] = _ell((x_run, y_F, z_sup), (0, 1, 0), (1, 0, 0), "ell34", "pvc34")
    L5 = L["p5_len"]
    x_man_end = d["xc"][-1] + L5 / 2 + ex + c34
    drill = bv("drill", "d") / 2
    holes = [(xc - (x_run + G), (0.0, -1.0, 0.0), drill) for xc in d["xc"]]
    e["SUP-manifold"] = _pipe_prims("pipe", (x_run + G, y_F, z_sup), (x_man_end, y_F, z_sup), "pvc34", holes)
    e["SUP-cap"] = _cap((x_man_end - c34, y_F, z_sup), (1, 0, 0), "cap34", "pvc34", c34)
    cap_end = x_man_end - c34 + bv("cap34", "W")
    W = cap_end + L["right_clear"] + a
    d["frame_W"] = W
    _frame_parts(d, W)
    d["frame_defl"] = _rail_deflection(d, W)
    d.update(x_r=x_r, y_r=y_r, x_bp=x_bp, z_tee=z_tee, z_v=z_v, z_out=z_out, z_bp_end=z_bp_end,
             pump_box=((x_body0, y_b0, tz["floor_in"]), (x_body1, y_b1, tz["floor_in"] + bv("pump", "body_h"))),
             x_man_end=x_man_end, cap_end=cap_end)
    d["supply_chain"] = ["PUMP", "SUP-bush38", "SUP-bush12", "SUP-union", "SUP-pipe-a", "SUP-ell-1", "SUP-riser",
                         "SUP-tee", "SUP-up", "SUP-ell-2", "SUP-xrun", "SUP-ell-3", "SUP-yrun", "SUP-ell-4",
                         "SUP-manifold", "SUP-cap"]
    d["bypass_chain"] = ["SUP-tee", "SUP-bp-1", "SUP-bp-ell", "SUP-bp-2", "SUP-valve", "SUP-bp-3"]
    ref12 = bv("bush12", "L") - bv("bush12", "N")
    d["joints"] += [
        ("PUMP", "SUP-bush38", r_npt, L2, L2, "pump 3/8 MNPT into the 438-073 FIPT (B1.20.1 L2; thread depth L - N)"),
        ("SUP-bush38", "SUP-bush12", ro12, ref12, c12, "438-073 spigot into the 437-101 1/2 socket"),
        ("SUP-bush12", "SUP-union", ro, du, c34, "437-101 spigot into the union"),
        ("SUP-pipe-a", "SUP-union", ro, du, c34, "pipe-a into the union"),
        ("SUP-pipe-a", "SUP-ell-1", ro, H - G, c34, "pipe-a into ell 1"),
        ("SUP-riser", "SUP-ell-1", ro, H - G, c34, "riser into ell 1"),
        ("SUP-riser", "SUP-tee", ro, Ht - Gt, c34, "riser into the bypass tee"),
        ("SUP-up", "SUP-tee", ro, Ht - Gt, c34, "up-pipe into the bypass tee"),
        ("SUP-bp-1", "SUP-tee", ro, H1 - G1, c34, "bypass into the tee branch"),
        ("SUP-bp-1", "SUP-bp-ell", ro, H - G, c34, "bypass into its ell"),
        ("SUP-bp-2", "SUP-bp-ell", ro, H - G, c34, "bypass down-pipe into its ell"),
        ("SUP-bp-2", "SUP-valve", ro, sd, c34, "bypass into the valve (socket (C - B)/2)"),
        ("SUP-bp-3", "SUP-valve", ro, sd, c34, "bypass outlet pipe into the valve"),
        ("SUP-up", "SUP-ell-2", ro, H - G, c34, "up-pipe into ell 2"),
        ("SUP-xrun", "SUP-ell-2", ro, H - G, c34, "X-run into ell 2"),
        ("SUP-xrun", "SUP-ell-3", ro, H - G, c34, "X-run into ell 3"),
        ("SUP-yrun", "SUP-ell-3", ro, H - G, c34, "Y-run into ell 3"),
        ("SUP-yrun", "SUP-ell-4", ro, H - G, c34, "Y-run into ell 4"),
        ("SUP-manifold", "SUP-ell-4", ro, H - G, c34, "manifold into ell 4"),
        ("SUP-manifold", "SUP-cap", ro, c34, c34, "manifold into its cap (cap socket depth not published: D2466 C)"),
    ]
    # ---- P5 taps and P7 clips
    d["p5_Rs"] = (bv("pvc34", "od") + 2 * bv("pvc34", "od_tol")) / 2
    oid = bv("oring", "id")
    cs = bv("oring", "cs")
    g_od = bv("gland", "od_rule") * (oid + 2 * cs)
    g_w = sum(bv("gland", "width")) / 2
    d["gland_L"] = sum(bv("gland", "depth")) / 2
    d["gland_r"] = (g_od / 2 - g_w, g_od / 2)
    d["p5"] = {h: p5_desc(d, h) for h in ("tap", "back")}
    R5 = _rot_cols((0, -1, 0), (0, 0, 1), (-1, 0, 0))
    dl5 = d["p5_Rs"] - bv("pvc34", "od") / 2
    for c in d["channels"]:
        pl0 = (R5, (c["xc"] + L5 / 2, y_F, z_sup))
        c["p5_pl"] = (R5, _add(pl0[1], R5[0], -dl5))
        for h, sg in (("tap", -1.0), ("back", 1.0)):
            pl = (R5, _add(pl0[1], R5[0], sg * dl5))
            e[f"P5-{c['name']}-{h}"] = S.expect_prims("printed", d["p5"][h], pl, part=f"P5-{h}")
    d["p7_ri"] = (bv("pvc34", "od") + 2 * bv("pvc34", "od_tol")) / 2
    d["p7"] = {v: p7_desc(d, v) for v in ("along", "across")}
    w7 = L["p7_w"]
    Rx = _rot_cols((0, 1, 0), (0, 0, 1), (1, 0, 0))            # pipe along +X
    Ry = _rot_cols((1, 0, 0), (0, 0, 1), (0, -1, 0))           # pipe along -Y, screw tab toward +X (off the leg)
    clips = []
    for k in (1, 2):
        clips.append(("X", x_run + G + (x_r - G - (x_run + G)) * k / 3))
    clips.append(("M", None))
    for xc in d["xc"][:-1]:
        clips.append(("F", xc + L["pitch_x"] / 2))
    d["p7_clips"] = []
    for j, (where, x) in enumerate(clips):
        if where == "M":
            pl = (Ry, (x_run, d["y_rail"]["M"] + w7 / 2, z_sup))
            v = "across"
        else:
            yy = y_r if where == "X" else y_F
            pl = (Rx, (x - w7 / 2, yy, z_sup))
            v = "along"
        name = f"P7-{j + 1}"
        e[name] = S.expect_prims("printed", d["p7"][v], pl, part=f"P7-{v}")
        d["p7_clips"].append((name, v, pl))


def _derive_feed(d):
    L = d["L"]
    e = d["expect"]
    ro, ri = bv("tube", "od") / 2, bv("tube", "id") / 2
    R = bv("tube", "bend_r")
    d["feed"] = []
    for c in d["channels"]:
        A = S.to_world(c["p5_pl"], d["p5"]["tap"]["tip"])
        F = c["p2_tip"]
        xr = c["xc"] - L["feed_dx"]
        z_top = F[2] + R + L["feed_top_clear"]
        pts = [A, (xr, A[1], A[2]), (xr, A[1], z_top), (xr, F[1], z_top), (F[0], F[1], z_top), F]
        name = f"FEED-{c['name']}"
        e[name] = P.sweep_expect("tube", pts, ro, ri, R)
        d["feed"].append(dict(name=name, pts=pts, z_top=z_top, length=e[name]["path_len"]))


def _derive_p6(d):
    """Service plate over a rough-cut lid window; ports, then the tote placed under it."""
    L = d["L"]
    e = d["expect"]
    tz = d["tote_z"]
    r34 = bv("pvc34", "od") / 2
    r2 = bv("pvc2", "od") / 2
    fit = L["fit"]
    ports = [("riser", d["x_r"], d["y_r"], r34 + fit), ("bypass", d["x_bp"], d["y_r"], r34 + fit),
             ("drop", d["x_mid"], d["y_coll"], r2 + fit), ("spare", d["x_r"], d["y_coll"], L["p6_port_d"] / 2),
             ("cord", d["x_bp"], d["y_coll"], L["p6_cord_d"] / 2)]
    cut = L["p6_cut"]
    x0w = min(x - r for _, x, _, r in ports) - cut
    x1w = max(x + r for _, x, _, r in ports) + cut
    y0w = min(y - r for _, _, y, r in ports) - cut
    y1w = max(y + r for _, _, y, r in ports) + cut
    ov = L["p6_overlap"]
    X0, Y0 = x0w - ov, y0w - ov
    Wx, Wy = (x1w - x0w) + 2 * ov, (y1w - y0w) + 2 * ov
    tl = L["p6_t_low"]
    th = tl + Wy * math.tan(math.radians(L["p6_pitch_deg"]))
    t_at = lambda yl: th - (th - tl) * yl / Wy                         # slab thickness at local y
    d["p6_box"] = dict(X0=X0, Y0=Y0, Wx=Wx, Wy=Wy, t_hi=th, t_low=tl, window=(x0w, x1w, y0w, y1w), ports=ports)
    add = [("prism", "x", [(0.0, 0.0), (Wy, 0.0), (Wy, tl), (0.0, th)], 0.0, Wx)]
    sub, corr = [], []
    cw_ = L["p6_collar_wall"]
    tops = {}
    for name, x, y, rb in ports:
        lx, ly = x - X0, y - Y0
        rc = rb + cw_
        hc = t_at(ly) + L["p6_collar_h"]
        add.append(("cyl", (lx, ly, 0.0), (0, 0, 1), hc, rc))
        corr.append(-math.pi * rc * rc * t_at(ly))
        hcone = rc - rb - 0.8
        add.append(("cone", (lx, ly, hc), (0, 0, 1), hcone, rc, rb + 0.8))
        sub.append(("cyl", (lx, ly, 0.0), (0, 0, 1), hc + hcone, rb))
        tops[name] = hc + hcone
    # zip-tie post beside the cord port, with a teardrop hole along x for the tie
    _, xc_, yc_, rcord = ports[4]
    pw, pd, ph = 10.0, 8.0, 22.0
    px0, py0 = xc_ - X0 - pw / 2, yc_ - Y0 + rcord + cw_ + 6.0
    add.append(("box", (px0, py0, 0.0), (px0 + pw, py0 + pd, t_at(py0) + ph)))
    corr.append(-pw * pd * t_at(py0 + pd / 2))
    zt_ = t_at(py0) + ph - 6.0
    sub.append(("prism", "x", S.teardrop_poly(2.5, 48, (py0 + pd / 2, zt_)), px0, px0 + pw))
    # screws
    rh = MAT.clearance_bore("M4") / 2
    screws = [(ov / 2, ov / 2), (Wx - ov / 2, ov / 2), (ov / 2, Wy - ov / 2), (Wx - ov / 2, Wy - ov / 2),
              (ov / 2, Wy / 2), (Wx - ov / 2, Wy / 2)]
    for sx, sy in screws:
        sub.append(("raw", ("cyl", (sx, sy, 0.0), (0, 0, 1), th, rh), math.pi * rh * rh * t_at(sy)))
    nrm = P.unit((0.0, (th - tl) / Wy, 1.0))
    yl_ = ov / 2                                   # front band, clear of the collars and screws
    lab = _label(d, "P6", (Wx / 2, yl_, t_at(yl_)), nrm, P.unit((0.0, 1.0, -(th - tl) / Wy)))
    d["p6_plate"] = dict(add=add, sub=sub, corr=corr, label=lab, tops=tops, screws=screws)
    d["p6_t_at"] = t_at
    pl = (S.IDENTITY, (X0, Y0, tz["top"]))
    e["P6-plate"] = S.expect_prims("printed", d["p6_plate"], pl, part="P6-plate")
    # backing frame under the lid
    tf = L["p6_frame_t"]
    tol = L["p6_win_tol"]
    lt = L["lid_t_draw"]
    f_add = [("box", (0.0, 0.0, 0.0), (Wx, Wy, tf))]
    f_sub = [("box", (x0w - tol - X0, y0w - tol - Y0, 0.0), (x1w + tol - X0, y1w + tol - Y0, tf))]
    ri_ins = bv("insert", "bore_M4") / 2
    for sx, sy in screws:
        f_sub.append(("cyl", (sx, sy, 0.0), (0, 0, 1), tf, ri_ins))
    d["p6_frame"] = dict(add=f_add, sub=f_sub, corr=[], label=_label(d, "P6", (Wx / 2, (ov - tol) / 2, tf), (0, 0, 1), (0, 1, 0)))
    # printed lid face down; flipped about X into place: local z 0 at the lid underside, local y -> world -y
    e["P6-frame"] = S.expect_prims("printed", d["p6_frame"], (S.rot_x(math.pi), (X0, Y0 + Wy, tz["top"] - lt)), part="P6-frame")
    # spare-port plug and cord bushing, printed flange down, placed flipped into their collars
    flip = S.rot_x(math.pi)
    rp = L["p6_port_d"] / 2
    plug = dict(add=[("cyl", (0, 0, 0), (0, 0, 1), 3.0, rp + 0.8 + 2.0),
                     ("cyl", (0, 0, 3.0), (0, 0, 1), L["p6_collar_h"], rp - fit)], sub=[], corr=[],
                label=_label(d, "S", (0.0, 0.0, 3.0 + L["p6_collar_h"]), (0, 0, 1), (0, 1, 0)))
    d["p6_plug"] = plug
    sx_, sy_ = ports[3][1], ports[3][2]
    e["P6-plug"] = S.expect_prims("printed", plug, (flip, (sx_, sy_, tz["top"] + tops["spare"] + 3.0)), part="P6-plug")
    w = L["p6_cord_slot"]
    def cpoly(R_):
        ph0 = math.pi / 2 + math.asin(w / 2 / R_)
        ph1 = math.pi / 2 - math.asin(w / 2 / R_) + 2 * math.pi
        n = 96
        pts = [(R_ * math.cos(ph0 + (ph1 - ph0) * k / n), R_ * math.sin(ph0 + (ph1 - ph0) * k / n)) for k in range(n + 1)]
        pts.append((w / 2, 0.0))
        pts += [(w / 2 * math.cos(-a_), w / 2 * math.sin(-a_)) for a_ in [math.pi * k / 24 for k in range(1, 24)]]
        pts.append((-w / 2, 0.0))
        return pts
    rcd = L["p6_cord_d"] / 2
    bush = dict(add=[("prism", "z", cpoly(rcd + 0.8 + 2.0), 0.0, 3.0), ("prism", "z", cpoly(rcd - fit), 3.0, 3.0 + L["p6_collar_h"])],
                sub=[], corr=[], label=_label(d, "C", (0.0, -(rcd - fit) / 2 - 2.0, 3.0 + L["p6_collar_h"]), (0, 0, 1), (0, 1, 0)))
    d["p6_cord"] = bush
    cx_, cy_ = ports[4][1], ports[4][2]
    e["P6-cord"] = S.expect_prims("printed", bush, (flip, (cx_, cy_, tz["top"] + tops["cord"] + 3.0)), part="P6-cord")
    # tote under the window, centred in X on the collector
    ext, ib = bv("tote", "ext"), bv("tote", "int_bot")
    cx, cy = d["x_mid"], (y0w + y1w) / 2
    wd = L["tote_wall_draw"]
    body = dict(add=[("box", (cx - ext[0] / 2, cy - ext[1] / 2, 0.0), (cx + ext[0] / 2, cy + ext[1] / 2, tz["rim"]))],
                sub=[("rloft", (tz["floor_in"], cx, cy, ib[0], ib[1]), (tz["rim"], cx, cy, ext[0] - 2 * wd, ext[1] - 2 * wd))])
    e["TOTE-body"] = S.expect_prims("tote", body, (S.IDENTITY, (0, 0, 0)))
    lid = dict(add=[("box", (cx - ext[0] / 2, cy - ext[1] / 2, tz["rim"]), (cx + ext[0] / 2, cy + ext[1] / 2, tz["top"]))],
               sub=[("box", (x0w, y0w, tz["rim"]), (x1w, y1w, tz["top"]))])
    e["TOTE-lid"] = S.expect_prims("tote", lid, (S.IDENTITY, (0, 0, 0)))
    d["tote_xy"] = (cx, cy)


# ---------------------------------------------------------------------------
# hydraulics
# ---------------------------------------------------------------------------
GPH_TO_M3S = 3.785411784e-3 / 3600.0
LPM_TO_M3S = 1e-3 / 60.0
FT = 0.3048


def pump_q(head_m: float) -> float:
    """Pump flow (m^3/s) at a head (m), linear between the published points; 0 past shut-off."""
    pts = [(0.0, bv("pump", "curve")[0][1] + (bv("pump", "curve")[0][1] - bv("pump", "curve")[1][1]) / 2)] + list(bv("pump", "curve"))
    h_ft = head_m / FT
    if h_ft <= pts[1][0]:
        (h0, q0), (h1, q1) = pts[1], pts[2]
    else:
        for (h0, q0), (h1, q1) in zip(pts[1:], pts[2:]):
            if h0 <= h_ft <= h1:
                break
        else:
            return 0.0
    q = q0 + (q1 - q0) * (h_ft - h0) / (h1 - h0)
    return max(0.0, q) * GPH_TO_M3S


def _hw(Lm: float, Q: float, D: float) -> float:
    """Hazen-Williams head loss (m): 10.67 L Q^1.852 / (C^1.852 D^4.8704), SI."""
    return 10.67 * Lm * Q ** 1.852 / (hv("C_hw") ** 1.852 * D ** 4.8704) if Q > 0 else 0.0


def _dw(Lm: float, Q: float, D: float) -> float:
    """Darcy-Weisbach (m): laminar 64/Re, else Blasius 0.316 Re^-0.25."""
    if Q <= 0:
        return 0.0
    A = math.pi * D * D / 4
    v = Q / A
    Re = v * D / hv("nu")
    f = 64 / Re if Re < 2300 else 0.316 * Re ** -0.25
    return f * Lm / D * v * v / (2 * G)


def _vh(Q: float, D: float) -> float:
    v = Q / (math.pi * D * D / 4)
    return v * v / (2 * G)


def _derive_hydraulics(d):
    L = d["L"]
    e = d["expect"]
    tz = d["tote_z"]
    D34 = (bv("pvc34", "od") - 2 * bv("pvc34", "wall")) / 1000.0
    # supply path pump -> manifold: pipes and fittings at the 3/4 size
    pipes = ["SUP-pipe-a", "SUP-riser", "SUP-up", "SUP-xrun", "SUP-yrun", "SUP-manifold"]
    L_pipe = sum(e[n]["length"] for n in pipes) / 1000.0
    L_eq = (hv("eq_union") + 2 * hv("eq_bushing") + 4 * hv("eq_ell") + hv("eq_tee_run")) / 1000.0
    # feed line: P5 drilled passage + bore, tube, P2 bore
    Dt = bv("tube", "id") / 1000.0
    Db = L["barb_bore"] / 1000.0
    Dp = bv("drill", "d") / 1000.0
    Lt = d["feed"][0]["length"] / 1000.0
    p5 = d["p5"]["tap"]
    L_pass = (p5["x_b"] - d["p5_Rs"] + bv("pvc34", "wall")) / 1000.0
    L_b5 = (p5["tip"][2] - L["p5_len"] / 2) / 1000.0
    L_b2 = d["p2"]["bore_len"] / 1000.0
    Kb = (1 - (Db / Dt) ** 2) ** 2

    def feed(q):
        return (_dw(L_pass, q, Dp) + hv("K_entry") * _vh(q, Dp) + hv("K_bend90") * _vh(q, Db)
                + hv("K_contract") * _vh(q, Db) + _dw(L_b5, q, Db) + Kb * _vh(q, Db)
                + _dw(Lt, q, Dt) + 4 * hv("K_bend_smooth") * _vh(q, Dt)
                + hv("K_contract") * _vh(q, Db) + _dw(L_b2, q, Db) + hv("K_bend90") * _vh(q, Db) + hv("K_exit") * _vh(q, Db))

    z_top = max(f["z_top"] for f in d["feed"]) + bv("tube", "id") / 2
    static = (z_top - tz["waterline"]) / 1000.0

    def head_closed(q):
        return static + _hw(L_pipe + L_eq, 6 * q, D34) + feed(q)

    q_chk = L["feed_flow_check"] * LPM_TO_M3S
    H_req = head_closed(q_chk)
    Q_at = pump_q(H_req)
    lo, hi = 1e-9, 20 * LPM_TO_M3S
    for _ in range(100):
        mid = (lo + hi) / 2
        if pump_q(head_closed(mid)) > 6 * mid:
            lo = mid
        else:
            hi = mid
    q_closed = lo
    # bypass fully open: node at the tee (head above the waterline h_t); channels and bypass in parallel
    L_tee_up = sum(e[n]["length"] for n in ("SUP-up", "SUP-xrun", "SUP-yrun", "SUP-manifold")) / 1000.0
    L_eq_up = 3 * hv("eq_ell") / 1000.0
    L_pump_tee = sum(e[n]["length"] for n in ("SUP-pipe-a", "SUP-riser")) / 1000.0
    L_eq_pt = (hv("eq_union") + 2 * hv("eq_bushing") + hv("eq_ell")) / 1000.0
    L_bp = sum(e[n]["length"] for n in ("SUP-bp-1", "SUP-bp-2", "SUP-bp-3")) / 1000.0
    L_eq_bp = (hv("eq_tee_branch") + hv("eq_ell")) / 1000.0
    z_bp_rel = (d["z_bp_end"] - tz["waterline"]) / 1000.0
    Cv = bv("valve34", "Cv")

    def q_ch_at(h_t):
        lo_, hi_ = 0.0, 20 * LPM_TO_M3S
        if h_t <= static:
            return 0.0
        for _ in range(80):
            m = (lo_ + hi_) / 2
            if static + _hw(L_tee_up + L_eq_up, 6 * m, D34) + feed(m) < h_t:
                lo_ = m
            else:
                hi_ = m
        return lo_

    def q_bp_at(h_t):
        lo_, hi_ = 0.0, 2e-3
        if h_t <= z_bp_rel:
            return 0.0
        for _ in range(80):
            m = (lo_ + hi_) / 2
            gpm = m / 6.30902e-5
            loss = z_bp_rel + _hw(L_bp + L_eq_bp, m, D34) + (gpm / Cv) ** 2 * 0.70307 + hv("K_exit") * _vh(m, D34)
            if loss < h_t:
                lo_ = m
            else:
                hi_ = m
        return lo_

    lo, hi = 0.0, 5.0
    for _ in range(80):
        h_t = (lo + hi) / 2
        Qp = 6 * q_ch_at(h_t) + q_bp_at(h_t)
        if pump_q(h_t + _hw(L_pump_tee + L_eq_pt, Qp, D34)) > Qp:
            lo = h_t
        else:
            hi = h_t
    q_open = q_ch_at(lo)
    # P3 spout orifice
    h_s = (spec("channel_t") + L["sump_d"]) / 1000.0
    A_sp = math.pi * (d["spout_bore"] / 1000.0) ** 2 / 4
    Q_spout = hv("Cd_orifice") * A_sp * math.sqrt(2 * G * h_s)
    # collector: Beij upstream depth from the critical depth at the tee, half the channels per side
    ri2 = (bv("pvc2", "od") / 2 - bv("pvc2", "wall")) / 1000.0
    Q_half = 3 * max(q_closed, spec("flow_max_lpm") * LPM_TO_M3S)

    def area_top(y):
        th_ = 2 * math.acos(1 - y / ri2)
        return ri2 * ri2 * (th_ - math.sin(th_)) / 2, 2 * math.sqrt(max(0.0, y * (2 * ri2 - y)))
    lo, hi = 1e-6, 2 * ri2 - 1e-6
    for _ in range(100):
        y = (lo + hi) / 2
        A_, T_ = area_top(y)
        if A_ ** 3 / T_ < Q_half ** 2 / G:
            lo = y
        else:
            hi = y
    y_c = lo * 1000.0
    y_up = hv("beij") * hv("beij_sf") * y_c
    z_inv = d["z_coll"] - (bv("pvc2", "od") / 2 - bv("pvc2", "wall"))
    # drain-back into the tote when the pump stops
    wi = spec("channel_w") - 2 * spec("channel_t")
    v_ch = L["n_ch"] * wi * spec("film_depth") * spec("channel_len")
    A_up, _ = area_top(y_up / 1000.0)
    v_coll = A_up * 1e6 * d["coll_len"]
    ri34 = D34 * 1000 / 2
    v_sup = math.pi * ri34 ** 2 * sum(e[n]["length"] for n in pipes if n not in ("SUP-pipe-a",))
    v_feed = L["n_ch"] * math.pi * (bv("tube", "id") / 2) ** 2 * d["feed"][0]["length"]
    ib = bv("tote", "int_bot")
    rise = (v_ch + v_coll + v_sup + v_feed) / (ib[0] * ib[1])
    d["hyd"] = dict(static=static, z_top=z_top, H_req=H_req, Q_req=6 * q_chk, Q_at=Q_at, q_closed=q_closed,
                    q_open=q_open, feed_loss_chk=feed(q_chk), supply_loss_chk=_hw(L_pipe + L_eq, 6 * q_chk, D34),
                    Q_spout=Q_spout, h_s=h_s, Q_half=Q_half, y_c=y_c, y_up=y_up, z_inv=z_inv,
                    drain_back=dict(channels=v_ch, collector=v_coll, supply=v_sup, feed=v_feed, rise=rise),
                    L_pipe=L_pipe, L_eq=L_eq)
    # return paths: inner floor at the low tip, spout entrance, spout tip, water surface over each spout, at the
    # tee, the tee branch socket bottom, the drop end
    paths = {}
    G1 = bv("tee2", "G1")
    for c in d["channels"]:
        paths[c["name"]] = [c["floor_end"], c["spout_top"], c["spout_tip"],
                            (c["xc"], d["y_coll"], z_inv + y_up), (d["x_mid"], d["y_coll"], z_inv + y_c),
                            (d["x_mid"], d["y_coll"], d["z_coll"] - G1), d["drop_end"]]
    d["return_paths"] = paths


def _derive_buy(d):
    """Bill of materials and cut lists."""
    L = d["L"]
    e = d["expect"]
    a = spec("a2020")
    stick = bv("pvc34", "stick")
    p34 = [(n, e[n]["length"]) for n in e if e[n].get("row") == "pvc34"]
    p2 = [(n, e[n]["length"]) for n in e if e[n].get("row") == "pvc2"]
    d["cut"] = dict(pvc34=cut_plan(p34, stick, L["pipe_end_trim"], L["pipe_kerf"]),
                    pvc2=cut_plan(p2, bv("pvc2", "stick"), L["pipe_end_trim"], L["pipe_kerf"]))
    W = d["frame_W"]
    ext = [("leg", "HFS5-2020", d["z_rt"], 6), ("rail", "HFS5-2040", W - 2 * a, 3)]
    for k0, k1 in (("F", "M"), ("M", "B")):
        ext.append((f"side {k0}-{k1}", "HFS5-2020", d["y_rail"][k1] - d["y_rail"][k0] - a, 2))
    d["extrusion_cuts"] = ext
    n = L["n_ch"]
    n_p7 = len(d["p7_clips"])
    bom = [
        ("Growrilla NFT channel 100x50, 2 m, with lid", GROWRILLA, n),
        ("HDX 27 gal tote 999-27G-HDX", BOUGHT["tote"]["ref"], 1),
        ("Little Giant PE-2.5F pump (518600)", LG, 1),
        ("Misumi HFS5-2020, cut to length (legs, side members)", f"{MISUMI} p.2239", 6 + 4),
        ("Misumi HFS5-2040, cut to length (rails)", MISUMI19, 3),
        ("Misumi HBLFSN5 bracket", f"{MISUMI} p.2245", sum(1 for k in e if k.startswith("BRK-"))),
        ("Misumi CBM5-10 + HNTT5-5 (bracket fixings, 2 per bracket)", f"{MISUMI} p.2245/2261", 2 * sum(1 for k in e if k.startswith("BRK-"))),
        ("Misumi HNTAJ5-5 T-nut (P1 x2, P4, P7)", f"{MISUMI} p.2267", 2 * 3 * n + n + n_p7),
        ("ISO 4762 M5 x 12 (P1 x2, P4 hanger, P7)", "ISO 4762", 2 * 3 * n + n + n_p7),
        ("ISO 4762 M4 x 12 (P4 clamp)", "ISO 4762", 2 * n),
        ("ISO 4762 M4 x 20 (P5 clamp)", "ISO 4762", 2 * n),
        ("ISO 4762 M4 x 25 (P6)", "ISO 4762", len(d["p6_plate"]["screws"])),
        ("ISO 4032 M4 nut (P4, P5)", "ISO 4032", 4 * n),
        ("CNC Kitchen M4 x 8.1 heat-set insert (P6 frame)", BOUGHT["insert"]["ref"], len(d["p6_plate"]["screws"])),
        ("AS568-205 O-ring, nitrile (P5)", "AS568", n),
        ("3/4 in PVC Sch 40 pipe, 10 ft stick", "ASTM D1785", len(d["cut"]["pvc34"])),
        ("2 in PVC Sch 40 pipe, 10 ft stick", "ASTM D1785", len(d["cut"]["pvc2"])),
        ("3/4 in 90 deg ell 406-007", BOUGHT["ell34"]["ref"], sum(1 for k in e if k.startswith("SUP-ell") or k == "SUP-bp-ell")),
        ("3/4 in tee 401-007", BOUGHT["tee34"]["ref"], 1),
        ("3/4 in cap 447-007", BOUGHT["cap34"]["ref"], 1),
        ("3/4 in union 457-007", BOUGHT["union34"]["ref"], 1),
        ("1/2 x 3/8 bushing spig x FIPT 438-073", BOUGHT["bush38"]["ref"], 1),
        ("3/4 x 1/2 bushing spig x soc 437-101", BOUGHT["bush12"]["ref"], 1),
        ("3/4 in compact ball valve 2122-007", BOUGHT["valve34"]["ref"], 1),
        ("2 in tee 401-020", BOUGHT["tee2"]["ref"], 1),
        ("2 in cap 447-020", BOUGHT["cap2"]["ref"], 2),
        ("Kuri Tec K010-0406 1/4 x 3/8 tubing, m", BOUGHT["tube"]["ref"], round(n * d["feed"][0]["length"] / 1000.0, 2)),
        ("1 in hole saw", BOUGHT["holesaw"]["ref"], 1),
        ("1/4 in drill", BOUGHT["drill"]["ref"], 1),
        ("3/16 in drill (lid screw holes)", "ANSI B94.11M", 1),
        ("PVC primer and cement (ASTM F656 / D2564)", "ASTM D2564", 1),
        ("silicone sealant (P2/P3 grooves)", "DESIGN", 1),
        ("zip tie (cord strain relief)", "DESIGN", 1),
    ]
    d["bom"] = bom
    d["printed"] = [("P1 saddle F/M/B", 3 * n), ("P2 feed cap", n), ("P3 drain cap", n), ("P4 collector saddle up+lo", n),
                    ("P5 manifold tap tap+back", n), ("P6 plate, frame, plug, cord bushing", 1),
                    ("P7 clip along", sum(1 for c in d["p7_clips"] if c[1] == "along")),
                    ("P7 clip across", sum(1 for c in d["p7_clips"] if c[1] == "across"))]


# ---------------------------------------------------------------------------
# validate: every check runs, every failure is raised together
# ---------------------------------------------------------------------------
def _tables():
    yield "SPEC", SPEC.items()
    yield "HYD", HYD.items()
    yield "LAYOUT", LAYOUT.items()
    for row, r in BOUGHT.items():
        yield f"BOUGHT.{row}", [(k, v) for k, v in r.items() if k not in ("what", "ref")]


def gaps() -> list[str]:
    """Load-bearing values that are not sourced: any PLACEHOLDER anywhere, any CONVENIENCE (awaiting derivation)."""
    out = []
    for tname, items in _tables():
        for k, v in items:
            if v[1] in ("PLACEHOLDER", "CONVENIENCE"):
                out.append(f"{tname}.{k} ({v[1]}: {v[2]})")
    return out


def validate(**overrides) -> dict:
    """Raise AssertionError on anything not buildable, not usable or not sourced. No warnings."""
    bad = []

    def need(ok, msg):
        if not ok:
            bad.append(msg)

    for tname, items in _tables():
        for k, v in items:
            need(isinstance(v, tuple) and len(v) == 3 and v[1] in TAGS and bool(v[2]), f"{tname}.{k}: value/tag/source missing")
    for k in overrides:
        need(k in LAYOUT, f"override {k}: not a LAYOUT input")
    d = derive(**overrides)
    L = d["L"]
    a = spec("a2020")
    # rules
    need(spec("slope_min") - 1e-12 <= L["slope"] <= spec("slope_max") + 1e-12, f"slope 1:{1 / L['slope']:.0f} outside 1:30..1:40")
    need(L["pitch_x"] > 2 * (d["p1"]["F"]["wo"] + L["p1_rib_w"]), "channel pitch narrower than two P1 saddles")
    # fasteners in the HFS5 slot
    p_lo, p_hi = d["slot_p"]
    for name, L_s, t in (("P1", L["p1_screw_L"], d["p1_t_base"]), ("P7", 12.0, L["p7_plate_t"]), ("P4 hanger", 12.0, L["p4_plate_t"])):
        p_ = L_s - t
        need(p_lo - 1e-9 <= p_ <= p_hi + 1e-9, f"{name}: M5 x {L_s:.0f} through {t:.1f} reaches {p_:.1f} into the slot, needs {p_lo:.1f}..{p_hi:.1f}")
        need(L_s in bv("shcs", "lengths"), f"{name}: M5 x {L_s} not an ISO 4762 length")
    for k, v in (("p4_screw_L", L["p4_screw_L"]), ("p5_screw_L", L["p5_screw_L"]), ("p6_screw_L", L["p6_screw_L"]),
                 ("p1_screw_L", L["p1_screw_L"])):
        need(v in bv("shcs", "lengths"), f"{k}: {v} mm is not an ISO 4762 length")
    # P1 head under the channel, ledges clear of the heads
    hd = bv("shcs", "dk_M5") / 2
    need(L["p1_screw_x"] + hd <= spec("channel_w") / 2 - L["p1_ledge_w"], "P1: M5 head runs under a ledge")
    need(L["p1_screw_x"] + 5.0 <= d["p1"]["F"]["wi"], "P1: HNTAJ5 (10 long) past the cheek")
    # P4 clamp screw: lower ear 6 + gap + upper ear to the nut trap top
    et = 6.0
    eng4 = L["p4_screw_L"] - et - L["p4_gap"] - 1.6
    need(eng4 >= bv("nut", "m_M4") - 1e-9, f"P4: M4 x {L['p4_screw_L']:.0f} engages {eng4:.1f} of the {bv('nut', 'm_M4')} nut")
    need(eng4 + (bv("pvc2", "od_tol") * 2) <= bv("nut", "m_M4") + 0.4 + 0.8 + 1e-9, "P4: M4 tip pierces the ear skin at OD min")
    eng5 = L["p5_screw_L"] - 2 * et - L["p5_gap"]
    need(eng5 >= bv("nut", "m_M4"), f"P5: M4 x {L['p5_screw_L']:.0f} leaves {eng5:.1f} past the ears, needs the nut {bv('nut', 'm_M4')}")
    # P5 O-ring gland (Parker face seal): depth inside the chart band, squeeze across the cross-section tolerance
    Lg = d["gland_L"]
    dlo, dhi = bv("gland", "depth")
    need(dlo - 1e-9 <= Lg <= dhi + 1e-9, f"P5 gland depth {Lg:.3f} outside Parker {dlo:.3f}..{dhi:.3f}")
    cs, tol = bv("oring", "cs"), bv("oring", "cs_tol")
    sq = ((cs - tol - Lg) / (cs - tol), (cs + tol - Lg) / (cs + tol))
    s_lo, s_hi = bv("gland", "squeeze")
    need(s_lo - 1e-9 <= min(sq) and max(sq) <= s_hi + 1e-9, f"P5 squeeze {sq[0]:.1%}..{sq[1]:.1%} outside {s_lo:.0%}..{s_hi:.0%}")
    ri_g, ro_g = d["gland_r"]
    need(ri_g - bv("drill", "d") / 2 >= 2 * MAT.NOZZLE, f"P5: gland inner wall {ri_g - bv('drill', 'd') / 2:.2f} mm round the passage < 2 nozzles")
    need(bv("oring", "id") / 2 - bv("drill", "d") / 2 >= 1.0, "P5: O-ring ID within 1 mm of the drilled hole")
    need(ro_g < d["p5_Rs"] - 2.0, "P5: gland wider than the seat")
    need(L["p5_len"] >= 2 * ro_g + 2 * 4.0, "P5: gland too close to the tap's ends")
    need(d["p5"]["tap"]["x_b"] - L["barb_bore"] / 2 - 0.8 >= d["p5_Rs"] + Lg, "P5: barb bore cuts the gland")
    # P6 screws across the lid range
    t_at = d["p6_t_at"]
    for sx, sy in d["p6_plate"]["screws"]:
        for lt in bv("tote", "lid_t_range"):
            e_ = L["p6_screw_L"] - t_at(sy) - lt
            need(e_ >= L["p6_engage_min"], f"P6 screw at y {sy:.0f}: lid {lt} leaves {e_:.1f} mm in the insert, needs {L['p6_engage_min']}")
            need(e_ - L["p6_frame_t"] <= 10.0, f"P6 screw at y {sy:.0f}: lid {lt}: tip {e_ - L['p6_frame_t']:.1f} below the frame")
    pb = d["p6_box"]
    need(pb["Wx"] <= MAT.BED[0] and pb["Wy"] <= MAT.BED[1], f"P6 plate {pb['Wx']:.1f} x {pb['Wy']:.1f} over the A1 bed {MAT.BED[:2]}")
    band = L["p6_overlap"] - L["p6_win_tol"]
    need(band - (L["p6_overlap"] / 2 + bv("insert", "bore_M4") / 2) >= bv("insert", "wall_M4"), "P6 frame: insert wall to the opening")
    # bed fits for every printed part
    for name, e_ in d["expect"].items():
        if e_["kind"] == "printed":
            lo, hi = S.desc_bbox(e_["geom"][1], (S.IDENTITY, (0, 0, 0)))
            sz = tuple(hi[i] - lo[i] for i in range(3))
            need(all(sz[i] <= MAT.BED[i] for i in range(3)), f"{name}: {tuple(round(x) for x in sz)} over the A1 build volume")
    # structure
    fd = d["frame_defl"]
    for case, ratio in (("operating", L["defl_op"]), ("flooded", L["defl_flood"])):
        for k in ("F", "M", "B"):
            r_ = fd[case][k]
            need(r_["max"] <= r_["span"] / ratio, f"rail {k} {case}: {r_['max']:.2f} mm > L/{ratio:.0f} = {r_['span'] / ratio:.2f}")
            need(r_["end_reaction"] <= bv("bracket", "load"), f"rail {k} {case}: end {r_['end_reaction']:.0f} N > HBLFSN5 {bv('bracket', 'load')}")
    fl = fd["flooded"]
    for i in range(L["n_ch"]):
        z = [d["z_under_rail"][k] - fl[k]["saddles"][i] for k in ("F", "M", "B")]
        need(z[0] - z[1] >= L["fall_margin"] and z[1] - z[2] >= L["fall_margin"],
             f"C{i + 1}: flooded floor at the rails {[round(x, 1) for x in z]} does not fall by {L['fall_margin']}")
    need(fd["leg"]["sf"] >= L["leg_sf"], f"leg buckling SF {fd['leg']['sf']:.1f} < {L['leg_sf']}")
    # hydraulics
    h = d["hyd"]
    need(h["Q_at"] >= h["Q_req"], f"pump {h['Q_at'] / GPH_TO_M3S:.0f} GPH at {h['H_req'] / FT:.2f} ft < required {h['Q_req'] / GPH_TO_M3S:.0f}")
    need(h["q_open"] <= spec("flow_min_lpm") * LPM_TO_M3S, f"bypass open still sends {h['q_open'] / LPM_TO_M3S:.2f} L/min per channel")
    need(h["q_closed"] >= spec("flow_max_lpm") * LPM_TO_M3S, f"bypass closed gives {h['q_closed'] / LPM_TO_M3S:.2f} L/min per channel")
    q_need = max(L["spout_capacity_x"] * spec("flow_max_lpm") * LPM_TO_M3S, h["q_closed"])
    need(h["Q_spout"] >= q_need, f"P3 spout carries {h['Q_spout'] / LPM_TO_M3S:.2f} L/min < {q_need / LPM_TO_M3S:.2f}")
    tip_z = d["channels"][0]["spout_tip"][2]
    need(tip_z - (h["z_inv"] + h["y_up"]) >= L["tip_air"], f"spout tip {tip_z - (h['z_inv'] + h['y_up']):.1f} mm above the collector water, needs {L['tip_air']}")
    need(h["y_up"] < 2 * (bv("pvc2", "od") / 2 - bv("pvc2", "wall")), "collector runs full")
    for name, pts in d["return_paths"].items():
        zs = [p_[2] for p_ in pts]
        need(all(b_ < a_ for a_, b_ in zip(zs, zs[1:])), f"return path from {name} does not fall all the way: {[round(z, 1) for z in zs]}")
    # tote: waterline, drop end, pump, drain-back
    tz = d["tote_z"]
    for fi in tz["floor_in_range"]:
        wl = fi + bv("tote", "fill_depth")
        need(wl < d["drop_end"][2] - 1.0, f"waterline {wl:.0f} at or above the drop end {d['drop_end'][2]:.0f}")
        need(wl > fi + bv("pump", "body_h"), f"waterline {wl:.0f} below the pump top")
    lid_under = tz["top"] - max(bv("tote", "lid_t_range"))
    need(tz["waterline"] + h["drain_back"]["rise"] <= lid_under - bv("tote", "freeboard"),
         f"drain-back raises the water to {tz['waterline'] + h['drain_back']['rise']:.0f}, over the lid less freeboard {lid_under - bv('tote', 'freeboard'):.0f}")
    ib = bv("tote", "int_bot")
    cx, cy = d["tote_xy"]
    (px0, py0, _), (px1, py1, _) = d["pump_box"]
    m_ = L["pump_wall_gap"]
    need(cx - ib[0] / 2 + m_ <= px0 and px1 <= cx + ib[0] / 2 - m_ and cy - ib[1] / 2 + m_ <= py0 and py1 <= cy + ib[1] / 2 - m_,
         "pump outside the tote's bottom interior less the wall gap")
    for nm, (x, y, z) in (("drop", d["drop_end"]), ("bypass", (d["x_bp"], d["y_r"], d["z_bp_end"]))):
        need(abs(x - cx) < ib[0] / 2 - 30 and abs(y - cy) < ib[1] / 2 - 30, f"{nm} end not over the tote's bottom interior")
    # frame clear of the tote
    need(cx - bv("tote", "ext")[0] / 2 > a + 10 and cx + bv("tote", "ext")[0] / 2 < d["frame_W"] - a - 10, "tote hits a leg")
    # P1 inside the frame, manifold inside the legs
    need(d["xc"][-1] + d["p1"]["F"]["wo"] + L["p1_rib_w"] <= d["frame_W"] - a, "P1 at C6 past the right leg")
    # feed lines: segments long enough for the bends
    R = bv("tube", "bend_r")
    for f in d["feed"]:
        sg = [math.dist(p_, q_) for p_, q_ in zip(f["pts"], f["pts"][1:])]
        need(sg[0] >= R and sg[-1] >= R and all(x >= 2 * R for x in sg[1:-1]), f"{f['name']}: runs {[round(x) for x in sg]} too short for bend r {R:.1f}")
    lens = [f["length"] for f in d["feed"]]
    need(max(lens) - min(lens) < 1e-6, f"feed lines not equal: {[round(x, 1) for x in lens]}")
    # pipe pieces fit a stick
    for nm, pcs in (("3/4", d["cut"]["pvc34"]), ("2", d["cut"]["pvc2"])):
        need(all(pcs), f"{nm} in cut plan empty stick")
    # unsourced
    g_ = gaps()
    if g_:
        bad.append(f"{len(g_)} load-bearing values not sourced:\n    " + "\n    ".join(g_))
    assert not bad, f"nft_table: {len(bad)} failures:\n  " + "\n  ".join(bad)
    return d


# ---------------------------------------------------------------------------
# report: the design review input
# ---------------------------------------------------------------------------
def _f(x, n=1):
    return f"{x:.{n}f}"


def report(d=None) -> str:
    d = d or derive()
    L = d["L"]
    h = d["hyd"]
    fd = d["frame_defl"]
    tz = d["tote_z"]
    out = []
    w = out.append
    lo, hi = d["bbox"]
    w(f"nft_table: {L['n_ch']} Growrilla 100x50 x 2 m at {L['pitch_x']:.0f} mm, slope 1:{1 / L['slope']:.0f}, "
      f"high-end underside {L['z_hi']:.1f} ({L['z_hi'] / IN:.0f} in)")
    w(f"  envelope {_f(hi[0] - lo[0])} x {_f(hi[1] - lo[1])} x {_f(hi[2] - lo[2])} mm; frame {_f(d['frame_W'])} wide, "
      f"rail tops at {_f(d['z_rt'])}, rails at y {', '.join(f'{k} {_f(v)}' for k, v in d['y_rail'].items())}")
    w(f"  P1 seat heights over the rail: " + ", ".join(f"{k} {_f(v, 2)}" for k, v in d["saddle_h"].items()))
    w("frame (HFS5-2040 on edge rails, six HFS5-2020 legs; E from Misumi p.2433)")
    for case, ratio in (("operating", L["defl_op"]), ("flooded", L["defl_flood"])):
        R = d["structure"][case]["reactions"]
        w(f"  {case}: per channel {R['total'] / G:.1f} kg -> rails F {R['F']:.1f} / M {R['M']:.1f} / B {R['B']:.1f} N")
        for k in ("F", "M", "B"):
            r_ = fd[case][k]
            w(f"    rail {k}: span {_f(r_['span'])}, max {r_['max']:.2f} mm (limit L/{ratio:.0f} = {r_['span'] / ratio:.2f}), "
              f"end reaction {r_['end_reaction']:.0f} N (HBLFSN5 {bv('bracket', 'load'):.0f})")
    lg = fd["leg"]
    w(f"  leg: {lg['P']:.0f} N, Euler {lg['Pcr']:.0f} N (K {L['leg_K']}, L {_f(lg['L'])}): SF {lg['sf']:.1f} (min {L['leg_sf']})")
    w("supply (bypass closed) and pump")
    w(f"  required {h['Q_req'] / LPM_TO_M3S:.1f} L/min ({h['Q_req'] / GPH_TO_M3S:.0f} GPH) = {L['n_ch']} x {L['feed_flow_check']:.1f} L/min")
    w(f"  static head {h['static']:.3f} m (waterline {_f(tz['waterline'])} to the feed lines' top {_f(h['z_top'])})")
    w(f"  supply friction {h['supply_loss_chk']:.3f} m: Hazen-Williams C {hv('C_hw'):.0f}, {h['L_pipe']:.2f} m pipe + "
      f"{h['L_eq']:.2f} m fitting equivalent (union, 2 bushings, 4 ells, tee run; Harvel)")
    w(f"  feed line friction {h['feed_loss_chk']:.3f} m per channel at {L['feed_flow_check']} L/min (Darcy-Weisbach, minor losses)")
    w(f"  total {h['H_req']:.3f} m = {h['H_req'] / FT:.2f} ft; PE-2.5F there: {h['Q_at'] / GPH_TO_M3S:.0f} GPH "
      f"({h['Q_at'] / LPM_TO_M3S:.1f} L/min) vs {h['Q_req'] / GPH_TO_M3S:.0f} GPH needed")
    w(f"  bypass closed: {h['q_closed'] / LPM_TO_M3S:.2f} L/min per channel; bypass open: {h['q_open'] / LPM_TO_M3S:.2f}: "
      f"the valve sets anything between, including the vault's 1-2")
    w("return")
    w(f"  P3 spout bore {d['spout_bore']:.1f} (OD {d['spout_od']:.1f}): orifice Cd {hv('Cd_orifice')} at {h['h_s'] * 1000:.1f} mm head "
      f"carries {h['Q_spout'] / LPM_TO_M3S:.2f} L/min (needs max({L['spout_capacity_x']:.0f} x {spec('flow_max_lpm'):.0f}, "
      f"{h['q_closed'] / LPM_TO_M3S:.2f}))")
    w(f"  collector level at {_f(d['z_coll'])}: {h['Q_half'] / LPM_TO_M3S:.2f} L/min per half, critical depth {h['y_c']:.1f}, "
      f"Beij x {hv('beij_sf')} upstream {h['y_up']:.1f} mm; spout tips {d['channels'][0]['spout_tip'][2] - h['z_inv'] - h['y_up']:.1f} mm above it")
    db = h["drain_back"]
    w(f"  drain-back {sum(v for k, v in db.items() if k != 'rise') / 1e6:.2f} L raises the tote {db['rise']:.0f} mm "
      f"(waterline {_f(tz['waterline'])}, lid underside {_f(tz['top'] - max(bv('tote', 'lid_t_range')))} at the thickest lid)")
    w(f"  drop end {_f(d['drop_end'][2])}, bypass end {_f(d['z_bp_end'])}, waterline {_f(tz['waterline'])}, pump top {_f(d['pump_box'][1][2])}")
    w("P5 gland (Parker Design Chart 4-2, AS568-205)")
    cs, tol = bv("oring", "cs"), bv("oring", "cs_tol")
    Lg = d["gland_L"]
    w(f"  depth {Lg:.3f} (chart {bv('gland', 'depth')[0]:.3f}-{bv('gland', 'depth')[1]:.3f}), groove {2 * d['gland_r'][0]:.2f}-{2 * d['gland_r'][1]:.2f} dia; "
      f"squeeze {(cs - tol - Lg) / (cs - tol):.1%}-{(cs + tol - Lg) / (cs + tol):.1%} (chart 20-30 %); "
      f"FDM radial error +/-0.1 would give {(cs - tol - Lg - 0.1) / (cs - tol):.1%}-{(cs + tol - Lg + 0.1) / (cs + tol):.1%}")
    pb = d["p6_box"]
    w(f"P6 plate {_f(pb['Wx'])} x {_f(pb['Wy'])} (A1 bed {MAT.BED[0]:.0f}), thickness {pb['t_low']:.1f}-{pb['t_hi']:.2f}, "
      f"window {_f(pb['window'][1] - pb['window'][0])} x {_f(pb['window'][3] - pb['window'][2])}")
    w("insertion depths (expected; table.py measures them on the geometry)")
    for male, female, r, want, mn, what in d["joints"]:
        w(f"  {want:6.2f} mm (min {mn:5.2f})  {what}")
    w("cut lists")
    for nm in ("pvc34", "pvc2"):
        for k, stick in enumerate(d["cut"][nm]):
            w(f"  {nm} stick {k + 1}: " + ", ".join(f"{p_} {l_:.0f}" for p_, l_ in stick))
    for what, part, ln, n in d["extrusion_cuts"]:
        w(f"  {part} x {n}: {ln:.1f} mm ({what})")
    w("BOM (bought)")
    for what, ref, n in d["bom"]:
        w(f"  {n:>6}  {what}  [{ref}]")
    w("printed (PETG, Bambu A1, 0.4 nozzle)")
    for what, n in d["printed"]:
        w(f"  {n:>6}  {what}")
    w("values by tag")
    for tag in ("DESIGN", "CONVENIENCE", "PLACEHOLDER", "INFERRED"):
        rows = [f"{t}.{k} = {v[0] if not isinstance(v[0], float) else round(v[0], 4)}: {v[2]}"
                for t, items in _tables() for k, v in items if v[1] == tag]
        w(f"  {tag} ({len(rows)})")
        for r_ in rows:
            w(f"    {r_}")
    w("not modelled")
    for x in NOT_MODELLED:
        w(f"  - {x}")
    return "\n".join(out)


if __name__ == "__main__":
    d = derive()
    print(report(d))
    try:
        validate()
        print("nft_table: ok")
    except AssertionError as ex:
        print(f"nft_table: FAIL: {ex}")


# ---------------------------------------------------------------------------
# print orientation, walls, functional faces, water bores (design review rules 3, 6; PARAMS_CONVENTION rule 9)
# ---------------------------------------------------------------------------
MAX_OVERHANG = (45.0, "DESIGN", "overhang limit from vertical for PETG at a 0.4 nozzle without support")
BORE_TILT_MAX = (2.0, "DESIGN", "a water bore counts as vertical within 2 deg (the P2 barb follows the 1:40 slope: 1.43 deg)")


def print_parts(d) -> dict:
    """Every printed variant: name -> (description, quantity)."""
    n = d["L"]["n_ch"]
    out = {f"P1-{k}": (d["p1"][k], n) for k in ("F", "M", "B")}
    out.update({"P2": (d["p2"], n), "P3": (d["p3"], n), "P4-up": (d["p4"]["up"], n), "P4-lo": (d["p4"]["lo"], n),
                "P5-tap": (d["p5"]["tap"], n), "P5-back": (d["p5"]["back"], n),
                "P6-plate": (d["p6_plate"], 1), "P6-frame": (d["p6_frame"], 1), "P6-plug": (d["p6_plug"], 1),
                "P6-cord": (d["p6_cord"], 1),
                "P7-along": (d["p7"]["along"], sum(1 for c in d["p7_clips"] if c[1] == "along")),
                "P7-across": (d["p7"]["across"], sum(1 for c in d["p7_clips"] if c[1] == "across"))})
    return out


def print_spec(d, part: str) -> dict:
    """Orientation (all parts are built in their print frame: up +Z, bed at z = 0), declared overhangs, analytic
    walls, functional faces (a point on each and its outward normal in the print frame) and water bores (axis)."""
    L = d["L"]
    nz = MAT.NOZZLE
    th = d["theta"]
    base = dict(up=(0.0, 0.0, 1.0), bed_z=0.0, known_overhangs=[], cyl_overhangs=[], functional={}, walls={}, water_bores={})
    cw = spec("channel_w")
    wi = cw / 2 + L["fit"]
    if part.startswith("P1"):
        desc = d["p1"][part[-1]]
        h = d["saddle_h"][part[-1]]
        base.update(bed_face="base underside (on the rail top)",
                    functional={"rail contact": ((0.0, 0.0, 0.0), (0, 0, -1)),
                                "corner ledge (channel seat)": ((desc["xl"] + 2.0, 0.0, h), (0, 0, 1)),
                                "cheek inner face (channel side)": ((desc["wi"], 0.0, h + 5.0), (-1, 0, 0))},
                    walls=dict(base=d["p1_t_base"], cheek=L["p1_cheek_t"], rib=L["p1_rib_t"],
                               ledge=L["p1_ledge_w"]))
    elif part == "P2":
        p2 = d["p2"]
        base.update(bed_face="sleeve floor underside",
                    functional={"floor top (channel underside, sealant)": ((0.0, L["sl_len"] - 5.0, p2["z_cu"]), (0, 0, 1)),
                                "wall inner face (sealant)": ((wi, L["sl_len"] - 5.0, p2["z_cu"] + 10.0), (-1, 0, 0)),
                                "barb ridge": (P.add(P.add(p2["base"], p2["axis"], L["barb_base_h"] + 0.01), (1, 0, 0), L["barb_ridge_d"] / 2), (1, 0, 0))},
                    walls=dict(floor=L["sl_floor"], wall=L["sl_wall"], wall_at_groove=L["sl_wall"] - L["groove_d"],
                               floor_at_groove=L["sl_floor"] - L["groove_d"], barb_tip=(L["barb_tip_d"] - L["barb_bore"]) / 2,
                               end_wall_behind_slot=L["p2_end_t"] / 2 - L["barb_bore"] / 2),
                    water_bores={"barb bore": p2["axis"]})
        base["known_overhangs"] = [("outlet slot roof, 5 mm bridge", p2["tip"][2] - p2["bore_len"] * math.cos(th))]
    elif part == "P3":
        p3 = d["p3"]
        base.update(bed_face="spout tip",
                    known_overhangs=[("sleeve floor underside: exterior, slicer support", p3["z_cu"] - L["sl_floor"]),
                                     ("chamber floor and end wall undersides: exterior, slicer support", L["spout_len"])],
                    functional={"floor top (channel underside, sealant)": ((0.0, -L["sl_len"] + 5.0, p3["z_cu"]), (0, 0, 1)),
                                "wall inner face (sealant)": ((wi, -L["sl_len"] + 5.0, p3["z_cu"] + 10.0), (-1, 0, 0)),
                                "spout OD (in P4)": ((d["spout_od"] / 2, p3["y_sp"], L["spout_len"] / 2), (1, 0, 0)),
                                "chamber floor (water)": ((0.0, p3["y_sp"] + d["spout_bore"] / 2 + 2.0, p3["z_cf_top"]), (0, 0, 1))},
                    walls=dict(floor=L["sl_floor"], wall=L["sl_wall"], wall_at_groove=L["sl_wall"] - L["groove_d"],
                               floor_at_groove=L["sl_floor"] - L["groove_d"], spout=L["spout_wall"], end=L["p3_end_t"],
                               tip_stop=L["end_gap"]),
                    water_bores={"spout bore": (0.0, 0.0, 1.0)})
    elif part.startswith("P4"):
        g, R_s = L["p4_gap"], d["p4_Rs"]
        s_af = bv("nut", "s_M4") + 2 * 0.15
        if part == "P4-up":
            base.update(bed_face="end face (pipe axis vertical)",
                        known_overhangs=[("nut trap ceilings, 3.6 mm bridge", L["p4_len"] / 2 + s_af / 2)],
                        functional={"seat (collector crown, beside the hole)": ((20.0, math.sqrt(R_s ** 2 - 400.0), L["p4_len"] / 2), (0, -1, 0)),
                                    "hanger plate (rail face)": ((-d["p4_web_x"] - L["p4_plate_t"], d["p4_slot_y"] + 6.0, L["p4_len"] / 2), (-1, 0, 0))},
                        walls=dict(shell=L["p4_shell"] + g / 2, ring=L["p4_ring_wall"], ear_skin=6.0 - 1.6 - (bv("nut", "m_M4") + 0.4),
                                   below_trap=1.6, trap_side=(L["p4_ear"] - s_af) / 2, plate=L["p4_plate_t"]))
        else:
            base.update(bed_face="end face (pipe axis vertical)",
                        functional={"seat (collector underside)": ((0.0, -R_s, L["p4_len"] / 2), (0, 1, 0))},
                        walls=dict(shell=L["p4_shell"] + g / 2, ear=6.0))
    elif part.startswith("P5"):
        R_s, g = d["p5_Rs"], L["p5_gap"]
        zc = L["p5_len"] / 2
        if part == "P5-tap":
            ri_g, ro_g = d["gland_r"]
            base.update(bed_face="end face (manifold axis vertical)",
                        cyl_overhangs=[("O-ring gland side walls: 2.64 mm deep, bridged; not sealing faces", zc)],
                        functional={"seat beside the gland": ((R_s, 0.0, zc + ro_g + 3.0), (-1, 0, 0)),
                                    "gland floor (O-ring)": ((R_s + d["gland_L"], 0.0, zc + (ri_g + ro_g) / 2), (-1, 0, 0)),
                                    "barb ridge": ((d["p5"]["tap"]["x_b"] + L["barb_ridge_d"] / 2, 0.0, L["p5_len"] + L["barb_base_h"] + 0.01), (1, 0, 0))},
                        walls=dict(crown=L["p5_t"] - d["gland_L"], gland_inner=ri_g - bv("drill", "d") / 2,
                                   bore_to_gland=d["p5"]["tap"]["x_b"] - L["barb_bore"] / 2 - (R_s + d["gland_L"]),
                                   barb_tip=(L["barb_tip_d"] - L["barb_bore"]) / 2, ear=6.0, seat_side=2.0),
                        water_bores={"barb bore": (0.0, 0.0, 1.0)}, drilled=["tap passage: printed as a teardrop pilot, drilled 1/4 in"])
        else:
            m = bv("nut", "m_M4") + 0.4
            base.update(bed_face="end face (manifold axis vertical)",
                        known_overhangs=[("hex pocket tops, 60 deg, 3.6 mm deep", zc + 0.75 * (bv("nut", "s_M4") + 0.3) / math.sqrt(3))],
                        functional={"seat": ((-R_s, 0.0, zc), (1, 0, 0))},
                        walls=dict(back=L["p5_back_t"], ear_behind_nut=6.0 - m, seat_side=2.0))
    elif part.startswith("P6"):
        pb = d["p6_box"]
        if part == "P6-plate":
            base.update(bed_face="underside (on the lid)",
                        functional={"underside (lid seal, light)": ((pb["Wx"] / 2, L["p6_overlap"] / 2, 0.0), (0, 0, -1))},
                        walls=dict(plate=pb["t_low"], collar=L["p6_collar_wall"], collar_lip=0.8),
                        water_bores={f"{k} collar": (0.0, 0.0, 1.0) for k in ("riser", "bypass", "drop")})
        elif part == "P6-frame":
            base.update(bed_face="lid face",
                        functional={"lid face": ((pb["Wx"] / 2, L["p6_overlap"] / 4, 0.0), (0, 0, -1))},
                        walls=dict(frame=L["p6_frame_t"], insert_to_opening=(L["p6_overlap"] - L["p6_win_tol"]) - (L["p6_overlap"] / 2 + bv("insert", "bore_M4") / 2)))
        else:
            base.update(bed_face="flange", walls=dict(flange=3.0))
    elif part.startswith("P7"):
        base.update(bed_face="clip end face (pipe axis vertical)",
                    functional={"ring bore (pipe)": ((0.0, d["p7_ri"], L["p7_w"] / 2), (0, -1, 0)),
                                "plate (rail underside)": ((0.0, L["hang"], 2.0), (0, 1, 0))},
                    walls=dict(ring=L["p7_ring"], plate=L["p7_plate_t"], stem=8.0))
    return base
