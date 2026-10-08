"""Tote bench: one solid per leg, rail, slat, stop, footrest and plank, from
params.derive; feet, totes and screw shanks as check bodies; the garage from
projects/garage to stand in. Every number is from params.derive.

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


def build_feet(version: str) -> dict[str, Part]:
    d = derive(version)
    out = {}
    for name, (base, r, h) in d["feet"].items():
        c = Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(base))
        c.label = name
        out[name] = c
    return out


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
    return build_site(d["top_x0"], d["top_x0"] + d["W"], "lip_wall")


def check_bench(version: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(version)
    label = f"tote bench {version}"
    asm = Compound(children=list(parts.values()))
    assert all(p.is_valid for p in parts.values()), f"{label}: invalid solid"
    expect_solids(asm, len(d["boards"]), label)
    feet, totes, site = build_feet(version), build_totes(version), build_garage(version)
    bb = asm.bounding_box()
    zmin = min(d["foot_h"], d["footrest_top"] - d["rail_h"])
    depth = d["D"] if d["top_overhang_front"] >= d["t"] - 1e-9 else d["y_front"] + d["t"] - d["y_back"]
    assert_bbox(asm, (d["W"], depth, d["H"] - zmin), zmin, d["bbox_tol"], label)
    vol = sum(p.volume for p in parts.values())
    assert abs(vol - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{label}: wood {vol:.0f} vs hand {d['wood_volume']:.0f}"
    for name, p in parts.items():
        _, size, lo = d["boards"][name]
        b = p.bounding_box()
        got = (*tuple(b.min), *tuple(b.size))
        assert all(abs(a - e) < d["bbox_tol"] for a, e in zip(got, (*lo, *size))), f"{label}: {name} is {got}, params {(*lo, *size)}"

    # nothing overlaps anything: wood, feet, totes, the lip, the wall, the slab
    _no_overlap([parts, feet, totes, site], label)

    # load path: planks on top rails, slats on mid rails, rails on legs, legs on feet, feet on the lip or the slab
    garage = Compound(children=list(site.values()))
    t = d["t"]
    for lad in d["ladders"]:
        i, lx = lad["i"], lad["leg"] + d["leg_x"] / 2
        for end, (y0, y1), zb in (("BACK", d["back_leg_y"], d["back_leg_z"][0]), ("FRONT", d["front_leg_y"], d["front_leg_z"][0])):
            ly, ground = (y0 + y1) / 2, zb - d["foot_h"]
            on = "lip" if end == "BACK" else "slab"
            assert abs(ground - (d["lip_h"] if on == "lip" else 0.0)) < 1e-6
            assert_material(feet[f"FOOT-L{i}-{end}"], {f"L{i} {end} foot": ((lx, ly, zb - 0.5), True)})
            assert_material(asm, {f"L{i} {end} leg on its foot": ((lx, ly, zb + 0.5), True)})
            assert_material(garage, {f"L{i} {end} {on} under the foot": ((lx, ly, ground - 0.5), True),
                                     f"L{i} {end} air over the {on}": ((lx, ly, ground + 0.5), False)})
            for side in ("L", "R"):
                rx = lad[f"rail_{side}"] + t / 2
                for lvl, (z0, z1) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                    assert_material(asm, {f"L{i} {lvl}-{side} rail beside the {end} leg": ((rx, ly, (z0 + z1) / 2), True)})
        for side in ("L", "R"):
            rx = lad[f"rail_{side}"] + t / 2
            assert_material(asm, {f"L{i} plank on the TOP-{side} rail": ((rx, d["y_back"] + d["rail_len"] / 2, d["top_rail_top"] + 0.5), True)})
    for col in d["columns"]:
        xm, j = (col["x0"] + col["x1"]) / 2, col["j"]
        yf = d["y_front"] - 0.5
        if col["kind"] == "T":
            for z in (1.0, d["mid_top"] - 1.0, d["slat_top"] + 1.0, d["top_rail_top"] - 1.0):
                assert_material(asm, {f"col {j} front open at z={z:.0f}": ((xm, yf, z), False)})
            assert_material(asm, {f"col {j} front slat": ((xm, yf, d["mid_top"] + t / 2), True)})
        else:
            # knee space: open from the floor to the planks, except the footrest bar across the front
            for z in (d["footrest_top"] + 1.0, d["mid_top"], d["top_rail_top"] - 1.0):
                for y in (d["y_back"] + 50.0, d["y_back"] + d["rail_len"] / 2, yf):
                    assert_material(asm, {f"knee {j} open at y={y:.0f} z={z:.0f}": ((xm, y, z), False)})
            assert_material(asm, {f"knee {j} footrest": ((xm, d["y_front"] + t / 2, d["footrest_top"] - 1.0), True)})
    # stops: each tote pushed 1 mm further back hits the lip (lower) or its stop board (upper)
    for tn, (size, lo) in d["totes"].items():
        j, lvl = tn.split("-")[1][1:], tn.split("-")[2]
        stop = site["LIP"] if lvl == "LOWER" else parts[f"C{j}-STOP"]
        pushed = _box(size, (lo[0], lo[1] - d["tote_stop_gap"] - 1.0, lo[2]), tn + "+pushed")
        assert interference_volume(pushed, stop) > 1.0, f"{label}: {tn} pushed home misses its stop"

    # screws: each passes through exactly its own board, bites its target by params' penetration, hits nothing else
    screws = build_screws(version)
    sa = 3.14159265 * (d["screw_spec"]["d"] / 2) ** 2
    allp = dict(parts, **feet, **totes, **site)
    for s, (sn, thr, into, _, _, ln) in zip(screws, d["screws"]):
        v_thr, v_into = interference_volume(s, parts[thr]), interference_volume(s, parts[into])
        assert abs(v_thr - sa * t) < 0.02 * sa * t, f"{label}: {sn} passes {v_thr / sa:.1f} mm of {thr}, params {t:.1f}"
        assert abs(v_into - sa * (ln - t)) < 0.02 * sa * (ln - t), f"{label}: {sn} bites {v_into / sa:.1f} mm of {into}"
        for other, p in allp.items():
            if other in (thr, into) or not _bbox_touch(s, p):
                continue
            assert interference_volume(s, p) < 1e-3, f"{label}: {sn} hits {other}"
    return dict(volume=vol, bbox=bb.size, assembly=asm, feet=Compound(children=list(feet.values())),
                totes=Compound(children=list(totes.values())), garage=garage, screws=Compound(children=screws))


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
        export(rep["feet"], f"tote_bench_{v}_feet", OUT)
        export(rep["totes"], f"tote_bench_{v}_totes", OUT)
        export(rep["garage"], f"tote_bench_{v}_garage", OUT)
        maybe_show(rep["assembly"], rep["totes"], rep["garage"], names=["bench", "totes", "garage"])
