r"""NFT rack family. Two layouts share the channel, the feed tube and the frame section:

    growing_up_pro  inactive. Multi-level frame after the AM Hydro "Get Growing UP Pro" bundle (vault:
                    T1TRTA/attachments/Amhydro3rack.pdf, page 2 text and page 3 BOM, 1/1/23): a flat level and two
                    pitched levels of 52 in channels, a placeholder collector, no reservoir.
    nft_table       ACTIVE. One pitched level of six Growrilla 100x50 channels, 2 m, lids at 250 mm, on a 2020 table;
                    an HDX 27 gal tote under the low end; supply from a submersible pump up a vinyl hose, a ball
                    valve and a 1 in PVC riser to the manifold; return from each drain cap through a PP elbow into a
                    Growrilla channel used as the collector, then down a PP pipe through the tote lid.

Everything downstream (rack.py, tests, freecad_view.py) reads `derive(rack)`. Every value carries a source tag.
SPEC holds the channel and frame parts, PLUMBING the bought pipes, fittings, pump and grommets (each row names its
standard or catalogue page), RACKS the layout inputs and RACK_SOURCES tags each of them. validate() refuses an
untagged value, and for the table it fails by name on every load-bearing value that is not sourced: a PLACEHOLDER
in PLUMBING or a reservoir registry field that is still None.

    AMHYDRO      stated by AM Hydro (PDF text or BOM)
    INFERRED     follows from a published number or drawing, not stated (say from what)
    VAULT        from the T1TRTA grow-system notes (file named)
    STANDARD     a published standard (named)
    SUBSTITUTE   a real catalogue part standing in for AM Hydro's unknown one (the table uses it as the part itself)
    VENDOR       published by the vendor of the part this model uses (page named)
    DESIGN       a designer's choice in this model, UNVERIFIED: no reference part behind it
    CONVENIENCE  set to draw the model, awaits derivation from a requirement (CLAUDE.md design review rule 1)
    PLACEHOLDER  geometry drawn for a part whose dimensions are unknown; shape and size are not facts

The community STEP (~/Downloads/hydroponic NFT system.STEP) gave which parts exist and how they connect. None of
its numbers are used.

Coordinates: origin = floor, outer front-left corner of the frame. +X right along the width, +Y toward the back,
+Z up. Channels run along +Y and fall toward the back: feed at the front (high) end, drain at the back (low) end.

    side view (x = channel centre), one pitched level:

        feed tube                                   front rail top z_f, back rail top z_b = level z
          __                                        z_f - z_b = slope * (D - a): the channel floor touches the
         /  \   ___________lid__________________    front rail's back top edge (y = a) and the back rail's outer
        |    | |__________channel_______________|_  top edge (y = D)
        O    |   [F]                         [B]  |  O = manifold in front of the channel's high end
     manifold                                     | stub (growing_up_pro) / drain cap + 87 deg elbow (nft_table)
                                                  O collector, behind the back posts

    nft_table, plan (collector and tote at the back, riser at the front left):

        y ^   [collector, falls to -X] ---> drain cap, elbow, PP pipe down through the tote lid
          |  +--+-----------------------------------------+--+   back posts and rail (y = D)
          |  |  | [tote, straddles the back line]          |  |
          |  |bay  C1   C2   C3   C4   C5   C6 (250 mm)    |  |
          |  +--+-----------------------------------------+--+   front posts and rail (y = 0)
          |   R=====manifold================================cap   riser R: elbow, pipe, valve, bushing, insert
          +----------------------------------------------------> x
       The bay left of C1 is derived: it puts the return drop over the tote lid clear of the back-left post.
"""
from __future__ import annotations

import math
from types import MappingProxyType

from cacad.registries.reservoirs import RESERVOIRS
from projects.nft_rack import legs as L_
from projects.tote_rack.params import TOTES

IN = 25.4

TAGS = ("AMHYDRO", "INFERRED", "VAULT", "STANDARD", "SUBSTITUTE", "VENDOR", "DESIGN", "CONVENIENCE", "PLACEHOLDER")

# ---------------------------------------------------------------------------
# Channel and frame parts. key -> (value mm, tag, source).
# ---------------------------------------------------------------------------
SPEC = MappingProxyType({
    # frame: AM Hydro's is steel with unknown member sizes
    "frame_a": (20.0, "SUBSTITUTE", "2020 aluminium extrusion, 20 x 20 mm section (the series name is the section). "
                "Drawn as a solid 20 x 20 bar, slots not modelled. Not AM Hydro's steel frame. Stiffness not sized"),
    # channel: AM Hydro GroClean section unknown; Growrilla 100x50 stands in
    "channel_w": (100.0, "SUBSTITUTE", "Growrilla NFT channel 100x50: width 100 mm "
                  "(growrillahydroponics.com, vault clipping 2025-05-04)"),
    "channel_h": (48.0, "SUBSTITUTE", "Growrilla NFT channel 100x50: height 48 mm (same page; the IT page also says "
                  "48). Taken as the body without the lid. Bottom 'special design' not published: flat floor drawn"),
    "channel_t": (2.5, "SUBSTITUTE", "Growrilla NFT channel 100x50: thickness 2.5 mm (same page)"),
    "lid_t": (2.5, "INFERRED", "Growrilla lid thickness not stated; taken as the 2.5 mm channel thickness"),
    "site_hole_d": (48.0, "SUBSTITUTE", "Growrilla lid hole diameter 48 mm, for its 5 cm net pot (vault clipping). "
                    "Growrilla's IT channel page says 'Diametro fori 40mm': conflict, clipping used as instructed"),
    "cap_t": (2.5, "PLACEHOLDER", "Growrilla end cap and drain cap geometry not published; drawn as a plate of "
              "the channel thickness closing each end"),
    "drain_od": (32.0, "SUBSTITUTE", "Growrilla drain cap: '32mm outlet size', takes 'any 32mm PP push-fit fitting' "
                 "(drain cap page). Outlet position, length and wall not published"),
    # growing_up_pro plumbing
    "manifold_od": (1.315 * IN, "STANDARD", "1 in PVC Sch 40, ASTM D1785: OD 1.315 in. Size from the vault "
                    "(multiLVLRack.md: 1 in PVC supply), not AM Hydro's manifold"),
    "manifold_wall": (0.133 * IN, "STANDARD", "1 in PVC Sch 40, ASTM D1785: minimum wall 0.133 in"),
    "manifold_len": (60 * IN, "AMHYDRO", "BOM: 5' Finishing Manifolds (3). growing_up_pro only; the table derives it"),
    "collector_od": (50.0, "PLACEHOLDER", "BOM: 5' Covered Collector (3); section unknown. Drawn as a 50 mm round "
                     "envelope so the drains land on something. growing_up_pro only"),
    "collector_len": (60 * IN, "AMHYDRO", "BOM: 5' Covered Collector (3). growing_up_pro only"),
    "feed_tube_od": (3 / 8 * IN, "VAULT", "3/8 in vinyl feed tube (multiLVLRack.md), taken as OD; ID unknown: "
                     "solid envelope"),
    # rules from the vault
    "plant_clear_min": (8 * IN, "VAULT", "multiLVLRack.md: 8-10 in vertical clearance between levels (low end). "
                        "Lights are not modelled, so this is lid top to the next level's underside"),
    "slope_min": (1 / 40, "VAULT", "NFT/vinylDOwn.md 'Slope': 1:30 to 1:40 ratio (also NFT 2Rail 4x4 Fencepost "
                  "System.md). Default 1:40 from the session prompt"),
    "slope_max": (1 / 30, "VAULT", "NFT/vinylDOwn.md: 1:30 to 1:40; multiLVLRack.md: 1/30"),
    "flow_min_lpm": (1.0, "VAULT", "NFT/vinylDOwn.md 'Optimal Flow Rates': 1/4 to 1/2 gal/min (1 to 2 L) per channel. "
                     "multiLVLRack.md says '1-2 GPM total system': not used"),
    "flow_max_lpm": (2.0, "VAULT", "NFT/vinylDOwn.md: 1 to 2 L/min per channel"),
    # this model's own choices
    "manifold_gap": (5.0, "DESIGN", "air between the manifold and the channel's high end cap, in Y"),
    "collector_gap": (5.0, "DESIGN", "air between the collector and the back posts' outer face, in Y"),
    "drain_stub_len": (50.0, "DESIGN", "growing_up_pro: drain stub length below the channel floor at the stub centre"),
    "feed_hole_inset": (40.0, "DESIGN", "feed hole centre from the high cap's outer face, along the channel"),
    "tube_rise": (60.0, "DESIGN", "feed tube top above the lid top at the feed hole"),
    "tube_bend_r": (25.0, "DESIGN", "feed tube centreline bend radius. Vinyl's minimum bend radius unknown"),
})


def spec(key: str) -> float:
    return SPEC[key][0]


# ---------------------------------------------------------------------------
# Channel kinds: sites per channel and their pitch along the channel.
# ---------------------------------------------------------------------------
CHANNEL_KINDS = MappingProxyType({
    "F": dict(label="finishing", sites=6, pitch=8 * IN,
              src=("INFERRED", "192 sites = 96 finishing on 16 channels = 6 per 52 in channel (AM Hydro BOM); 8 in "
                   "pitch matches the guide's commercial spacing")),
    "N": dict(label="nursery", sites=10, pitch=125.0,
              src=("SUBSTITUTE", "Growrilla 125 mm hole spacing with 48 mm holes: 10 sites in a 52 in channel. "
                   "AM Hydro's 24 at 2 in does not fit 48 mm holes (3 mm web). 4 x 10 = 40 nursery sites, not 96")),
    "G": dict(label="growrilla", sites=8, pitch=250.0,
              src=("VENDOR", "Growrilla pre-drilled lid, 'Hole spacing 1: 250mm', '8 net pots / 2mt' (vault clipping). "
                   "Holes drawn centred on the 2 m lid, 125 mm from each end: INFERRED, positions not published")),
})

# ---------------------------------------------------------------------------
# Bought plumbing for the table. Each row names its standard or catalogue page; each dimension is (mm, tag, source).
# Inches converted at 25.4. Spears numbers drift between catalogue editions by up to 1/16 in (2012/2019/2025 sheets
# saved in the session scratchpad): the Dec 2025 / Dec 2024 editions are used. Caliper the bought part.
# ---------------------------------------------------------------------------
def _i(x):
    return x * IN


SPEARS_SCH40 = "Spears 'Schedule 40 Fittings Technical' Dec 2025 (parts.spearsmfg.com/sourcebook/SCH40TECH_40-1_T.pdf)"
OSTENDORF = "Ostendorf HT system Plus catalogue (DE, 07/2019)"
ORENCO = "Orenco 'Pipe Grommets' NTD-GOP-GRM-1 Rev.1 08/24, Specifications table"

PLUMBING = MappingProxyType({
    "pvc1_pipe": dict(what="1 in PVC Sch 40 pipe: riser and manifold", ref="ASTM D1785",
                      od=(_i(1.315), "STANDARD", "ASTM D1785 1 in: mean OD 1.315 in +/- .005 (Spears p.4; Charlotte DC-PR p.27)"),
                      wall=(_i(0.133), "STANDARD", "ASTM D1785 1 in Sch 40: min wall .133 in (same tables)")),
    "pvc34_pipe": dict(what="3/4 in IPS size (the 460-007 spigot and the 437-131 socket)", ref="ASTM D1785",
                       od=(_i(1.050), "STANDARD", "ASTM D1785 3/4 in: mean OD 1.050 in (Spears p.4)"),
                       wall=(_i(0.113), "STANDARD", "ASTM D1785 3/4 in Sch 40: min wall .113 in")),
    "d2466_1": dict(what="1 in Sch 40 socket", ref="ASTM D2466",
                    depth_min=(_i(0.875), "STANDARD", "ASTM D2466 1 in: min socket length C .875 in (Spears p.4)")),
    "d2466_34": dict(what="3/4 in Sch 40 socket", ref="ASTM D2466",
                     depth_min=(_i(0.719), "STANDARD", "ASTM D2466 3/4 in: min socket length C .719 in (Spears p.4)")),
    "ell_406_010": dict(what="1 in PVC Sch 40 90 deg elbow S x S, manifold inlet", ref=f"Spears 406-010, {SPEARS_SCH40} p.21",
                        G=(_i(11 / 16), "VENDOR", "G laying length: intersection of centre lines to bottom of socket"),
                        H=(_i(1 + 25 / 32), "VENDOR", "H: intersection of centre lines to face of fitting (2012: 1-13/16, 2019: 1-3/4)"),
                        M=(_i(1 + 5 / 8), "VENDOR", "M: outside diameter of socket hub")),
    "cap_447_010": dict(what="1 in PVC Sch 40 cap, manifold end", ref=f"Spears 447-010, {SPEARS_SCH40} p.60",
                        M=(_i(1 + 19 / 32), "VENDOR", "M: OD of socket hub (2012: 1-9/16)"),
                        W=(_i(1 + 5 / 8), "VENDOR", "W: height of cap (2012: 1-9/16)"),
                        depth=(_i(0.875), "STANDARD", "socket depth not published for 447-010: ASTM D2466 minimum used")),
    "valve_2122_010": dict(what="1 in PVC compact ball valve, socket ends, balancing", ref=(
        "Spears 2122-010 (EPDM), Valves Technical 'Compact Ball Valves' Dec 2024 p.5, Dimension Reference +/- 1/16"),
        A=(_i(2 + 1 / 4), "VENDOR", "A: end diameter (drawing)"),
        B=(_i(1 + 15 / 16), "VENDOR", "B socket: 'Valve Lay Length' (between socket bottoms)"),
        C=(_i(4 + 1 / 4), "VENDOR", "C: overall end to end (drawing)"),
        D=(_i(2 + 13 / 16), "VENDOR", "D: valve centreline to handle top (drawing)"),
        E=(_i(3 + 3 / 4), "VENDOR", "E: handle length (drawing)"),
        bore=(_i(1.315 - 2 * 0.133), "INFERRED", "ball bore not published; drawn full port at the 1 in pipe's ID"),
        handle_w=(20.0, "PLACEHOLDER", "handle width not published; drawn 20 mm. Envelope only")),
    "bush_437_131": dict(what="1 x 3/4 PVC flush reducer bushing, spigot x socket", ref=f"Spears 437-131, {SPEARS_SCH40} p.54",
                         L=(_i(1 + 1 / 4), "VENDOR", "L: overall length; the spigot is 1 in pipe OD"),
                         N=(_i(5 / 16), "VENDOR", "N: spigot face to socket bottom (drawing); socket depth = L - N"),
                         bore=(_i(1.050 - 2 * 0.113), "INFERRED", "through bore past the socket not published: 3/4 Sch 40 ID")),
    "ins_460_007": dict(what="3/4 PVC insert (barb) x IPS spigot adapter, hose to bushing", ref=f"Spears 460-007, {SPEARS_SCH40} p.53",
                        L=(_i(2 + 23 / 32), "VENDOR", "L: overall length"),
                        N=(_i(5 / 32), "VENDOR", "N: collar thickness (drawing)"),
                        Z=(_i(27 / 32), "VENDOR", "Z: insert barb OD (drawing). ASTM D2609 insert for PE pipe: it is "
                           "0.094 in over the vinyl hose's 0.750 ID. Fit on vinyl not stated by Spears"),
                        spigot=(_i(1 + 1 / 4 - 5 / 16), "PLACEHOLDER", "spigot length not published; drawn = the bushing's "
                                "socket depth so the collar seats on the bushing face"),
                        insert_env=(_i(0.75), "INFERRED", "insert drawn at the hose ID (contact envelope); barb ribs not drawn")),
    "hose_34": dict(what="3/4 in ID clear PVC hose, pump to riser", ref=(
        "Kuriyama Kuri Tec K010-1216X100 (products.kuriyama.com), vault: 3/4 vinyl"),
        id=(_i(0.75), "VENDOR", "Nominal ID 3/4 in"),
        od=(_i(1.0), "VENDOR", "Nominal OD 1 in; wall 1/8 in"),
        bend_r=(3 * _i(1.0), "DESIGN", "K010 bend radius not published. Excelon RNT 3/4 x 1 (US Plastic 59022): "
                "'minimum bend radius of 3x diameter', diameter not named: 3 x OD taken, the larger")),
    "pp32_pipe": dict(what="PP-HT DN32 drainage pipe with socket (return line)", ref=f"Ostendorf HTEM DN32, {OSTENDORF} p.3-4; EN 1451-1",
                      od=(32.0, "STANDARD", "EN 1451-1 dn 32: dem 32.0 (Table 2, SIST EN 1451-1:2018 preview p.15)"),
                      wall=(1.8, "VENDOR", "Ostendorf p.3 s = 1,8; Pestan S20/SDR41 and Huliot S16 also 1.8. The 3.0 seen "
                            "before is Growrilla's 32 mm PVC tube; UK 32 mm push-fit (BS 5254) is 34.6 OD and does not fit"),
                      D=(44.0, "VENDOR", "Ostendorf p.3: D 'der groesste Aussendurchmesser' (socket hub)"),
                      t=(40.0, "VENDOR", "Ostendorf p.3: t 'Stutzentiefe' socket depth"),
                      shoulder=(1.8, "INFERRED", "socket-bottom shoulder drawn one wall (s) thick at the hub OD, so the hub "
                                "joins the body as one solid; not published"),
                      lengths=((150.0, 250.0, 500.0, 1000.0, 2000.0, 3000.0), "VENDOR",
                               "HTEM DN32 L, socket bottom to plain end: 150/250/500/1000/2000/3000 (p.4, art. 110000-110070)")),
    "pp32_elbow": dict(what="PP-HT DN32 87 deg elbow, socket x spigot (each drain cap and the collector outlet)", ref=(
        f"Ostendorf HTB 87 deg DN32 art. 110140, {OSTENDORF} p.5; Growrilla sells a 'gomito 87 PP 32' with no dimensions"),
        angle=(87.0, "VENDOR", "HTB Bogen 87 deg"),
        z1=(19.0, "VENDOR", "z1: axis intersection to spigot start (drawing)"),
        z2=(23.0, "VENDOR", "z2: axis intersection to socket bottom (drawing)"),
        l1=(61.0, "VENDOR", "l1: axis intersection to spigot end (drawing)"),
        body_od=(32.0, "INFERRED", "body between socket and corner drawn at the DN32 OD; the socket is the p.3 HTEM socket"),
        wall=(1.8, "INFERRED", "fitting wall taken as the pipe's s = 1.8")),
    "drain_cap": dict(what="Growrilla drain cap 100x50: 32 mm outlet", ref="growrillahydroponics.com drain cap page (EN/IT)",
                      spigot_od=(32.0, "VENDOR", "'32mm outlet size'; IT: 'manicotto di uscita di diametro 32mm'"),
                      spigot_len=(40.0, "PLACEHOLDER", "not published; drawn = the HTB socket depth t 40 so the elbow seats on the cap"),
                      spigot_z=(2.5 + 16.0, "PLACEHOLDER", "outlet centre height not published; drawn with the outlet's "
                                "underside on the channel floor (floor top + radius). Solid envelope, wall unknown")),
    "grommet_g1l": dict(what="EPDM grommet for the 32 mm return through the tote lid", ref=f"Orenco G1L, {ORENCO}",
                        OD=(_i(1 + 7 / 8), "VENDOR", "OD 1 7/8 (48)"),
                        ID=(_i(1 + 1 / 4), "VENDOR", "ID 1 1/4 (32): 0.25 mm under the PP pipe's 32.0, drawn at the pipe OD"),
                        GD=(_i(1 + 5 / 8), "VENDOR", "GD 1 5/8 (41): over the hole, drawn at the hole (compressed)"),
                        GW=(_i(1 / 4), "VENDOR", "GW 1/4 (6): groove width, the thickest lid it takes"),
                        T=(_i(9 / 16), "VENDOR", "T 9/16 (14)"),
                        hole=(_i(1 + 9 / 16), "VENDOR", "Holesaw size 1 9/16 (40)")),
    "grommet_g07l": dict(what="EPDM grommet for the supply hose through the tote lid", ref=f"Orenco G07L, {ORENCO}",
                         OD=(_i(1 + 1 / 2), "VENDOR", "OD 1 1/2 (38)"),
                         ID=(_i(1.0), "VENDOR", "ID 1 (25) = the hose OD. Orenco sizes are 'standard IPS'; a tube fit is not stated"),
                         GD=(_i(1 + 1 / 4), "VENDOR", "GD 1 1/4 (32), drawn at the hole"),
                         GW=(_i(3 / 16), "VENDOR", "GW 3/16 (5)"),
                         T=(_i(7 / 16), "VENDOR", "T 7/16 (11)"),
                         hole=(_i(1 + 1 / 4), "VENDOR", "Holesaw size 1 1/4 (32)")),
})

PUMPS = MappingProxyType({
    "AAPW400": dict(
        what="Hydrofarm Active Aqua AAPW400 submersible pump",
        ref="Hydrofarm owner's manual (planetnatural.com/wp-content/uploads/active-aqua-pump.pdf) and hydrofarm.com AAPW400",
        size=((_i(6.3), _i(4.7), _i(3.9)), "PLACEHOLDER", "hydrofarm.com lists 6.3L x 4.7W x 3.9H in as the 'EA' "
              "logistics size, not the pump: drawn as an upper-bound box. Caliper the pump"),
        outlet=((0.0, 0.0), "PLACEHOLDER", "outlet is on top ('black fittings attach to the top of the pump', manual); "
                "position not published, drawn at the top centre"),
        barb_d=(19.0, "VENDOR", "manual: fitting sizes '1/2, 3/4 in (12.7, 19 mm)'; the 3/4 barb is used, drawn at the hose ID"),
        barb_len=(25.0, "PLACEHOLDER", "barb fitting height above the pump not published"),
        rated_gph=(370.0, "VENDOR", "manual table and hydrofarm.com: rated 370 GPH (label and retailers: 400)"),
        # head ft -> GPH, read off the manual's 'Performance Chart' at 250 dpi (curve that meets 0 ft at 400 GPH)
        curve=(((0.5, 369.0), (1.0, 341.0), (1.5, 312.0), (2.5, 268.0), (3.0, 248.0), (3.5, 228.0), (5.0, 168.0),
                (7.0, 95.0)), "VENDOR", "digitised from the owner's manual performance chart, about +/- 5 GPH; shut-off "
               "head on the chart about 8.2 ft (retailers: 7.54 ft)")),
})


def pv(row: str, key: str):
    return PLUMBING[row][key][0]


# ---------------------------------------------------------------------------
# Family axis: one rack per entry. Inputs only.
# ---------------------------------------------------------------------------
RACKS = {
    "growing_up_pro": dict(
        W=60 * IN, D=46 * IN, H=92 * IN,
        levels=("flat", "FFFNNNNFFF", "FFFFFFFFFF"),
        channel_len=52 * IN,
        slope=1 / 40,
        level_z0=None, level_pitch=None,
    ),
    "nft_table": dict(
        levels=("GGGGGG",),
        channel_len=2000.0,
        slope=1 / 40,
        work_h=36 * IN,
        channel_pitch=250.0,
        overhang_front=100.0,
        overhang_back_min=20.0,
        reservoir="HDX_27GAL",
        tote_label="HDX_207585",
        pump="AAPW400",
        tote_post_gap=10.0,
        grommet_edge=90.0,
        supply_z=500.0,
        riser_offset=90.0,
        riser_pipe=40.0,
        manifold_end=40.0,
        pump_wall_gap=20.0,
        coll_edge=20.0,
        coll_hole_clear=1.5,
        tip_margin=3.0,
        return_depth_min=50.0,
        tote_draw=dict(lid_t=3.0, wall_t=3.0),
    ),
}

RACK_SOURCES = {
    "growing_up_pro": dict(
        W=("AMHYDRO", "BOM: 60\" wide x 46\" deep by 92\" tall Steel Table Frame"),
        D=("AMHYDRO", "BOM: 60\" wide x 46\" deep by 92\" tall Steel Table Frame"),
        H=("AMHYDRO", "BOM: 60\" wide x 46\" deep by 92\" tall Steel Table Frame"),
        levels=("INFERRED", "PDF: propagation trays below, 20 channels on the top two levels (10 each). Nursery "
                "channels in the middle of level 2: read off the render, not stated"),
        channel_len=("AMHYDRO", "BOM: Gro Clean NFT Channel (52\" Finishing / Nursery Sections)"),
        slope=("VAULT", "vinylDOwn.md 1:30 to 1:40, default 1:40; AM Hydro's slope unknown"),
        level_z0=("CONVENIENCE", "even split of 92 in: AM Hydro level heights unknown. Awaits measurement"),
        level_pitch=("CONVENIENCE", "even split of 92 in: AM Hydro level spacing unknown. Awaits measurement"),
    ),
    "nft_table": dict(
        levels=("DESIGN", "owner's choice 2026-10-01: one level, 6 Growrilla channels at the 250 mm lid"),
        channel_len=("VENDOR", "Growrilla 100x50: 'Channel lenght: 2 meters', uncut bar and lid (vault clipping)"),
        slope=("VAULT", "vinylDOwn.md 1:30 to 1:40, default 1:40"),
        work_h=("DESIGN", "owner's choice 2026-10-01: channel floor 36 in above the floor at the high end (US "
                "counter-height convention, not a standard)"),
        channel_pitch=("DESIGN", "owner's choice 2026-10-01: channels 250 mm apart across, the lid's own pitch (square grid)"),
        overhang_front=("DESIGN", "channel high end 100 mm in front of the front posts: room for the cap and feed hole"),
        overhang_back_min=("DESIGN", "least back overhang: keeps the drain cap off the back rail"),
        reservoir=("VAULT", "cacad.registries.reservoirs HDX_27GAL: the tote on hand. Caliper fields None until measured"),
        tote_label=("VENDOR", "projects/tote_rack TOTES['HDX_207585'] label envelope 28.6 x 19.6 x 15.2 in with lid. "
                    "HD SKU 207585 now sells model 999-27G-HDX (interior at bottom 22.98 x 14.02 x 14.30 in); the older "
                    "'Strong Box' under the same SKU is 30.125 x 20.25 x 13.813 in. Measure the tote you have"),
        pump=("VENDOR", "owner's choice 2026-10-01: Active Aqua AAPW400 (PUMPS)"),
        tote_post_gap=("DESIGN", "air between the tote and the back-left post, in X"),
        grommet_edge=("DESIGN", "grommet centre from the tote's outer top edge; clears the wall draft at the return pipe "
                      "end. Rim lip unknown (registry rim_lip None)"),
        supply_z=("DESIGN", "height of the supply hose run, between the tote lid and the front rail; clips not modelled"),
        riser_offset=("DESIGN", "riser axis left of channel 1's centre: clears the channel by the valve radius plus 11 mm"),
        riser_pipe=("DESIGN", "exposed 1 in pipe between the elbow and the valve (cut length)"),
        manifold_end=("DESIGN", "manifold run past the last feed tube to the cap's socket face"),
        pump_wall_gap=("DESIGN", "pump body clear of the tote's bottom interior edge"),
        coll_edge=("DESIGN", "collector lid hole edge to the end of the collector body"),
        coll_hole_clear=("DESIGN", "radial air around each elbow spigot in its collector lid hole (hole saw to choose)"),
        tip_margin=("DESIGN", "least air between an elbow spigot tip and the collector floor or lid underside"),
        return_depth_min=("DESIGN", "least drop of the return pipe's end below the tote lid underside"),
        tote_draw=("PLACEHOLDER", "tote lid and rim wall thickness, drawn 3 mm: not published, not in the registry"),
    ),
}

ACTIVE_RACKS = ("nft_table",)

COMMON = MappingProxyType(dict(bbox_tol=0.05))

NOT_MODELLED = {
    "growing_up_pro": (
        "propagation trays (5 x AM Hydro cMPT): dimensions unknown",
        "reservoirs (2 x 50 gal), pumps (2), feed/return plumbing to them: dimensions unknown",
        "T5 6-tube fixtures (2 per level): dimensions unknown",
        "net pots (Growrilla 5 cm): height and rim unknown; sites shown as lid holes",
        "propagation-level manifold and collector (BOM has 3 of each; 2 drawn, on the NFT levels)",
        "covered collector lid, drain path through the cap (no hole in the floor), pipe and tube walls of the drains",
        "manifold and collector supports, frame brackets and fasteners",
    ),
    "nft_table": (
        "lights and net pots (sites shown as lid holes)",
        "feed tube grommets/barbs at the manifold (vault: microgrommets) and the feed tube's bore (ID unknown)",
        "clips and supports for the manifold, riser, hose run, collector and return pipe; frame brackets and fasteners",
        "the bores of the drain cap outlet, the pump barb and the 460-007 adapter (solid envelopes)",
        "tote rim lip, feet and ribs; the tote's walls drawn straight-drafted from the published bottom interior",
        "push-fit seal rings in the PP sockets; barb ribs; pipe cut lengths' tolerances",
        "air stone and pump cord",
    ),
}


# ---------------------------------------------------------------------------
# derive
# ---------------------------------------------------------------------------
def _rot(theta: float, s: float, zl: float) -> tuple[float, float]:
    """Channel-local (along, up) -> world (dy, dz) for a channel falling at angle theta toward +Y."""
    return s * math.cos(theta) + zl * math.sin(theta), -s * math.sin(theta) + zl * math.cos(theta)


def _box_bbox(x0: float, x1: float, s0: float, s1: float, z0: float, z1: float, place) -> tuple:
    """World bbox of a channel-local box, from its 8 rotated corners."""
    pts = [place(x, s, z) for x in (x0, x1) for s in (s0, s1) for z in (z0, z1)]
    return tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3))


def _box(expect, name, kind, lo, size):
    hi = tuple(l + z for l, z in zip(lo, size))
    expect[name] = dict(kind=kind, lo=tuple(lo), hi=hi, volume=size[0] * size[1] * size[2], box=(tuple(lo), tuple(size)))


def _channel_parts(d, expect, name, kind, xc, y_hi, z_hi, s_feed, y_m, z_m):
    """Body, lid, two caps and the feed tube of one channel (both layouts). Returns (channel dict, tube dict)."""
    cw, ch, ct, lt, capt = (spec(k) for k in ("channel_w", "channel_h", "channel_t", "lid_t", "cap_t"))
    theta, L = d["theta"], d["channel_len"]
    hole_r, tube_r, man_r = spec("site_hole_d") / 2, spec("feed_tube_od") / 2, spec("manifold_od") / 2
    place = lambda x, s_, z: (xc + x, y_hi + _rot(theta, s_, z)[0], z_hi + _rot(theta, s_, z)[1])
    k = CHANNEL_KINDS[kind]
    sites = [capt + L / 2 + (m - (k["sites"] - 1) / 2) * k["pitch"] for m in range(k["sites"])]
    u_area = cw * ch - (cw - 2 * ct) * (ch - ct)
    lo, hi = _box_bbox(-cw / 2, cw / 2, capt, capt + L, 0.0, ch, place)
    expect[f"{name}-body"] = dict(kind="channel", lo=lo, hi=hi, volume=u_area * L)
    lo, hi = _box_bbox(-cw / 2, cw / 2, capt, capt + L, ch, ch + lt, place)
    holes = k["sites"] * math.pi * hole_r ** 2 + math.pi * tube_r ** 2
    expect[f"{name}-lid"] = dict(kind="lid", lo=lo, hi=hi, volume=(cw * L - holes) * lt)
    for end, s0 in (("hi", 0.0), ("lo", capt + L)):
        lo, hi = _box_bbox(-cw / 2, cw / 2, s0, s0 + capt, 0.0, ch + lt, place)
        expect[f"{name}-cap-{end}"] = dict(kind="cap", lo=lo, hi=hi, volume=cw * capt * (ch + lt))
    # feed tube: manifold top, up, over, down onto the lid at the feed hole (lid-normal hole, vertical tube)
    yf, zf_lid = place(0.0, s_feed, ch + lt)[1:]
    z_peak = zf_lid + spec("tube_rise")
    z_end = zf_lid + tube_r * d["slope"]    # just clear of the lid's uphill rim under the tube
    r_b = spec("tube_bend_r")
    pts = [(xc, y_m, z_m + man_r), (xc, y_m, z_peak), (xc, yf, z_peak), (xc, yf, z_end)]
    seg = [abs(pts[1][2] - pts[0][2]), abs(pts[2][1] - pts[1][1]), abs(pts[3][2] - pts[2][2])]
    path = (seg[0] - r_b) + (seg[1] - 2 * r_b) + (seg[2] - r_b) + 2 * (math.pi * r_b / 2)
    d["tube_len"][name] = path
    expect[f"{name}-tube"] = dict(kind="tube", lo=(xc - tube_r, min(y_m, yf) - tube_r, z_m + man_r),
                                  hi=(xc + tube_r, max(y_m, yf) + tube_r, z_peak + tube_r),
                                  volume=math.pi * tube_r ** 2 * path)
    c = dict(name=name, kind=kind, xc=xc, y_hi=y_hi, z_hi=z_hi, sites=sites, s_feed=s_feed, place=place)
    return c, dict(name=f"{name}-tube", pts=pts, r=tube_r, bend_r=r_b, segs=seg)


def _function_numbers(d, expect):
    capt, hole_r, tube_r, L = spec("cap_t"), spec("site_hole_d") / 2, spec("feed_tube_od") / 2, d["channel_len"]
    channels = d["channels"]
    d["sites"] = {k: sum(CHANNEL_KINDS[c["kind"]]["sites"] for c in channels if c["kind"] == k) for k in CHANNEL_KINDS}
    d["channels_by_kind"] = {k: sum(1 for c in channels if c["kind"] == k) for k in CHANNEL_KINDS}
    d["site_web"] = {k: v["pitch"] - 2 * hole_r for k, v in CHANNEL_KINDS.items()}
    d["first_site_edge"] = {k: capt + L / 2 - (v["sites"] - 1) / 2 * v["pitch"] - hole_r for k, v in CHANNEL_KINDS.items()}
    d["feed_hole_edge"] = spec("feed_hole_inset") + tube_r
    d["bbox"] = (tuple(min(e["lo"][i] for e in expect.values()) for i in range(3)),
                 tuple(max(e["hi"][i] for e in expect.values()) for i in range(3)))


def derive(rack: str, **overrides) -> dict:
    """Every dimension rack.py and the tests need. Overrides are for what-if tables and controls only."""
    s = dict(RACKS[rack])
    c = dict(COMMON)
    for k, v in overrides.items():
        (s if k in s else c)[k] = v
    d = dict(rack=rack, **s, **c)
    d["theta"] = math.atan(s["slope"])
    d["tube_len"] = {}
    if "work_h" in s:
        _derive_table(d, s)
    else:
        _derive_amhydro(d, s)
    return d


def _derive_amhydro(d, s):
    W, D, H = s["W"], s["D"], s["H"]
    a = spec("frame_a")
    theta = d["theta"]
    n_lv = len(s["levels"])
    pitch = s["level_pitch"] if s["level_pitch"] is not None else H / (n_lv + 1)
    z0 = s["level_z0"] if s["level_z0"] is not None else pitch
    d["level_pitch_used"], d["level_z0_used"] = pitch, z0
    span = D - a                                   # floor contact: front rail back top edge (y=a) to back rail outer top edge (y=D)
    d["support_span"], d["drop"] = span, s["slope"] * span

    expect = {}   # name -> dict(kind, lo, hi, volume): the analytic envelope every built solid must match
    for nm, x, y in (("FL", 0, 0), ("FR", W - a, 0), ("BL", 0, D - a), ("BR", W - a, D - a)):
        _box(expect, f"POST-{nm}", "frame", (x, y, 0.0), (a, a, H))
    levels = []
    for i, lv in enumerate(s["levels"], start=1):
        zb = z0 + (i - 1) * pitch
        pitched = lv != "flat"
        zf = zb + (d["drop"] if pitched else 0.0)
        levels.append(dict(i=i, kind=("nft" if pitched else "flat"), channels=("" if not pitched else lv), z_b=zb, z_f=zf))
    d["levels_derived"] = levels
    rings = [(f"L{lv['i']}", lv["z_b"], lv["z_f"]) for lv in levels] + [("TOP", H, H)]
    for tag, zb, zf in rings:
        _box(expect, f"{tag}-RAIL-F", "frame", (a, 0.0, zf - a), (W - 2 * a, a, a))
        _box(expect, f"{tag}-RAIL-B", "frame", (a, D - a, zb - a), (W - 2 * a, a, a))
        _box(expect, f"{tag}-RAIL-L", "frame", (0.0, a, zb - a), (a, D - 2 * a, a))
        _box(expect, f"{tag}-RAIL-R", "frame", (W - a, a, zb - a), (a, D - 2 * a, a))

    capt = spec("cap_t")
    Lo = s["channel_len"] + 2 * capt
    drain_r, coll_r, man_r = spec("drain_od") / 2, spec("collector_od") / 2, spec("manifold_od") / 2
    d.update(channel_overall=Lo, Lo=Lo)
    s_drain = Lo - capt - drain_r                  # drain stub centre along the channel: touching the low cap's inner face
    y_drain = D + spec("collector_gap") + coll_r   # collector behind the back posts; the stub sits over its axis
    y_hi = y_drain - s_drain * math.cos(theta)
    d.update(y_hi=y_hi, y_lo=y_hi + Lo * math.cos(theta), y_drain=y_drain)
    d["overhang_front"] = -y_hi
    d["overhang_back"] = d["y_lo"] - D
    s_feed = spec("feed_hole_inset")
    channels, tubes, pipes = [], [], []
    for lv in levels:
        if lv["kind"] != "nft":
            continue
        n = len(lv["channels"])
        cpitch = (W - 2 * a) / n                   # equal cells across the inner width
        d.setdefault("channel_pitch", {})[lv["i"]] = cpitch
        z_floor = lambda y, zf=lv["z_f"]: zf - s["slope"] * (y - a)   # floor line through (y=a, z_f)
        z_hi = z_floor(y_hi)
        y_m = y_hi - spec("manifold_gap") - man_r
        for j, kind in enumerate(lv["channels"]):
            xc = a + (j + 0.5) * cpitch
            name = f"L{lv['i']}-C{j + 1:02d}"
            ch_, tube = _channel_parts(d, expect, name, kind, xc, y_hi, z_hi, s_feed, y_m, z_hi)
            ch_.update(level=lv["i"], s_drain=s_drain)
            channels.append(ch_)
            tubes.append(tube)
            # drain stub: vertical, top cut by the inclined floor, bottom on the collector's top
            z_stub_bot = z_floor(y_drain) - spec("drain_stub_len")
            expect[f"{name}-drain"] = dict(kind="drain", lo=(xc - drain_r, y_drain - drain_r, z_stub_bot),
                                           hi=(xc + drain_r, y_drain + drain_r, z_floor(y_drain - drain_r)),
                                           volume=math.pi * drain_r ** 2 * spec("drain_stub_len"))
        ml = spec("manifold_len")
        pipes.append(dict(name=f"L{lv['i']}-manifold", kind="manifold", y=y_m, z=z_hi, r=man_r,
                          r_in=man_r - spec("manifold_wall"), x0=W / 2 - ml / 2, length=ml))
        expect[f"L{lv['i']}-manifold"] = dict(kind="manifold", lo=(W / 2 - ml / 2, y_m - man_r, z_hi - man_r),
                                              hi=(W / 2 + ml / 2, y_m + man_r, z_hi + man_r),
                                              volume=math.pi * (man_r ** 2 - (man_r - spec("manifold_wall")) ** 2) * ml)
        cl = spec("collector_len")
        z_c = z_floor(y_drain) - spec("drain_stub_len") - coll_r
        pipes.append(dict(name=f"L{lv['i']}-collector", kind="collector", y=y_drain, z=z_c, r=coll_r, r_in=0.0,
                          x0=W / 2 - cl / 2, length=cl))
        expect[f"L{lv['i']}-collector"] = dict(kind="collector", lo=(W / 2 - cl / 2, y_drain - coll_r, z_c - coll_r),
                                               hi=(W / 2 + cl / 2, y_drain + coll_r, z_c + coll_r),
                                               volume=math.pi * coll_r ** 2 * cl)
    d.update(channels=channels, tubes=tubes, pipes=pipes, expect=expect)
    _function_numbers(d, expect)
    clear = {}
    nxt = [lv["z_b"] for lv in levels[1:]] + [H]
    for lv, z_next in zip(levels, nxt):
        if lv["kind"] != "nft":
            continue
        top = max(e["hi"][2] for nm, e in expect.items() if nm.startswith(f"L{lv['i']}-C") and e["kind"] in ("lid", "cap"))
        tube_top = max(e["hi"][2] for nm, e in expect.items() if nm.startswith(f"L{lv['i']}-C") and e["kind"] == "tube")
        clear[lv["i"]] = dict(lid_top=top, tube_top=tube_top, next_underside=z_next - a, plant_clear=z_next - a - top)
    d["headroom"] = clear


def _down_turn(o, angle_deg, side):
    """Direction leaving an elbow whose socket takes a spigot pointing along o: turned by angle_deg toward -Z, in the
    vertical plane containing o. `side` is the horizontal unit direction of o."""
    a = math.atan2(-o[2], math.hypot(o[0], o[1])) + math.radians(angle_deg)   # angle below horizontal
    return (side[0] * math.cos(a), side[1] * math.cos(a), -math.sin(a))


def _pp_elbow(c_socket_bottom, o_in, o_out):
    """Ostendorf HTB 87 on a spigot pointing along o_in whose end sits at the socket bottom. Returns (legs, corner,
    spigot end)."""
    z2, l1, t = pv("pp32_elbow", "z2"), pv("pp32_elbow", "l1"), pv("pp32_pipe", "t")
    ro, ri = pv("pp32_elbow", "body_od") / 2, pv("pp32_elbow", "body_od") / 2 - pv("pp32_elbow", "wall")
    hub = pv("pp32_pipe", "D") / 2
    corner = L_.add(c_socket_bottom, o_in, z2)
    sh = pv("pp32_pipe", "shoulder")
    lg = L_.elbow(corner, tuple(-x for x in o_in),
                  [(None, z2 - sh, ro, ri), (z2 - sh, z2, hub, ri), (z2, z2 + t, hub, pv("pp32_pipe", "od") / 2)],
                  o_out, [(None, l1, ro, ri)])
    return lg, corner, L_.add(corner, o_out, l1)


def _derive_table(d, s):
    """Two passes: lay the table out with no bay, find where the return pipe crosses the tote lid, then widen the
    bay left of channel 1 by what keeps the tote clear of the back-left post. Everything is x-shifted by the bay."""
    trial = dict(d, bay=0.0, tube_len={})
    _table_layout(trial, s)
    a = spec("frame_a")
    need = a + s["tote_post_gap"] + s["grommet_edge"] - trial["return_lid_point"][0]
    d["bay"] = max(0.0, need)
    d["bay_governed_by"] = ("return pipe over the tote lid, tote clear of the back-left post" if need > 0
                            else "none: no bay needed")
    _table_layout(d, s)


def _table_layout(d, s):
    a, theta, slope = spec("frame_a"), d["theta"], s["slope"]
    cw, ch, ct, lt, capt = (spec(k) for k in ("channel_w", "channel_h", "channel_t", "lid_t", "cap_t"))
    Lc_ = s["channel_len"]
    Lo = Lc_ + 2 * capt
    n = len(s["levels"][0])
    pitch = s["channel_pitch"]
    expect = {}
    joints = []          # (male, female, male's entering radius, expected depth mm, min depth mm or None, label)
    d.update(channel_overall=Lo, Lo=Lo)

    # ---- channel low end: drain cap spigot -> elbow -> drop tip, in channel-local terms (independent of position) ----
    spo, spl, spz = pv("drain_cap", "spigot_od") / 2, pv("drain_cap", "spigot_len"), pv("drain_cap", "spigot_z")
    y_hi = -s["overhang_front"]
    o_ch = (0.0, math.cos(theta), -math.sin(theta))
    up_ch = (0.0, math.sin(theta), math.cos(theta))
    ang = pv("pp32_elbow", "angle")
    o_drop = _down_turn(o_ch, ang, (0.0, 1.0, 0.0))
    p_sp0_rel = L_.add(L_.add((0.0, 0.0, 0.0), o_ch, Lo), up_ch, spz)      # spigot root on the cap's outer face
    p_sp1_rel = L_.add(p_sp0_rel, o_ch, spl)
    _, corner_rel, tip_rel = _pp_elbow(p_sp1_rel, o_ch, o_drop)
    delta_tip = tip_rel[1] - Lo * math.cos(theta)                           # tip ahead of the low cap face, in Y
    coll_w = cw
    ob_need = spec("collector_gap") + coll_w / 2 - delta_tip                # collector clear of the back posts
    ovb = max(s["overhang_back_min"], ob_need)
    d["overhang_back_governed_by"] = "overhang_back_min" if ovb == s["overhang_back_min"] else "collector clear of the posts"
    y_lo = y_hi + Lo * math.cos(theta)
    D = y_lo - ovb
    span = D - a
    d.update(D=D, support_span=span, drop=slope * span, y_hi=y_hi, y_lo=y_lo, overhang_front=-y_hi, overhang_back=ovb)
    z_f = s["work_h"] + slope * (y_hi - a)          # floor line z(y) = z_f - slope (y - a) passes z_hi = work_h at y_hi
    z_b = z_f - d["drop"]
    z_hi = s["work_h"]
    d["levels_derived"] = [dict(i=1, kind="nft", channels=s["levels"][0], z_b=z_b, z_f=z_f)]
    d["level_z0_used"] = z_b
    tip_z_rel = tip_rel[2]                          # relative to z_hi

    # ---- collector: a Growrilla channel along X behind the back posts, falling at the same slope toward -X ----
    y_coll = y_lo + delta_tip
    tc = theta
    ac = (-math.cos(tc), 0.0, -math.sin(tc))        # along, downhill
    uc = (-math.sin(tc), 0.0, math.cos(tc))         # up, normal to the floor
    xc_ = (0.0, 1.0, 0.0)                           # across
    hole_c = spo + s["coll_hole_clear"]
    tl = TOTES[s["tote_label"]]
    tote_L, tote_W, tote_H = tl["lid_l"], tl["lid_w"], tl["h_with_lid"]
    xs_rel = [j * pitch for j in range(n)]
    Lcol = (xs_rel[-1] - xs_rel[0]) + 2 * (hole_c + s["coll_edge"])
    Lco = Lcol + 2 * capt
    c_drop = _down_turn(ac, ang, (-1.0, 0.0, 0.0))
    x_t0_min = a + s["tote_post_gap"]
    bay = d["bay"]
    x1 = a + bay + pitch / 2
    W = 2 * a + bay + n * pitch
    d["W"] = W

    # ---- frame: posts to their rail tops, one ring of rails ----
    _box(expect, "POST-FL", "frame", (0.0, 0.0, 0.0), (a, a, z_f))
    _box(expect, "POST-FR", "frame", (W - a, 0.0, 0.0), (a, a, z_f))
    _box(expect, "POST-BL", "frame", (0.0, D - a, 0.0), (a, a, z_b))
    _box(expect, "POST-BR", "frame", (W - a, D - a, 0.0), (a, a, z_b))
    _box(expect, "L1-RAIL-F", "frame", (a, 0.0, z_f - a), (W - 2 * a, a, a))
    _box(expect, "L1-RAIL-B", "frame", (a, D - a, z_b - a), (W - 2 * a, a, a))
    _box(expect, "L1-RAIL-L", "frame", (0.0, a, z_b - a), (a, D - 2 * a, a))
    _box(expect, "L1-RAIL-R", "frame", (W - a, a, z_b - a), (a, D - 2 * a, a))
    d["H"] = z_f

    # ---- channels, feed tubes, drain spigots and elbows ----
    man_r = pv("pvc1_pipe", "od") / 2
    man_ri = man_r - pv("pvc1_pipe", "wall")
    y_m = y_hi - spec("manifold_gap") - man_r
    z_m = z_hi
    s_feed = spec("feed_hole_inset")
    channels, tubes, returns = [], [], []
    d["channel_pitch"] = {1: pitch}
    for j, kind in enumerate(s["levels"][0]):
        xc = x1 + j * pitch
        name = f"L1-C{j + 1:02d}"
        c, tube = _channel_parts(d, expect, name, kind, xc, y_hi, z_hi, s_feed, y_m, z_m)
        c.update(level=1)
        off = (xc, y_hi, z_hi)
        sp0 = L_.add(off, p_sp0_rel)
        spig = L_.straight(sp0, o_ch, [(spl, spo, 0.0)])
        expect[f"{name}-drain"] = L_.legs_expect("drain", spig)
        lg, corner, tip = _pp_elbow(L_.add(sp0, o_ch, spl), o_ch, o_drop)
        expect[f"{name}-elbow"] = L_.legs_expect("fitting", lg)
        joints.append((f"{name}-drain", f"{name}-elbow", spo, pv("pp32_pipe", "t"), None,
                       f"{name} drain cap spigot in the HTB socket"))
        c.update(drain_root=sp0, elbow_corner=corner, tip=tip, o_drop=o_drop)
        channels.append(c)
        tubes.append(tube)
        # water's lowest line: channel floor at the low end, spigot invert, then the drop's axis
        floor_lo = L_.add(L_.add(off, o_ch, capt + Lc_), up_ch, ct)
        inv0 = L_.add(sp0, up_ch, -spo)
        returns.append(dict(name=name, pts=[floor_lo, inv0, L_.add(inv0, o_ch, spl), tip]))

    # ---- collector, placed ----
    x_hi_face = x1 + xs_rel[-1] + hole_c + s["coll_edge"] + capt     # collector hi cap's outer face
    xs = [x1 + x for x in xs_rel]
    tip_z = z_hi + tip_z_rel
    tip_lat = spo * math.sqrt(1 - o_drop[2] ** 2)          # tilt of the tip disc
    # local frame origin z (floor bottom at the hi cap's outer face): centre the tips between floor top and lid underside
    s_at = lambda x: (x_hi_face - x) / math.cos(tc)          # along-collector coordinate at world x (on the axis)
    def zw(x, zl):                                           # world z of the collector axis point at x, local height zl
        return -s_at(x) * math.sin(tc) + zl * math.cos(tc)
    # three constraints on the collector's height (its origin z, Ozc), all at the worst drop:
    #   tip above the floor top (+X drop, highest floor), tip below the lid underside (-X drop, lowest lid),
    #   the elbow's socket hub above the lid top (+X drop, highest lid). Ozc sits midway in what they leave.
    hub_r, sh, z2 = pv("pp32_pipe", "D") / 2, pv("pp32_pipe", "shoulder"), pv("pp32_elbow", "z2")
    corner_z = z_hi + corner_rel[2]
    hub_low = corner_z + (z2 - sh) * math.sin(theta) - hub_r * math.cos(theta)   # hub rises going back up the channel
    m = s["tip_margin"]
    up_floor = (tip_z - tip_lat) - zw(xs[-1] + spo, ct)
    up_hub = hub_low - zw(xs[-1] + hub_r, ch + lt)
    lo_lid = (tip_z + tip_lat) - zw(xs[0] - spo, ch)
    Ozc = (lo_lid + min(up_floor, up_hub)) / 2
    d["collector_tip_air"] = dict(floor=up_floor - Ozc, lid=Ozc - lo_lid, hub=up_hub - Ozc)
    d["collector_z_governed_by"] = "hub over the lid" if up_hub < up_floor else "tip over the floor"
    Oc = (x_hi_face, y_coll, Ozc)
    Fc = (Oc, xc_, ac, uc)
    d["collector_frame"] = Fc
    d["collector_len"] = Lcol
    # parts: body, lid with the drop holes, hi cap, lo drain cap, drain spigot, elbow
    u_area = cw * ch - (cw - 2 * ct) * (ch - ct)
    lo, hi = L_.frame_box_bbox(Fc, -cw / 2, cw / 2, capt, capt + Lcol, 0.0, ch)
    expect["COLL-body"] = dict(kind="collector", lo=lo, hi=hi, volume=u_area * Lcol,
                               geom=("ubody", Fc, cw, ch, ct, capt, capt + Lcol))
    lid_n = uc
    holes, hole_vol = [], 0.0
    for c in channels:
        cosg = abs(L_.dot(c["o_drop"], lid_n))
        holes.append((c["tip"], c["o_drop"], hole_c))
        hole_vol += math.pi * hole_c ** 2 * lt / cosg
    lo, hi = L_.frame_box_bbox(Fc, -cw / 2, cw / 2, capt, capt + Lcol, ch, ch + lt)
    expect["COLL-lid"] = dict(kind="collector", lo=lo, hi=hi, volume=cw * Lcol * lt - hole_vol,
                              geom=("plate", Fc, (-cw / 2, cw / 2, capt, capt + Lcol, ch, ch + lt), holes))
    for end, s0 in (("hi", 0.0), ("lo", capt + Lcol)):
        lo, hi = L_.frame_box_bbox(Fc, -cw / 2, cw / 2, s0, s0 + capt, 0.0, ch + lt)
        expect[f"COLL-cap-{end}"] = dict(kind="cap", lo=lo, hi=hi, volume=cw * capt * (ch + lt),
                                         geom=("plate", Fc, (-cw / 2, cw / 2, s0, s0 + capt, 0.0, ch + lt), []))
    c_sp0 = L_.frame_place(Fc, 0.0, Lco, spz)
    spig = L_.straight(c_sp0, ac, [(spl, spo, 0.0)])
    expect["COLL-drain"] = L_.legs_expect("drain", spig)
    lg, c_corner, c_tip = _pp_elbow(L_.add(c_sp0, ac, spl), ac, c_drop)
    expect["COLL-elbow"] = L_.legs_expect("fitting", lg)
    joints.append(("COLL-drain", "COLL-elbow", spo, pv("pp32_pipe", "t"), None, "collector drain spigot in the HTB socket"))

    # ---- tote, return pipe, grommets ----
    td = s["tote_draw"]
    tlid_t, wall_t = td["lid_t"], td["wall_t"]
    body_h = tote_H - tlid_t
    in_bot_L, in_bot_W, in_h = _i(22.98), _i(14.02), _i(14.30)   # HD 999-27G-HDX interior at bottom (tote_label)
    floor_top = body_h - in_h
    # return pipe: HTEM socket over the elbow spigot; pick the shortest stocked length that ends deep enough
    t_pp, D_pp, r_pp = pv("pp32_pipe", "t"), pv("pp32_pipe", "D") / 2, pv("pp32_pipe", "od") / 2
    ri_pp = r_pp - pv("pp32_pipe", "wall")
    sock_face = L_.add(c_tip, c_drop, -t_pp)
    lid_under = body_h
    need = None
    for Lp in pv("pp32_pipe", "lengths"):
        end = L_.add(c_tip, c_drop, Lp)
        if end[2] <= lid_under - s["return_depth_min"]:
            need = Lp
            break
    assert need is not None, "no stocked HTEM length reaches the tote"
    Lp = need
    d["return_len"] = Lp
    sh = pv("pp32_pipe", "shoulder")
    ret = L_.straight(sock_face, c_drop, [(t_pp, D_pp, r_pp), (sh, D_pp, ri_pp), (Lp - sh, r_pp, ri_pp)])
    expect["RET-pipe"] = L_.legs_expect("pipe", ret)
    joints.append(("COLL-elbow", "RET-pipe", r_pp, t_pp, None, "HTB spigot in the HTEM socket"))
    ret_end = L_.add(c_tip, c_drop, Lp)
    # where the pipe axis crosses the lid's mid-plane
    zmid = body_h + tlid_t / 2
    k = (zmid - c_tip[2]) / c_drop[2]
    ret_lid = L_.add(c_tip, c_drop, k)
    # tote: back edge grommet_edge behind the return, left edge clear of the post; the bay was sized on the tip x
    x_t0 = ret_lid[0] - s["grommet_edge"]
    y_t1 = ret_lid[1] + s["grommet_edge"]
    t_lo = (x_t0, y_t1 - tote_W, 0.0)
    d.update(tote_lo=t_lo, tote_size=(tote_L, tote_W, tote_H), tote_floor_top=floor_top, tote_lid_under=lid_under)
    cav_bot = ((x_t0 + (tote_L - in_bot_L) / 2, t_lo[1] + (tote_W - in_bot_W) / 2), (in_bot_L, in_bot_W))
    cav_top = ((x_t0 + wall_t, t_lo[1] + wall_t), (tote_L - 2 * wall_t, tote_W - 2 * wall_t))
    hcav = body_h - floor_top
    Ab, At = in_bot_L * in_bot_W, cav_top[1][0] * cav_top[1][1]
    Am = (in_bot_L + cav_top[1][0]) / 2 * (in_bot_W + cav_top[1][1]) / 2
    cav_vol = hcav / 6 * (Ab + 4 * Am + At)
    _vol = tote_L * tote_W * body_h - cav_vol
    expect["TOTE-body"] = dict(kind="tote", lo=t_lo, hi=(x_t0 + tote_L, y_t1, body_h), volume=_vol,
                               geom=("tub", t_lo, (tote_L, tote_W, body_h), floor_top, cav_bot, cav_top))
    d["tote_cavity"] = dict(bot=cav_bot, top=cav_top, z0=floor_top, z1=body_h, volume=cav_vol)
    # pump on the floor at the front of the cavity, centred in X
    P = PUMPS[s["pump"]]
    pL, pW, pH = P["size"][0]
    x_p = x_t0 + tote_L / 2
    y_p = cav_bot[0][1] + s["pump_wall_gap"] + pW / 2
    p_lo = (x_p - pL / 2, y_p - pW / 2, floor_top)
    _box(expect, "PUMP", "pump", p_lo, (pL, pW, pH))
    expect["PUMP"]["geom"] = ("box", p_lo, (pL, pW, pH))
    out_xy = (x_p + P["outlet"][0][0], y_p + P["outlet"][0][1])
    barb_r, barb_l = pv("hose_34", "id") / 2, P["barb_len"][0]   # contact envelope at the hose ID (barb_d is the nominal)
    pump_top = floor_top + pH
    barb = L_.straight((out_xy[0], out_xy[1], pump_top), (0, 0, 1), [(barb_l, barb_r, 0.0)])
    expect["PUMP-barb"] = L_.legs_expect("fitting", barb)

    # ---- supply: elbow at the manifold's left end, pipe, valve, bushing, insert, hose ----
    x_r = x1 - s["riser_offset"]
    G, H_, M = pv("ell_406_010", "G"), pv("ell_406_010", "H"), pv("ell_406_010", "M")
    e_corner = (x_r, y_m, z_m)
    ell = L_.elbow(e_corner, (1, 0, 0), [(None, G, M / 2, man_ri), (G, H_, M / 2, man_r)],
                   (0, 0, -1), [(None, G, M / 2, man_ri), (G, H_, M / 2, man_r)])
    expect["SUP-elbow"] = L_.legs_expect("fitting", ell)
    # manifold pipe: from the elbow's +X socket bottom to the cap's socket bottom
    cap_M, cap_W, cap_dep = pv("cap_447_010", "M"), pv("cap_447_010", "W"), pv("cap_447_010", "depth")
    x_cap_face = x1 + (n - 1) * pitch + spec("feed_tube_od") / 2 + s["manifold_end"]
    x_m0, x_m1 = x_r + G, x_cap_face + cap_dep
    man = L_.straight((x_m0, y_m, z_m), (1, 0, 0), [(x_m1 - x_m0, man_r, man_ri)])
    expect["SUP-manifold"] = L_.legs_expect("manifold", man)
    cap = L_.straight((x_cap_face, y_m, z_m), (1, 0, 0), [(cap_dep, cap_M / 2, man_r), (cap_W - cap_dep, cap_M / 2, 0.0)])
    expect["SUP-cap"] = L_.legs_expect("fitting", cap)
    joints += [("SUP-manifold", "SUP-elbow", man_r, H_ - G, pv("d2466_1", "depth_min"), "manifold in the 406-010 socket"),
               ("SUP-manifold", "SUP-cap", man_r, cap_dep, pv("d2466_1", "depth_min"), "manifold in the 447-010 cap")]
    # riser pipe: elbow down-socket bottom to the valve's top socket bottom
    vA, vB, vC, vD, vE = (pv("valve_2122_010", k) for k in "ABCDE")
    v_sock = (vC - vB) / 2
    z_valve_top = z_m - H_ - s["riser_pipe"]
    z_r0, z_r1 = z_m - G, z_valve_top - v_sock
    riser = L_.straight((x_r, y_m, z_r0), (0, 0, -1), [(z_r0 - z_r1, man_r, man_ri)])
    expect["SUP-riser"] = L_.legs_expect("pipe", riser)
    valve = L_.straight((x_r, y_m, z_valve_top), (0, 0, -1),
                        [(v_sock, vA / 2, man_r), (vB, vA / 2, pv("valve_2122_010", "bore") / 2), (v_sock, vA / 2, man_r)])
    expect["SUP-valve"] = L_.legs_expect("valve", valve)
    zc_v = z_valve_top - vC / 2
    hw = pv("valve_2122_010", "handle_w")
    h_lo = (x_r - hw / 2, y_m - vD, zc_v - vE / 2)
    _box(expect, "SUP-valve-handle", "valve", h_lo, (hw, vD - vA / 2, vE))
    expect["SUP-valve-handle"]["geom"] = ("box", h_lo, (hw, vD - vA / 2, vE))
    joints += [("SUP-riser", "SUP-elbow", man_r, H_ - G, pv("d2466_1", "depth_min"), "riser in the 406-010 down socket"),
               ("SUP-riser", "SUP-valve", man_r, v_sock, pv("d2466_1", "depth_min"), "riser in the valve's top socket")]
    # bushing: 1 in spigot up into the valve's bottom socket, to its bottom
    bL, bN = pv("bush_437_131", "L"), pv("bush_437_131", "N")
    z_valve_bot = z_valve_top - vC
    z_b_top = z_valve_bot + v_sock
    z_b_bot = z_b_top - bL
    r34 = pv("pvc34_pipe", "od") / 2
    bush = L_.straight((x_r, y_m, z_b_bot), (0, 0, 1),
                       [(bL - bN, man_r, r34), (bN, man_r, pv("bush_437_131", "bore") / 2)])
    expect["SUP-bushing"] = L_.legs_expect("fitting", bush)
    joints.append(("SUP-bushing", "SUP-valve", man_r, v_sock, pv("d2466_1", "depth_min"), "437-131 spigot in the valve's bottom socket"))
    # insert adapter: spigot up into the bushing socket, collar, barb down
    iL, iN, isp = pv("ins_460_007", "L"), pv("ins_460_007", "N"), pv("ins_460_007", "spigot")
    i_top = z_b_bot + (bL - bN)
    ins_r = pv("ins_460_007", "insert_env") / 2
    ins = L_.straight((x_r, y_m, i_top), (0, 0, -1), [(isp, r34, 0.0), (iN, r34, 0.0), (iL - isp - iN, ins_r, 0.0)])
    expect["SUP-insert"] = L_.legs_expect("fitting", ins)
    joints.append(("SUP-insert", "SUP-bushing", r34, bL - bN, pv("d2466_34", "depth_min"), "460-007 spigot in the bushing socket"))
    z_collar_bot = i_top - isp - iN
    z_ins_tip = i_top - iL
    # hose: pump barb root, up through the lid, run to the front, along X, up over the insert to the collar
    h_ro, h_ri, R = pv("hose_34", "od") / 2, pv("hose_34", "id") / 2, pv("hose_34", "bend_r")
    zr = s["supply_z"]
    pts = [(out_xy[0], out_xy[1], pump_top), (out_xy[0], out_xy[1], zr), (out_xy[0], y_m, zr), (x_r, y_m, zr),
           (x_r, y_m, z_collar_bot)]
    expect["SUP-hose"] = L_.sweep_expect("hose", pts, h_ro, h_ri, R)
    joints += [("PUMP-barb", "SUP-hose", barb_r, barb_l, None, "pump barb in the hose"),
               ("SUP-insert", "SUP-hose", ins_r, z_collar_bot - z_ins_tip, None, "460-007 insert in the hose")]
    d["supply_chain"] = ["PUMP", "PUMP-barb", "SUP-hose", "SUP-insert", "SUP-bushing", "SUP-valve", "SUP-riser",
                         "SUP-elbow", "SUP-manifold", "SUP-cap"]

    # ---- tote lid with the two grommet holes, and the grommets ----
    g = {}
    for key, gid, p_axis, o_axis, pipe_r in (("RET", "grommet_g1l", ret_lid, c_drop, r_pp),
                                             ("SUP", "grommet_g07l", (out_xy[0], out_xy[1], zmid), (0.0, 0.0, -1.0), h_ro)):
        gOD, gGD, gGW, gT, hole = (pv(gid, k) for k in ("OD", "GD", "GW", "T", "hole"))
        fl = (gT - gGW) / 2
        start = L_.add(p_axis, o_axis, -gT / 2)
        gl = L_.straight(start, o_axis, [(fl, gOD / 2, pipe_r), (gGW, hole / 2, pipe_r), (fl, gOD / 2, pipe_r)])
        expect[f"{key}-grommet"] = L_.legs_expect("grommet", gl)
        g[key] = (p_axis, o_axis, hole / 2)
    lid_lo = (x_t0, t_lo[1], body_h)
    lid_holes = [(g[k][0], g[k][1], g[k][2]) for k in ("RET", "SUP")]
    hv = sum(math.pi * r ** 2 * tlid_t / abs(o[2]) for _, o, r in lid_holes)
    expect["TOTE-lid"] = dict(kind="tote", lo=lid_lo, hi=(x_t0 + tote_L, y_t1, tote_H), volume=tote_L * tote_W * tlid_t - hv,
                              geom=("plate", ((0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
                                    (x_t0, x_t0 + tote_L, t_lo[1], y_t1, body_h, tote_H), lid_holes))
    joints += [("RET-pipe", "RET-grommet", r_pp, None, None, "return pipe through the G1L"),
               ("SUP-hose", "SUP-grommet", h_ro, None, None, "hose through the G07L")]
    d["grommet_gw"] = {k: pv(gid, "GW") for k, gid in (("RET", "grommet_g1l"), ("SUP", "grommet_g07l"))}

    # ---- return paths: centreline points from each channel's drain to the tote, must fall all the way ----
    paths = {}
    for r_ in returns:
        c = next(c for c in channels if c["name"] == r_["name"])
        s_tip = (x_hi_face - c["xc"]) / math.cos(tc)
        land = (c["xc"], y_coll, Ozc - s_tip * math.sin(tc) + ct * math.cos(tc))   # collector floor under the tip
        c_inv0 = L_.add(c_sp0, uc, -spo)
        paths[r_["name"]] = r_["pts"] + [land, L_.frame_place(Fc, 0.0, capt + Lcol, ct), c_inv0,
                                         L_.add(c_inv0, ac, spl), c_tip, ret_end]
    d["return_paths"] = paths
    d["return_end"] = ret_end
    d["return_lid_point"] = ret_lid

    d.update(channels=channels, tubes=tubes, pipes=[], expect=expect, joints=joints,
             x1=x1, x_r=x_r, y_m=y_m, z_m=z_m, y_coll=y_coll, out_xy=out_xy, pump_top=pump_top, hose_pts=pts,
             valve_center_z=zc_v, insert_tip_z=z_ins_tip, collar_z=z_collar_bot)
    _function_numbers(d, expect)

    # ---- pump duty: required flow, static head, rated flow at that head ----
    req = (n * spec("flow_min_lpm"), n * spec("flow_max_lpm"))
    z_top_supply = max(e["hi"][2] for nm, e in expect.items() if e["kind"] == "tube")
    reg = RESERVOIRS[s["reservoir"]]
    wl = None if reg.fill_depth is None else lid_under - reg.fill_depth
    head_bound = z_top_supply - floor_top                 # waterline unknown: worst case at the tote floor
    head = None if wl is None else z_top_supply - wl
    d["pump_duty"] = dict(req_lpm=req, req_gph=tuple(q * 60 / 3.785411784 for q in req), z_top=z_top_supply,
                          waterline=wl, head=head, head_bound=head_bound,
                          gph_at_bound=pump_gph(s["pump"], head_bound / (12 * IN)),
                          gph_at_head=None if head is None else pump_gph(s["pump"], head / (12 * IN)))
    d["NOT_MODELLED"] = NOT_MODELLED.get(d["rack"], ())


def pump_gph(pump: str, head_ft: float) -> float | None:
    """Linear interpolation on the digitised chart; None outside it."""
    pts = PUMPS[pump]["curve"][0]
    for (h0, q0), (h1, q1) in zip(pts, pts[1:]):
        if h0 <= head_ft <= h1:
            return q0 + (q1 - q0) * (head_ft - h0) / (h1 - h0)
    return None


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def _sources_ok(rack):
    s = RACKS[rack]
    for k, (v, tag, src) in SPEC.items():
        assert v is not None and tag in TAGS and src, f"SPEC {k}: value/tag/source missing ({v}, {tag})"
    for k, kv in CHANNEL_KINDS.items():
        assert kv["src"][0] in TAGS and kv["src"][1], f"channel kind {k}: no source"
    src = RACK_SOURCES.get(rack, {})
    untagged = [k for k in s if k not in src or src[k][0] not in TAGS]
    assert not untagged, f"{rack}: inputs without a source tag: {untagged}"


def gaps(rack: str) -> list[str]:
    """Load-bearing values that are not sourced: PLACEHOLDERs in the bought parts the rack uses, and reservoir
    registry fields still None. Empty for growing_up_pro (it uses none of them)."""
    s = RACKS[rack]
    if "work_h" not in s:
        return []
    out = []
    for row, r in list(PLUMBING.items()) + [(s["pump"], PUMPS[s["pump"]])]:
        for k, v in r.items():
            if isinstance(v, tuple) and len(v) == 3 and v[1] == "PLACEHOLDER":
                out.append(f"{row}.{k} (PLACEHOLDER: {v[2]})")
    if RACK_SOURCES[rack]["tote_draw"][0] == "PLACEHOLDER":
        out.append(f"tote_draw {s['tote_draw']} (PLACEHOLDER: tote lid and wall thickness)")
    out.append(f"cap_t (PLACEHOLDER: {SPEC['cap_t'][2]})")
    reg = RESERVOIRS[s["reservoir"]]
    for f in ("lid_outer", "lid_thickness", "rim_lip", "wall_draft_deg", "inner_depth", "fill_depth"):
        if getattr(reg, f) is None:
            out.append(f"reservoir {reg.name}.{f} is None (caliper it: cacad/registries/reservoirs.py)")
    return out


def validate(rack: str) -> dict:
    """Raise AssertionError on anything not buildable, not usable or not sourced. No warnings."""
    d = derive(rack)
    s = RACKS[rack]
    _sources_ok(rack)
    for row, r in list(PLUMBING.items()) + list(PUMPS.items()):
        for k, v in r.items():
            if isinstance(v, tuple):
                assert len(v) == 3 and v[1] in TAGS and v[2], f"{row}.{k}: value/tag/source missing"
    assert spec("slope_min") - 1e-12 <= s["slope"] <= spec("slope_max") + 1e-12, f"{rack}: slope 1:{1 / s['slope']:.0f} outside 1:30..1:40"
    zs = [lv["z_b"] for lv in d["levels_derived"]]
    H = d.get("H", s.get("H"))
    assert zs == sorted(zs) and zs[0] > spec("frame_a"), f"{rack}: levels {zs} do not fit"
    if "work_h" not in s:
        assert max(lv["z_f"] for lv in d["levels_derived"]) < H - spec("frame_a"), f"{rack}: levels {zs} do not fit in H {H:.0f}"
    assert d["overhang_front"] > 0 and d["overhang_back"] > 0, f"{rack}: overhangs {d['overhang_front']:.1f} / {d['overhang_back']:.1f}"
    for i, p in d.get("channel_pitch", {}).items():
        assert p > spec("channel_w"), f"{rack}: level {i} channel pitch {p:.1f} <= channel width {spec('channel_w')}"
    used = {c["kind"] for c in d["channels"]}
    for k in used:
        assert d["site_web"][k] > 0, f"{rack}: {k} site web {d['site_web'][k]:.1f} mm: holes merge"
        assert d["first_site_edge"][k] > d["feed_hole_edge"], f"{rack}: {k} first site hole cuts the feed hole"
        assert d["first_site_edge"][k] > spec("cap_t"), f"{rack}: {k} sites run into the caps"
    for t in d["tubes"]:
        assert all(sg > 2 * t["bend_r"] for sg in t["segs"][1:2]) and all(sg > t["bend_r"] for sg in (t["segs"][0], t["segs"][2])), \
            f"{rack}: {t['name']} runs {[round(x, 1) for x in t['segs']]} too short for bend r {t['bend_r']}"
    if "work_h" not in s:
        assert d["sites"]["F"] == 96, f"{rack}: finishing sites {d['sites']['F']}, AM Hydro states 96"
        for i, h in d["headroom"].items():
            assert h["plant_clear"] >= spec("plant_clear_min"), f"{rack}: level {i} plant clearance {h['plant_clear']:.0f} < {spec('plant_clear_min'):.0f}"
            assert h["tube_top"] < h["next_underside"], f"{rack}: level {i} feed tubes hit the level above"
        return d
    _validate_table(d, s)
    return d


def _validate_table(d, s):
    """Every check runs; all failures are raised together, layout first, then the unsourced values."""
    rack = d["rack"]
    bad = []

    def need(ok, msg):
        if not ok:
            bad.append(msg)

    for k, v in d["collector_tip_air"].items():
        need(v >= s["tip_margin"], f"collector: {k} air {v:.1f} mm, min {s['tip_margin']} (tip_margin): the HTB 87 spigot "
             f"leaves {sum(d['collector_tip_air'][x] for x in ('lid', 'hub')):.1f} mm between tip-under-lid and hub-over-lid "
             "across a collector falling 1:40")
    hs = d["expect"]["SUP-hose"]["segs"]
    R = pv("hose_34", "bend_r")
    need(hs[0] > R and hs[-1] > R and all(x > 2 * R for x in hs[1:-1]), f"hose runs {[round(x) for x in hs]} too short for bend r {R}")
    for name, pts in d["return_paths"].items():
        zs = [p[2] for p in pts]
        need(all(b_ < a_ for a_, b_ in zip(zs, zs[1:])), f"return path from {name} does not fall all the way: {[round(z, 1) for z in zs]}")
    need(d["tote_lo"][0] >= spec("frame_a") + s["tote_post_gap"] - 1e-6, f"tote at x {d['tote_lo'][0]:.1f} hits the back-left post")
    need(pv("ell_406_010", "H") - pv("ell_406_010", "G") >= pv("d2466_1", "depth_min"), "ell_406_010: socket shallower than ASTM D2466")
    duty = d["pump_duty"]
    q = duty["gph_at_bound"]
    need(q is not None and q >= duty["req_gph"][1], f"pump gives {q} GPH at {duty['head_bound'] / (12 * IN):.2f} ft, needs {duty['req_gph'][1]:.0f}")
    reg = RESERVOIRS[s["reservoir"]]
    if reg.lid_thickness is not None:
        for k, gw in d["grommet_gw"].items():
            need(reg.lid_thickness <= gw, f"tote lid {reg.lid_thickness} mm thicker than the {k} grommet groove {gw:.1f}")
    if reg.fill_depth is not None:
        wl = duty["waterline"]
        need(wl < d["return_end"][2], f"waterline {wl:.0f} at or above the return pipe end {d['return_end'][2]:.0f}")
        need(wl > d["pump_top"], f"waterline {wl:.0f} below the pump top {d['pump_top']:.0f}")
    else:
        bad.append("waterline unknown (fill_depth None): cannot check it sits below the return pipe end and above the pump")
    g = gaps(rack)
    if g:
        bad.append(f"{len(g)} load-bearing values not sourced:\n    " + "\n    ".join(g))
    assert not bad, f"{rack}: {len(bad)} failures:\n  " + "\n  ".join(bad)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
def report(rack: str) -> str:
    d = derive(rack)
    s = RACKS[rack]
    if "work_h" in s:
        return _report_table(d, s)
    lo, hi = d["bbox"]
    W, D, H = s["W"], s["D"], s["H"]
    L = [f"{rack}: frame {W:.0f} x {D:.0f} x {H:.0f} mm ({W / IN:g} x {D / IN:g} x {H / IN:g} in); "
         f"overall {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} x {hi[2] - lo[2]:.0f} mm with plumbing",
         f"  slope 1:{1 / s['slope']:g} ({math.degrees(d['theta']):.2f} deg): drop {d['drop']:.1f} mm over the {d['support_span']:.0f} mm support span",
         f"  levels (back rail top, CONVENIENCE even split, pitch {d['level_pitch_used']:.1f} mm = {d['level_pitch_used'] / IN:.2f} in):"]
    for lv in d["levels_derived"]:
        extra = ""
        if lv["kind"] == "nft":
            h = d["headroom"][lv["i"]]
            extra = (f", front rail {lv['z_f']:.1f}; {len(lv['channels'])} channels {lv['channels']} at "
                     f"{d['channel_pitch'][lv['i']]:.1f} mm pitch; plant clearance {h['plant_clear']:.0f} mm "
                     f"({h['plant_clear'] / IN:.1f} in, min {spec('plant_clear_min') / IN:g})")
        L.append(f"    L{lv['i']} {lv['kind']:4s} z {lv['z_b']:.1f} ({lv['z_b'] / IN:.1f} in){extra}")
    L.append(f"  channel {s['channel_len']:.0f} mm + 2 caps = {d['Lo']:.0f}; overhang front {d['overhang_front']:.1f}, back {d['overhang_back']:.1f}")
    for k in ("F", "N"):
        kv = CHANNEL_KINDS[k]
        L.append(f"  {kv['label']:9s}: {d['channels_by_kind'][k]} channels x {kv['sites']} sites at {kv['pitch']:.1f} mm = "
                 f"{d['sites'][k]} sites; hole web {d['site_web'][k]:.1f}; first hole edge {d['first_site_edge'][k]:.1f} "
                 f"from the high end (feed hole edge {d['feed_hole_edge']:.1f})  [{kv['src'][0]}]")
    L.append(f"  sites total {sum(d['sites'].values())} (AM Hydro: 192 = 96 finishing + 96 nursery)")
    L.append(f"  feed tube path {next(iter(d['tube_len'].values())):.0f} mm each, {len(d['tubes'])} tubes; parts: {len(d['expect'])} solids")
    L.append("  rack inputs:")
    for k, (tag, src) in RACK_SOURCES[rack].items():
        L.append(f"    {k:16s} {str(s[k]) if not isinstance(s[k], float) else f'{s[k]:.3f}':>9s}  {tag:11s} {src}")
    L.append("  not modelled:")
    L += [f"    - {x}" for x in NOT_MODELLED[rack]]
    return "\n".join(L)


def _f(x):
    return f"{x:.1f}"


def _report_table(d, s) -> str:
    rack = d["rack"]
    lo, hi = d["bbox"]
    W, D, H = d["W"], d["D"], d["H"]
    duty = d["pump_duty"]
    k = CHANNEL_KINDS["G"]
    L = [f"{rack}: frame {W:.0f} x {D:.0f} x {H:.0f} mm ({W / IN:.1f} x {D / IN:.1f} x {H / IN:.1f} in, H = front rail top); "
         f"overall {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} x {hi[2] - lo[2]:.0f} mm, from ({_f(lo[0])}, {_f(lo[1])}, {_f(lo[2])})",
         f"  slope 1:{1 / s['slope']:g} ({math.degrees(d['theta']):.2f} deg): drop {d['drop']:.1f} mm over the {d['support_span']:.0f} mm support span",
         f"  working height (channel floor at the high end) {s['work_h']:.1f} mm = {s['work_h'] / IN:g} in; front rail top "
         f"{d['levels_derived'][0]['z_f']:.1f}, back rail top {d['levels_derived'][0]['z_b']:.1f}",
         f"  channels: {len(d['channels'])} x Growrilla 100x50, {s['channel_len']:.0f} mm + 2 caps = {d['Lo']:.0f}, at {s['channel_pitch']:.0f} mm "
         f"across; overhang front {d['overhang_front']:.1f}, back {d['overhang_back']:.1f} (governed by {d['overhang_back_governed_by']})",
         f"  sites: {k['sites']} per channel at {k['pitch']:.0f} mm, 48 mm holes = {d['sites']['G']} sites; hole web {d['site_web']['G']:.1f}; "
         f"first hole edge {d['first_site_edge']['G']:.1f} from the high end (feed hole edge {d['feed_hole_edge']:.1f})",
         f"  plumbing bay left of channel 1: {d['bay']:.1f} mm (governed by {d['bay_governed_by']})",
         f"  frame rails span {W - 2 * spec('frame_a'):.0f} mm in 2020 (SUBSTITUTE): stiffness NOT sized. Six channels, water film and "
         "plants hang on the front and back rails; size the member before building",
         "  supply (pump to feed tubes):",
         f"    pump {PUMPS[s['pump']]['what']} on the tote floor at z {d['tote_floor_top']:.1f}, top {d['pump_top']:.1f}; outlet barb at "
         f"({_f(d['out_xy'][0])}, {_f(d['out_xy'][1])})",
         f"    hose 3/4 x 1 in, path {d['expect']['SUP-hose']['path_len']:.0f} mm, runs {[round(x) for x in d['expect']['SUP-hose']['segs']]}, "
         f"bend r {pv('hose_34', 'bend_r'):.1f}; through a G07L grommet; run height {s['supply_z']:.0f}",
         f"    riser at x {d['x_r']:.1f}, y {d['y_m']:.1f}: 460-007 insert tip z {d['insert_tip_z']:.1f}, collar {d['collar_z']:.1f}; 437-131; "
         f"2122-010 valve centre z {d['valve_center_z']:.1f}; 1 in pipe; 406-010 elbow; manifold "
         f"{d['expect']['SUP-manifold']['hi'][0] - d['expect']['SUP-manifold']['lo'][0]:.0f} mm at z {d['z_m']:.1f}; 447-010 cap",
         f"    feed tubes {len(d['tubes'])} x {next(iter(d['tube_len'].values())):.0f} mm, top z {duty['z_top']:.1f}",
         "  return (drain caps to tote):",
         f"    6 x drain cap spigot (PLACEHOLDER) + HTB 87 deg elbow down through a hole in the collector lid: tips "
         f"{d['collector_tip_air']['floor']:.1f} mm above the collector floor (+X end), {d['collector_tip_air']['lid']:.1f} under "
         f"its lid (-X end); elbow socket hubs {d['collector_tip_air']['hub']:.1f} above the lid top (+X end); min "
         f"{s['tip_margin']} (height governed by the {d['collector_z_governed_by']})",
         f"    collector: Growrilla 100x50 cut to {d['collector_len']:.0f} mm, axis y {d['y_coll']:.1f}, falls 1:{1 / s['slope']:g} to -X; "
         "drain cap, HTB 87 deg elbow",
         f"    return pipe HTEM DN32 L {d['return_len']:.0f} (shortest stocked length reaching {s['return_depth_min']:.0f} below the lid), "
         f"through a G1L grommet at ({_f(d['return_lid_point'][0])}, {_f(d['return_lid_point'][1])}); end z {d['return_end'][2]:.1f}",
         f"    fall: every return path drops at every point ({len(d['return_paths'])} paths checked in validate)",
         f"  tote: HDX 27 gal label envelope {d['tote_size'][0]:.1f} x {d['tote_size'][1]:.1f} x {d['tote_size'][2]:.1f} at "
         f"({_f(d['tote_lo'][0])}, {_f(d['tote_lo'][1])}); lid underside {d['tote_lid_under']:.1f}, floor top {d['tote_floor_top']:.1f} "
         f"(published 999-27G-HDX interior; the SKU sold two totes)",
         "  pump duty:",
         f"    required {len(d['channels'])} channels x {spec('flow_min_lpm'):g}-{spec('flow_max_lpm'):g} L/min = {duty['req_lpm'][0]:g}-"
         f"{duty['req_lpm'][1]:g} L/min = {duty['req_gph'][0]:.0f}-{duty['req_gph'][1]:.0f} GPH",
         f"    static head, waterline to the top of the feed tubes (z {duty['z_top']:.0f}): "
         + ("UNKNOWN: reservoir fill_depth is None. " if duty["head"] is None else f"{duty['head']:.0f} mm. ")
         + f"Bound with the waterline at the tote floor: {duty['head_bound']:.0f} mm = {duty['head_bound'] / (12 * IN):.2f} ft",
         f"    AAPW400 at {duty['head_bound'] / (12 * IN):.2f} ft: {duty['gph_at_bound']:.0f} GPH = {duty['gph_at_bound'] * 3.785411784 / 60:.1f} L/min "
         f"(chart, +/- 5 GPH); rated 370 GPH at 0 ft. Friction in the hose and fittings not counted. The valve throttles the excess",
         f"  parts: {len(d['expect'])} solids; joints with a measured insertion: {sum(1 for j in d['joints'] if j[3] is not None)}",
         "  bought plumbing:"]
    for row, r in PLUMBING.items():
        L.append(f"    {row:15s} {r['what']}  [{r['ref']}]")
        for kk, v in r.items():
            if isinstance(v, tuple):
                val = v[0] if not isinstance(v[0], float) else f"{v[0]:.3f}"
                L.append(f"      {kk:12s} {str(val):>10s}  {v[1]:11s} {v[2]}")
    P = PUMPS[s["pump"]]
    L.append(f"    {s['pump']:15s} {P['what']}  [{P['ref']}]")
    for kk, v in P.items():
        if isinstance(v, tuple):
            L.append(f"      {kk:12s} {str(v[0]) if not isinstance(v[0], float) else f'{v[0]:.3f}':>10s}  {v[1]:11s} {v[2]}"[:400])
    L.append("  part spec:")
    for kk, (v, tag, src) in SPEC.items():
        L.append(f"    {kk:16s} {v:9.3f}  {tag:11s} {src}")
    L.append("  rack inputs:")
    for kk, (tag, src) in RACK_SOURCES[rack].items():
        v = s[kk]
        L.append(f"    {kk:17s} {str(v) if not isinstance(v, float) else f'{v:.3f}':>12s}  {tag:11s} {src}")
    L.append("  not modelled:")
    L += [f"    - {x}" for x in NOT_MODELLED[rack]]
    return "\n".join(L)


if __name__ == "__main__":
    for rack in RACKS:
        try:
            validate(rack)
            print(report(rack), "\n  ok" + ("" if rack in ACTIVE_RACKS else " (inactive)"))
        except AssertionError as e:
            print(report(rack))
            print(f"{rack}: FAIL: {e}")
