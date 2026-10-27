# Tote bench

A workbench that stores four HDX 27 gal totes in one bay (two on the floor,
two on a plywood shelf) under a 23/32 in plywood work top at about 38-3/8 in,
with a pegboard hutch and a 12 in shelf on the two back legs at 72 in. Built
mostly from lumber on hand (four 72 in 2x4s, four 31 in 2x4s, four 45 deg
braces, 2x2s); four 2x4s, one plywood sheet, a pegboard panel, screws
and two L-brackets are bought. Lumber, not a print: the manufacturability layer is the cut plan
against the inventory and each joint's screw against the stocked lengths.

![render](../../docs/img/tote_bench.png)

Why it is laid out this way (the full rationale is in `params.py`'s docstring):

- Four legs at the corners and nothing else upright. The front legs stop
  under the top; the back legs run on to 72 in and carry the hutch.
- Three 2x4 side rails per side (floor, shelf, top), on edge on the legs'
  inner faces. They sit outside the tote bay, so they cost no height, and
  they are the 31 in 2x4s on hand, uncut: the bench is 31 in deep.
- Across the bay only what must be: the top's aprons on edge (a stiff top),
  the shelf rails flat (so two tote levels fit under the top) and a back
  stretcher at the floor that stops the floor totes.
- Plywood top and shelf; a 2x2 lip stops the shelf totes. A plywood back
  panel, the sheet's last strip, is the side-to-side bracing.
- Hutch: pegboard on 2x2 cleats and a middle post; a 12 in shelf on 2x4 arms
  and a front rail, held up by two of the 45 deg braces. The bench tips at
  about 38 lb pulled at the top: anchor it to a wall stud (two L-brackets).

## Status

STATUS is `concept`: modelled and checked (no overlaps, the totes clear
everything and sit against their stops, every modelled screw bites its member,
touches nothing else and is driven before anything covers its head, and the
build sheet's assembly order brings every piece in along a clear path).
Racking (back panel) and tipping (anchor) are checked in `validate()`; the
screw lateral value behind the racking check is UNVERIFIED (NDS Table 12M as
read in review). Nothing cut. The FreeCAD view is written but not yet run
against FreeCAD.

## Sources

- Lumber: ALSC PS 20 dressed sizes (2x4 = 1-1/2 x 3-1/2, 2x2 = 1-1/2 square).
- Plywood: US DOC PS 1, 23/32 Performance Category (sold as 3/4 in).
- Screws: ASME B18.6.1 #8 wood screw shank; 6D penetration from AWC NDS 2018.
- Rails and aprons: SPF No.2 design values, NDS 2018 Supplement Table 4A.
- HDX 27 gal Tough Storage Tote: exterior at top from
  `cacad.registries.reservoirs.HDX_27GAL` (homedepot.com 999-27G-HDX page);
  75 lb capacity from the listing at
  https://slickdeals.net/f/18829045-hdx-27-gal-tough-storage-tote-6-97-store-pick-up-at-home-depot
- Pegboard: VENDOR, 1/4 in tempered hardboard, 2 x 4 ft panel.
- UNVERIFIED: the brace lengths (18-24 in long point; all are recut to one
  length the shortest reaches) and the 2x2 length (taken as 8 ft).

## Layout

```
params.py        LUMBER, TOTE, SCREW, SPF (sourced), INVENTORY (on hand), DESIGN; derive() places every board,
                 brace, tote and screw, plans the cuts and the shopping; validate() refuses anything not buildable
bench.py         build_bench (one solid per board and brace, the notched top), build_totes, build_screws,
                 check_bench (geometry, load-path probes, totes clear and at their stops, every screw bites)
freecad_view.py  STEP -> FreeCAD document, translucent totes (FreeCAD open, MCP Addon RPC server started)
build_sheet.py   out/build_sheet.md: cuts, layout marks from the floor, assembly order checked for screw access
                 and insertion path, screws, shopping, open issues
tests/           geometry + function, sources, inventory, fit, structure, negative controls, build sheet
```

## Run

```
.venv/bin/python projects/tote_bench/params.py         # design, cut plan against inventory, shopping list
.venv/bin/python projects/tote_bench/bench.py          # build + checks -> out/tote_bench.step, .stl (+ _totes)
.venv/bin/python projects/tote_bench/build_sheet.py    # -> out/build_sheet.md
.venv/bin/python projects/tote_bench/freecad_view.py   # FreeCAD open, MCP Addon RPC server started
.venv/bin/python -m pytest projects/tote_bench -q
```
