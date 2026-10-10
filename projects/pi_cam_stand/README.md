# pi_cam_stand

A printed desk stand for a Pi 4B and a Camera Module 2. It replaces the bought
dev stand camera_reader sits on. The Pi lies flat in the base. The camera
is screwed to a carrier by all four of its holes, on a hinge at the top of a
column, and tilts from straight down to 30° up. Nothing has been printed yet.

![Assembled, Pi side](../../docs/img/pi_cam_stand_v0.png)

![Camera side: four M2 screws, ribbon slot under the camera, knuckle between the cheeks](../../docs/img/pi_cam_stand_v0_front.png)

Two PETG parts, no support: `stand.py` (base, Pi bosses and column, printed
upright) and `carrier.py` (camera plate and hinge knuckle, printed flat on its
back). It needs the 300 mm ribbon (Adafruit 1648); the camera's 150 mm one is
too short. DESIGN.md has the parts list, assembly, design rules and checks.

## Status

Passes: `validate()` and the `assembly.py` checks pass, through the full
tilt range. Not printed. Open: the camera's back-side connector height is
unpublished (the 4 mm bosses allow up to 3.5), and hinge clamp force and
column stiffness are not computed.

## Sources

Every number in `params.py` is a `(value, TAG, source)` triple and
`validate()` refuses an untagged one. The Pi 4B and Camera Module 2 come from
Raspberry Pi's mechanical drawings (solids shared with camera_reader), the
ribbon from Adafruit 1648, screws and nuts from ISO 7045 / 4032, clearances
from `cacad.registries.materials`.

## Run

```
.venv/bin/python projects/pi_cam_stand/params.py            # the design, printed and validated
.venv/bin/python projects/pi_cam_stand/assembly.py          # checks + out/*.step, *.stl, V0.3mf
.venv/bin/python projects/pi_cam_stand/freecad_assembly.py  # out/pi_cam_stand_V0.FCStd, exploded view (needs the RPC server)
.venv/bin/python -m pytest projects/pi_cam_stand
```
