# sen6x_enclosure

A printed PETG box for one Sensirion SEN6x air-quality module (SEN62, 63C, 65,
66, 68 or 69C share one package). Two parts: a base the sensor drops into and
a flat lid on four M3 screws in heat-set inserts. Not printed yet.

![FreeCAD: SEN6x enclosure, lid translucent, cable by pin](../../docs/img/freecad_sen6x_enclosure.png)

The sensor's air path decides the box. Air enters through the fan grille on
the top face and leaves underneath, through a duct that exits by an arch in
each long side. The base floor closes the duct, the lid has a hole over each
top opening, and each long wall has a window on the arch. The cable leaves
under one wall through a floor groove; plug it in before the sensor goes in.

## Status

Passes: 25.6 + 2.0 mm tall, 70.6 x 30.5 mm outside, checked against
Sensirion's own STEP model. Open: print and fit check.

## Sources

Every number in `params.py` is a `(value, TAG, source)` triple and
`validate()` refuses an untagged one. Sensirion's STEP and datasheet give the
module; the connector is an ACES 51468-0064N-001 taking a JST GHR-06V-S plug;
inserts are CNC Kitchen's published hole size. The vendor STEP lives in `ref/`
(gitignored): download it from Sensirion to rebuild the checks.

## Run

```
.venv/bin/python projects/sen6x_enclosure/params.py      # prints the design
.venv/bin/python projects/sen6x_enclosure/enclosure.py   # -> out/
.venv/bin/python -m pytest projects/sen6x_enclosure
```
