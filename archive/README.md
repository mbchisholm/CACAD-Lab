# archive

Parked work. Kept for its numbers, findings and the rules it produced; not
installed, not collected by pytest, not on the README's main path.

`cable_gland/` (parked 2026-09-20): an M16 panel-mount cable gland with
printed threads, slotted collet and TPU seal inserts, plus its coupon plate,
FreeCAD verification tool, tests and thread findings (`FINDINGS_threads.md`,
F2–F6). Its M16 was printed and did not fit; the thread-clearance coupon was
never measured. Sidelined because printed threads and seals are a different
problem from mounting boards.

`cacad_threads/`: the `cacad` modules the gland needed and nothing else does:
`threads.py` (bd_warehouse IsoThread helpers), `geometry.py` (ISO core
radius, hex across corners, clamp force), `cantilever.py` and
`materials_strain.py` (finger root strain against a bulk/across-layer
allowable), `probes_thread.py` (`assert_thread_present`).

To run the gland again: `uv pip install -e ".[archive]"`, copy the
`cacad_threads/` modules back into `cacad/` (restore the `__init__` exports
and `cacad.registries.materials` strain table), and run it from
`archive/cable_gland/` with its own `import params` style. It predates F23
and F24, so it does not run in the build123d-mcp sandbox.

`nft_rack_v1/` (parked 2026-10-01): the first NFT table and the AM Hydro
multi-level layout. Its `nft_table` layout ended in FAIL on unpublished
parts (AAPW400 body, Growrilla drain cap, PP collector margin) and caliper
gates on the tote. Superseded by `projects/nft_table/`; its leg formulas
moved to `cacad/plumbing.py`. Its imports of `projects.nft_rack.*` no
longer resolve: read it, do not run it.

`mount_plate/` (parked 2026-10-07): the first board-registry plate and tray.
Valid solids that would not hold the board; `REVIEW.md` lists why.
Replaced by `projects/standoff_plate/`.

`enclosure_atlas/` (parked 2026-10-07): a spec-only enclosure for Atlas EZO
circuits, gated on caliper measurements. No geometry. Superseded by
`projects/nutrient_controller/`.
