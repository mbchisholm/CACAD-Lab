# nutrient_controller: the design

The three concepts, the box, and the B1 and B2 mounts. How it was built is in
`MODELLING.md`; the parts list, placeholders and log are in `NOTES.md`.

## Concepts

Three rough concepts, all on the HDX 27 gal tote, each holding the same
electronics as envelopes:

| | A: box on the lid | B: box on the end wall | C: screen on a post + box on the lid |
|---|---|---|---|
| lid lifts off alone | no | yes | no |
| lowest opening over the waterline | +160 mm | +100 mm | +160 mm |
| TDS probe cable to spare | +420 mm | +480 mm | +158 mm |
| holes in the tote | 7 in the lid | 4 in the wall | 3 in the lid |

![Concept A](../../docs/img/nutrient_controller_concept_a.png)
![Concept B](../../docs/img/nutrient_controller_concept_b.png)
![Concept C](../../docs/img/nutrient_controller_concept_c.png)

B went forward: it is the only one where taking the lid off leaves the
probes, the tube and the electronics where they are.

## The box (B1 and B2)

The box is 110 × 150 × 44 mm and prints on its back. Inside are:
- the DFRobot SEN0244 TDS board, with an ADS1115 reading it;
- the Adafruit MOSFET driver for the pump;
- a Perma-Proto carrying the XIAO ESP32-C3 and the Pololu 5 V regulator.

Each board sits on bosses whose height is derived from a stocked screw. A
nut pocket opens to the back face, and the boss is raised until an M2 × 10
ends inside its nut and 0.4 mm short of the back. The Kamoer NKP pump bolts
outside the left wall with its motor inside. Its tubes leave the head
towards the wall, so no liquid enters the box.

Cables come in from below through Lapp glands, with a drip loop. The M16
gland for the TDS probe is sized so the probe's XH plug (9.3 mm diagonal)
passes through it open. The cover carries the OLED behind a window, three
IP67 buttons and the LED, and has a 3 mm drip skirt over the body's edge.
The box hangs by three keyholes on mushroom posts on a printed plate and
lifts off for service.

![B2 with the cover off](../../docs/img/nutrient_controller_b2_open.png)

## B1: plate bolted through the wall

The post plate bolts flat to the tote's end wall with four M5 bolts through
a backing plate inside the tote. The probe cables leave the tote through one
hole behind the plate. Every hole in the tote sits at least 50 mm above the
waterline. It is the stiffer mount and the cleaner lid, but it means drilling
one particular tote. It stays in `params.py` as the alternative: validated,
not built.

![B1 front](../../docs/img/nutrient_controller_b1_front.png)
![B1 from the tote side: bolt holes, cable window, tube slot](../../docs/img/nutrient_controller_b1_back.png)

## B2: rim clamp (active)

The post plate bolts to a printed C-hook through two vertical slots, which
set the box top anywhere from 29 to 41 mm below the rim. The hook's bridge
sits on the rim and its inner jaw bears on the inside face. An ISO 4017
M6 × 60, turned by a printed knob, presses a printed pad on the outside. The
throat takes any wall or lip from 2 to 35 mm thick at the screw. The hook is
60 mm wide, so a bucket rim of 150 mm radius leaves only a 3 mm gap across
it. The probe cables and the dosing tube cross the rim in a 16 × 3 mm groove
on the bridge, then run down outside to the glands. The hook prints upside
down on its bridge, so the jaw and leg are plain walls on the printer.

![Section through the hook: inner jaw, container wall, pad, M6, knob, post plate, box](../../docs/img/nutrient_controller_b2_section.png)
![The hook seen from the jaw side: cable groove on the bridge, throat, slot for a hook bolt](../../docs/img/nutrient_controller_b2_clamp.png)

## Limits

Nothing has been printed, so every DESIGN clearance is still untested in PETG.
Several bought-part numbers are PLACEHOLDER:
- every board's PCB thickness;
- the OLED panel's thickness;
- the TDS probe's cable diameter;
- the USB-C plug's overmold.

The design tolerates each one (the list and how is in `NOTES.md`), but none
has been confirmed.

B2 has two costs B1 doesn't. The lid rests on the hook's bridge, 6 mm high
there, and a snap-on lid won't latch at that spot. The TDS probe's 830 mm
lead is tight: 53 mm to spare on the HDX tote, 13 mm on a container whose
rim is 200 mm above the water, so anything deeper needs an extension. The
clamp holds by friction and one screw, which makes the hook the first part
for a `cad-design-review` pass.

The firmware (sprout-cut `nutrient-analog-xiao`) needs `activeHigh=true` for
the MOSFET driver. It has no button or LED pins yet.
