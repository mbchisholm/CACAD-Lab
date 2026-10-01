# FINDINGS — empirical library and kernel facts

Pinned to the versions they were observed on. Re-run the snippet in a fresh
session to see whether a later version changed the behaviour.

| component | version |
|---|---|
| Python | 3.12.9 (CPython, macOS 26.6.2, arm64) |
| build123d | 0.11.1 |
| bd_warehouse | 0.3.0 |
| cadquery-ocp-novtk (OCP) | 7.9.3.1.1 → OpenCascade 7.9.3 |
| FreeCAD | 1.1.3 (build 20260725, git 145529f) → OpenCascade **7.8.1** |
| FreeCAD RPC | freecad-mcp addon XML-RPC on 127.0.0.1:9875, `execute_code`, 90 s GUI dispatch timeout (F17) |
| KiCad / KiCadStepUp | KiCad 10.0.4, KiCadStepUp 11.09.6 |
| build123d-mcp | 0.3.84 via `uv tool run` |

Status: **CONFIRMED** = reproduced in isolation, more than once or across parameters.
**OBSERVED** = happened in the project, not isolated; the snippet is the best
available reproduction, not a proof.

Snippet convention: each prints `PASS` when the finding still holds
(i.e. the workaround is still needed) and `FIXED`/`CHANGED` otherwise.

---

## F1. `Shape.is_valid` is a property, not a method — CONFIRMED

**Symptom.** `shape.is_valid()` raises `TypeError: 'bool' object is not callable`.
**Cause.** build123d 0.11.1 declares `is_valid` with `@property` on `Shape`.
**Workaround.** Use `shape.is_valid`. Any spec that says `is_valid()` needs one edit.

```python
from build123d import Box
s = Box(1, 1, 1)
print("PASS (property)" if isinstance(type(s).is_valid, property) else "CHANGED (callable now)")
```

## F2–F6. bd_warehouse thread findings — moved to `archive/cable_gland/FINDINGS_threads.md` (2026-09-20)

Mating phase (F2), fusing a thread empties the compound (F3), `fade` end
finish overrun (F4), the 0.2 mm interference (F5) and fused-seam pcurve flags
(F6) all concern printed threads, parked with the cable gland. Numbers are
kept so cross-references in the archive still resolve.

## F7. Compound-vs-compound booleans return garbage when a compound's own solids overlap — CONFIRMED

**Symptom.** `body.intersect(nut)` where both are Compounds of overlapping
solids (core + 0.2-mm-overlapping thread) returned 1574 mm³ for parts that
do not touch; nut ± 180° both read 0.
**Cause.** OCC boolean arguments must not self-interfere; a compound whose
children overlap is an invalid argument. No error is raised.
**Workaround.** Pairwise: `sum(vol(a_i ∩ b_j))` over the solids of each part
(`cacad.interference_volume`). Same rule in FreeCAD (`Part.common`).

A toy pair of overlapping cylinders far from the other part does *not*
trigger it (returns 0); the thread compounds do, and the compound result is
the same number at the right and the wrong phase — a tell-tale for "the
boolean ignored the argument".

```python
from build123d import *
from bd_warehouse.thread import IsoThread
A = (Align.CENTER, Align.CENTER, Align.MIN)
def vol(x):
    if x is None: return 0.0
    return sum(s.volume for s in x) if isinstance(x, (list, ShapeList)) else x.volume
def thread(major, length, external, fin):
    t = IsoThread(major, 1.5, length, external=external, end_finishes=fin, interference=0.2).solids()
    return t[0].fuse(*t[1:])
r = IsoThread(20, 1.5, 10, external=True, simple=True).min_radius
bolt = Compound(children=[Cylinder(r, 10, align=A), thread(20, 10, True, ("fade", "chamfer"))])
nut = Compound(children=[Cylinder(13, 6, align=A) - Cylinder(20.3 / 2, 6, align=A), thread(20.3, 6, False, ("chamfer", "fade"))])
dz = 4.0
right = nut.rotate(Axis.Z, (dz / 1.5) * 360 + 180).moved(Location((0, 0, dz)))
wrong = right.rotate(Axis.Z, 180)
pair = lambda a, b: sum(vol(x.intersect(y)) for x in a.solids() for y in b.solids())
w_r, w_w, p_r, p_w = vol(bolt.intersect(right)), vol(bolt.intersect(wrong)), pair(bolt, right), pair(bolt, wrong)
print(f"PASS (compound {w_r:.1f}/{w_w:.1f} at right/wrong phase; pairwise {p_r:.1f}/{p_w:.1f})"
      if abs(w_r - w_w) < 1e-3 and p_r < 1e-3 and p_w > 1 else f"CHANGED ({w_r:.3f},{w_w:.3f},{p_r:.3f},{p_w:.3f})")
```

## F8. STEP round-trip adds pcurve flags that the exact BREP does not have — CONFIRMED

**Symptom.** Same part: FreeCAD BOP check flags 69 faces (body) / 7 (nut)
after STEP export+import, but 1 / 5 from the exact BREP, and 0 / 0 once the
threads are unfused. All added flags are on thread faces.
**Cause.** STEP re-approximates the helical BSpline pcurves; the importer's
tolerance is tighter than the approximation.
**Consequence.** Review STEP files for topology and interference, not for
pcurve tolerance verdicts; if the verdict matters, check the BREP.
**Reproduction.** Needs FreeCAD: check the same part from `export_brep` and
`export_step`, compare flagged-face counts.

## F9. TechDraw section view of this assembly takes FreeCAD down — OBSERVED (3×, not isolated)

**Symptom.** Creating a `TechDraw::DrawViewSection` over the helical parts:
1st attempt rendered; the next three attempts ended with FreeCAD gone
(connection refused within seconds of `doc.recompute()`), on two different
projection settings and on both fused and unfused sources. Once the section
rendered, `getVertexByIndex` returned model-unit coordinates centred on the
view with Y inverted, and dimensions matched params to 1e-3.
**Also observed.** Changing `Direction` on a live section leaves stale
geometry mixed into the vertex list (290 vs 387 vertices, impossible z);
`page.addView(view)` resets `view.X/Y` — set them after adding.
**Workaround.** None found; the drawing step was removed. Don't retry
projection variants against a crashing HLR.

## F10. FreeCAD dimensions render in the user's unit schema, not in mm — OBSERVED

**Symptom.** TechDraw dimensions showed 0.63 for a 16 mm diameter:
`FreeCAD.Units.getSchema()` returned 2 (Imperial decimal) on this machine;
`dim.getRawValue()` was still 16.0.
**Workaround (written, never rendered because of F9).** Wrap the export in
`old = FreeCAD.Units.getSchema(); FreeCAD.Units.setSchema(0); try: ... finally: FreeCAD.Units.setSchema(old)`.
Never change the user's preference permanently.

## F11. STEP import of multi-solid parts in FreeCAD: labels, nesting, local coordinates — CONFIRMED

**Symptom.** A build123d `Compound(children=[core, thread1, thread2], label="body_M16")`
imports as `App::LinkGroup "body_M16"` → per-solid `Compound2` wrappers with
labels like `=>[0:1:1:3]` → `Part::Feature "SOLID"` leaves. **Leaf shapes are
in local coordinates**; the offset (e.g. z = −12 for the panel thread) sits on
the wrapper's `Placement`. Reading leaves and assigning `.Placement` replaced
that offset (both ±180° phases read 0 interference — impossible, which is how
it was caught).
**Workaround.** For an assembly: map parts by `o.Label` for objects whose
`InList` contains the root group; use `o.Shape.Solids` of that object (already
composed). For a single-part file: the one object with empty `InList`. To move
a copied solid, `rotate`/`translate` (compose), never assign `Placement`.
**Also.** `Import.insert` into a GUI-mode document is fine; each
`execute_code` must finish inside the RPC's 90 s dispatch timeout — split
per-face checks per part.

## F12. In-process OCP cannot run the BOP CurveOnSurface check — CONFIRMED

**Symptom.** `BOPAlgo_ArgumentAnalyzer` in OCP 7.9.3 exposes `*Mode()` as
getters only (reference-returning setters are not bound), so every mode is
off and `GetCheckResult()` is empty regardless of the shape.
`BOPTools_AlgoTools.ComputeTolerance_s(face, edge)` requires float
out-parameters that the binding drops, so the deviation cannot be read.
**Workaround.** Run the check in FreeCAD (`Shape.check(True)`), whose C++
wrapper sets all modes.

```python
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
a = BOPAlgo_ArgumentAnalyzer()
setters = [m for m in dir(a) if m.startswith("Set") and m.endswith("Mode") and "Parallel" not in m]
print("PASS (no mode setters bound)" if not setters else f"CHANGED (setters: {setters})")
```

## F13. `Shape.intersect` returns `None`, a Shape, or a `ShapeList` — CONFIRMED

Handle all three when summing volumes (`cacad.volume_of`). `ShapeList`
has no `.volume`.

## F14. `Face.normal_at(u, v)` accepts parametric (u, v) in 0..1 — CONFIRMED

Used for overhang sampling on cones, BSplines and planes; equal to
`normal_at(position_at(u, v))`.

## F15. `Mesher.add_shape` writes one 3MF object per solid, so an unfused part becomes a slicer collision — CONFIRMED

**Symptom.** `coupon_plate_M16.3mf` (7 parts) loaded in Bambu Studio as 14
objects named `Object_1..Object_14`. The thread compounds were reported as
floating cantilevers, and the body core and its thread raised a gcode-path
conflict at layer 19.
**Cause.** `Mesher.add_shape` expands a `Compound` into one mesh object per
child (`shapes.extend(list(input_shape))`) and names objects from
`shape.label`, which a placed part does not carry (`part_number` only fills
the `partnumber` attribute, which slicers ignore). A slicer unions
overlapping shells *within* one object only; across objects the 0.2 mm thread
interference that F5(b) relies on reads as two objects intersecting.
**Rule.** Unfused compounds that rely on slicer union must be exported as one
mesh per part. STL export already does this (`export_stl` tessellates the
whole shape); for 3MF use `cacad.export_3mf`, which tessellates each part
whole with `Mesher._mesh_shape` and sets `name` and `partnumber` from the dict
key. The model stays unfused (F5, F7); this is an export-only change.

```python
import zipfile, tempfile, os
from build123d import *
from cacad import export_3mf
c = Compound(children=[Box(4, 4, 4), Box(4, 4, 4).moved(Location((3.8, 0, 0)))])
m = Mesher(); m.add_shape(c, part_number="part"); f1 = os.path.join(tempfile.mkdtemp(), "a.3mf"); m.write(f1)
f2 = str(export_3mf({"part": c}, f1.replace("a.3mf", "b.3mf")))
count = lambda f: zipfile.ZipFile(f).read("3D/3dmodel.model").decode().count("<mesh>")
n1, n2 = count(f1), count(f2)
print(f"PASS (add_shape wrote {n1} objects, export_3mf wrote {n2})" if n1 > 1 and n2 == 1 else f"CHANGED ({n1}, {n2})")
```

## Tooling: FreeCAD GUI, KiCad, MCP servers

These were met while wiring the tools, not while modelling. No snippet: each
needs the GUI or a board file. Dates are when they were observed.

## F16. KiCadStepUp `export_pcb` reads the GUI selection, not its argument — CONFIRMED (2026-09-16)

**Symptom.** Called with a sketch name and nothing selected in the GUI, it
stripped the whole Edge.Cuts layer from the `.kicad_pcb` and wrote nothing
back.
**Rule.** Commit the KiCad project first. `FreeCADGui.Selection.addSelection(sketch)`
before calling, and announce the push: it writes the board file.

## F17. `execute_code` has a ~90 s GUI dispatch budget — CONFIRMED (2026-09-16/17)

**Symptom.** A StepUp board load with models, or a 14 MB STEP export, times
out the synchronous RPC while FreeCAD keeps working; the GUI recovers when the
job ends.
**Rule.** One small job per call (the shape check in `cacad.freecad` sends
one part and one source per RPC). Long jobs go through `execute_code_async`
or wait on the output file. The **Start RPC Server** button in the MCP Addon
workbench must be pressed every launch; when calls fail, check that first.

## F18. Community STEP models: right envelope, wrong holes — CONFIRMED (2026-09-16)

**Symptom.** A community Arduino Uno model matched the outline and thickness
but had one hole 0.7 mm off and Ø3.5 instead of Ø3.2. Header sockets are
drawn as solid blocks, so mating pins register ~5 mm³ of "interference".
**Rule.** Community models serve for heights and collision envelopes only.
Holes and outlines come from `cacad.registries.boards`, with the source. A
few mm³ against a header block is an LOD artefact, not a collision.

## F19. `kicad-cli pcb export step` drops VRML-only components — OBSERVED (2026-09-16)

Without `--subst-models` a footprint whose only 3D model is `.wrl` vanishes
silently. KiCad 10's model path variable is `KICAD10_3DMODEL_DIR`
(`/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels`). The
headless FreeCAD binary is `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd`,
not `Contents/MacOS/FreeCADCmd`.

## F20. A boss on an engraved face leaves a void under it — CONFIRMED (2026-09-14)

An engraved outline groove (2 layers deep) cut before a boss was added left
a 0.4 mm void where the groove crossed the boss footprint. Start the boss
below the groove floor (`projects/mount_plate/mount_plate.py`) or engrave
last.

## F21. build123d-mcp `render_view` at the default angle can hide a feature — OBSERVED (2026-09-14)

One iso render dropped a whole hole pattern. Render two angles and confirm
with `find_holes` or a probe (`cacad.assert_material`); never sign off on one
image.

## F22. Embossed text under ~4 mm or non-bold prints as noise — OBSERVED (2026-09-14)

Stroke width falls under one extrusion width. Bold, >= 4 mm, three layers
tall (`coupons/fdm_coupon.py` `label()`).

## F23. build123d-mcp rejects blocked imports anywhere in the file, including under `__main__` — CONFIRMED (2026-09-17)

**Symptom.** `execute_file` on a part whose `__main__` block did
`from pathlib import Path` failed with `SecurityError: Import of 'pathlib'
is not allowed` although that block never runs in the sandbox.
**Cause.** `session.check_ast` walks the whole source with `ast.walk` and
rejects `Import`/`ImportFrom` nodes for `os`, `pathlib`, `sys`, `subprocess`
and the network modules wherever they appear. The allow list
(`--allow-imports`) is matched on the top-level module name only, so a
package on the list may import those modules internally.
**Rule.** A part file names no filesystem module. It computes its output
folder as a string (`__file__.rsplit("/", 1)[0] + "/out"`) and calls
`cacad.export(part, name, out_dir)`, which creates the folder; `pathlib`
and `sys` are imported inside `cacad.export`'s functions, not at module
level, so `import cacad` stays sandbox-clean. `types` (for
`MappingProxyType`) has to be on the allow list.

---

## F24. build123d-mcp rejects a part file's sibling `import params` — CONFIRMED (2026-09-20)

**Symptom.** `execute_file` on `projects/standoff_plate/plate.py` failed with
`SecurityError: Import of 'params' is not allowed` although the file was
otherwise sandbox-clean (F23).
**Cause.** The allow list is matched on the top-level module name, and the
project folder is not on the sandbox's `sys.path`, so `import params` is
neither allowed nor resolvable. `projects` is on the list, but until now it
was importable only when the cwd happened to be the repo root: the editable
install mapped `cacad` alone.
**Rule.** `pyproject.toml` installs `projects*` and `coupons*` editable too
(namespace packages, no `__init__.py`), and a part file imports its params as
`from projects.<name>.params import derive`; tests do the same and need no
`sys.path` insert in conftest. The archived gland's files (`import params`,
`import sys`, `common.py` with `pathlib`) predate this and do not run in the
sandbox; `tools/verify_mcp.py` was only ever used on the flat scripts.

## F25. build123d-mcp keeps imported project modules for the life of the server — CONFIRMED (2026-09-20)

**Symptom.** After editing `projects/standoff_plate/params.py`, `execute_file`
on `plate.py` failed with `KeyError: 'tray'` (a key the new file defines).
`reset` did not help; `importlib` is blocked in `execute`.
**Cause.** The sandbox imports `projects.<name>.params` into the server
process's module cache once; `reset` clears session objects, not
`sys.modules`.
**Rule.** After editing any module a part file imports, restart the MCP
server (or the session) before `execute_file`, or render the exported STEP
through `import_cad_file`, which reads the file and needs no import. The
exported STEP is also what the slicer sees, so it is the better thing to
look at anyway.

## F26. FreeCAD `Shape.BoundBox` is loose on torus and cut-cylinder faces — CONFIRMED (2026-09-30)

**Symptom.** `projects/nft_rack/freecad_view.py` compared each imported part's
world `BoundBox` with params' analytic envelope. The 104 planar parts agreed to
0.05 mm and all 144 volumes agreed to 0.1 %, but every swept feed tube was
2.45 mm too large at its two bends (Y and Z max) and every drain stub, a
cylinder cut by the 1:40 floor plane, was 0.08 mm too tall.
**Cause.** `BoundBox` adds the extent of the surface's construction (torus,
the elliptical cut edge) rather than the trimmed face. `Shape.optimalBoundingBox(False, False)`
on the same shapes gives params' numbers to 0.001 mm; build123d's
`bounding_box()` was already optimal.
**Rule.** A FreeCAD position check uses `optimalBoundingBox(False, False)`,
not `BoundBox`, whenever a part has a non-planar face. An axis-aligned box
part is unaffected, which is why `tote_rack` never saw it.

## F27. build123d-mcp `import_cad_file` failed on a STEP in `~/Downloads` with spaces in its name — OBSERVED (2026-09-30)

**Symptom.** `import_cad_file("/Users/.../Downloads/hydroponic NFT system.STEP")`
returned `Error executing tool import_cad_file` with no message. A copy at a
space-free path in the session scratchpad imported (228 solids).
**Cause.** Not isolated: the path had spaces *and* sat outside the working
directory; either may be the trigger.
**Rule.** Copy an external STEP to a space-free path under the repo
(a project's gitignored `ref/`) or the scratchpad before importing it.

## TODO — data that only printed coupons can supply

Nothing below is settled. FINDINGS entries above are geometry/kernel facts;
these are manufacturing facts and have **no measurement yet**.

- [ ] **Hole clearance, insert bore, shrinkage** (`python coupons/fdm_coupon.py` →
  `coupons/out/fdm_coupon.stl`: five M5 clearance holes 5.10..5.30, five M3
  heat-set insert bores 3.8..4.2 × 6 deep on a raised pad, one 20 mm cube;
  PETG, 0.4 nozzle, labelled and dated). Fill in:

  | measurement | result |
  |---|---|
  | smallest hole an M5 screw slips through freely → `CLEAR_SLIP` (now 0.20, guess) | |
  | smallest hole that takes the screw with clearance for misalignment → `CLEAR_LOOSE` (now 0.40, guess) | |
  | bore the M3 insert seats in without splitting the boss → `INSERT_BORE_M3` (now 4.00, guess) | |
  | cube X / Y / Z vs 20.00 → shrinkage | |

  Replace the three values in `cacad/registries/materials.py` and date the change.
  Nothing prints for fit until this row is filled.
- [ ] Sliver exclusion threshold (`nozzle_d²`) and the 60° flank acceptance
  are slicer-side assumptions, not measured.
- [ ] **Slicer settings: brim and stringing.** On the cable gland's first
  print the brim made the threaded parts hard to fit together, and the
  covers tested showed stringy overlap. Not measured, and the settings used
  were not recorded. Before the next fit print, record the Bambu Studio
  profile (brim type and gap, retraction, travel, temperature), and check
  whether any mating face touches the bed where a brim would sit.
