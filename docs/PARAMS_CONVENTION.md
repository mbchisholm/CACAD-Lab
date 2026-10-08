# PARAMS_CONVENTION — one file owns every number

What worked on the cable gland (now `archive/cable_gland/`), written as the
rule, with the reason each rule exists. `docs/templates/printed/params.py.tmpl` is the skeleton (`python -m cacad.new <name>` copies it);
`projects/standoff_plate/params.py` is the live example.

## Shape of the file

```
STATUS          concept | passes | printed | parked (cacad/tests/test_project_contract.py checks it)
COMMON          family-wide rules and clearances (MappingProxyType: read-only)
SIZES           the family axis: one dict per size, inputs only
ACTIVE_SIZES    the sizes build/test actually run
derive(size)    every dimension the build scripts need, computed
validate(size)  arithmetic sanity of derive(); raises AssertionError
```

Build scripts, assembly, tests and export loops read only `derive(size)`.
Nothing downstream holds a number. If a script needs a value that
`derive()` does not provide, add it to `derive()`; do not compute it in
the script.

## Rules

1. **Inputs vs derived.** `SIZES` holds what a designer would choose; `derive`
   holds what follows. If two inputs are coupled by a formula, one of them is
   derived. Example: the standoff plate's thickness is
   `max(plate_min_t, pocket_depth + web)`, never typed, so a deeper nut
   pocket cannot leave a thin web behind.

2. **Named clearances, one field each, in COMMON.** `screw_clearance`,
   `nut_pocket_clearance`, `board_air_gap`, `boss_pin_margin`: mm, each with a
   comment saying which two surfaces it separates, and where its number comes
   from (ISO 273 plus the FDM allowance, an insert vendor's hole size, a
   published FDM fit guideline: `cacad.registries.materials`). A clearance
   folded into a diameter cannot be audited.

3. **`derive(size, **overrides)`.** Overrides replace SIZES/COMMON entries for
   what-if tables and never appear in build code. A trade-off table generated
   from the same `derive()` the build uses is worth more than any hand
   calculation.

4. **`validate()` fails, never warns.** An assertion is a claim that the part
   is buildable *and* usable. The rule that must be in every family:
   *a dimension that is not physically obtainable is a failing test.* Not
   purchasable (a screw length nobody stocks), not printable (wall < 2×
   nozzle), not assemblable (the screw tip passes the bed face) — all
   `assert`, none `print`. An unknown value is not a failure: estimate it
   (rule 5) rather than leaving it `None`.

5. **Every number says where it came from.** A number comes from a standard,
   a vendor sheet, a KiCad/Eagle file, or it is a DESIGN choice. For
   ideation, `# UNVERIFIED` on a value means "estimated: a guess, a rough
   number, a community model's figure". A part that has to fit carries a tag
   per value, `(value, TAG, source)`, and `validate()` refuses an untagged
   value (projects/nft_table is the worked example):

   ```
   STANDARD     a published standard, named (ASTM D1785, ISO 273)
   VENDOR       published by the vendor of the part used (sheet and page named)
   NOTES        the author's own design notes; not independently sourced
   INFERRED     follows from a published number, not stated (say from what)
   DESIGN       a designer's choice; the part is designed to tolerate it
   CONVENIENCE  set to draw the model; awaits derivation (design review rule 1)
   PLACEHOLDER  drawn for a part whose geometry is unknown
   ```

   A load-bearing PLACEHOLDER fails `validate()`: unbuyable or unsourced is a
   failing test. When a bought part's geometry is unpublished, design a
   printed interface that does not depend on it instead of measuring it.
   UNVERIFIED never excuses a validate() failure.

6. **ACTIVE_SIZES gates work.** Inactive sizes still pass `validate()` (their
   arithmetic is cheap and catches rule drift), but nothing builds or tests
   them until you add them. Promotion is a one-line diff.

7. **Competing requirements meet in `max()`.** A height, travel or length that
   several requirements need is `max()` of the individually derived needs,
   and `derive()` records which one governs (`standoff_governed_by`). Never
   let one requirement set a shared dimension silently.

8. **Library and bought-part facts live in COMMON with the evidence.** A
   fastener table names its standard (ISO 4032, ISO 4762); a kernel
   workaround names its FINDINGS entry. A future reader must be able to tell
   a design choice from a fact.

9. **Print orientation is data.** `PRINT_ORIENTATION[part] = {up, bed_face,
   bed_z, known_overhangs, overhang_exceptions}`. `known_overhangs` may be
   empty but must exist. Tests read it; the coupon/export code reads it.

10. **Material allowables state bulk and across-layer.** When a part flexes,
    the table holds bulk numbers, a layer factor gives the across-layer
    estimate, `derive()` reports both and `validate()` says which governs.
    (The strain table and cantilever check are in `archive/cacad_threads/`
    until a board-mount part needs them.)

11. **The `__main__` of params prints the design.** Running `python params.py`
    prints every derived number, wall, stack and which requirement governs,
    for active and inactive sizes alike — that printout is the design review
    input.

## What this convention does not do

It does not define geometry. Geometry lives in one script per part, each
reading `derive()`, each ending in its own `check_<part>()`, each applying
finish features last. It does not know about assemblies beyond the z levels
`derive()` provides; a `build_hardware()` places the bought parts and boards,
tests measure.
