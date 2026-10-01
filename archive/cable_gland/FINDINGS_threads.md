# Thread findings — parked with the cable gland (2026-09-20)

Moved out of `docs/FINDINGS.md` when the printed-thread work was sidelined.
Same version table and status conventions as that file. F1 and F7–F24 stay
there; these numbers are kept so references in this folder still resolve.

---

## F2. IsoThread internal-on-external mating phase — CONFIRMED

**Symptom.** A nut built with `IsoThread(external=False)` placed on a bolt
built with `IsoThread(external=True)` interferes unless rotated by a specific
angle; the angle depends on the axial offset.
**Cause.** Both threads start their helix at their own z=0 with the same
angular phase, so tooth lands on tooth. The internal must be rotated so its
tooth lands in the groove (180°) plus the helix advance for the axial shift.
**Rule.** With the internal thread moved up by `dz`:
`rotate about Z by +(dz / pitch) * 360 + 180` degrees.
Verified at dz = 4.0, 3.3, 1.7 mm (M20×1.5, 0.3 mm diametral clearance):
zero interference over ~160–200°, independent of major diameter and end finishes.
**Derivation history (why three points).** A one-point scan at dz = 2.0 gave
zero at 300°, which fits both `-(dz/P)*360 + 60` and `+(dz/P)*360 + 180`. The
first was adopted and failed at dz = 4.0 (51 mm³). One offset cannot
distinguish the sign; three can. See MISTAKES.md #1.

```python
from build123d import *
from bd_warehouse.thread import IsoThread
A = (Align.CENTER, Align.CENTER, Align.MIN)
def vol(x):
    if x is None: return 0.0
    return sum(s.volume for s in x) if isinstance(x, (list, ShapeList)) else x.volume
ext = IsoThread(20, 1.5, 10, external=True,  end_finishes=("chamfer", "fade"))
bolt = Cylinder(ext.min_radius, 10, align=A) + ext.solids()[0].fuse(*ext.solids()[1:])
it  = IsoThread(20.3, 1.5, 6, external=False, end_finishes=("chamfer", "fade"))
nut = (Cylinder(13, 6, align=A) - Cylinder(20.3/2, 6, align=A)) + it.solids()[0].fuse(*it.solids()[1:])
ok = True
for dz in (1.7, 3.3, 4.0):
    n = nut.rotate(Axis.Z, (dz/1.5)*360 + 180).moved(Location((0, 0, dz)))
    bad = nut.rotate(Axis.Z, (dz/1.5)*360).moved(Location((0, 0, dz)))
    ok &= vol(bolt.intersect(n)) < 1e-3 and vol(bolt.intersect(bad)) > 1.0
print("PASS (rule holds at 3 offsets)" if ok else "CHANGED")
```

## F3. Fusing a multi-solid IsoThread onto a body silently returns an empty Compound — CONFIRMED

**Symptom.** `body + iso_thread` returns a `Compound` with `len(solids()) == 0`
and `_dim is None`; the next `-` raises
`ValueError: Dimensions of objects to subtract from are inconsistent`.
Seen with a chamfer-ended external thread fused onto (hex prism + core
cylinder). Same thread onto the bare core cylinder works. `('fade','fade')`
works; `('chamfer',*)`, `('square',*)`, `('raw',*)` tops fail.
**Cause.** `IsoThread` is a Compound of one solid per turn; `Shape.fuse`
passes all of them to one `BRepAlgoAPI_Fuse`, which fails without raising.
**Workaround.** Fuse the turns together first (they fuse cleanly), then use
that single solid: `turns[0].fuse(*turns[1:])` — `cacad.solid_thread`.

```python
from build123d import *
from bd_warehouse.thread import IsoThread
A = (Align.CENTER, Align.CENTER, Align.MIN)
hexp = extrude(RegularPolygon(12 / 0.8660254, 6), 5).moved(Location((0, 0, 1.5)))
th = IsoThread(20, 1.5, 10, external=True, end_finishes=("fade", "chamfer"))
core = Cylinder(th.min_radius, 10, align=A).moved(Location((0, 0, 6.5)))   # exact root radius (see F5)
th = th.moved(Location((0, 0, 6.5)))
direct = hexp + core + th
turns = th.solids(); one = turns[0].fuse(*turns[1:])
via_solid = hexp + core + one
print("PASS (direct fuse empty, solid_thread ok)" if len(direct.solids()) == 0 and len(via_solid.solids()) == 1
      else f"CHANGED (direct={len(direct.solids())}, via_solid={len(via_solid.solids())})")
```

## F4. `end_finishes=('fade','square')` external thread overruns its length — CONFIRMED (cause not isolated)

**Symptom.** `IsoThread(20, 1.5, 10, external=True, end_finishes=('fade','square'))`
fused on a core has bbox z max 11.31, not 10.0. `('chamfer','square')`,
`('chamfer','fade')`, `('fade','chamfer')` stay within 0..10.
**Cause.** Not isolated. The 'square' end is meant to clip at z=length; with a
'fade' bottom the clip does not happen for the last loop.
**Workaround.** Do not use 'square' with a 'fade' partner; use chamfer/fade.

```python
from build123d import *
from bd_warehouse.thread import IsoThread
A = (Align.CENTER, Align.CENTER, Align.MIN)
th = IsoThread(20, 1.5, 10, external=True, end_finishes=("fade", "square"))
p = Cylinder(th.min_radius, 10, align=A) + th.solids()[0].fuse(*th.solids()[1:])
z = p.bounding_box().max.Z
print(f"PASS (overrun to z={z:.2f})" if z > 10.05 else "FIXED (stays within length)")
```

## F5. `thread_interference=0.2` is load-bearing; do not zero it — CONFIRMED

**Symptom / cause, two regimes.**
(a) *Fused:* with `interference=0.0` the thread root cylinder is coincident with
the core cylinder; `+` gives 2 solids and an invalid shape; `fuse(glue=True)`
gives 1 invalid solid (FreeCAD agrees). With 0.2 the fuse works but leaves
48 sliver faces (< 0.02 mm²) and pcurve-tolerance flags where the sweep seams
cross the core (F6).
(b) *Unfused compound (chosen):* the thread solid overlaps the core by 0.2 so a
slicer unions the two shells; at 0.0 the shells only touch, which can leave
hairline slits after tessellation.
**Workaround.** Keep 0.2 (the bd_warehouse default), keep threads as separate
solids in a Compound, do booleans pairwise (F7).
**Knife-edge note.** The core radius must be exactly `IsoThread.min_radius`
(9.188101183952089 for M20×1.5). With 9.188 — 0.1 µm smaller — the
`interference=0.2` fuse returns an *empty* compound (F3 behaviour), the
`interference=0` fuse "succeeds" with a 0.1 µm shell, and glue fuse gives
2 solids. The fuse outcome flips on a sub-tolerance radius change; the
unfused compound does not have this sensitivity.

**Size dependence (2026-09-17, same snippet at four majors, exact `min_radius`, pitch 1.5, length 10):**

| major | `interference=0` fuse | glue fuse | `interference=0.2` fuse |
|---|---|---|---|
| M12 | 1 solid, **invalid** | invalid | 1 valid solid, 49 slivers |
| M16 | 1 solid, **valid** ← inverts | invalid | 1 valid solid, 48 slivers |
| M20 | 2 solids, **invalid** | invalid | 1 valid solid, 48 slivers |
| M24 | 1 solid, **invalid** | invalid | 1 valid solid, 49 slivers |

The `interference=0` branch inverts at M16: the fused route has no
size-independent behaviour even at the exact radius. The 0.2 fuse and the
glue failure are consistent across sizes. The production route (unfused
compound, F5b) performs no fuse and so is unaffected *by construction*, but
that has only been demonstrated at M16 (0 BOP flags in FreeCAD, pairwise
booleans agree).

**GATE — family extension to M12/M20 is BLOCKED** until one of:
(a) the unfused-compound route is shown size-independent: build the M12 and
M20 parts, run the FreeCAD exact-BREP BOP check (F6/F8) and the pairwise
interference checks (F7) on them, 0 flags and agreement required; or
(b) a fuse strategy that gives the same outcome at all four majors.
(a) is the expected path; it is a check, not a redesign.

```python
from build123d import *
from bd_warehouse.thread import IsoThread
A = (Align.CENTER, Align.CENTER, Align.MIN)
r = IsoThread(20, 1.5, 10, external=True, simple=True).min_radius   # exact root radius
core = Cylinder(r, 10, align=A)
def one(i):
    t = IsoThread(20, 1.5, 10, external=True, end_finishes=("fade", "chamfer"), interference=i).solids()
    return t[0].fuse(*t[1:])
f0 = core + one(0.0); g0 = core.fuse(one(0.0), glue=True); f2 = core + one(0.2)
sliv = sum(1 for f in f2.faces() if f.area < 0.16)
print("PASS (i=0 fuse broken, i=0.2 fuses with slivers)" if (len(f0.solids()) != 1 or not f0.is_valid)
      and not g0.is_valid and len(f2.solids()) == 1 and sliv > 10 else f"CHANGED ({len(f0.solids())},{f0.is_valid},{g0.is_valid},{len(f2.solids())},{sliv})")
```

## F6. Fused thread seams: `InvalidCurveOnSurface` that no fixer clears — CONFIRMED

**Symptom.** FreeCAD `Shape.check(True)` (BOP argument analyzer) flags
`BOPAlgo_InvalidCurveOnSurface` on 1 body face / 5 nut faces of the exact
BREP of fused parts, always where a thread flank or root meets the
core/bore cylinder. `BRepCheck` says valid. No self-intersections.
**Cause.** The intersection edges of the swept flank surfaces with the
cylinder get pcurves that deviate from their 3D curves by more than the edge
tolerance. Tried and failed to clear it: `Shape.clean()`, `Shape.fix()`,
`BRepLib.SameParameter(shape, 1e-5, True)`, glue fuse, cutting the
opposite-type thread solid as a groove (worse: 14 flags, and it shifts the profile).
**Workaround.** Don't fuse: `Compound([core, thread_solid])` — 0 flags on the
exact BREP for every part.
**Reproduction.** Needs FreeCAD: export BREP via `export_brep`, then in FreeCAD
`Part.Shape().read(path)` and `f.check(True)` per face. In-process OCP cannot run
this check (F12).


## TODO — coupon data the gland was waiting on

- [ ] **Printed thread fit — clearance ladder** (`python projects/cable_gland/coupon.py` →
  `projects/cable_gland/out/coupon_plate_M16.3mf`: one body, five nuts embossed with their
  diametral `thread_clearance`, one collet; PETG, 0.4 nozzle). Fill in per nut:

  | clearance | starts by hand? | runs full 6 mm? | drag (none / light / binds) | wobble at seated? | notes |
  |---|---|---|---|---|---|
  | 0.150 | | | | | |
  | 0.225 | | | | | |
  | 0.300 (production) | | | | | |
  | 0.375 | | | | | |
  | 0.450 | | | | | |

  Result to record: the smallest clearance that runs freely → new
  `COMMON["thread_clearance"]`; whether the panel thread takes a DIN 439 B
  M16×1.5 nut by hand (steel nut on printed external thread, 0.0 modelled
  clearance on that side beyond the ISO profile); printer, layer height,
  material lot. Until then `thread_clearance = 0.3` is a modelling
  assumption, not a printed one.
- [ ] **Collet finger root strain across layer lines in PETG** (the collet on
  the same plate). Model: L 8.0, t 1.40, δ 0.66 → 2.17 % root strain against a
  bulk allowable of 4.5 % and an across-layer *estimate* of 2.25 % (factor
  0.5, assumed). Fill in:

  | test | result |
  |---|---|
  | fingers deflect 0.66 mm radially (press between flats) without whitening | |
  | survives 10 × full nut travel (2.46 mm) in the printed body + nut | |
  | crack location if any (root at base ring / mid-finger / tip) | |
  | derived: `layer_adhesion_factor` to replace 0.5 | |

  The 0.5 factor and the 4.5 % bulk number are both unverified inputs.
- [ ] **Insert compression model.** 2 inserts come from a volume-conservation
  bulge model at 19.7 % actual axial compression; no printed TPU insert has
  been squeezed.
