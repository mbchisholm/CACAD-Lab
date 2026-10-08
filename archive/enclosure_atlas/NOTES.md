# enclosure-atlas

An enclosure for Atlas Scientific sensor electronics (EZO circuits and their
probes), mounted on a 27-gallon HDX tote, printed in PETG. The first real
design in this repo. Status: spec only. No geometry until the inputs below
exist.

## What the model has to answer

The enclosure and the tote are modelled together so these questions get a
number, not an opinion:

- Do the probe cables and any tubing reach the liquid through the lid with
  the enclosure where it sits?
- Can the lid still come off with the enclosure attached?
- Is every opening in the enclosure above the working waterline, and does
  water shed off every horizontal surface?
- Can a probe be swapped without unmounting the box?
- Does a pump, if one lives under the lid, have head clearance? (Later; no
  pump chosen.)

Whatever the answers need is what gets measured. Nothing else about the tote
is modelled.

## Inputs and their sources

| input | source | status |
|---|---|---|
| tote lid outline, lid thickness, rim lip, wall draft, depth, waterline | calipers on the tote, into `reservoirs.py` | not measured |
| EZO circuit outline and pin pitch | Atlas datasheet | not entered |
| carrier board (which one: Whitebox Tentacle, Atlas EZO carrier, or own board) | owner decision | open |
| probe body diameters and BNC connector envelope | Atlas probe datasheets | not entered |
| enclosure wall, floor, clearances | `constants.py` after Checkpoint 2 | coupon unprinted |
| screw and insert sizes | on hand: M3 heat-set inserts, M2 and M3 screws | known |

## Open decisions

- Mount style: on the lid, hooked over the rim, or on the wall. Decides which
  tote numbers matter first. Lid-mount is the simplest and keeps everything
  above the waterline; rim-hook survives lid removal.
- Which carrier board. This fixes the outline the enclosure is built around
  and whether the KiCad round-trip (own board) is in play.
- Whether the analog-sensor variant is the same enclosure with a different
  board registry entry, or a different shape. Decide after this one exists.

## Log

- 2026-09-17: spec written. Tote and Atlas numbers to be measured and entered
  before any part file.
