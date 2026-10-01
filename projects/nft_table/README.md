# nft_table

One level of six Growrilla 100x50 NFT channels on a 2040/2020 table, fed by a
Little Giant PE-2.5F in an HDX 27 gal tote, plumbed in Sch 40 PVC. Every
interface whose geometry nobody publishes is a printed PETG part. Every number
in `params.py` is tagged and sourced; `validate()` passes, and the tests check the
assembly on its solids.

v1 is in `archive/nft_rack_v1/`. It ended in FAIL on caliper-gated tote fields
and on parts with unpublished geometry (the AAPW400 body, the Growrilla drain
cap, a PP collector). v2 designs around those unknowns instead of measuring them.

## Run

```
.venv/bin/python projects/nft_table/params.py        # the design: frame, hydraulics, BOM, cut lists, tags
.venv/bin/python projects/nft_table/table.py         # build, check, out/nft_table.step
.venv/bin/python projects/nft_table/p1_saddle.py     # one part: print checks, orientation report, out/P1-*.3mf
.venv/bin/python projects/nft_table/freecad_view.py  # FreeCAD cross-check and assembly (RPC server running)
.venv/bin/python -m pytest -q projects/nft_table
```

## The design

- **Frame.** HFS5-2040 rails on edge (front, mid, back) on six HFS5-2020 legs,
  2020 side members, and HBLFSN5 brackets. Rail sag is computed from Misumi's
  published I and E: L/360 under the operating load, L/200 under the flooded
  load (drain blocked), and the floor must still fall through every rail.
- **Channels.** Six channels, 250 mm apart, 2 m uncut, at 1:40. The high end's
  underside is at 36 in. Each channel sits on three **P1** saddles bolted to the
  level rails; the saddle heights carry the slope.
- **Supply.** PE-2.5F (3/8 MNPT), then Spears 438-073 and 437-101 bushings, a
  457-007 union and a 3/4 in riser up through **P6**. A tee splits it:
  - The bypass runs through a 2122-007 ball valve back into the tote.
  - The main runs under the rails in **P7** clips to a 3/4 in manifold under the
    front rail, closed by a 447-007 cap.
  - Each channel's **P5** tap on the manifold feeds its **P2** cap through equal
    1/4 x 3/8 in vinyl lines.
- **Return.** Each **P3** cap drops a spout through a 1 in hole-saw hole into a
  level 2 in collector, located by **P4**. A 401-020 tee at the centre drops 2 in
  pipe through P6 into the tote.

| part | what it does | prints |
|---|---|---|
| P1 | channel saddle, graded F/M/B, bears on the channel's corners and walls only | base down |
| P2 | feed cap: sleeve, sealant groove, vertical barb aimed at the floor | floor down |
| P3 | drain cap: sleeve, sealant groove, chamber, spout sized by the orifice equation | spout tip down, exterior supported |
| P4 | two-piece clamp on the 2 in collector; hole-saw guide; hangs from the back rail | end down |
| P5 | two-piece tap: AS568-205 in a Parker face-seal gland, 1/4 in barb | end down |
| P6 | lid plate + backing frame for any lid 1.5–5 mm, collars, cord bushing, spare-port plug | flat |
| P7 | snap clip under a rail, 'along' or 'across' | end down |

## Owner decisions on 2026-10-01 that differ from the spec

- **Feed lines** are 1/4 ID x 3/8 OD vinyl (Kuri Tec K010-0406). 1/4 in drip
  tubing can't pass 2 L/min per channel at a head the pump can supply.
- **The frame** has six legs, and the flooded load is gated.
- **The collector** is level. A rigid centre tee can't take two halves falling
  toward it.
- **The pump** is the Little Giant PE-2.5F. Its male discharge needs a
  spigot x FIPT bushing, not a male adapter.

## Open

- **Growrilla's lid holes:** the clipping says 48 mm, Growrilla's IT page says 40 mm. 48 is used.
- **The O-ring gland's FDM tolerance:** if FDM puts ±0.1 mm on the radial gland
  depth, squeeze runs 20.0–30.0 %, right on Parker's limits. The nominal is 23–27 %.
- **Cord OD and plug size are not published.** The cord bushing's 7 mm slot and the
  36 mm port are DESIGN values. The zip-tie post takes any cord.
- **P3 prints on its spout tip**, with slicer support under its exterior undersides.
- **The P5 passage prints as a pilot** and is drilled to 1/4 in after printing.
  It is the one water passage not printed vertical.
- `params.NOT_MODELLED` lists what is not drawn.
