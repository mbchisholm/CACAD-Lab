# birdhouse: the design

Changes from the reference, assembly, printing, the checks, the power budget,
wiring, parts and what is not verified. The front page is `README.md`.

## What changed from the reference

- **Perch:** a 10 mm rod, 50 mm long, on a root cone, 12 mm below the hole.
- **Floor fit:** the floor clears the walls, jambs and panel by 0.4 mm
  (`materials.FIT_CLEAR`). A 0.6 mm chamfer on its bed edge takes the
  elephant's foot out of the fit, which is the usual reason a flat-printed
  plate binds. Four 6 mm drain holes go through it.
- **Electronics in the roof:** the tray (the nest's ceiling) carries every
  board. The cap is only a weather cover with the panel bonded to its top.
- **Mount:** a lug on the back with a vertical M6 bolt, for a bracket
  flange like the downpipe clamp in the reference photos.

## How it goes together

1. Drop the floor in from the top onto the ledge.
2. Slide the front panel down its jamb slots onto the sill.
3. Lay the tray on the wall tops. It holds the panel down.
4. Lower the cap over the tray. Its shoulder rests on the tray's rim and its
   skirt laps the body.

To clean the box, lift the cap, lift the tray (the electronics stay on it)
and pull the panel up.

## Parts and printing

Five PETG parts, one file each: `body.py`, `floor.py`, `front.py`,
`tray.py`, `cap.py`. `params.py` holds every number with its source.
`hardware.py` models the bought parts as envelopes.

- **Body, floor, tray:** print upright or flat as modelled.
- **Front panel:** print on its inner face, so the perch and the hole come
  out vertical.
- **Cap:** print upside down on its sloped top. No supports.
- **Slicer:** sparse infill for the cap's solid eave.
- **Colour:** light-coloured PETG. The reference is black, and a black box in
  sun cooks both nestlings and the cell.

## What `assembly.py` checks

`assembly.py` checks that:
- 12 parts and hardware pieces clear each other pairwise;
- the 12 designed contacts touch;
- the camera sees 99% of the floor and nothing on the tray;
- each part stands on its bed face with no overhang over 45°, except the
  18 mm bridge under the lug.

## Power

```
6 V 1 W panel --VIN--> bq25185 board (Adafruit 6106) --JST--> 18650 (Samsung 30Q, Keystone 1042)
                          |
                       5 V boost (+)
                          |
                       TPL5110 VDD (Adafruit 3435) --DRV (switched 5 V)--> ESP32-CAM 5V
                                ^ DONE <-------------------------------- IO13
```

The timer powers the camera once per interval. The camera reads the battery,
lights the IR LEDs, takes and uploads a frame, then raises DONE. The timer
then cuts power completely. Deep sleep would cost 6 mA, nearly the whole
budget; with the camera off, about 85 µA is left.

Budget at a 10-minute interval (`params.py` prints it):

| | |
|---|---|
| Load | 0.44 Wh/day (144 wakes × 10 s at 180 mA, IR 1 s at 50 mA) |
| Cell | 8.6 Wh usable, 19.5 days with no sun |
| December harvest | 1.08 Wh/day, 2.4× the load |

`validate()` fails if the cell lasts under 7 days with no sun, or if December
sun doesn't cover 1.5× the load. A 4-minute interval fails the second check.

## Wiring

The ESP32-CAM lies face down. Its header pins point up into the cap, and
female Dupont leads plug onto them. `wiring_room` in the model is the space
they need.

| ESP32-CAM pin | goes to | why |
|---|---|---|
| 5V | TPL5110 DRV | switched 5 V |
| GND | common ground | charger (−), timer, IR string, divider |
| IO13 | TPL5110 DONE | high when finished: power off until the next interval |
| IO12 | AO3400A gate, 10 k to GND | IR on/off. Strapping pin: the pull-down holds it low at boot |
| IO14 | 1 M / 1 M divider from the battery, 100 nF to GND | ADC2: read it before WiFi starts |
| IO15, IO2 | spare | strapping pins; room for a PIR or a BME280 |
| IO4 | nothing | the white flash LED; keep it low |
| IO0 | GND jumper, only to flash | camera clock at run time |
| U0RXD/U0TXD | programmer, on the bench | or OTA; the board lifts out of its cradle |
| 3V3, VCC, IO16 | nothing | IO16 is the PSRAM chip select |

Off the camera:
- **Panel lead:** through the cap hole, then a 3.5 × 1.1 mm jack pigtail to
  the charger's VIN and G pads.
- **Timer power:** charger 5 V (+)/(−) to the TPL5110's VDD and GND.
- **IR string:** 5 V (switched DRV) → 39 Ω → TSHG6400 → TSHG6400 → AO3400A
  drain; source to GND. That is 50 mA.
- **Battery sense:** the charger's BAT pad to the divider top.

## Bill of materials

| part | source |
|---|---|
| ESP32-CAM (Ai-Thinker) with an OV2640 night-vision module (no IR-cut filter) | marketplace |
| Vishay TSHG6400 850 nm LED × 2, 39 Ω 1/4 W, AO3400A | Digi-Key / Mouser |
| Adafruit 6106 bq25185 charger + 5 V boost | adafruit.com |
| Adafruit 3435 TPL5110 timer | adafruit.com |
| Adafruit 3809 6 V 1 W panel | adafruit.com |
| Samsung 30Q 18650, Keystone 1042 holder | 18650batterystore.com, Digi-Key |
| 1 M × 2, 100 nF, 10 k, Dupont leads, 3.5 × 1.1 jack pigtail, 2.5 mm zip ties × 2 | |
| M6 hex bolt (ISO 4017) + nut, outdoor silicone | |

## Not verified yet

- **Cold charging.** Li-ion must not charge below 0 °C. The bq25185 has a
  thermistor input, but I haven't checked whether Adafruit's board brings it
  out. In a NY winter this is the largest open risk.
- **Sun.** The 1.5 peak-sun hours for December is an estimate; check the site
  in NREL PVWatts. Shade under a tree breaks the budget.
- **Wake time.** 10 s per wake is an estimate. Measure it with the INA219.
- **Standby.** The charger board's green 5 V LED draws about 1 mA. Remove it.
- **Board geometry:**
  - The bq25185 board's size is "approximately" from a listing. The tray
    holds every board by its outline, so hole positions don't matter.
  - The ESP32-CAM's lens position comes from the reference model.
  - Its shield height and lens drop are estimates.
  - Check that a 2 mm band at each short end of your board is free of
    components; the end ledges rest there.
- **Optics:**
  - The stock-lens FOV is the commonly quoted figure, not a datasheet value.
  - The lens is focused far away. Refocus it to about 12 cm.
- **Cap.** It sits on gravity and its skirt, like the reference. That's
  untested in wind.
- **Perch.** Nest-box guidance (NABS, Cornell NestWatch) advises against
  perches: they help house sparrows and predators. Built as asked; to drop it,
  remove the two perch lines in `front.py`.
- **Species.** The 38 mm (1.5 in) hole is the bluebird standard. The
  93 × 111 mm floor is under the bluebird minimum of 4 × 4 in (102 mm) across
  the width. Change `outer` for a bluebird box, or the hole for chickadees
  and wrens (28.6 mm, 1-1/8 in).
