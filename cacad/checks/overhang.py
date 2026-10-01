"""Overhang from face normals in the declared orientation."""
from __future__ import annotations

from build123d import GeomType, Vector

from cacad.probes import max_overhang_deg


def overhang_report(part, params: dict) -> dict:
    """params:
        up            build direction in the part frame
        bed_z         z of the bed face (faces that never rise above the first
                      layer, measured along `up`, are on the bed: skipped)
        max_deg       limit from vertical (0 = wall, 90 = ceiling)
        nozzle_d      faces with area < nozzle_d**2 are slivers a slicer cannot
                      resolve: skipped and counted
        buried_bands  [(r_min, r_max, z_min, z_max)]: faces entirely inside such
                      a band are inside another solid of the same part (e.g. the
                      overlap band of an unfused thread) and are not exposed
        exceptions    [(name, z, ...)] planar faces whose centre is at z are
                      declared ceilings (support accepted there)
    Returns {worst_ok, offenders, exceptions_found, slivers}. Assert on it with
    `check_overhang`."""
    up = Vector(params["up"]).normalized()
    first_layer = params["nozzle_d"] / 2
    sliver_area = params["nozzle_d"] ** 2
    bed_z = params["bed_z"]
    bands = params.get("buried_bands", [])
    exc = params.get("exceptions", [])

    def exposed(f):
        if f.area < sliver_area:
            return False
        bb = f.bounding_box()
        top = max((v.Z - bed_z) * up.Z for v in (bb.min, bb.max))
        if top <= first_layer:
            return False
        rs = [(v.X**2 + v.Y**2) ** 0.5 for v in f.vertices()]
        return not (rs and any(r0 - 0.01 <= min(rs) and max(rs) <= r1 + 0.01 and bb.min.Z >= z0 - 0.01 and bb.max.Z <= z1 + 0.01
                               for r0, r1, z0, z1 in bands))

    def is_exception(f):
        return f.geom_type == GeomType.PLANE and any(abs(f.center().Z - e[1]) < 1e-3 for e in exc)

    rep = dict(worst_ok=0.0, offenders=[], exceptions_found=[], slivers=sum(1 for f in part.faces() if f.area < sliver_area))
    for f in part.faces().filter_by(exposed):
        ang, _ = max_overhang_deg([f], up)
        row = (round(ang, 1), f.geom_type.name, round(f.area, 2), round(f.center().Z, 2))
        if ang > params["max_deg"] + 0.5:
            (rep["exceptions_found"] if is_exception(f) else rep["offenders"]).append(row)
        else:
            rep["worst_ok"] = max(rep["worst_ok"], ang)
    return rep


def check_overhang(part, params: dict) -> dict:
    """Fails on any undeclared face over the limit, and — so a stale exception
    list cannot hide a reorientation — fails if a declared exception is not
    actually found when exceptions are declared."""
    rep = overhang_report(part, params)
    assert not rep["offenders"], f"undeclared overhangs > {params['max_deg']} deg: {rep['offenders']}"
    if params.get("exceptions"):
        assert rep["exceptions_found"], "declared exceptions not found: orientation or exception list is stale"
    return rep
