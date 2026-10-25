"""Workbench on the lip wall: one solid per leg, rail, stretcher, shelf and top
layer, placed from params.derive; the feet as cylinders, the totes as check
envelopes, and the garage (slab, lip, wall) from projects/garage to stand in.
Every number is from params.derive.

    .venv/bin/python projects/workbench/bench.py [--show]     # builds params.ACTIVE_BENCHES
"""
from __future__ import annotations

from build123d import Align, Box, Compound, Cylinder, Location, Part

from cacad import assert_bbox, assert_material, expect_solids, interference_volume
from projects.garage.garage import build_site
from projects.workbench.params import ACTIVE_BENCHES, derive

ALIGN_MIN = (Align.MIN, Align.MIN, Align.MIN)


def _box(size, lo, label: str) -> Part:
    b = Box(*size, align=ALIGN_MIN).moved(Location(lo))
    b.label = label
    return b


def build_bench(bench: str) -> dict[str, Part]:
    """name -> solid, each in its assembled position."""
    d = derive(bench)
    return {name: _box(size, lo, name) for name, (_, size, lo) in d["boards"].items()}


def build_feet(bench: str) -> dict[str, Part]:
    """Leveling feet as pad-diameter cylinders from the floor (or lip top) to the leg end, at their mid-travel set."""
    d = derive(bench)
    out = {}
    for name, (base, r, h) in d["feet"].items():
        c = Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location(base))
        c.label = name
        out[name] = c
    return out


def build_totes(bench: str) -> dict[str, Part]:
    d = derive(bench)
    return {name: _box(size, lo, name) for name, (size, lo) in d["totes"].items()}


def build_garage(bench: str) -> dict[str, Part]:
    d = derive(bench)
    return build_site(d["top_x0"], d["top_x0"] + d["W"], d["wall"])


def _bbox_touch(a: Part, b: Part, tol: float = 0.5) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


def _no_overlap(groups: list[dict[str, Part]], label: str):
    """Pairwise across and within the groups: touching faces are fine, shared volume is not (F7: never compound-vs-compound)."""
    items = [(n, p) for g in groups for n, p in g.items()]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (na, a), (nb, b) = items[i], items[j]
            if not _bbox_touch(a, b):
                continue
            v = interference_volume(a, b)
            assert v < 1e-3, f"{label}: {na} and {nb} overlap by {v:.3f} mm^3"


def check_bench(bench: str, parts: dict[str, Part]) -> dict:
    """Geometry and function layers. Raises."""
    d = derive(bench)
    label = f"bench {bench}"
    asm = Compound(children=list(parts.values()))
    assert all(p.is_valid for p in parts.values()), f"{label}: invalid solid"
    expect_solids(asm, len(d["boards"]), label)
    feet, totes, site = build_feet(bench), build_totes(bench), build_garage(bench)
    bb = asm.bounding_box()
    assert_bbox(asm, (d["W"], d["D"], d["H"] - d["foot_h"]), d["foot_h"], d["bbox_tol"], label)
    assert abs(bb.min.X - d["top_x0"]) < d["bbox_tol"] and abs(bb.min.Y - d["y_back"]) < d["bbox_tol"], f"{label}: bbox min {bb.min}"
    vol = sum(p.volume for p in parts.values())
    assert abs(vol - d["wood_volume"]) < 1e-3 * d["wood_volume"], f"{label}: wood volume {vol:.0f} vs hand {d['wood_volume']:.0f}"
    for name, p in parts.items():
        _, size, lo = d["boards"][name]
        b = p.bounding_box()
        got = (*tuple(b.min), *tuple(b.size))
        assert all(abs(a - e) < d["bbox_tol"] for a, e in zip(got, (*lo, *size))), f"{label}: {name} is {got}, params says {(*lo, *size)}"

    # nothing overlaps anything: wood, feet, totes, and the garage itself (the lip, the wall, the slab)
    _no_overlap([parts, feet, totes, site], label)

    # load path, probed: top on rails, rails on legs, legs on feet, feet on the slab or the lip
    garage = Compound(children=list(site.values()))
    for fr in d["frames"]:
        i, lx = fr["i"], fr["leg"] + d["leg_x"] / 2
        for end, ly, zb in (("BACK", sum(d["back_leg_y"]) / 2, d["back_leg_z"][0]), ("FRONT", sum(d["front_leg_y"]) / 2, d["front_leg_z"][0])):
            ground_z = zb - d["foot_h"]
            on = "lip" if end == "BACK" else "slab"
            assert_material(feet[f"FOOT-F{i}-{end}"], {f"F{i} {end} foot under the leg": ((lx, ly, zb - 0.5), True)})
            assert_material(asm, {f"F{i} {end} leg above its foot": ((lx, ly, zb + 0.5), True),
                                  f"F{i} {end} air beside the foot": ((fr["leg"] + 0.5, ly, zb - 0.5), False)})
            assert_material(garage, {f"F{i} {end} {on} under the foot": ((lx, ly, ground_z - 0.5), True),
                                     f"F{i} {end} air over the {on} at the foot": ((lx, ly, ground_z + 0.5), False)})
            assert (on == "lip") == (abs(ground_z - d["lip_h"]) < 1e-6)
        for side in ("L", "R"):
            if f"rail_{side}" not in fr:
                continue
            rx = fr[f"rail_{side}"] + d["rail_t"] / 2
            for lvl, (z0, z1) in (("MID", d["mid_rail_z"]), ("TOP", d["top_rail_z"])):
                for ly in (sum(d["back_leg_y"]) / 2, sum(d["front_leg_y"]) / 2):
                    assert_material(asm, {f"F{i}{side} {lvl} rail at the leg": ((rx, ly, (z0 + z1) / 2), True)})
                assert_material(asm, {f"F{i}{side} {lvl} board on the rail": ((rx, d["y_back"] + d["rail_len"] / 2, z1 + 0.5), True)})
    # the front is open between the legs from the slab to the top: nothing crosses a tote's way out
    for j, (x0, x1) in enumerate(d["bays_x"]):
        xm, yf = (x0 + x1) / 2, d["y_front"] - 0.5
        for z in (1.0, d["shelf_bot"] - 1.0, d["shelf_top"] + 1.0, d["top_rail_top"] - 1.0):
            assert_material(asm, {f"bay {j} front open at z={z:.0f}": ((xm, yf, z), False)})
        assert_material(asm, {f"bay {j} shelf": ((xm, yf, d["shelf_bot"] + d["ply_t"] / 2), True)})
    # the lip and the stretcher are the stops: each tote, pushed 1 mm further back, would hit its stop
    stops = {"LOWER": ("LIP", site["LIP"]), "UPPER": ("STRETCHER", None)}
    for tn, (size, lo) in d["totes"].items():
        j, lvl = int(tn.split("-")[1][1:]), tn.split("-")[2]
        stop_name, stop = stops[lvl]
        stop = stop or parts[f"STRETCHER-B{j}"]
        pushed = _box(size, (lo[0], lo[1] - d["tote_stop_gap"] - 1.0, lo[2]), tn + "+pushed")
        assert interference_volume(pushed, stop) > 1.0, f"{label}: {tn} pushed home misses its stop {stop_name}"
    return dict(volume=vol, bbox=bb.size, assembly=asm, feet=Compound(children=list(feet.values())),
                totes=Compound(children=list(totes.values())), garage=garage)


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    for bench in ACTIVE_BENCHES:
        parts = build_bench(bench)
        rep = check_bench(bench, parts)
        bb = rep["bbox"]
        print(f"{bench}: bbox {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm (wood, feet below), wood {rep['volume'] / 1e6:.1f} L, "
              f"solids {len(rep['assembly'].solids())}, feet {len(rep['feet'].solids())}, totes {len(rep['totes'].solids())}, "
              f"garage {len(rep['garage'].solids())}")
        export(rep["assembly"], f"workbench_{bench}", OUT)
        export(rep["feet"], f"workbench_{bench}_feet", OUT)
        export(rep["totes"], f"workbench_{bench}_totes", OUT)
        export(rep["garage"], f"workbench_{bench}_garage", OUT)
        maybe_show(rep["assembly"], rep["feet"], rep["totes"], rep["garage"], names=["bench", "feet", "totes", "garage"])
