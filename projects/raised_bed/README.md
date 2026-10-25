# Raised bed

An open-bottom bed of 1x6 cedar fence pickets screwed to a 4x4 cedar post in
each inside corner. Long pickets run the full outer length and cover the
short pickets' end grain; posts sit flush with the top course and do not
show from outside. No legs, no floor. Lumber, not a print: the
manufacturability layer is the cut plan against stocked lengths and the
screw against the stocked ladder, not walls and overhangs.

## Status

STATUS is `passes`: geometry and function checks (no overlaps, every screw
through its picket and into one post), the cut plan and the screw ladder pass
for the active beds, and FreeCAD positions agree with params. Nothing is cut yet.

Picket end trim is bounded, not measured: a dog-ear with two 45 deg clips
and a flat top cannot remove more than half the picket width (69.8 mm).
Caliper a picket's thickness and tape its length before cutting; the 4x2
plan leaves 7.5 mm on the picket that yields three short sides, and a full
5/8 in picket leaves the 1-5/8 in screw 0.4 mm above the 6D minimum.

## Sources

`params.py` tags every row of `LUMBER` (actual dressed sizes, a source per
row) and `SCREWS` (#8, 6D penetration). Stocked lengths and the screw ladder
are the manufacturability limits; measure the real stock before cutting.

## Layout

```
params.py   LUMBER (actual sizes, source per row), SCREWS (#8, 6D penetration), BEDS (outer L x W, courses),
            derive(bed), validate(bed); the printout is the cut list
bed.py      build_bed (one solid per picket and post), build_screws (shank envelopes), check_bed
freecad_view.py  STEP -> FreeCAD Assembly (one post grounded, coloured by kind), exploded view from
            derive()["explode_moves"], BOM sheet; saved as out/*.FCStd. Checks every part's position against
            params (with a shifted control that must disagree), and the exploded and restored positions
tests/      geometry + function (no overlaps, each screw through its picket and into one post), cut plan, screws
```

## Run

```
.venv/bin/python projects/raised_bed/params.py     # design review and cut list, every bed
.venv/bin/python projects/raised_bed/bed.py        # ACTIVE_BEDS -> out/raised_bed_<bed>.step, .stl
.venv/bin/python -m pytest projects/raised_bed -q
.venv/bin/python projects/raised_bed/freecad_view.py    # FreeCAD open, MCP Addon RPC server started
```

Change a size in params, re-run `bed.py`, then `freecad_view.py`; it rebuilds the FreeCAD
document from the new STEP. Do not edit parts or placements in FreeCAD.
