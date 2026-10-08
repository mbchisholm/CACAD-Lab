# nutrient_controller

A printed PETG controller box for a hydroponic reservoir. It reads TDS and
water temperature, doses nutrient concentrate with one peristaltic pump, and
shows its state on an OLED with three buttons and an LED. The active
revision, B2, hangs beside any tote or bucket on a clamp over the rim, so the
container is never drilled. Nothing has been printed yet.

![B2 on a container wall: box, cover, post plate, rim hook and knob](../../docs/img/nutrient_controller_b2_front.png)

| file | what is in it |
|---|---|
| `DESIGN.md` | the three concepts, the box, the B1 and B2 mounts, limits |
| `MODELLING.md` | how it was modelled: approach, code layout, build123d methods, what the checks caught |
| `NOTES.md` | the working log: parts list with sources, placeholders, what comes next |

## Status

STATUS is `passes`: B2 validates and its assembly checks pass, including the
clamp across a 2 to 35 mm container wall. B1 (bolted through the wall) stays
in `params.py` as the alternative: validated, not built. Open: the first
print, and the PLACEHOLDER values below.

Limits worth knowing: every DESIGN clearance is untested in PETG; the TDS
probe's 830 mm lead leaves 53 mm to spare on the HDX tote and 13 mm on a
deeper container; the clamp holds by friction and one screw, so the hook is
the first part for a `cad-design-review` pass.

## Sources

Every number in `params.py` comes from a standard (ISO 273, ISO 4762, ISO
4017), a vendor sheet (Lapp, Kamoer, JST, E-Switch), a board file (Adafruit's
Eagle files, Seeed's KiCad project), or is a DESIGN choice with a comment.
Anything else is marked PLACEHOLDER: every board's PCB thickness, the OLED
panel's thickness, the TDS probe's cable diameter, the USB-C plug overmold.
Where a value is unpublished (the pump flange hole height, the tote wall
slope, the rim profile) the part is designed so it does not depend on it.
`NOTES.md` lists each and how the design tolerates it.

Vendor sheets and Eagle files live in `ref/`, which is gitignored: the sources
are named in `params.py`, but the files are only on the machine that fetched
them.

## Run

```
.venv/bin/python projects/nutrient_controller/params.py     # every derived number, both revisions
.venv/bin/python projects/nutrient_controller/assembly.py   # build, check, out/B2.3mf and out/B2_assembly.step
.venv/bin/python -m pytest -q projects/nutrient_controller
```

Single parts build on their own (`body.py`, `cover.py`, `wall_plate.py`,
`rim_hook.py`), each writing its STEP and STL to `out/`. To build B1 instead,
set `ACTIVE_SIZES = ("B1",)` in `params.py`.
