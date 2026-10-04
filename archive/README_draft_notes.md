# CACAD: Computer-Aided Computer Aided Design

This repo is a collection of my various experiments trying to use AI agents for 3D design - I am calling this genre Computer-Aided Computer-Aided Design (lol). 

## Repo Structure
Primarily the repo is made up of 2 parts:

- `cacad/` is the shared package, kind of like a shared library or toolbox for working with build123d & FreeCAD

- `projects/` contains examples of what I've been able to make Each folder has its own `params.py`, parts, tests, and outputs that get used by CACAD

There are also a few miscellaneous tools and tests and config files.


### Structure and Methods

NOTE:I think this section should become a table that more succinctly describes the role each file/folder plays, and we should group it different. So for example I'd put the checks/ folder down near the bottom because it only comes into play at the end. I'd also do a better job of explaining what geometry.py actually does, among other lines. 
```
cacad/
  selectors.py    pick faces and edges by geometry (a circle of radius r at height z), never by index
  threads.py      bd_warehouse IsoThreads as single solids, kept separate from the core they sit on
  probes.py       "is there material at this point", "is there a tooth AND a groove here",
                  thinnest wall on a section, worst overhang angle from face normals
  booleans.py     interference volume between parts, solid by solid
  finishing.py    chamfer with fallback sizes; required=True for the ones that are not cosmetic
  export.py       STEP + STL, and a 3MF with one named mesh per part
  geometry.py     ISO thread root radius, hex across-corners, clamp force from torque
  checks/         printability (walls vs nozzle), orientation (bed face exists), overhang (undeclared
                  ceilings fail), cantilever (bending strain across layers) — each takes a part and a
                  dict of limits, so the same check runs from pytest or a script
  freecad/        the RPC client, pairwise re-derivation of placements and booleans, a BOP shape
                  check from STEP and BREP, and the KiCad-board-to-STEP freeze
  registries/     boards (outline, hole pattern, source), reservoirs, printer and material numbers
```


NOTE: I don't think this lays it out well at all and a better more intuitive explanation is needed. This is written as if between two people who have both seen the repo before. 

A part file uses it like this: 
- read numbers from `params.derive(size)` and the registries, build the solid.
- Select the edges to chamfer with `circular_edges(...)`, add threads with `with_threads(core, [solid_thread(...)])`
- Then, `assert_material`, `assert_bbox`, `min_ring_wall` proves the features exist before `export` writes anything.


### Projects

NOTE: I think I'd start with the simplest first, the standoffs, show how we made those, and then move on. Also I think the readme should also cover the kicadstepup-freecad connection. 

#### **Making Cable Glands** 

NOTE: maybe link to subfolder

![Cable gland parts: body, collet, TPU insert, nut](docs/img/cable_gland_parts.png)

A panel-mount gland for a 5–10 mm cable: body with a 13 mm panel thread, gasket recess and compression-stop foot, hex, and a neck thread; a slotted collet; TPU seal sleeves (one per cable sub-range, IDs derived); a domed nut whose ledge squeezes the insert onto the cable. Everything comes from `params.py`: change `hex_af` and the wrench flat, the flange, the overhang cone and the test that checks them all move together. Twenty-one tests cover mating (the nut threads on, and a +180° phase error collides), stroke, hard stops, wall thickness, print orientation, overhang and finger strain. A FreeCAD script re-derives the placements and booleans independently. M12 and M20 are in `params.SIZES` but gated until the M16 has been printed. Its README has the design.

![Coupon plate: body, five nuts at 0.15–0.45 mm thread clearance, collet](docs/img/cable_gland_coupon_plate.png)

`coupon.py` lays out a print plate for the first physical test: the body, five nuts built at increasing thread clearance with the value embossed on each, and the collet, as one 3MF with each part a single named mesh. The nut that runs freely at the smallest clearance sets the production value.

### ** Creating custom mounting plates and enclosure trays from board hole patterns** 

This was the second project attempted, building off the spacers.

![Mount plate for an ADS1115 with integrated bosses](docs/img/mount_plate.png)

`mount_plate([(BOARDS["ADS1115"], (0, 0))], screw="M2", standoff=8)` gives a plate sized to the boards you list, with clearance holes at the registry's hole pattern, an engraved outline as a placement guide, the board name embossed, and either a flat plate for loose spacers or integrated bosses of the height you ask for. Add a board to `cacad/registries/boards.py` with its datasheet and it works for that one too.

![Enclosure tray for two ADS1115 boards with a cable slot](docs/img/enclosure_tray.png)

`tray(placements, screw, cable_side)` in `enclosure.py` is the same idea with walls: a filleted open-top box, bosses and holes per board, and a U-slot through one end wall for the cable. The slot width is an 8 mm guess until a cable is measured.

#### **Parametric standoffs** 

![M3 standoff ladder, 5 to 15 mm](docs/img/standoffs.png)

`spacer(length)`: an M3 unthreaded standoff, 6 mm OD, chamfered, in whatever length. The file exports a 5/8/10/12/15 mm ladder and each length on its own. Small, but it's the part every board project ends up needing and it reads the same clearance constant as everything else.

#### **enclosure on a reservoir lid** 

A spec, no geometry yet: an enclosure for Atlas Scientific EZO sensor circuits and their probes, mounted on the lid of a 27-gallon tote, with probes and tubing reaching the liquid. `NOTES.md` lists the questions the model has to answer (can the lid still come off, does every opening sit above the waterline, can a probe be swapped without unmounting) and the numbers it's waiting on: the tote hasn't been measured.

### Calibration Files

![FDM calibration coupon: hole clearance ladder, insert bore ladder, 20 mm cube](docs/img/fdm_coupon.png)

`coupons/fdm_coupon.py` is the plate that prints before anything else does: five 5 mm holes at +0.10 to +0.30 clearance, five M3 heat-set insert bores from 3.8 to 4.2 mm on a raised pad, and a 20 mm cube for shrinkage, all labelled. Its measurements replace the three TODO values in `cacad/registries/materials.py`. The cable gland's thread-clearance plate above is the second coupon.

### Everything else

NOTE: this should be a table or just subsections, not a code block. 

```
docs/FINDINGS.md   kernel and tooling facts F1..F23, each with a snippet that prints PASS while the
                   behaviour still holds; the TODO tables the coupons fill in
docs/PARAMS_CONVENTION.md, params_template.py   how a params.py is written, and the skeleton
tools/verify_mcp.py   run a part through build123d-mcp from a shell (the renders above came from it)
CLAUDE.md          the rules for the agent, alongside the mistake that created it
.mcp.json          build123d-mcp and freecad-mcp servers
```


## How it works

A project starts with its `params.py`: the inputs per size, the family-wide rules, a `derive()` that computes every other dimension, and a `validate()` that fails on anything you can't buy or print. Board outlines, reservoir dimensions and printer numbers live in `cacad/registries/`, each next to the datasheet, KiCad file or caliper reading it came from. A number with no source doesn't go in. `docs/PARAMS_CONVENTION.md` has the rules and `docs/params_template.py` is the skeleton.

Each part is then one file built from `params.derive(size)`. Faces and edges are selected by geometric predicate (`cacad.selectors`), never by index, so a parameter change can't quietly pick a different face. Threads come from bd_warehouse and stay as separate solids overlapping the core by 0.2 mm; the slicer unions them.

Checks run as pytest in three layers. Geometry: the part is valid, has the expected number of solids and bounding box, and probes at points that must and must not be material pass. Manufacturability: walls measured on sections against the nozzle, a declared print orientation whose bed face is verified to exist, overhangs computed from face normals with slivers excluded, and bending strain stated across layer lines, not just bulk. Function: mating parts placed and intersected pairwise, strokes measured on the geometry, hard stops present. `cacad/checks/` holds the reusable ones.

Export is STEP and STL per part plus a 3MF print plate with one named mesh per part (`cacad.export_3mf`). Then a coupon prints before anything prints for fit: `coupons/fdm_coupon.py` covers hole clearance, heat-set insert bores and shrinkage, and the cable gland has its own thread-clearance ladder.

Two assumptions run through the shared code: the part axis is Z, and a part may be a compound of overlapping solids, so every probe and boolean works per solid.

Inside a Claude Code session the `build123d-mcp` server in `.mcp.json` runs a part file, validates it, finds the holes and renders it. `tools/verify_mcp.py` does the same from a shell.

### About build123d

NOTE:expand on its role

Build123d is a Python-based, parametric (BREP) modeling framework for both 2D and 3D. It provides a python-based interface for working with Open Cascade's geometric kernel. For example:

![Simple rectangular plate](docs/img/ex1_Simple_Rectangular_Plate.png)
![Plate with hole](docs/img/ex2_Plate_With_Hole.png)

I would check out the rest of these examples to get a better understanding of how this works. https://build123d.readthedocs.io/en/latest/introductory_examples.html

Parts can be exported to FreeCAD or the like. This makes it a lot easier to prompt an agent and end up with usable, exportable, parameterizable parts for 3D printing or CNC machining. It doesn't replace the traditional CAD experience and it is limited when it comes to complex constraint geometry and assemblies, but it has let me build several handy widgets already. This repo is the tooling I've built to use it in a way that's practical and (hopefully) time-saving.

### FreeCAD's Role

FreeCAD has three jobs here, all reached over the `freecad-mcp` addon's RPC server 

It is a second implementation. Each part's own STEP is imported, the placements are recomputed from `params` inside FreeCAD, the booleans run there, and the volumes are compared with build123d's. A BOP check runs on every solid and face, from the STEP and from the exact BREP, so exporter artefacts can be told from real defects. FreeCAD 1.1.3 and build123d both run OpenCascade (7.8.1 vs 7.9.3), so this is a second code path, not a second kernel, and the check always includes a case that must disagree so that agreement on zeros proves something.

It is the KiCad bridge. A board goes through KiCadStepUp to a frozen STEP (`cacad.freecad.kicad_freeze`), so an enclosure can be checked against the real board and, if needed, dictate its outline.

And it is a viewer a person can click around in.

What it no longer does is compose assemblies. Nothing drawn in FreeCAD becomes source; if a part is wrong, the fix is in its `.py`. Setup is: open FreeCAD, pick the MCP Addon workbench, press **Start RPC Server**. Every launch. Keep each call small; the GUI gives one call about 90 seconds.

## Decisions the AI Made over the course of the experiments

**Code-first over FreeCAD composition.** The first plan had FreeCAD doing all composition and assembly. In practice that path needed a manual button press per launch, a GUI-thread timeout and an opaque binary file in git, while build123d caught the same collisions with none of that. FreeCAD kept the jobs it does well.

**Threads as separate overlapping solids, not fused.** Fusing a bd_warehouse thread onto its core leaves sliver faces and pcurve-tolerance flags that no fixer clears, and next to a hex the fuse can silently return an empty compound (`docs/FINDINGS.md` F3, F5, F6). Keeping the thread as its own solid overlapping the core by 0.2 mm sidesteps all of it; the cost is that every boolean between parts has to run solid-by-solid (F7) and the 3MF has to be one mesh per part (F15).

**Registries instead of numbers in parts.** `cacad/registries/boards.py` holds a board's outline and hole pattern once, with its source; every part that mounts that board reads it. A wrong number gets fixed in one place. The alternative, constants in each part file, is how a 0.7 mm hole error from a community STEP model would have spread.

**pytest checks over the MCP server's printability analysis.** build123d-mcp can render, find holes and estimate printability, and it's useful for a quick look. But a check that lives in a test file is versioned, deterministic and runs without a session, so the tests are the source of truth and the MCP tools are a convenience.

**Findings as reproductions, not notes.** Each entry in `docs/FINDINGS.md` is pinned to the library versions it was seen on and carries a snippet that prints `PASS` while the behaviour holds and `CHANGED` when a newer version fixes it. A gotcha list rots; a snippet tells you when it's safe to delete the workaround.



## CURRENT STATUS

Nothing has been printed. Both coupons are exported and unprinted, so the clearance values in `cacad/registries/materials.py` are the starting guesses, marked TODO, and nothing should be printed for fit until they're replaced. The cable gland's M12 and M20 sizes are in its `params.py` but gated: the fused-thread behaviour turned out to be size-dependent, and the unfused route has to be shown clean at those sizes before they're activated. `cacad.export_3mf` reaches into two private `Mesher` methods, which is fine on build123d 0.11.1 and may not survive an upgrade. And FreeCAD's RPC server has to be started by hand on every launch; when the FreeCAD calls fail, that's the first thing to check.

NOTE: talk about known issues like the freecad crashing bug during 2d drawing.

## Setup & Installation

NOTE: we really need a usage section I guess but that can come after we've built it out further. 
```
uv venv --python 3.12 .venv
uv pip install -r requirements.txt && uv pip install -e .
.venv/bin/python -m pytest -q                      # the shared package and every project
.venv/bin/python projects/cable_gland/build.py     # -> projects/cable_gland/out/
```

Use Python version 3.12, I believe the OpenCascade stuff doesn't work for 3.13 yet.

## Resources

Build123D (see above) link needed to docs and github

BD Warehouse: Generates special types of parametric parts that work with build123d https://bd-warehouse.readthedocs.io/en/latest/index.html
  - fastener - Nuts, Screws, Washers and custom holes
  - flange - Standardized parametric flanges
  - pipe - Standardized parametric pipes
  - thread - Parametric helical threads (Iso, Acme, Plastic, etc.)

freecad-mcp: the RPC server and addon workbench this repo talks to https://github.com/neka-nat/freecad-mcp

PARTCAD: Useful but not comprehensive collection of parts & assemblies, mostly related to electrical / mechanical stuff. Good starting point, I got the arduino and raspberry pi parts from here. https://partcad.org/repository
