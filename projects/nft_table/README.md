# nft_table

One level of six Growrilla 100x50 NFT channels on a 2040/2020 table, fed by a
Little Giant PE-2.5F in an HDX 27 gal tote, plumbed in Sch 40 PVC. Every
interface whose geometry nobody publishes is a printed PETG part. Every number
in `params.py` is tagged and sourced; `validate()` passes, and the tests check the
assembly on its solids.

v1 is in `archive/nft_rack_v1/`. It ended in FAIL on caliper-gated tote fields
and on parts with unpublished geometry (the AAPW400 body, the Growrilla drain
cap, a PP collector). v2 designs around those unknowns instead of measuring them.

`DESIGN.md` has the frame, channels, supply, return and the seven printed parts
(P1 to P7).

## Status

STATUS is `passes`: `validate()` passes and the tests check the assembly on its
solids; FreeCAD positions agree with params. Nothing is built or printed. The
open items below decide the first print.

## Sources

Each value is tagged STANDARD, VENDOR, NOTES, INFERRED, DESIGN, CONVENIENCE or
PLACEHOLDER, with the document named (Misumi frame data, Spears catalogue
editions, Parker O-ring tables, Growrilla and Little Giant pages). `NOTES` is the
author's own design guidance, not independently sourced. Where a part's geometry
is unpublished, a printed PETG interface is designed around it.

## Run

```
.venv/bin/python projects/nft_table/params.py        # the design: frame, hydraulics, BOM, cut lists, tags
.venv/bin/python projects/nft_table/table.py         # build, check, out/nft_table.step
.venv/bin/python projects/nft_table/p1_saddle.py     # one part: print checks, orientation report, out/P1-*.3mf
.venv/bin/python projects/nft_table/freecad_view.py  # FreeCAD cross-check and assembly (RPC server running)
.venv/bin/python -m pytest -q projects/nft_table
```

## Open

- **Growrilla's lid holes:** the clipping says 48 mm, Growrilla's IT page says 40 mm. 48 is used.
- **The O-ring gland's FDM tolerance:** if FDM puts ±0.1 mm on the radial gland
  depth, squeeze runs 20.0–30.0 %, right on Parker's limits. The nominal is 23–27 %.
- **Cord OD and plug size are not published.** The cord bushing's 7 mm slot and the
  36 mm port are DESIGN values. The zip-tie post takes any cord.
- **P3 prints on its spout tip**, with slicer support under its exterior undersides.
- **The P5 passage prints as a pilot** and is drilled to 1/4 in after printing.
  It is the one water passage not printed vertical.
- `params.NOT_MODELLED` lists what is not drawn.
