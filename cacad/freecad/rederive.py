"""Independent re-derivation of an assembly inside FreeCAD.

The pattern: do NOT import the assembled STEP and trust its placement. Import
each part's own STEP, recompute every placement (z, rotation) from the params
dict inside FreeCAD, run the boolean there, and compare with the build tool's
number. Agreement means the build's placement math and the kernel's boolean
agree with a second implementation; it does not mean a second kernel
(FreeCAD 1.1.3 and build123d both run OpenCascade — 7.8.1 vs 7.9.3).

Requires a FreeCAD with the freecad-mcp style XML-RPC server (`execute_code`).
Facts encoded (FINDINGS F7, F11): booleans pairwise per solid; use the root
object's shape, not leaves; compose transforms with rotate/translate.
"""
from __future__ import annotations

import json

from .rpc import FreeCADRPC


PAIRWISE_COMMON = r'''
import FreeCAD, Import, json
D = json.loads(%(d)r)
def load(path):
    doc = FreeCAD.newDocument("rd")
    Import.insert(path, doc.Name)
    doc.recompute()
    roots = [o for o in doc.Objects if getattr(o, "Shape", None) is not None and not o.InList]
    assert len(roots) == 1, "expected one root object in " + path
    solids = [so.copy() for so in roots[0].Shape.Solids]      # world coords: leaves are local (F11)
    FreeCAD.closeDocument(doc.Name)
    return solids
def placed(solids, z, rot):
    out = []
    for so in solids:
        c = so.copy(); c.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 0, 1), rot); c.translate(FreeCAD.Vector(0, 0, z))
        out.append(c)
    return out
parts = {k: placed(load(v["step"]), v["z"], v["rot_deg"]) for k, v in D["parts"].items()}
out = {}
for a, b in D["pairs"]:
    out[a + "&" + b] = round(sum(sa.common(sb).Volume for sa in parts[a] for sb in parts[b]), 6)
print("JSON:" + json.dumps(out))
'''


def pairwise_common_in_freecad(fc: FreeCADRPC, parts: dict, pairs: list[tuple[str, str]]) -> dict[str, float]:
    """parts: {name: {"step": path, "z": float, "rot_deg": float}} — placements
    recomputed from params by the caller, not read from an assembly file.
    Returns {"a&b": volume}."""
    return fc.run(PAIRWISE_COMMON % dict(d=json.dumps(dict(parts=parts, pairs=[list(p) for p in pairs]))), "pairwise common")


def compare(expected: dict[str, float], got: dict[str, float], tol_abs: float = 1e-3, tol_rel: float = 0.02) -> list[str]:
    """Return a list of mismatch descriptions (empty = agree). Zero-volume
    expectations use tol_abs; non-zero ones tol_rel. Include at least one pair
    that is *expected* to interfere, so agreement on zeros is not vacuous."""
    bad = []
    for k, e in expected.items():
        g = got[k]
        ok = abs(g - e) <= tol_abs if abs(e) < tol_abs else abs(g - e) <= max(tol_abs, tol_rel * abs(e))
        if not ok:
            bad.append(f"{k}: expected {e:.4f}, FreeCAD {g:.4f}")
    if all(abs(e) < tol_abs for e in expected.values()):
        bad.append("no non-zero expectation: agreement on zeros alone proves nothing")
    return bad
