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
vendor.py   vendor STEP models placed on their plates, checked against the registry and for fit
freecad_view.py   the NUTRIENT_ANALOG plates, boards and screws in one FreeCAD document, bbox cross-check
tests/      geometry + function, walls measured on sections, orientation, overhang, screw stack,
            vendor models (with planted defects)
```

```
.venv/bin/python projects/standoff_plate/params.py     # design review printout, every plate
.venv/bin/python projects/standoff_plate/plate.py      # ACTIVE_PLATES -> out/*.step, *.stl, *.3mf
.venv/bin/python projects/standoff_plate/vendor.py     # NUTRIENT_ANALOG: vendor checks -> out/*_boards.step, *_screws.step
.venv/bin/python projects/standoff_plate/freecad_view.py   # then: FreeCAD document NutrientAnalog_plates
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

Mount holes (`mount=dict(screw="M3", sides="X" | "Y")`, flat plates only):
four plain through bores, one per plate corner, `mount_inset` (head radius
+ `mount_head_seat`) from both edges. On the two mount sides the plate grows
a strip so each head sits wholly outside every board outline with
`mount_access_clearance` to spare, and `check_plate` proves a head-sized
driver column reaches it straight down past the boards and their screws.
Pick the sides no connector faces; `validate()` refuses a connector that
faces one. The clamp is `plate_t`; the screw length is set by what the
plate mounts to.

Declared ceiling: the annulus above each nut pocket (4.3 mm hex, bridged).
The nut bears on it. If bridging sags in practice, the alternative is a
sacrificial layer across the pocket, drilled out after printing.

Placements are `(board, (x, y), rot)` with `rot` a multiple of 90; the
registry board is rotated once in `derive()` and nothing downstream rotates
anything. A two-hole board is accepted when its hole line passes through the
board centre (TCA9548A). A board whose holes are all on one end (MOSFET 5648)
gets a solid rest pad (`rest_pad_d`, boss-high, no bore) under each hole
mirrored through its centre. The plate row must give the distance from that
pad to the nearest through-hole pin (`rest_nearest_pin`, from the board file),
or `validate()` refuses it (ADS1115_V1, BME280).

A screw head wider than a board's nearest top copper is refused unless the row
says `screw_pa=True`: a PA (nylon) screw of the same standard.

## The analog nutrient node

`NUTRIENT_ANALOG` in params lists one plate per board of sprout-cut's
`nutrient-analog-xiao` env:

- `SEN0244`: TDS, M3. No vendor STEP.
- `SURVEYOR_PH`: Atlas Surveyor analog pH, M2.5 (its hole is 3.0), 48 × 45 × 9.0.
- `ADS1115`: reads both probes.
- `MOSFET_5648x3`: three pump drivers (acid, nutrient A, nutrient B), M2 PA, 31.4 × 74.3 × 9.0.
  Two bosses and two rest pads per board.
- `PERMAPROTO`: XIAO ESP32-C3 + Pololu D24V10F5 carrier, M2. Its nearest breadboard via is
  3.81 from a mount hole, so an M2.5 or M3 boss would sit under a soldered lead. 49.2 × 63.8 × 8.8.

The OLED is not on a plate: it mounts behind the box cover's window. To swap a
board, edit its `PLATES` row.

`VENDOR_STEPS` names a vendor model per board. The files live in `ref/vendor_step/`,
which is gitignored. Sources: Adafruit_CAD_Parts (1085, 5648, 1608) and Atlas
(`pH-Gravity.zip`). `vendor.py` reads each STEP's PCB solid and checks it
against the registry: outline within 0.05, thickness against `board_t` within
0.02, every registry hole within 0.05. It then places the model on its bosses
and requires zero interference with the plate, the screws, the nuts, the mount
screws and the neighbouring boards. Two tests prove the check bites: a board
sunk 0.5 mm, and the MOSFET STEP turned 180°.

Every board thickness on these plates now comes from its vendor STEP: 1.57 for
Adafruit, 1.59 for Atlas, 1.60 for the Perma-Proto. A board without a STEP on
the machine shows as its registry envelope, translucent in FreeCAD, and its
vendor test skips with the source named.

Status (2026-09-21): active and passing — `ADS1115`, `INA219`, `TCA9548A`,
`FEATHER` (flat plates), `ADS1115x2_tray`, and `SENSOR_HUB_tray` (INA219 +
2 × ADS1115 + TCA9548A in one column, 35.7 × 90.9 × 16.4, 14 bosses, six
openings). Added 2026-10-07: `SEN0244` (DFRobot Gravity analog TDS, M3 × 10
+ ISO 4032 nuts, 48 × 45 × 9.0 with M3 mount holes, holes 35 × 25 from DFRobot's layout PDF; the
hole diameter is scaled from that drawing, not dimensioned) and `EZO_ISO_x2`
(two Atlas isolated EZO carriers, pH + EC, M2 × 10, 81 × 48 × 8.8 with M3 mount holes; the
carrier hole is 3.0 so M3 is refused; Atlas's STEP placed on it intersects
nothing). Failing by rule — `ADS1115x2` (inner connectors face each other
6.5 mm apart, plug needs 15), `ADS1115_V1` and `BME280` (holes on one edge),
`UNO_R3` (no `nearest_pin`), `FEATHER_tray` (USB-C plug envelope not yet in
the connector registry; the Feather joins the hub tray when it is).
`ADS1115_V1` (two-hole revision) and `BME280` fail `validate()` until the row
gives the nearest pin to their rest pads. `UNO_R3` fails
until the registry has its `nearest_pin`. Nothing prints for fit until the
coupons are measured: `screw_clearance` is `CLEAR_LOOSE` (a guess) and
`nut_pocket_clearance` 0.30 has no coupon at all.
