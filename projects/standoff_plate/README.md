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

STATUS is `passes`. Active and passing (2026-09-21): `ADS1115`, `INA219`,
`TCA9548A`, `FEATHER` (flat plates), `ADS1115x2_tray`, and `SENSOR_HUB_tray`
(INA219 + 2 × ADS1115 + TCA9548A in one column, 35.7 × 90.9 × 16.4, 14 bosses,
six openings). Added 2026-10-07:
- `SEN0244`: DFRobot Gravity analog TDS, M3 × 10 + ISO 4032 nuts, 48 × 45 × 9.0
  with M3 mount holes. Holes 35 × 25 from DFRobot's layout PDF; the hole
  diameter is scaled from that drawing, not dimensioned.
- `EZO_ISO_x2`: two Atlas isolated EZO carriers (pH + EC), M2 × 10,
  81 × 48 × 8.8 with M3 mount holes. The carrier hole is 3.0, so M3 is refused;
  Atlas's STEP placed on it intersects nothing.

Failing by rule, on purpose:
- `ADS1115x2`: inner connectors face each other 6.5 mm apart, the plug needs 15.
- `ADS1115_V1`, `BME280`: holes on one edge, and the family has no rest under a
  free edge.
- `UNO_R3`: the registry has no `nearest_pin` yet.
- `FEATHER_tray`: the USB-C plug envelope is not in the connector registry; the
  Feather joins the hub tray when it is.

Nothing prints for fit until the coupons are measured: `screw_clearance` is
`CLEAR_LOOSE` (a guess) and `nut_pocket_clearance` 0.30 has no coupon at all.

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
tests/      geometry + function, walls measured on sections, orientation, overhang, screw stack
```

## Run

```
.venv/bin/python projects/standoff_plate/params.py     # design review printout, every plate
.venv/bin/python projects/standoff_plate/plate.py      # ACTIVE_PLATES -> out/*.step, *.stl, *.3mf
.venv/bin/python -m pytest projects/standoff_plate -q
```
