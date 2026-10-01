# Standoff plate and tray

A flat plate with printed bosses that carries one or more boards from
`cacad.registries.boards` on M-screws, with each hex nut captured in a pocket
open to the bed face. With `tray=True` the plate grows walls to a derived
rim and every board-edge connector in the registry gets a U-opening sized
from its plug (`cacad.registries.connectors`). Built to test whether the
shared library and the params convention extend past the cable gland; the
tray is the rescope of `projects/mount_plate/` (see its `REVIEW.md`).

```
params.py   PLATES (which boards, where, which screw, tray or not), SCREWS (ISO 4032 / 4762),
            derive(plate), validate(plate)
plate.py    build_plate, build_hardware (boards, screws, nuts, plugs and unplugging reach as placed
            envelopes), check_plate
tests/      geometry + function, walls measured on sections, orientation, overhang, screw stack
```

```
.venv/bin/python projects/standoff_plate/params.py     # design review printout, every plate
.venv/bin/python projects/standoff_plate/plate.py      # ACTIVE_PLATES -> out/*.step, *.stl, *.3mf
.venv/bin/python -m pytest projects/standoff_plate -q
```

Standoff height is `max(underside clearance, stock screw length)`: the screw
must pass through the nut and stop `screw_tip_min` above the bed face, and
the standoff rises in layer steps until a stocked length lands in that
window. For the ADS1115 the screw ladder governs (5.20 vs 4.50).

Connectors: a plug must be able to come out. `validate()` fails when a
connector faces another board closer than plug length + `finger_room`; a
connector facing a wall gets an opening `plug_w + 2 × opening_clearance`
wide from `opening_below` under the board top to the rim. The rim is the
board top + the tallest top-side thing (connector or header, whichever the
registry and the caliper say) + `lid_clearance`. No lid yet.

Declared ceiling: the annulus above each nut pocket (4.3 mm hex, bridged).
The nut bears on it. If bridging sags in practice, the alternative is a
sacrificial layer across the pocket, drilled out after printing.

Placements are `(board, (x, y), rot)` with `rot` a multiple of 90; the
registry board is rotated once in `derive()` and nothing downstream rotates
anything. A two-hole board is accepted when its hole line passes through the
board centre (TCA9548A), refused when the holes are on one edge (ADS1115_V1,
BME280): the family has no rest for a cantilevered edge.

Status (2026-09-21): active and passing — `ADS1115`, `INA219`, `TCA9548A`,
`FEATHER` (flat plates), `ADS1115x2_tray`, and `SENSOR_HUB_tray` (INA219 +
2 × ADS1115 + TCA9548A in one column, 35.7 × 90.9 × 16.4, 14 bosses, six
openings). Failing by rule — `ADS1115x2` (inner connectors face each other
6.5 mm apart, plug needs 15), `ADS1115_V1` and `BME280` (holes on one edge),
`UNO_R3` (no `nearest_pin`), `FEATHER_tray` (USB-C plug envelope not yet in
the connector registry; the Feather joins the hub tray when it is).
`ADS1115_V1` (two-hole revision) fails `validate()` by design: the board
cantilevers and this family has no rest under a free edge. `UNO_R3` fails
until the registry has its `nearest_pin`. Nothing prints for fit until the
coupons are measured: `screw_clearance` is `CLEAR_LOOSE` (a guess) and
`nut_pocket_clearance` 0.30 has no coupon at all.
