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

Bores and bosses (changed after the first print, 2026-10-15, docs/PRINT_LOG.md):
the boss bore is ISO 273 medium plus the DESIGN FDM allowance
(`materials.clearance_bore`: M2 2.6, M2.5 3.1, M3 3.6), and so is a mount bore
unless the plate names its own. The boss wall is 1.6, or what the board's
nearest pin leaves after `boss_pin_margin` (Adafruit M2 boards: 1.51), never
under `min_wall`. Each boss has a 45° flare at its root, `boss_root_flare`
(1.0) out and up. That is no more than `board_air_gap`, so it stays under every
pin tail. In a tray the inner wall moves out until every flare stops a nozzle
width short of it.

Declared ceilings: a stepped bridge over each nut pocket, so no perimeter of
the bore is printed in air. The first layer above the pocket leaves a slot
`bore + bridge_relief` wide, running flat to flat; the slicer bridges along it.
The second layer bridges across the slot and leaves a square. From the third
layer up the bore is round. The web is 1.6: the two stepped layers plus six full
ones. The nut bears on the first layer. These are the only overhangs, five faces
per pocket.

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
