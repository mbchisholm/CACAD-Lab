"""Tote bench: one solid per sill, ledger, leg, rail, slat, footrest and
plank, from params.derive; totes and screw shanks as check bodies; the garage
from projects/garage to stand in. Every number is from params.derive.

    .venv/bin/python projects/tote_bench/bench.py [--show]     # builds params.ACTIVE_VERSIONS
"""
from __future__ import annotations

from build123d import Align, Compound, Cylinder, Location, Part, Plane

from cacad import assert_bbox, assert_material, expect_solids, interference_volume
from projects.garage.garage import build_site
from projects.tote_bench.params import ACTIVE_VERSIONS, derive
from projects.workbench.bench import _bbox_touch, _box, _no_overlap


def build_bench(version: str) -> dict[str, Part]:
    d = derive(version)
    return {name: _box(size, lo, name) for name, (_, size, lo) in d["boards"].items()}


def build_totes(version: str) -> dict[str, Part]:
    d = derive(version)
    return {name: _box(size, lo, name) for name, (size, lo) in d["totes"].items()}


def build_screws(version: str) -> list[Part]:
    """Shank envelopes, head point to tip, in params' order."""
    d = derive(version)
    r = d["screw_spec"]["d"] / 2
    return [Cylinder(r, ln, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(Plane(origin=head, z_dir=u)))
            for _, _, _, head, u, ln in d["screws"]]


def build_garage(version: str) -> dict[str, Part]:
    d = derive(version)
    return build_site(0.0, d["W"], "lip_wall")


def check_bench(version: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(version)
    label = f"tote bench {version}"
    asm = Compound(children=list(parts.values()))
    assert all(p.is_valid for p in parts.values()), f"{label}: invalid solid"
    expect_solids(asm, len(d["boards"]), label)
    totes, site = build_totes(version), build_garage(version)
    bb = asm.bounding_box()
    assert_bbox(asm, (d["W"], d["wall_gap"] + d["D"], d["H"]), 0.0, d["bbox_tol"], label)
    vol = sum(p.volume for p in parts.values())
    assert abs(vol - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{label}: wood {vol:.0f} vs hand {d['wood_volume']:.0f}"
    for name, p in parts.items():
        _, size, lo = d["boards"][name]
        b = p.bounding_box()
        got = (*tuple(b.min), *tuple(b.size))
        assert all(abs(a - e) < d["bbox_tol"] for a, e in zip(got, (*lo, *size))), f"{label}: {name} is {got}, params {(*lo, *size)}"

    # nothing overlaps anything: wood, totes, the lip, the wall, the slab
    _no_overlap([parts, totes, site], label)

    # load path, probed. The back frame: sill on the lip against the drywall, back legs lapped on sill and ledger
    garage = Compound(children=list(site.values()))
    t, lip_h = d["t"], d["lip_h"]
    for x in (10.0, d["W"] / 2, d["W"] - 10.0):
        assert_material(asm, {f"sill at x={x:.0f}": ((x, t / 2, lip_h + 1.0), True),
                              f"ledger at x={x:.0f}": ((x, t / 2, d["top_rail_top"] - 1.0), True)})
        assert_material(garage, {f"lip under the sill at x={x:.0f}": ((x, t / 2, lip_h - 1.0), True),
                                 f"drywall behind the sill at x={x:.0f}": ((x, -1.0, lip_h + 1.0), True)})
    for lad in d["ladders"]:
        i, lx = lad["i"], lad["leg"] + d["leg_x"] / 2
        by, fy = sum(d["back_leg_y"]) / 2, sum(d["front_leg_y"]) / 2
        assert_material(asm, {f"L{i} back leg on the lip": ((lx, by, lip_h + 1.0), True),
                              f"L{i} sill behind the back leg": ((lx, t / 2, lip_h + 1.0), True),
                              f"L{i} ledger behind the back leg": ((lx, t / 2, d["top_rail_top"] - 1.0), True),
                              f"L{i} front leg on the slab": ((lx, fy, 1.0), True)})
        assert_material(garage, {f"L{i} lip under the back leg": ((lx, (by + d["lip_depth"]) / 2, lip_h - 1.0), True),
                                 f"L{i} slab under the front leg": ((lx, fy, -1.0), True)})
        for side in ("L", "R"):
            rx = lad[f"rail_{side}"] + t / 2
            for lvl, (z0, z1) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                for ly in (by, fy):
                    assert_material(asm, {f"L{i} {lvl}-{side} rail beside its leg": ((rx, ly, (z0 + z1) / 2), True)})
            assert_material(asm, {f"L{i} plank on the TOP-{side} rail": ((rx, d["y_lap"] + d["rail_len"] / 2, d["top_rail_top"] + 0.5), True)})
    for col in d["columns"]:
        xm, j, yf = (col["x0"] + col["x1"]) / 2, col["j"], d["y_front"] - 0.5
        if col["kind"] == "T":
            for z in (1.0, d["mid_top"] - 1.0, d["slat_top"] + 1.0, d["top_rail_top"] - 1.0):
                assert_material(asm, {f"col {j} front open at z={z:.0f}": ((xm, yf, z), False)})
            assert_material(asm, {f"col {j} front slat": ((xm, yf, d["mid_top"] + t / 2), True)})
        else:
            for z in (d["footrest_top"] + 1.0, d["mid_top"], d["top_rail_top"] - 1.0):
                for y in (d["y_lap"] + 50.0, d["y_lap"] + d["rail_len"] / 2, yf):
                    assert_material(asm, {f"knee {j} open at y={y:.0f} z={z:.0f}": ((xm, y, z), False)})
            assert_material(asm, {f"knee {j} footrest": ((xm, d["y_front"] + t / 2, d["footrest_top"] - 1.0), True)})
    # stops: each tote pushed 1 mm further back hits the lip (lower) or the ledger (upper)
    for tn, (size, lo) in d["totes"].items():
        stop = site["LIP"] if tn.endswith("LOWER") else parts["LEDGER"]
        pushed = _box(size, (lo[0], lo[1] - d["tote_stop_gap"] - 1.0, lo[2]), tn + "+pushed")
        assert interference_volume(pushed, stop) > 1.0, f"{label}: {tn} pushed home misses its stop"

    # screws: each passes through exactly its own board, bites its target by params' penetration, hits nothing else
    screws = build_screws(version)
    sa = 3.14159265 * (d["screw_spec"]["d"] / 2) ** 2
    allp = dict(parts, **totes, **site)
    for s, (sn, thr, into, _, _, ln) in zip(screws, d["screws"]):
        v_thr, v_into = interference_volume(s, parts[thr]), interference_volume(s, parts[into])
        assert abs(v_thr - sa * t) < 0.02 * sa * t, f"{label}: {sn} passes {v_thr / sa:.1f} mm of {thr}, params {t:.1f}"
        assert abs(v_into - sa * (ln - t)) < 0.02 * sa * (ln - t), f"{label}: {sn} bites {v_into / sa:.1f} mm of {into}"
        for other, p in allp.items():
            if other in (thr, into) or not _bbox_touch(s, p):
                continue
            assert interference_volume(s, p) < 1e-3, f"{label}: {sn} hits {other}"
    return dict(volume=vol, bbox=bb.size, assembly=asm, totes=Compound(children=list(totes.values())), garage=garage,
                screws=Compound(children=screws))


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for v in ACTIVE_VERSIONS:
        parts = build_bench(v)
        rep = check_bench(v, parts)
        bb = rep["bbox"]
        print(f"{v}: bbox {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm, wood {rep['volume'] / 1e6:.1f} L, "
              f"solids {len(rep['assembly'].solids())}, screws {len(rep['screws'].solids())} checked")
        export(rep["assembly"], f"tote_bench_{v}", OUT)
        export(rep["totes"], f"tote_bench_{v}_totes", OUT)
        export(rep["garage"], f"tote_bench_{v}_garage", OUT)
        maybe_show(rep["assembly"], rep["totes"], rep["garage"], names=["bench", "totes", "garage"])
