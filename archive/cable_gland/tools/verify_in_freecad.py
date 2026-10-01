#!/usr/bin/env python
"""Independent verification of a gland size in FreeCAD, via the FreeCAD RPC
server (`cacad.freecad`: freecad-mcp XML-RPC on 127.0.0.1:9875).

    .venv/bin/python tools/verify_in_freecad.py [M16]

1. Shape check: import out/gland_<size>_assembly.step, run BRepCheck
   (Shape.isValid) and the BOP argument check (Shape.check(True)) on every
   solid and every face. Flagged faces are classified as thread-region or
   not. The same check is run on exact BREPs written by build123d so STEP
   round-trip artefacts can be told apart from native defects.
2. Interference: import body + nut STEP separately, place the nut in FreeCAD
   from params (phase + z), Part boolean common, compare the volume with
   build123d's own result. Mismatch -> exit code 2 and STOP.
There is no drawing step: creating a TechDraw section of this assembly took
FreeCAD down three times (2026-09-16/17), and the five dimensions it produced
the one time it rendered already matched params.

Exit code 0 = all agree, 1 = shape check found a real defect, 2 = interference
mismatch.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import params  # noqa: E402
from assembly import place_nut  # noqa: E402
from body import BODY_SOLIDS, build_body  # noqa: E402
from collet import build_collet  # noqa: E402
from cacad import interference_volume  # noqa: E402
from cacad.freecad import FreeCADRPC, check_part, summarize  # noqa: E402
from common import OUT_DIR  # noqa: E402
from insert import build_insert  # noqa: E402
from nut import NUT_SOLIDS, build_nut  # noqa: E402

EXPECTED_SOLIDS = dict(body=BODY_SOLIDS, nut=NUT_SOLIDS, collet=1, insert=1)


def hdr(title: str):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 1. Shape check
# ---------------------------------------------------------------------------
def shape_check(fc: FreeCADRPC, size: str, d: dict, parts: dict) -> bool:
    hdr("1. FreeCAD shape check (BRepCheck + BOP argument analyzer)")
    ti = d["thread_interference"]
    thread_bands = [
        ("panel thread", d["panel_core_r"] - ti, d["thread_major"] / 2, -d["panel_thread_len"], 0.0),
        ("neck thread", d["neck_core_r"] - ti, d["neck_major"] / 2, d["hex_top_z"], d["neck_top_z"]),
        ("nut thread", params.iso_core_radius(d["nut_thread_major"], d["pitch"]),
         d["nut_bore_r"] + d["thread_interference"], 0.0, d["nut_hex_h"]),
        ("nut thread (assembled)", params.iso_core_radius(d["nut_thread_major"], d["pitch"]),
         d["nut_bore_r"] + d["thread_interference"], d["nut_z"], d["nut_z"] + d["nut_hex_h"]),
    ]
    asm = OUT_DIR / f"gland_{size}_assembly.step"
    rep = {name: check_part(fc, part, f"{name}_{size}", asm, OUT_DIR, thread_bands, root_label=f"gland_{size}")
           for name, part in parts.items()}

    ok = True
    total_flags = 0
    for source in ("step", "brep"):
        print(f"\n  [{source.upper()}]")
        for name, part in parts.items():
            r = rep[name][source]
            good, line = summarize(r, EXPECTED_SOLIDS[name], round(sum(so.volume for so in part.solids()), 3))
            print(f"  {name + '_' + size:12s} {line}")
            ok &= good
            total_flags += len(r["faces"])
    print("\n  Verdict:", ("clean: no BOP flags on any solid" if total_flags == 0 else
                           "no self-intersections, no invalid faces; only InvalidCurveOnSurface (pcurve tolerance) on thread faces")
          if ok else "REAL DEFECT FOUND - see above")
    return ok


# ---------------------------------------------------------------------------
# 2. Interference
# ---------------------------------------------------------------------------
COMMON_CODE = r'''
import FreeCAD, Part, Import, json, math
D = json.loads(%(d)r)
def load(path):
    """All solids of a single-part STEP (core + unfused threads), in world
    coordinates: taken from the root object's shape, because STEP leaves
    keep their solids in local coordinates with the offset on the parent."""
    doc = FreeCAD.newDocument("cmn")
    Import.insert(path, doc.Name)
    doc.recompute()
    roots = [o for o in doc.Objects if getattr(o, "Shape", None) is not None and not o.InList]
    assert len(roots) == 1, "expected one root object in " + path
    solids = [so.copy() for so in roots[0].Shape.Solids]
    FreeCAD.closeDocument(doc.Name)
    return solids
def common_vol(a_solids, b_solids):
    """Pairwise: the parts' own solids overlap each other by design, so a
    compound-vs-compound boolean is not a valid OCC argument."""
    return round(sum(sa.common(sb).Volume for sa in a_solids for sb in b_solids), 6)
def placed(solids, z, rot_deg=0.0):
    """Compose with whatever placement the STEP leaves carry (assigning
    .Placement would replace it)."""
    out = []
    for so in solids:
        c = so.copy()
        c.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), rot_deg)
        c.translate(FreeCAD.Vector(0, 0, z))
        out.append(c)
    return out
body = load(D["body_step"]); nut = load(D["nut_step"]); collet = load(D["collet_step"]); ins = load(D["insert_step"])
out = {}
out["seated"] = common_vol(body, placed(nut, D["nut_z"], D["phase"]))
out["seated+180"] = common_vol(body, placed(nut, D["nut_z"], D["phase"] + 180.0))
tight = placed(nut, D["nut_z"] - D["nut_travel"], D["phase_tight"])
out["tight_body_nut"] = common_vol(body, tight)
out["tight_nut_insert"] = common_vol(tight, placed(ins, D["insert_z"]))
out["tight_nut_collet"] = common_vol(tight, placed(collet, D["collet_z"]))
# the assembly STEP already carries build123d's placement: cross-check that too
doc = FreeCAD.newDocument("asm"); Import.insert(D["assembly_step"], doc.Name); doc.recompute()
objs = {o.Label: o.Shape.Solids for o in doc.Objects
        if getattr(o, "Shape", None) is not None and any(p.Label == D["root_label"] for p in o.InList)}
out["assembly_step"] = common_vol(objs[D["body_label"]], objs[D["nut_label"]])
out["assembly_step_collet_body"] = common_vol(objs[D["body_label"]], objs[D["collet_label"]])
out["assembly_step_collet_nut"] = common_vol(objs[D["nut_label"]], objs[D["collet_label"]])
out["assembly_step_insert_nut"] = common_vol(objs[D["nut_label"]], objs[D["insert_label"]])
out["assembly_step_insert_collet"] = common_vol(objs[D["collet_label"]], objs[D["insert_label"]])
FreeCAD.closeDocument(doc.Name)
print("JSON:" + json.dumps(out))
'''


def interference_check(fc: FreeCADRPC, size: str, d: dict, parts: dict) -> bool:
    hdr("2. Independent interference (FreeCAD Part.common vs build123d intersect)")
    from assembly import place_collet, place_insert
    from insert import insert_name
    b123d_seated = interference_volume(parts["body"], place_nut(parts["nut"], d))
    b123d_wrong = interference_volume(parts["body"], _rot180(place_nut(parts["nut"], d)))
    tight = place_nut(parts["nut"], d, extra_travel=d["nut_travel"])
    b123d_tight_insert = interference_volume(tight, place_insert(parts["insert"], d))
    b123d_tight_collet = interference_volume(tight, place_collet(parts["collet"], d))
    dz_tight = d["hex_top_z"] - d["hex_top_z"]  # nut bottom on hex top
    payload = dict(body_step=str(OUT_DIR / f"body_{size}.step"), nut_step=str(OUT_DIR / f"nut_{size}.step"),
                   collet_step=str(OUT_DIR / f"collet_{size}.step"),
                   insert_step=str(OUT_DIR / f"{insert_name(size, d['insert_ids'][0])}.step"),
                   assembly_step=str(OUT_DIR / f"gland_{size}_assembly.step"), root_label=f"gland_{size}",
                   phase=d["nut_phase_deg"], nut_z=d["nut_z"], nut_travel=d["nut_travel"],
                   phase_tight=(dz_tight / d["pitch"]) * 360 + d["thread_phase_offset_deg"],
                   insert_z=d["insert_z"], collet_z=d["collet_z"],
                   body_label=f"body_{size}", nut_label=f"nut_{size}", collet_label=f"collet_{size}",
                   insert_label=f"insert_{size}")
    t = time.time()
    r = fc.run(COMMON_CODE % dict(d=json.dumps(payload)), "Part.common")
    print(f"  nut placed in FreeCAD: z={d['nut_z']:.3f}  rotZ={d['nut_phase_deg']:.1f} deg   ({time.time() - t:.1f}s)")
    print(f"  {'':22s}{'FreeCAD':>12s}{'build123d':>12s}")
    print(f"  {'body∩nut seated':22s}{r['seated']:12.4f}{b123d_seated:12.4f}")
    print(f"  {'body∩nut seated+180':22s}{r['seated+180']:12.4f}{b123d_wrong:12.4f}")
    print(f"  {'body∩nut hard stop':22s}{r['tight_body_nut']:12.4f}")
    print(f"  {'nut∩insert hard stop':22s}{r['tight_nut_insert']:12.4f}{b123d_tight_insert:12.4f}   (axial squeeze, by design)")
    print(f"  {'nut∩collet hard stop':22s}{r['tight_nut_collet']:12.4f}{b123d_tight_collet:12.4f}   (finger preload, by design)")
    print(f"  {'body∩nut (asm STEP)':22s}{r['assembly_step']:12.4f}")
    print(f"  {'body∩collet (asm STEP)':22s}{r['assembly_step_collet_body']:12.4f}")
    print(f"  {'nut∩collet (asm STEP)':22s}{r['assembly_step_collet_nut']:12.4f}")
    print(f"  {'nut∩insert (asm STEP)':22s}{r['assembly_step_insert_nut']:12.4f}")
    print(f"  {'collet∩insert (asm STEP)':22s}{r['assembly_step_insert_collet']:12.4f}")
    tol = d["volume_tol"]
    rel = lambda a, b: abs(a - b) <= max(0.02 * abs(b), tol)
    agree = (abs(r["seated"] - b123d_seated) <= tol and r["seated"] <= tol and r["assembly_step"] <= tol
             and r["tight_body_nut"] <= tol
             and r["assembly_step_collet_body"] <= tol and r["assembly_step_collet_nut"] <= tol
             and r["assembly_step_insert_nut"] <= tol and r["assembly_step_insert_collet"] <= tol
             and rel(r["seated+180"], b123d_wrong) and rel(r["tight_nut_insert"], b123d_tight_insert)
             and rel(r["tight_nut_collet"], b123d_tight_collet))
    print("\n  Verdict:", "AGREE" if agree else "MISMATCH - STOP")
    return agree


def _rot180(nut):
    from build123d import Axis
    return nut.rotate(Axis.Z, 180)


# ---------------------------------------------------------------------------
def main() -> int:
    size = next((a for a in sys.argv[1:] if a in params.SIZES), params.ACTIVE_SIZES[0])
    d = params.derive(size)
    fc = FreeCADRPC()
    ver = fc.version()
    print(f"FreeCAD {ver['fc']} / OCC {ver['occ']}  <-  {size}")
    for name in ("body", "nut", "collet", "gland_%s_assembly" % size):
        p = OUT_DIR / (f"{name}.step" if name.startswith("gland") else f"{name}_{size}.step")
        if not p.exists():
            print(f"missing {p}; run build.py first")
            return 1
    parts = dict(body=build_body(size), nut=build_nut(size), collet=build_collet(size),
                 insert=build_insert(size, d["insert_ids"][0]))

    rc = 0
    if not shape_check(fc, size, d, parts):
        rc = 1
    if not interference_check(fc, size, d, parts):
        print("\nSTOP: FreeCAD and build123d disagree on interference. Not proceeding.")
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
