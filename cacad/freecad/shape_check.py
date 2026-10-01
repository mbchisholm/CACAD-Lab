"""BOP argument check of a part inside FreeCAD, from STEP and from exact BREP.

Runs BRepCheck (`Shape.isValid`) and the BOP argument analyzer
(`Shape.check(True)`) on every solid and every face. Per solid, not on the
whole shape: parts are compounds of overlapping solids and the whole-shape
check would report the intended overlap (FINDINGS F5, F7). Flagged faces are
classified into caller-supplied radial bands (r_core, r_major, z0, z1) so
thread-face pcurve flags (F6) can be told from real defects, and the same
check on the exact BREP tells STEP round-trip artefacts apart (F8).
"""
from __future__ import annotations

import json
from pathlib import Path

from .rpc import FreeCADRPC

CHECK_CODE = r'''
import FreeCAD, Part, Import, json, re, math
D = json.loads(%(d)r)
def classify(rmin, rmax, zmin, zmax):
    """band name if the face lies radially between a band's core and major radius."""
    for name, rc, rmaj, z0, z1 in D["bands"]:
        if rmin >= rc - 0.01 and rmax <= rmaj + 0.01 and zmin >= z0 - 0.5 and zmax <= z1 + 0.5:
            return name
    return "OTHER"
def check_shape(sh):
    rep = dict(shape_type=sh.ShapeType, n_solids=len(sh.Solids), n_faces=len(sh.Faces),
               volume=round(sum(so.Volume for so in sh.Solids), 3), brep_valid=all(so.isValid() for so in sh.Solids),
               whole=[], faces=[])
    for so in sh.Solids:
        try:
            so.check(True)
        except Exception as e:
            rep["whole"] = sorted(set(rep["whole"]) | set(re.findall(r"BOPAlgo_\w+", str(e))))
    for i, f in enumerate(sh.Faces):
        try:
            f.check(True)
        except Exception as e:
            kinds = sorted(set(re.findall(r"BOPAlgo_\w+", str(e))))
            bb = f.BoundBox
            rs = [math.hypot(v.X, v.Y) for v in f.Vertexes] or [0.0]
            rep["faces"].append(dict(i=i, surf=f.Surface.__class__.__name__, area=round(f.Area, 4),
                                     z=[round(bb.ZMin, 2), round(bb.ZMax, 2)],
                                     r=[round(min(rs), 3), round(max(rs), 3)], kinds=kinds,
                                     region=classify(min(rs), max(rs), bb.ZMin, bb.ZMax)))
    return rep
def part_shapes(doc, root_label):
    """{part label: shape} for the direct children of the assembly group."""
    return {o.Label: o.Shape for o in doc.Objects
            if getattr(o, "Shape", None) is not None and any(p.Label == root_label for p in o.InList)}
if D["source"] == "step":
    doc = FreeCAD.newDocument("chk")
    Import.insert(D["step"], doc.Name)
    doc.recompute()
    shapes = part_shapes(doc, D["root_label"]) if D.get("root_label") else None
    if shapes is None:
        roots = [o for o in doc.Objects if getattr(o, "Shape", None) is not None and not o.InList]
        sh = roots[0].Shape
    else:
        sh = shapes[D["label"]]
    out = check_shape(sh)
    FreeCAD.closeDocument(doc.Name)
else:
    sh = Part.Shape(); sh.read(D["brep"])
    out = check_shape(sh)
print("JSON:" + json.dumps(out))
'''


def check_part(fc: FreeCADRPC, part, label: str, step: Path, brep_dir: Path, bands: list,
               root_label: str | None = None) -> dict:
    """Check one build123d part from two sources. `step` is either the part's
    own STEP (root_label None) or an assembly STEP with `label` as a direct
    child of `root_label`. Returns {"step": report, "brep": report}; each
    report carries `volume`, `n_solids`, `brep_valid`, `whole`, `faces`.
    One RPC per source so each stays inside the dispatcher budget."""
    from build123d import export_brep
    brep = Path(brep_dir) / f"{label}.brep"
    export_brep(part, str(brep))
    base = dict(bands=[list(b) for b in bands], label=label, root_label=root_label)
    return {
        "step": fc.run(CHECK_CODE % dict(d=json.dumps(dict(base, source="step", step=str(step)))), f"STEP {label}"),
        "brep": fc.run(CHECK_CODE % dict(d=json.dumps(dict(base, source="brep", brep=str(brep)))), f"BREP {label}"),
    }


def summarize(report: dict, expected_solids: int, expected_volume: float, vol_tol: float = 0.01,
              tolerated=("BOPAlgo_InvalidCurveOnSurface",)) -> tuple[bool, str]:
    """Verdict for one report: ok when solid count and volume match, BRepCheck
    passes, every flagged face lies in a declared band, and the only BOP kinds
    are the tolerated pcurve-tolerance ones."""
    kinds = sorted({k for f in report["faces"] for k in f["kinds"]} | set(report["whole"]))
    regions: dict[str, int] = {}
    for f in report["faces"]:
        regions[f["region"]] = regions.get(f["region"], 0) + 1
    dv = abs(report["volume"] - expected_volume)
    bad_kinds = [k for k in kinds if k not in tolerated]
    outside = [f for f in report["faces"] if f["region"] == "OTHER"]
    ok = not bad_kinds and not outside and report["brep_valid"] and report["n_solids"] == expected_solids and dv <= vol_tol
    line = (f"{report['shape_type']:8s} solids={report['n_solids']}/{expected_solids} faces={report['n_faces']:3d} "
            f"BRepCheck.isValid={report['brep_valid']}  vol={report['volume']:.3f} (expected {expected_volume:.3f}, d={dv:.4f})\n"
            f"         BOP kinds={kinds or 'none'}  flagged faces by band={regions or 'none'}")
    if outside:
        line += "".join(f"\n         OUTSIDE declared bands: {f}" for f in outside)
    if bad_kinds:
        line += f"\n         non-tolerance BOP errors: {bad_kinds}"
    return ok, line
