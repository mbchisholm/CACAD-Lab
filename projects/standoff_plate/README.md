# Standoff plate and tray

A flat plate with printed bosses that carries one or more boards from
`cacad.registries.boards` on M-screws, with each hex nut captured in a pocket
open to the bed face. With `tray=True` the plate grows walls to a derived
rim and every board-edge connector in the registry gets a U-opening sized
from its plug (`cacad.registries.connectors`). Built to test whether the
shared library and the params convention extend past the cable gland; the
tray is the rescope of `archive/mount_plate/` (see its `REVIEW.md`).

`DESIGN.md` has the rules: standoff height, connectors, mount holes, the
declared ceiling and placements.

## Status

STATUS is `passes`. First print 2026-10-15 (`ANALOG_NODE`, docs/PRINT_LOG.md):
the hole patterns fit, but the M2 bores were tight and one boss broke off. Since
then every plate has ISO 273 medium + FDM allowance bores, a 1 mm root flare
on each boss, a 1.6 web over each nut pocket, and a stepped bridge into the bore
(DESIGN.md). It has not been reprinted. `nut_pocket_clearance` 0.30 is UNVERIFIED.

Active and passing (sizes after the 2026-10-15 change):
- `ADS1115`, `INA219`, `TCA9548A`, `FEATHER`: flat plates, M2 × 10.
- `ADS1115x2_tray`; `SENSOR_HUB_tray`: INA219 + 2 × ADS1115 + TCA9548A in one
  column, 37.0 × 92.2 × 16.4, 14 bosses, six openings.
- `SEN0244`: DFRobot Gravity analog TDS, M3 × 12, 48 × 45 × 10.8, M3 mount
  holes. Holes 35 × 25 from DFRobot's layout PDF, diameter scaled from it.
- `EZO_ISO_x2`: two Atlas isolated EZO carriers, M2 × 10, 81 × 48 × 8.8. The
  carrier hole is 3.0, so M3 is refused; Atlas's STEP on it intersects nothing.
- `NUTRIENT_ANALOG` (sprout-cut `nutrient-analog-xiao`), one plate per board:
  `SEN0244`, `SURVEYOR_PH` (M2.5, its hole is 3.0), `ADS1115` (`board_t` from
  Adafruit's STEP), `MOSFET_5648x3` (three pump drivers, M2 PA, 31.4 × 75.3 × 9.0,
  two bosses and two rest pads each), `PERMAPROTO` (XIAO ESP32-C3 + Pololu, M2).
- `ANALOG_NODE`: SEN0244, ADS1115 and pH on one plate, 111.8 × 48 × 8.8, M2 × 10.
- `SURVEYOR_PH_tile`: the Surveyor as a `module_grid` tile (`mount=dict(..., grid=True)`:
  outline n × 20 - 0.4, M3 holes on the corner cell centres), 59.6 × 59.6 × 9.0.

Built in `projects/sen66_bench`: `SEN66_BENCH` (Metro), `SEN66_PI` (Pi 4B), `SEN66_PERF`
(proto-board, M1.6). Each `keep_in` covers the SEN66 like a board.

Failing by rule, on purpose:
- `ADS1115x2`: inner connectors face each other 6.5 mm apart, the plug needs 15.
- `ADS1115_V1`, `BME280`: holes on one edge; the rest pad for the free edge
  needs the nearest pin to it, and the registry does not have it yet.
- `UNO_R3`: the registry has no `nearest_pin` yet.
- `FEATHER_tray`: the USB-C plug envelope is not in the connector registry.

## Sources

Screws and nuts are ISO 4762 and ISO 4032. Board outlines, holes and pin
keepouts come from the vendor's Eagle file through `tools/board_from_eagle.py`
where one exists (Adafruit), otherwise from the vendor's drawing or STEP, with
the source in `cacad/registries/boards.py`. Connector plugs are in
`cacad/registries/connectors.py`. Clearances are ISO 273 plus a DESIGN FDM
allowance (`cacad.registries.materials`); UNVERIFIED values in `params.py`
never pass a part that has to fit. Vendor STEPs live in `ref/` (gitignored).

## Layout

```
params.py   PLATES (which boards, where, which screw, tray or not), SCREWS (ISO 4032 / 4762),
            derive(plate), validate(plate)
plate.py    build_plate, build_hardware (boards, screws, nuts, plugs and unplugging reach as placed
            envelopes), check_plate
vendor.py   vendor STEP models placed on their plates, checked against the registry and for fit
freecad_view.py   the NUTRIENT_ANALOG plates, boards and screws in one FreeCAD document, bbox cross-check
tests/      geometry + function, walls measured on sections, orientation, overhang, screw stack,
            vendor models (with planted defects)
```

## Run

```
.venv/bin/python projects/standoff_plate/params.py     # design review printout, every plate
.venv/bin/python projects/standoff_plate/plate.py      # ACTIVE_PLATES -> out/*.step, *.stl, *.3mf
.venv/bin/python projects/standoff_plate/vendor.py     # NUTRIENT_ANALOG: vendor checks -> out/*_boards.step, *_screws.step
.venv/bin/python projects/standoff_plate/freecad_view.py   # then: FreeCAD document NutrientAnalog_plates
.venv/bin/python -m pytest projects/standoff_plate -q
```
