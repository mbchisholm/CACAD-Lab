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
board centre (TCA9548A), refused when the holes are on one edge (ADS1115_V1,
BME280): the family has no rest for a cantilevered edge.
