# sen66_bench

An open PETG plate for a first SEN66 test. It holds an Adafruit Metro ESP32-S3
and the Adafruit SEN6x breakout (PID 6331) on M2 bosses, with the nuts captured
from underneath. The SEN66 has no mounting holes, so it drops into a 2 mm lip.
It is not an enclosure. Not printed yet.

![loaded: Metro, breakout, SEN66 envelope](../../docs/img/sen66_bench.png)

The Metro's STEMMA QT and the breakout's are level and face each other, 28 mm
apart: a 50 mm or longer STEMMA QT cable. The SEN66 sits with its fan at -X and
its GH socket on the side facing the breakout. The GH plug hangs to 0.74 mm
above the sensor's bottom, so a 2.4 mm groove under it gives the wires room to
turn. The groove leaves through the lip, under the outlet arch, straight towards
the breakout's GH socket. Plug the GH cable into the sensor before you set it in
the lip. The plate closes the sensor's open bottom duct, as Sensirion asks, and
the lip stays under the outlet arches.

![section through the socket and the groove](../../docs/img/sen66_bench_section.png)

## Status

STATUS is `passes`. 122.8 × 75.0 × 8.8 (plate 4.0, bosses to 8.8), one solid.
Hardware: 8 × M2 × 10 ISO 4762 and 8 × M2 ISO 4032 nuts. The Metro takes M2
because its hole beside the IOH header is 3.56 mm from a pin, and only an M2 boss
fits there. `validate()` refuses planted defects (tests).
UNVERIFIED: board thickness 1.6 (not in the Eagle files) and how far the
breakout's GH mouth stands past its edge (1.0 allowed). Not yet checked against
Adafruit's STEP models.

## Sources

Board outlines, holes, pin keepouts and connectors come from Adafruit's Eagle
files (`Adafruit Metro ESP32-S3 Rev B.brd`, `Adafruit SEN6x Breakout.brd`) via
`tools/board_from_eagle.py`, in `cacad/registries/boards.py`. The plate under
the boards is `projects/standoff_plate` row `SEN66_BENCH`, built with that
project's rules and checks. Sensor outline, outlet arch, socket, plug and groove
depth are `projects/sen6x_enclosure`'s numbers (Sensirion datasheet and STEP,
JST eGH). The lip fit is `materials.FIT_CLEAR` (DESIGN). Placements are DESIGN,
and `validate()` holds every relation they rely on.

## Run

```
.venv/bin/python projects/sen66_bench/params.py          # prints the design
.venv/bin/python projects/sen66_bench/sen66_bench.py     # -> out/*.step, *.stl, *.3mf
.venv/bin/python -m pytest projects/sen66_bench
```
