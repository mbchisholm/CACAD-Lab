# camera_reader

The bench optics for the camera absorbance reader v0 (spec:
`ref/camera-reader-v0.md`). A Pi 4B and a Camera Module 2 NoIR stand in a
bought dev stand. Five printed PETG parts turn that stand into a photometer:
a snout from the camera to a dark cell box, the box itself, an LED retainer, a
lid and a riser that holds the box at lens height. Nothing has been printed
yet.

![Camera reader V0](../../docs/img/camera_reader_v0.png)

## What is bought, and where its numbers come from

| Part | Source of every number |
|---|---|
| Stand (upright + base) | elric's "Dev stand for Raspberry Pi and Camera Module 2", MakerWorld. Standard Digital File License, so the meshes stay in gitignored `ref/stand/`. The numbers in `params.STAND` were measured by sectioning the meshes. The designer worked in inches, so every level is a round fraction (slot floor 0.200 in, camera seat 0.245 in). |
| Pi 4B | Raspberry Pi drawing RP-008343: outline, holes and every component height (the drawing's Z labels). Component extents are scaled off the drawing, not dimensioned. PCB thickness is UNVERIFIED. |
| Camera Module 2 NoIR | Raspberry Pi drawing RP-008149 (outline, holes, lens position) and the docs spec table (9 mm depth, 62.2 × 48.8° FOV). |
| 50 mm cuvette | MSE Supplies LS4035 product data: 45 × 12.5 × 52.5, 10 mm inside width, 17.5 ml. |
| 10 mm cuvette | Standard 12.5 × 12.5 × 45 macro cell. UNVERIFIED until a vendor is picked. |
| LEDs, diffuser | Generic 5 mm LED (UNVERIFIED; the spec still has to pick parts). Diffuser is 3 mm opal acrylic, cut by you to `params.py`'s printed size. |

Raspberry Pi publishes no STEP for the Pi 4B or Camera Module 2, only
drawings, so `hardware.py` builds both from the drawings and exports
`out/pi4b_local.step` and `out/cam_v2_local.step`.

## The optics

```
camera pocket -> snout: collar on the pocket rim, 143 mm tunnel, 3 baffles
  -> cell box: [REF | 50 mm | 10 mm] against the masked datum wall
     -> 3 mm opal diffuser -> 30 mm white-lined cavity -> 7 LEDs + retainer
```

![Section along the optical axis](../../docs/img/camera_reader_v0_section.png)

- **The stand sets the axis.** The lens sits 155.0 mm above the table. The
  riser is derived from that, so the box needs no adjustment.
- **The collar locates the snout and carries no load.** It slides 8 mm over
  the camera pocket's rim (0.4 mm fit) and stops on it. The box and riser
  carry the weight.
- **The 50 mm cell sits on the axis.** Its rays run 52.5 mm through the
  liquid. Off-axis, they hit its side wall. `validate()` checks that every ray
  from the lens pupil to each window stays inside that cell's 10 mm of liquid
  and misses the other cell.
- **Cells register against a datum.** Each cuvette's far face bears on the
  mask wall, and the pockets give 0.4 mm side play.
- **The LEDs are clamped, not pressed.** Each LED flange is squeezed 0.2 mm
  between the back wall and a retainer nub. The retainer is held by two M3
  screws in heat-set inserts.

At the datum the camera resolves 6.7 px/mm in the 2×2 binned mode, so each
7 × 18 mm window gives about 5,700 px. The spec hoped for "tens of
thousands". Getting there means moving the cells closer or making the windows
bigger, which is a decision for after E1.

## Light leaks you have to close

- **Rear hole.** The stand has a Ø14.6 hole in its plate right behind the
  camera. Put black tape over it.
- **Ribbon notch.** Close the collar's ribbon notch with a felt flap around
  the ribbon.
- **Lining.** Line the snout and the box's cell compartment with black
  flocking. Line the LED cavity with white film. Black PETG passes some NIR,
  so the 850 and 940 nm channels need the lining.

The read sequence's dark frame measures whatever leak is left.

## Build and check

```
.venv/bin/python projects/camera_reader/params.py           # the design, printed
.venv/bin/python projects/camera_reader/assembly.py         # checks + out/*.step, *.stl, V0.3mf
.venv/bin/python projects/camera_reader/freecad_assembly.py # out/camera_reader_V0.FCStd (needs the RPC server)
.venv/bin/python -m pytest projects/camera_reader
```

Without the GUI, `freecad_assembly.py` prints a one-line `freecadcmd` call that
builds the same document headless. The FreeCAD document is a real Assembly
(FreeCAD 1.x workbench): the stand meshes become solids, the boards come from
their local STEPs with placements from `hardware.py`, and the upright is
grounded.

The assembly checks are:
- all 19 parts clear pairwise;
- the seven designed contacts touch;
- every window's light reaches the lens past every printed part;
- the collar wraps the rim;
- overhang is checked at 45° in each part's print orientation, with the two
  bridges declared.

As a cross-check against the real meshes rather than the envelope, FreeCAD
measured the snout against the stand upright: 0 mm³ overlap at 0 mm
distance. Three small overlaps sit within the bought parts themselves:
- Pi/upright, 0.11 mm³, and upright/base, 0.08 mm³: mesh facets at the
  contact faces.
- Camera/upright, 0.41 mm³: the stand's retention lip laps over the camera
  board's edge. That lip is how the stand holds the camera.

## Hardware to buy

- **Flange:** 4 × M3 × 10 ISO 7045 screws and 4 × M3 ISO 4032 nuts.
- **Retainer:** 2 × M3 × 8 ISO 7045 screws and 2 × M3 heat-set inserts
  (CNC Kitchen standard).
- **Diffuser:** opal acrylic cut to 60.5 × 62.6 × 3 mm.
- **Lining:** felt or flocking, plus white film.

## Open

- LED part numbers. The LED hole and retainer nubs follow the generic 5 mm
  LED until a datasheet replaces it.
- The 10 mm cuvette vendor.
- A leaf spring that pushes each cuvette onto the datum, if E1 shows
  repositioning error.
- Lighter riser: it is 141 cm³ (~180 g PETG) as drawn.
