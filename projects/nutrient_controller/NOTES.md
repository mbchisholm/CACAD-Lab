# nutrient_controller

A printed PETG housing that regulates one HDX 27 gal tote: TDS and water
temperature in, one peristaltic dose out, an OLED, three buttons and an LED on
the front. Stage: **ideation**. Three massing concepts exist to pick a
direction; nothing here is ready to print for fit.

Supersedes the `enclosure_atlas` spec (Atlas EZO, caliper-gated) for the
analog build.

## Electronics (the config this housing serves)

From sprout-cut env `nutrient-analog-xiao` (`platformio.ini:309-363`):

| function | part | bus / pin |
|---|---|---|
| MCU | Seeed XIAO ESP32-C3 | native USB-C |
| TDS | DFRobot SEN0244 board + probe, read by ADS1115 AIN1 | I2C 0x48, D4/D5 |
| OLED | SSD1306 128x64 | I2C 0x3D, same bus |
| temperature | DS18B20, 4.7 k pull-up | D10 |
| pump | peristaltic on an active-low relay | D2 (nutrient_a) |

Housing carries **one pump, no pH** (owner, 2026-10-04); the env drives three
relays and a pH probe. With one pump, D1 and D3 are free; buttons and LED need
four pins, so the fourth comes from D6/D7 (UART0, unused under USB CDC) or a
strapping pin (D0/D8/D9) with a pull-up. The env wires no buttons or LED yet.

## Concepts

All in the tote frame (`params.py` docstring). `concepts.py` builds them;
`out/<concept>.3mf` holds every printed part, bought-part envelope and the tote
as separate meshes.

| | A_lid | B_wall | C_split |
|---|---|---|---|
| where | wedge box screwed to the lid | tall box bolted to the outside of the short end wall | slim UI head on a 2020 post + wet pod on the lid |
| lid lifts off alone | no: box, probes and tube ride it | **yes**: nothing on the lid | no: pod rides it |
| lowest opening over waterline | +160 mm | +100 mm (wall hole) | +160 mm |
| TDS lead spare (830 mm lead) | +420 mm | +480 mm | **+158 mm** |
| tote modification | 7 lid holes | 4 wall holes (probe grommet, tube, 2 bolts) | 3 lid holes |
| printed parts | base 193x130x42, cover, holster | body 62x120x170, front, wedge spacer, holster | head (2), pod 163x90x44, holster |
| screen height | at lid level, tilted 18 deg | vertical, below the rim | ~120 mm over the rim, tilted 17 deg |
| depends on unpublished tote geometry | lid flatness (screws + fender washers tolerate it) | **end-wall draft**: 7.9 deg INFERRED; the spacer is a separate part to swap | lid flatness |

Spare lead = lead length - (exit to probe tip 40 mm under the waterline +
probe body + 150 mm service loop). C pays for the pod-to-head run.

**Reading.** B is the only one where the lid is a lid again: top off,
probes and dosing line stay put, and the electronics never sit over open
water. Its cost is drilling the tote wall and the draft it has to bridge. A is
the quickest to print and the easiest to tune. C puts the screen where you'd
read it but its TDS lead is tight and it is two enclosures.

## What every concept still lacks (fidelity stage)

1. **Pick the bought parts and source them** into the registries:
   - XIAO: Seeed's DXF and KiCad project → `boards.py`. It has no holes, so it gets an edge cradle.
   - SEN0244: DFRobot dimension drawing → `boards.py`. Holes unpublished → edge rail.
   - OLED module: a vendor with an Eagle file, so `tools/board_from_eagle.py` works.
   - Pump: a model with a published drawing, which fixes the voltage.
   - Relay or MOSFET module.
   - DC jack, buttons, LED bezel, PG7 cable glands.
   - `Mating` rows for PH2.0-3P, XH2.54-2P and the USB-C plug overmold, which the USB-IF spec has and the registry is missing.
2. **Interfaces replace envelopes**: cradles, a window bezel that clamps the
   OLED, button plungers, M3 heat-set cover screws (`materials.INSERT_*`),
   split grommets on the probe cables, a drip lip at the cover joint.
3. **Mount**: A, screws through the lid with fender washers. B, the wedge
   spacer derived from the draft, and a printed wall-hole template.
4. **Checks**: `cacad.checks` printability and overhang per part,
   PRINT_ORIENTATION in params, and `cad-design-review` on the mount.
5. **Optional**: a KiCad carrier for XIAO + ADS1115 + screw terminals instead of
   hand wiring (`cacad.freecad.kicad_freeze` brings it back as STEP).

## Open decisions (owner)

- Concept: A, B, C or a hybrid.
- Pump voltage: 12 V (needs a jack and a buck converter) or 5 V (one USB-C feeds everything, smaller box).
- Relay (sprout-cut today) or a MOSFET module for a DC pump: smaller, silent, no contact wear.
- Concentrate bottle size; 500 mL drawn.

## Log

- 2026-10-04: concepts A/B/C built as massing models; function checks pass
  (no envelope collisions, dry parts in dry cavities, all on the A1 bed,
  openings over the waterline). Renders in `out/*.png`.
