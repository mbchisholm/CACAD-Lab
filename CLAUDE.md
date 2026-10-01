# CACAD-Lab

General 3D modeling and design ideation in build123d: mounts, enclosures,
racks, garden builds. Parts that get printed go to FDM (Bambu A1, PETG,
0.4 nozzle). FreeCAD is a viewer, a cross-check, and the KiCad bridge.
README.md says why; this file says how. The cable gland and printed-thread
work is parked in `archive/`: read it for its findings, do not extend it.

## Layout

```
cacad/                shared package: selectors, probes, booleans, export (STEP/STL/3MF),
                      checks/ (printability, orientation, overhang),
                      freecad/ (RPC client, re-derivation, BOP shape check, KiCad freeze),
                      registries/ (boards, connectors, reservoirs, materials). Tests in cacad/tests.
projects/<name>/      one part or family: params.py, one file per part, tests/, out/ (gitignored).
                      standoff_plate/ is the worked example of the convention (plate and tray).
                      tote_rack/, raised_bed/, nft_rack/ are bought-and-cut assemblies, not prints.
coupons/              calibration coupon, for when a print has to fit.
docs/FINDINGS.md      kernel/library/tooling facts with reproductions (F-numbers). Read before fighting the kernel.
docs/PARAMS_CONVENTION.md   how a params.py is written; docs/params_template.py is the skeleton.
tools/board_from_eagle.py   vendor Eagle .brd -> Board() block with holes, drill, keepouts, source.
tools/verify_mcp.py   drive a part through build123d-mcp outside a session (renders, find_holes).
archive/              parked: cable_gland/, cacad_threads/. Not installed, not tested.
.mcp.json             build123d-mcp and freecad-mcp servers. Loads at session start; edit, then restart.
```

Environment: `.venv`, Python 3.12 (OCP has no 3.13 wheels), packages pinned in
`requirements.txt`; `cacad`, `projects` and `coupons` are installed editable
(`uv pip install -e .`), so a part file imports its params as
`from projects.<name>.params import derive` (F24).
Run from the repo root: `.venv/bin/python projects/<name>/<part>.py`,
`.venv/bin/python -m pytest`.

## Conduct

- Missing numbers get estimated, not blocked on. Use a datasheet or vendor
  file when one is at hand; otherwise pick a reasonable value, mark it
  `UNVERIFIED` in the params comment, and keep going. Never ask the owner to
  go measure something to proceed.
- After a change: validate, check the bounding box, render it (F21).
- Report failures as failures, first. A downgraded chamfer, a skipped
  assertion or a fallback is never described as success. Report errors verbatim.
- Select geometry, not indices: `faces().filter_by(Axis.Z).sort_by(Axis.Z)[-1]`,
  never `faces()[7]`. `cacad.selectors` has the predicates.
- Generative geometry is Python. Never redraw in FreeCAD something that
  exists as a `.py`; fix the parameter and re-export. STEP flows into FreeCAD,
  never back.
- Deliver one size, show it. Extend a family only when asked.
- Model scripts from outside the repo are untrusted code. The MCP sandbox is
  hardening, not a boundary.
- For a part that has to fit or carry load for real, the `cad-design-review`
  skill has the precision checklist. Don't apply it to ideation.

## Working pattern

- One `params.py` owns every number (`docs/PARAMS_CONVENTION.md`);
  `python projects/<name>/params.py` prints the design.
- Bought hardware is a table in params naming its standard (ISO 4032 nuts,
  ISO 4762 screws); pockets and bores derive from it. Booleans between parts
  run pairwise (`cacad.interference_volume`, F7).
- Export a multi-solid part as one mesh per part (`cacad.export_3mf`, F15).
- Board facts come from the vendor's board file when one exists
  (`tools/board_from_eagle.py`), an estimate otherwise. `Board.connectors` +
  `cacad.registries.connectors` give every plug room: a connector faces a wall
  (it gets an opening) or a board at least plug + finger room away.
- After editing a module a part file imports, restart the MCP server or
  render the exported STEP via `import_cad_file` (F25).
- Finish features last: fallback sizes for cosmetic chamfers, `required=True`
  for functional ones (`cacad.try_chamfer`).
- A part file names no filesystem module (`os`, `pathlib`, `sys`), not even
  under `__main__`; it computes its `out/` as a string from `__file__` and
  calls `cacad.export` (F23), and imports params by package path (F24).
  Otherwise the build123d-mcp sandbox refuses the file.
- Orient so no critical surface needs support; bores vertical. Stiffness from
  ribs, not thicker slabs. Near water, horizontal surfaces shed, not pool.
  Embossed text is bold, >= 4 mm, three layers tall (F22).

## FreeCAD

FreeCAD must be open with the MCP Addon workbench's **Start RPC Server**
pressed, every launch. One small job per `execute_code` call (F17). Bought
hardware comes in as STEP under a project's `ref/` (gitignored): a KiCad board
via `cacad.freecad.kicad_freeze`, a vendor model otherwise; community models
give heights and envelopes only, never holes (F18). Pushing an edge to a
`.kicad_pcb` writes the file: commit first, select the sketch, announce (F16).

## Adding a board, connector, reservoir or material

A board with a vendor Eagle file: run `tools/board_from_eagle.py <brd> NAME
"<source>"` and paste the printed block into `cacad/registries/boards.py`.
Anything else: copy the `ADS1115` block and fill it from a datasheet, or
estimate and mark `UNVERIFIED`. A connector is a `Mating` row in
`connectors.py`; a reservoir copies the `HDX_27GAL` block in `reservoirs.py`.
Printer and material numbers live in `materials.py`.
