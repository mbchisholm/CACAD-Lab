# nutrient_controller

A printed PETG housing that regulates one HDX 27 gal tote: TDS and water
temperature in, one peristaltic dose out, an OLED, three buttons and an LED on
the front. Concept B (box hung beside the container) chosen 2026-10-04.
Active revision **B2** clamps over the rim of any tote or bucket, no drilling;
**B1** bolts through the HDX wall and stays in params as the alternative
(validated, not built). Neither has been printed.

Supersedes the `enclosure_atlas` spec (Atlas EZO, caliper-gated) for the
analog build.

    .venv/bin/python projects/nutrient_controller/params.py      # the design, printed
    .venv/bin/python projects/nutrient_controller/assembly.py    # build, check, out/B2.3mf
    .venv/bin/python -m pytest projects/nutrient_controller

## B2: the rim clamp (active)

The same box, cover and post plate as B1. Instead of bolting through the
wall, the post plate bolts to a printed C-hook (2 x M5 through vertical slots,
so the box sits 29-41 mm under the rim). The hook's bridge sits on the rim
top, its inner jaw bears on the container's inside face, and an ISO 4017
M6 x 60 with a printed knob and pad clamps the outside. The throat takes any
wall or lip from 2 to 35 mm thick at the screw; the 60 mm wide hook sits on a
round bucket rim down to R150 (3 mm sagitta). Probe cables and the dosing
tube go over the rim in a 16 x 3 groove on the bridge, then down outside to
the glands from below, as in B1.

Costs against B1:
- the lid rests on the bridge: raised 6 mm there, and a snap-on lid will not latch at that spot;
- the TDS probe lead is tight: +53 mm spare on the HDX, +13 mm for a container whose rim is 200 mm above the
  water (the design limit); a deeper container needs a probe extension;
- the clamp holds by friction and the screw: it is the part that wants `cad-design-review` first.

The assembly check runs the clamp at the thinnest, middle and thickest
container: hook clear of the wall, pad landing on it, knob clear of the box,
plate and cover, the M6 through its nut. The tests plant a 45 mm wall and
misaligned hook bolts and expect the checks to fail.

Printed parts added for B2: hook 59 x 60 x 81 (prints upside down on its
bridge), knob 26 x 12, pad 20 x 6. The post plate loses its tote-bolt holes
and window and gains two M5 nut bosses.

## B1 in one paragraph (alternative: bolted through the wall)

A wall plate bolts flat to the outside of the tote's short end wall (4 x M5
through the wall into a backing plate inside the tote). The box hangs on the
plate's three mushroom posts by keyholes and lifts off for service. It sits
parallel to the wall, so the wall's draft never enters a dimension. Probe
cables leave the tote through one hole behind the plate, run down the gap
behind the box and enter cable glands in its bottom wall from below (drip
loop). The pump flange bolts to the outside of the -Y wall, motor inside; both
tubes leave the head towards the plate, the outlet into the tote through its
own hole, the inlet down to a concentrate bottle on the floor. The lid is
untouched.

## Parts

| part | model | source |
|---|---|---|
| MCU | Seeed XIAO ESP32-C3, on a Perma-Proto quarter | Seeed KiCad Edge.Cuts; Adafruit Eagle |
| 5 V | Pololu D24V10F5 (5.1-36 V in), on the Perma-Proto | Pololu dimension PDF |
| ADC | Adafruit ADS1115 (STEMMA QT) | Eagle, `boards.ADS1115` |
| TDS | DFRobot SEN0244 board + probe | DFRobot layout PDF, `boards.SEN0244` |
| temperature | DS18B20 stainless probe, 1 m | PLACEHOLDER (generic) |
| pump | Kamoer NKP-DC-S06, 12 V, straight bracket | Kamoer NKP datasheet p.2 |
| pump driver | Adafruit MOSFET driver 5648 (AO3406, 1.5 A) | Eagle, `boards.MOSFET_5648` |
| display | Adafruit 1.3in 128x64 OLED 938 (SSD1306, I2C 0x3D) | Eagle, `boards.OLED_938` |
| buttons | 3 x E-Switch PV0, IP67, 12 mm | PV0 datasheet |
| LED | 5 mm in Bivar CR-174 clip + ring | CR-174 datasheet |
| power in | Switchcraft 722A 2.1 mm jack, 12 V | Switchcraft sheet |
| glands | Lapp SKINTOP ST-M M16 (TDS), M12 (DS18B20) + GMP-GL-M locknuts | Lapp DB53111000EN, DB53119000EN |
| fasteners | M2 x 10 (ADS1115, PA nylon on the MOSFET), M2.5 x 10 (SEN0244), M3 x 8 + CNC Kitchen inserts (carrier, cover), M3 x 10 (pump); B2: 2 x M5 x 20 ISO 4762 + ISO 4032 (hook), M6 x 60 ISO 4017 + ISO 4032 (clamp); B1: 4 x M5 x 25 ISO 4762 + ISO 10511 + ISO 7089 (plate) | ISO tables in params |

Vendor sheets are in `ref/vendor_sheets/` and the Eagle files in `ref/eagle/`
(both gitignored). The sprout-cut env needs one change for the MOSFET driver:
the pump output becomes active-high (`activeHigh=true`). Pins for three buttons
and the LED: D1, D3 (free with one pump) plus D6/D7 (UART0, unused under USB
CDC).

## Printed parts (PETG, A1 bed)

| part | size, mm | prints on |
|---|---|---|
| body | 44 x 110 x 150 | its back; wall holes are truncated teardrops |
| cover | 6.5 x 114 x 154 | its front face |
| post plate | 25.6 x 148 x 150 | its container-side face; post heads have 45 deg undersides |
| B2 hook | 59 x 60 x 81 | upside down on its bridge; holes teardrop, nut pocket 45 deg roof |
| B2 knob, pad | 26 x 12, 20 x 6 | flat |
| B1 backing plate | 4 x 148 x 150 | flat |

## Still a placeholder (does not block a first print; each is tolerated by design)

- PCB thickness of every board (1.6), the XIAO's height, the 2.54 header body under it.
- OLED panel thickness: the 4.0 bosses clear a panel up to 3.0.
- TDS probe body and cable OD: the M16 gland seals 4-10; a heat-shrink sleeve builds a thin cable up.
- USB-C plug overmold: USB-IF spec not read; the opening is 13.5 x 8.
- NKP flange thickness and the hole and tube offsets: drawn, not dimensioned; the wall slots, sliding nuts
  and the plate's tube slot absorb them.
- HDX wall thickness (B1): the M5 x 25 covers 2-5 mm. Rim profile (B2): the clamp takes 2-35 mm.
- WAGO 2060 terminal height 4.5, INFERRED from the series.

## Next

1. Print the hook, knob and pad first and clamp them on the tote: the cheapest test of the mount. Then the body
   and cover; fit the boards, glands, buttons and pump. Measure nothing: if a part does not fit, the clearance it
   violates is named in params.
2. `cad-design-review` on the hook (it carries the box by friction and one screw).
3. Cable strain relief inside the box, an optional anti-lift screw through the back into the plate, labels.
4. Optional: a KiCad carrier replacing the Perma-Proto.

## Concepts (2026-10-04, superseded by B1)

`concepts.py` and `concept_params.py` keep the three massing models (A_lid,
B_wall, C_split) that chose the direction. B won: it is the only one where
the lid lifts off alone. B1 replaced its wedge spacer (which needed the wall's
draft) with keyholes on a plate that follows the wall.

## Log

- 2026-10-04: concepts A/B/C built as massing models; function checks pass.
- 2026-10-04: B chosen. B1 modelled on sourced parts. Boards from Adafruit Eagle files, JST, Lapp, Kamoer,
  E-Switch, Bivar, Switchcraft, Pololu sheets. Assembly checks pass: 37 envelopes, 4 printed parts, no unplanned
  contact, keyholes pass the post heads, tubes pass the plate, every tote hole >= 50 mm over the waterline.
  The checks found and fixed: ADS1115 plug vs pump nut block, pump flange vs cover skirt, cover corner fillets
  vs body, tangent insert columns (non-manifold mesh, FINDINGS F31).
- 2026-10-04: B2, the rim clamp: no hole in the container, any wall or lip 2-35 mm. Assembly checks pass at
  2, 18.5 and 35 mm (46 envelopes, 6 printed parts). The overhang check caught a horizontal hex nut pocket
  (60 deg roof); it now has a 45 deg roof.
