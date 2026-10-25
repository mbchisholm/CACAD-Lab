# standoff_plate: how the rules work

Standoff height, connectors, mount holes, the declared ceiling and placements.
The front page is `README.md`.

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

Vendor models (`VENDOR_STEPS`, files in the gitignored `ref/vendor_step/`):
`vendor.py` reads each STEP's PCB solid and requires its outline within 0.05
of the registry, its thickness within 0.02 of `board_t`, and every registry
hole within 0.05. Placed on its bosses, the model must not intersect the
plate, the screws, the nuts, the mount screws or the boards beside it. Two
tests prove the check bites: a board sunk 0.5 mm, and the MOSFET STEP turned
180°. A board with no STEP on the machine shows as its registry envelope, and
its vendor test skips with the source named.

## ANALOG_NODE (2026-10-08)

The analog front end of nutrient_controller L1 on one open plate, 111.8 x
48 x 8.8: SEN0244, ADS1115 and Surveyor pH in a row, 6 mm apart, each turned
90 degrees so both probe connectors (XH, SMA) face -Y. On a wall the probe
leads hang down and the signal headers face up, one jumper from the ADS1115
between them. M2 x 10 for all three (it passes 2.5, 3.0 and 3.05), with an
ISO 7089 M2 washer on the two 3.0 holes. Every connector faces +-Y, so the
mount strips are on +-X: four M4 / #8 holes, bore 4.7 (ISO 273 medium + the
FDM allowance; a plate may now name its own mount bore). Vendor STEPs
(Adafruit, Atlas) are checked on the single-board plates (`vendor.py`).
