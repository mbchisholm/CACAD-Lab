# Parametric panel-mount cable gland

M16×1.5, three printed mating parts plus TPU seal sleeves, a bought DIN 439 B
locknut and a flat gasket. M12 and M20 are in `params.SIZES`, arithmetically
valid, marked UNVERIFIED and not built (see Status). This is the project the
rules in `CLAUDE.md` and most of `docs/FINDINGS.md` came from.

| part | role | material |
|---|---|---|
| body | panel thread, gasket recess with compression-stop foot, hex, neck thread, collet seat | PETG |
| collet | rigid seat for the insert: base ring, 8 mm fingers (t 1.4), 15° tip taper | PETG |
| insert ×2 | TPU 95A sleeves, the seal; the nut ledge squeezes them axially (19.7 %) | TPU |
| nut | internal thread, relief, 15° cone (finger preload), flat ledge (insert), exit bore | PETG |
| locknut | DIN 439 B M16×1.5, 8 mm — bought | steel |

```
params.py    family axis (SIZES), family-wide rules (COMMON), derive(size), validate(size)
common.py    OUT_DIR, export with this project's default folder, assert_walls (reads the params dict)
body.py      panel thread + gasket flange (recess, compression-stop foot) + hex + neck thread + seat
collet.py    slotted ring, stepped bore, short taper
insert.py    TPU 95A seal sleeve, one per cable sub-range (IDs derived in params)
nut.py       hex + dome; internal thread, relief, cone, insert ledge, exit bore
assembly.py  places the parts; computes the thread phase that mates nut onto body
build.py     builds ACTIVE_SIZES, checks, exports STEP + STL to out/
coupon.py    clearance-ladder print plate: body, five nuts at 0.15..0.45 mm, collet -> one 3MF
tests/       21 pytest checks: mating, stroke, printability, orientation, overhang, strain
tools/verify_in_freecad.py   shape check + pairwise interference in FreeCAD (cacad.freecad)
```

Everything generic (selectors, thread helpers, probes, pairwise booleans,
export, printability checks) is imported from `cacad`.

## Run

From the repo root:

```
.venv/bin/python projects/cable_gland/params.py          # arithmetic check of every size, no geometry
.venv/bin/python projects/cable_gland/body.py M16 --show # one part, optional ocp-vscode viewer
.venv/bin/python projects/cable_gland/build.py           # all active sizes -> out/
.venv/bin/python projects/cable_gland/coupon.py M16      # out/coupon_plate_M16.3mf, 7 named objects
.venv/bin/python -m pytest projects/cable_gland -q
.venv/bin/python projects/cable_gland/tools/verify_in_freecad.py M16   # FreeCAD RPC up; exit 0 = agrees
```

Known FreeCAD result on M16: exact BREPs are clean (0 BOP flags on every
solid). A STEP round-trip adds `InvalidCurveOnSurface` on a handful of thread
faces (F8); nothing else. Interference volumes match build123d to 4 decimals,
including the by-design overlaps at the hard stop.

## How it is built

- Z is the gland axis, Z=0 is the panel's outer face = the foot ring. The
  gasket sits in a recess above it, `standoff` deep (gasket_t × (1 −
  compression)); the foot stops compression there. Panel thread to −Z, nut to
  +Z. Panel thread length is derived: panel_max + locknut_h + spare, rounded
  up to 0.5.
- Parts are Compounds: a finished core solid plus unfused thread solids that
  overlap it by `thread_interference` (F5, F6). Booleans between parts are
  done solid-by-solid (F7). The 3MF exports one mesh per part so the slicer
  unions the overlap instead of reporting a collision (F15).
- Nominal assembled position: nut seated at first contact (cone on the collet
  taper, ledge on the insert top) with `nut_travel` of tightening left.
  `nut_travel = max(collet_seat_travel, insert_compression_travel)`; the hard
  stop is the nut's bottom face on the hex top.
- The insert is the seal: the nut ledge squeezes it axially by `nut_travel`
  and it bulges onto the cable. The collet fingers close by
  `collet_tip_deflection` on top of that; `finger_tradeoff_table()` shows what
  length and thickness buy. Insert IDs come out of `derive()["insert_coverage"]`.
- Body prints neck-down so the sealing faces face up. The flange is a 45°
  frustum and the hex neck side is a 45° cone from a 1 mm hard-stop ring; the
  seat floor and that ring are the declared ceilings (`PRINT_ORIENTATION`),
  and the overhang test fails on any other.

## Open questions

1. Printed thread fit at 0.3 mm modelled clearance — the coupon plate.
2. Collet root strain 2.17 % across PETG layers against an *estimated*
   allowable of 2.25 % — the coupon, and it may say no.
3. Insert count (2) rests on a first-order bulge model at 19.7 % compression —
   squeeze a printed insert.
4. Hard stop is a 1.35 mm flat ring on the hex top (declared ceiling); the
   fully self-supporting alternative is a countersunk nut seat at +2 mm.
5. All M12/M20 values; all cable ranges; hex AF, neck thread and thread
   lengths against a catalogue gland.
6. Height above panel 30.3 mm vs ~22 for a commercial M16 — the insert stack
   and 13 mm thread are the cost of printability and a bought nut.

## Status

M16 built, checked, tested. **M12/M20 are blocked** by the F5 gate: the
fused-thread behaviour is size-dependent, and the unfused route must be shown
clean at those sizes (FreeCAD BOP + pairwise checks) before they are
activated. Next physical step: print `out/coupon_plate_M16.3mf` and fill in
the TODO tables at the end of `docs/FINDINGS.md`.

First print (observed, not measured): the brim made the threaded parts hard
to fit together, and the covers tested had stringy overlap. Both point at
slicer settings rather than geometry; see the slicer-settings item in the
TODO list at the end of `docs/FINDINGS.md`.
