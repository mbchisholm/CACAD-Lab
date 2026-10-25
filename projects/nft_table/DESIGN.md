# nft_table: the design

Frame, channels, supply, return and the seven printed parts. The front page is
`README.md`; open items are there too.

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

## Author decisions on 2026-10-01 that differ from the spec

- **Feed lines** are 1/4 ID x 3/8 OD vinyl (Kuri Tec K010-0406). 1/4 in drip
  tubing can't pass 2 L/min per channel at a head the pump can supply.
- **The frame** has six legs, and the flooded load is gated.
- **The collector** is level. A rigid centre tee can't take two halves falling
  toward it.
- **The pump** is the Little Giant PE-2.5F. Its male discharge needs a
  spigot x FIPT bushing, not a male adapter.
