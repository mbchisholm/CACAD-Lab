# Tote rack

A single column of totes, N high, hung by their rim on a pair of 1x1
runners so each slides out like a drawer. Load path: rim -> 1x1 runner ->
1x2 stringer on edge -> 2x4 leg -> floor. The front is open below a top
tie; two ties and the eight stringers brace the frame. From the "Garage
Tote Bin Storage Rack - CAD-Ready Spec" (Sep 2026); its coordinate system
and member IDs are kept, so its bounding-box table (S7) is a test.
Lumber, not a print: the manufacturability layer is the cut plan against
8 ft stock and each joint's screw against the stocked ladder.

```
params.py   LUMBER (ALSC PS 20 dressed sizes), SCREWS (#8, 6D penetration), RACKS (tote and pitch inputs, S4),
            derive(rack), validate(rack); the printout is the design review and cut list
rack.py     build_rack (one solid per member), build_totes (rim + body envelopes), build_screws, check_rack
freecad_view.py  STEP -> FreeCAD Assembly (front-left leg grounded, coloured by lumber size), translucent totes,
            screw shank envelopes, exploded view from derive()["explode_moves"], BOM sheet; saved as out/*.FCStd
build_sheet.py   shop sheets: one SVG per distinct member with its cut length and every pilot hole dimensioned
            from end A, plus out/build_sheet_<rack>.md (cut plan per stick, drill, assembly steps, screws)
tests/      geometry + function, spec S7 table reproduced, cut plan, screws, open front, sheets cover every screw
ref/        (gitignored) the HDX 207 585 vendor model (Parasolid .x_t, unreadable here) and its label photo
```

```
.venv/bin/python projects/tote_rack/params.py     # design review and cut list, every rack
.venv/bin/python projects/tote_rack/rack.py       # ACTIVE_RACKS -> out/tote_rack_<rack>.step, .stl (+ _totes)
.venv/bin/python -m pytest projects/tote_rack -q
.venv/bin/python projects/tote_rack/freecad_view.py    # FreeCAD open, MCP Addon RPC server started
.venv/bin/python projects/tote_rack/build_sheet.py     # -> out/sheets/*.svg, out/build_sheet_<rack>.md
```

The sheets are plain SVG; to see one as PNG without adding a rasterizer, render it through FreeCAD's Qt
(`PySide.QtSvg.QSvgRenderer`) over the RPC server, or open it in a browser.

Change the tote or pitch in params, re-run `rack.py`, then `freecad_view.py`;
it rebuilds the FreeCAD document from the new STEP. Do not edit parts or
placements in FreeCAD.

## The actual bin

`TOTES["HDX_207585"]` holds what the label says (28.6 x 19.6 x 15.2 in, with lid) and `RACKS["hdx_207585"]`
is the rack for it. Its rim width, body width and lip thickness are `None`, so `validate()` fails by name
until the bin is calipered (or the `.x_t` is exported to STEP from Onshape and read there). The label alone
already says the spec's example tote (30 x 20.5 in) is not this bin: the rim is at most 19.6 in, so a 19 in
rail span leaves at most 0.3 in of bearing per side and `S_rail` must come down once `TWr` is known.

## What the model found in the spec

- The rim (20.5 in) is exactly the inside width of the legs (W - 3 = 20.5):
  zero side clearance, the tote rubs both legs. `derive()["rim_side_clear"]`
  reports it; `validate()` only refuses a negative value. Measure the tote.
- The spec's own check "base = railtop - TH + 0.75" needs a rim lip
  thickness it never lists. `T_rim` (UNVERIFIED, 0.75 in) holds it; with it,
  the top tote's rim top is 68.75 in and the front top tie clearance is
  1.75 in, not the 2.5 in the spec claims.
- The 2.5 in frame screws in the shopping list (S9) exit a 1.5 in leg when
  driven through a 0.75 in stringer. `derive()` picks 2 in for
  stringer->leg and runner->stringer, 2.5 in for the ties into the legs.
- The tote's Y position is not in the spec; it is centred in the depth.
- Optional members (back diagonal brace, back stops) are not modelled: the
  spec gives neither a placement for the brace within the tie stack nor a
  stop height.
