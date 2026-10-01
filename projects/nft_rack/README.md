# NFT rack

Two layouts share one channel, feed tube and frame section. **`nft_table` is active**: a single-level table of six
Growrilla 100x50 channels, 2 m, lids at 250 mm, on 2020 extrusion. An HDX 27 gal tote sits under the low end. The
supply runs from a submersible pump, up a vinyl hose and a PVC riser with a ball valve, to a 1 in manifold that
feeds each channel through a 3/8 in tube. The return runs from each drain cap through a PP elbow into a Growrilla
channel used as the collector, then down a PP pipe into the tote. **`growing_up_pro`** (the 3-level AM Hydro
layout) is inactive. It still passes `validate()` but is not built or tested.

Not a print: the checks are placement, contact, insertion and fall, and where each number comes from. Every value
carries a source tag (`params.TAGS`). Every pipe and fitting is a `PLUMBING` row naming its standard or catalogue
page: ASTM D1785/D2466 and Spears Sch 40 parts, Ostendorf HT DN32, Orenco grommets, Kuri Tec hose. The pump is in
`PUMPS`, with the flow-at-head chart digitised from Hydrofarm's manual. The tote is wired through
`cacad.registries.reservoirs.HDX_27GAL`.

```
params.py        SPEC, CHANNEL_KINDS, PLUMBING, PUMPS, RACKS + RACK_SOURCES, derive(rack) with every part's analytic
                 envelope and hand volume and every joint's expected insertion, validate(rack), gaps(rack); the
                 printout is the design review
legs.py          the plumbing solids' hand volume and box: stepped hollow cylinders, mitred elbows, filleted sweeps
rack.py          build_rack, check_rack (+ check_plumbing: supply continuity, insertion measured on the geometry,
                 drop tips inside the collector, return end inside the tote, fall)
freecad_view.py  STEP -> FreeCAD Assembly coloured by kind, POST-FL grounded, Spec sheet with every tag and every
                 PLUMBING row; positions checked against params (optimal bbox, F26) with a must-disagree control
tests/           check_rack, tags, the table's and AM Hydro's numbers, the leg formulas against OCC at four bends,
                 must-fail controls (channel 1 mm low; envelope shifted 1 mm; valve seated 1 mm high; collector lid
                 3 mm high; an uphill return point)
```

```
.venv/bin/python projects/nft_rack/params.py         # design review; ends in FAIL until the gaps below are measured
.venv/bin/python projects/nft_rack/rack.py           # nft_table -> out/nft_rack_nft_table.step, .stl (~30 s)
.venv/bin/python -m pytest projects/nft_rack -q      # test_every_rack_validates fails by design until then
.venv/bin/python projects/nft_rack/freecad_view.py   # FreeCAD open, MCP Addon RPC server started
```

## What the model sets

- Slope 1:40 (`vinylDOwn.md`, default from the brief). Channel floor 36 in (914.4 mm) above the floor at the high
  end. The front rail sits `slope x (D - 20)` = 46.6 mm above the back rail.
- Footprint, all derived: 1629 x 1884 mm (64.1 x 74.2 in). Depth = channel run − 100 mm front overhang − 20 mm back
  overhang. Width = six 250 mm cells + posts + an 89 mm bay left of channel 1. The bay puts the return pipe over
  the tote lid with the tote clear of the back-left post.
- Supply: the hose runs 2.58 m at 500 mm height. The riser is a 460-007 insert, a 437-131 bushing, a 2122-010
  valve, 1 in pipe and a 406-010 elbow into a 1.39 m manifold, capped with a 447-010. Every socket's insertion is
  measured on the geometry and meets ASTM D2466.
- Return: HTB 87° elbows drop into a 1325 mm collector falling 1:40 to −X. The return is the shortest stocked
  HTEM DN32 that reaches the tote (500 mm), through a G1L grommet.
- Pump: 6 channels × 1–2 L/min = 95–190 GPH. Worst-case static head (waterline at the tote floor) is 1009 mm =
  3.31 ft, where the AAPW400 chart gives 236 GPH. Friction not counted.

## Open, in the order validate() reports them

- **Collector margin**: the HTB's 61 mm spigot leaves 4.4 mm across a collector falling 1:40. That is 2.2 mm of
  tip-under-lid at −X and 2.2 mm of hub-over-lid at +X, against a 3 mm DESIGN minimum. Possible fixes: a flatter
  collector, a short HTEM drop pipe under each elbow, or moving the collector back so the hubs clear its lid edge.
- **Waterline**: unknown until `fill_depth` is measured, so the return-end and pump-submerged checks cannot run.
- **Measure**: the six HDX_27GAL registry fields (SKU 207585 has sold two different totes); the AAPW400 body,
  outlet position and barb height (Hydrofarm's 6.3 x 4.7 x 3.9 in is a logistics size); the Growrilla drain cap
  (spigot length and height, cap thickness); the 460-007 spigot length; the valve handle width; the tote lid and
  wall thickness.
- **Frame**: a 1.59 m 2020 rail carries the channels. Its stiffness is not sized.
- Tight but clear: the manifold's inlet elbow hub is 1.1 mm from channel 1's high cap (`manifold_gap` 5 mm minus
  the hub's 3.9 mm over the pipe).
- Not drawn: lights, net pots, supports and clips, feed-tube grommets, and the fittings' seals and barb ribs
  (`params.NOT_MODELLED`).
