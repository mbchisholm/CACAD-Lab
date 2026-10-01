"""Print checks for one printed part in its print frame (up +Z, bed at z = 0), from params.print_spec: declared bed
face, overhang from face normals (planar ceilings declared by z, curved ones by name and centre z), walls against
nozzle multiples, functional faces never facing down past the limit, water bores vertical, the F22 label. No numbers
live here."""
from __future__ import annotations

import math

from build123d import GeomType, Vector

from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import overhang_report
from cacad.checks.printability import check_walls_vs_nozzle
from cacad.registries import materials as MAT
from projects.nft_table import build as B
from projects.nft_table import params as PR
from projects.nft_table import shapes as S


def _face_at(part, pt):
    best = min(part.faces(), key=lambda f: f.distance_to(Vector(*pt)))
    return best, best.distance_to(Vector(*pt))


def check_print(name: str, solid, desc: dict, spec: dict) -> dict:
    """Raises on the first failure. Returns the orientation report."""
    up = spec["up"]
    max_deg = PR.MAX_OVERHANG[0]
    assert solid.is_valid and len(solid.solids()) == 1, f"{name}: {len(solid.solids())} solids or invalid"
    bb = solid.bounding_box()
    assert abs(bb.min.Z - spec["bed_z"]) < 1e-6, f"{name}: lowest point {bb.min.Z:.3f}, bed at {spec['bed_z']}"
    assert all(s_ <= b_ for s_, b_ in zip((bb.size.X, bb.size.Y, bb.size.Z), MAT.BED)), f"{name}: over the A1 build volume"
    check_declared_orientation(solid, dict(up=up, bed_z=spec["bed_z"], bed_face=spec["bed_face"],
                                           known_overhangs=[k for k, _ in spec["known_overhangs"]]))
    rep = overhang_report(solid, dict(up=up, bed_z=spec["bed_z"], max_deg=max_deg, nozzle_d=MAT.NOZZLE,
                                      exceptions=[(k, z) for k, z in spec["known_overhangs"]]))
    # curved ceilings declared by name and centre z (the gland walls): every remaining offender must be one of them
    left = []
    for o in rep["offenders"]:
        ang, kind, area, zc = o
        if kind != "PLANE" and any(abs(zc - z) < 1e-2 for _, z in spec["cyl_overhangs"]):
            continue
        left.append(o)
    assert not left, f"{name}: undeclared overhangs > {max_deg} deg: {left}"
    if spec["known_overhangs"]:
        found = {round(o[3], 2) for o in rep["exceptions_found"]}
        for k, z in spec["known_overhangs"]:
            assert any(abs(z - f) < 1e-2 for f in found), f"{name}: declared overhang '{k}' at z {z:.2f} not found (stale list)"
    check_walls_vs_nozzle(spec["walls"], dict(nozzle_d=MAT.NOZZLE, wall_multiple=2.0))
    # functional faces: the face at each point exists and does not face down past the limit
    lim = -math.sin(math.radians(90.0 - max_deg))
    for fname, (pt, n_out) in spec["functional"].items():
        f, dist = _face_at(solid, pt)
        assert dist < 0.05, f"{name}: functional face '{fname}' not found at {tuple(round(x, 2) for x in pt)} ({dist:.3f})"
        nz = f.normal_at(f.center()).Z if f.geom_type == GeomType.PLANE else n_out[2]
        assert nz >= lim - 1e-9 or abs(pt[2] - spec["bed_z"]) < 1e-6, f"{name}: functional face '{fname}' faces down ({nz:.2f}): needs support"
        for k, z in spec["known_overhangs"]:
            assert abs(pt[2] - z) > 1e-3 or f.geom_type != GeomType.PLANE or nz > -0.99, \
                f"{name}: functional face '{fname}' is the declared overhang '{k}'"
    for bname, axis in spec["water_bores"].items():
        a = S.P.unit(axis)
        tilt = math.degrees(math.acos(min(1.0, abs(a[2]))))
        assert tilt <= PR.BORE_TILT_MAX[0] + 1e-9, f"{name}: water bore '{bname}' {tilt:.2f} deg off vertical"
    lab = desc.get("label")
    assert lab, f"{name}: no label (F22)"
    assert lab["h"] >= 4.0 and abs(lab["t"] - 3 * MAT.LAYER) < 1e-9, f"{name}: label not >= 4 mm and three layers (F22)"
    assert S.P.dot(S.P.unit(lab["n"]), up) > 0.99, f"{name}: label not on a face pointing up in print"
    vol_hand = S.desc_volume(desc) + B.label_volume(desc)
    assert abs(solid.volume - vol_hand) <= 1e-3 * vol_hand, f"{name}: volume {solid.volume:.1f} vs hand {vol_hand:.1f}"
    return dict(name=name, bed_face=spec["bed_face"], size=(bb.size.X, bb.size.Y, bb.size.Z), worst_ok=rep["worst_ok"],
                declared=[k for k, _ in spec["known_overhangs"]] + [k for k, _ in spec["cyl_overhangs"]],
                exceptions_found=rep["exceptions_found"], functional=list(spec["functional"]),
                walls=spec["walls"], water_bores=list(spec["water_bores"]), drilled=spec.get("drilled", []),
                volume=solid.volume, label=lab["text"])


def orientation_report(r: dict) -> str:
    lines = [f"{r['name']}: bed = {r['bed_face']}; up +Z; size {r['size'][0]:.1f} x {r['size'][1]:.1f} x {r['size'][2]:.1f} mm; "
             f"{r['volume'] / 1000:.1f} cm^3; label '{r['label']}'",
             f"  worst undeclared overhang {r['worst_ok']:.1f} deg (limit {PR.MAX_OVERHANG[0]:.0f})",
             f"  declared overhangs: {r['declared'] or 'none'}",
             f"  functional faces, none on support: {r['functional']}",
             f"  walls: " + ", ".join(f"{k} {v:.2f}" for k, v in r["walls"].items()) + f" (>= {2 * MAT.NOZZLE:.1f})",
             f"  water bores vertical: {r['water_bores'] or 'none'}" + (f"; drilled after printing: {r['drilled']}" if r["drilled"] else "")]
    return "\n".join(lines)


def build_and_check(names: list[str], d=None) -> dict:
    """name -> (solid, report) for the listed print_parts variants."""
    d = d or PR.derive()
    pp = PR.print_parts(d)
    out = {}
    for n in names:
        desc, _ = pp[n]
        solid = B.desc_solid(desc)
        out[n] = (solid, check_print(n, solid, desc, PR.print_spec(d, n)))
    return out
