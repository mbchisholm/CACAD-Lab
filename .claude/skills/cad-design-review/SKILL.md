---
name: cad-design-review
description: Review rules for parametric mechanical CAD in build123d/OCC (or any code-CAD) that catch functional defects geometric validity misses — convenience-set dimensions, unbuyable parts, orientation-dependent material margins, support on sealing faces, non-independent "verification", and stroke/travel set by one subsystem. Use only when the owner asks for a design review, or a part has to fit, seal or carry load for real (mating threads, seals, press fits, load-bearing mounts). Not for ideation, concept models, or rough-fit parts.
---

# cad-design-review

A part that has to fit or work for real. Geometry that is valid, the right
size and green in tests can still be unbuildable, unbuyable or
non-functional. Apply the rules below before reporting done. Each rule is
backed by a defect from the archived cable gland that passed every
geometric check.

## Rules

1. **Convenience is not a dimension.** Any value chosen to dodge a kernel
   problem (tangent faces, failed boolean, chamfer that would not apply) or
   rounded for tidiness is flagged in the report as "convenience-set, awaits
   derivation" and derived from its functional requirement before the part
   is called done. Ask the owner if the derived value changes the envelope.
2. **Unbuyable or unmeasurable = failing test.** If a load-bearing value could
   be looked up today (nut heights, sheet thicknesses, standard holes,
   gasket sizes) and isn't, `validate()` fails. UNVERIFIED marks design
   choices awaiting a reference part; it never marks facts.
3. **Three layers per part: geometry, manufacturability, function.** Geometry:
   valid, solid count, bbox. Manufacturability: measured walls vs nozzle
   multiples, declared orientation with the bed face verified, overhang from
   face normals with slivers excluded, orientation-dependent allowables.
   Function: mating parts placed and intersected *pairwise*, strokes measured
   on geometry (a ledge position, not an undeformed overlap), hard stops
   present, seals geometry-set, engagement with the purchased part.
4. **Shared strokes are `max()` of competing needs**, the params record which
   governs, and every dependent model is re-run with the *actual* value.
5. **State allowables as bulk vs across-layer**, the factor, and which one the
   assertion uses. Never report "passes" alone.
6. **Functional faces (sealing, bearing, mating) never print on support.**
   Fix by orientation or by self-support geometry; declare any remaining
   ceiling by name; the overhang test fails on undeclared ceilings *and* on
   declared ones that are no longer there. After adding a cone or chamfer,
   check what it removed (hard stops, wrench flats).
7. **Same kernel is not independent.** build123d and FreeCAD are both
   OpenCascade. Say so. Get independence from recomputing placement from
   params in the second tool, a different check (BOP analyzer vs BRepCheck),
   BREP-vs-STEP attribution, and a must-disagree control case.
8. **A formula fitted at one point is a hypothesis.** Validate at three or
   more points spanning the parameter before it enters params; if a later
   result contradicts it, state old rule, new rule and evidence, re-run every
   dependent test, and leave the history in the params comment.
9. **Failures are reported as failures, first.** A failed step 0 stops the
   sequence with numbers; downgraded chamfers, skipped assertions and
   fallbacks are never described as success.
10. **Budgets are itemised in the report**, including changes nobody asked
    for, with the total and any overrun.

## Working pattern

- One params file owns every number (`docs/PARAMS_CONVENTION.md`);
  `python params.py` prints the design review input.
- Bought hardware is a table with its standard named (ISO 4032, ISO 4762);
  a part that consumes it derives its pocket, bore or length from the table.
  Booleans between parts run pairwise, solid by solid (`docs/FINDINGS.md` F7);
  export one mesh per part (F15).
- Select faces/edges by geometric predicate, finish features last with
  fallback for cosmetic ones and `required=True` for functional ones.
- Deliver one size fully passing, stop, show it; extend the family only
  when the owner says.
- A section render is part of the review: the hard-stop defect was visible
  in a section and in nothing else.

## Where the evidence lives

`docs/FINDINGS.md` (kernel and tooling facts with reproductions), `cacad/` (selectors, probes,
checks, FreeCAD cross-checks), `projects/standoff_plate/` (the live worked
example), `archive/cable_gland/` (the parked project every rule above came
from; its cases are the ones in brackets).
