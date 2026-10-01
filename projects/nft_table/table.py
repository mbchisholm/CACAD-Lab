"""NFT table assembly: every solid from params.derive() via build.py, placed, then checked in three layers
(geometry, contact/insertion, function). Every number is from params.

    .venv/bin/python projects/nft_table/table.py [--show]     # -> out/nft_table.step, .stl
"""
from __future__ import annotations

import math

from build123d import Compound, Part

from cacad import assert_material, expect_solids, interference_volume
from projects.nft_table import build as B
from projects.nft_table.params import COMMON, derive, spec


def build_table(d: dict | None = None) -> dict[str, Part]:
    """name -> solid in its assembled position."""
    d = d or derive()
    out = {}
    for name, e in d["expect"].items():
        p = B.build_expect(e)
        p = p if isinstance(p, Part) else Part(p.wrapped)
        p.label = name
        out[name] = p
    return out


def expected_box(e):
    lo, hi = e["lo"], e["hi"]
    if e["geom"][0] == "prims":
        lb = B.label_bbox(e["geom"][1], e["geom"][2])
        if lb:
            lo = tuple(min(lo[i], lb[0][i]) for i in range(3))
            hi = tuple(max(hi[i], lb[1][i]) for i in range(3))
    return lo, hi


def expected_volume(e):
    return e["volume"] + (B.label_volume(e["geom"][1]) if e["geom"][0] == "prims" else 0.0)


def _bbox(p):
    bb = p.bounding_box()
    return tuple(bb.min), tuple(bb.max)


def _touch(a, b, tol=0.5):
    return all(a[0][i] <= b[1][i] + tol and b[0][i] <= a[1][i] + tol for i in range(3))


def measure_insertion(d: dict, male: str, female: str, r: float) -> float:
    """Length of the male inside the female, on the geometry: volume of (male filled) n (female filled) over the
    male's entering cross-section."""
    me, fe = d["expect"][male], d["expect"][female]
    v = interference_volume(B.build_expect(me, filled=True, label=False), B.build_expect(fe, filled=True, label=False))
    return v / (math.pi * r * r)


def check_fall(paths: dict) -> None:
    for name, pts in paths.items():
        zs = [p[2] for p in pts]
        assert all(b < a for a, b in zip(zs, zs[1:])), f"return path from {name} does not fall all the way: {[round(z, 1) for z in zs]}"


def check_geometry(d: dict, parts: dict) -> dict:
    exp = d["expect"]
    assert set(parts) == set(exp), f"built {sorted(set(parts) - set(exp))} not in params, missing {sorted(set(exp) - set(parts))}"
    tol, vrel = COMMON["bbox_tol"], COMMON["vol_rel"]
    for name, p in parts.items():
        assert p.is_valid, f"{name} invalid"
        assert len(p.solids()) == 1, f"{name} has {len(p.solids())} solids"
        lo, hi = expected_box(exp[name])
        got = _bbox(p)
        bad = [round(g - w, 3) for g, w in zip((*got[0], *got[1]), (*lo, *hi)) if abs(g - w) > tol]
        assert not bad, f"{name} bbox {[round(x, 2) for x in (*got[0], *got[1])]} vs params {[round(x, 2) for x in (*lo, *hi)]}"
        vw = expected_volume(exp[name])
        assert abs(p.volume - vw) <= vrel * vw, f"{name} volume {p.volume:.1f} vs hand {vw:.1f}"
    asm = Compound(children=list(parts.values()))
    expect_solids(asm, len(exp), "nft_table")
    # pairwise: nothing overlaps (touching faces and lines give zero volume)
    boxes = {n: _bbox(p) for n, p in parts.items()}
    names = list(parts)
    over, checked = [], 0
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if _touch(boxes[names[i]], boxes[names[j]]):
                checked += 1
                v = interference_volume(parts[names[i]], parts[names[j]])
                if v > 1e-3:
                    over.append(f"{names[i]} x {names[j]}: {v:.3f} mm^3")
    assert not over, "overlaps:\n  " + "\n  ".join(over)
    return dict(assembly=asm, pairs=checked)


def check_contacts(d: dict, parts: dict) -> dict:
    """What must touch, touches: supply and bypass chains, feed lines on both barbs, channels on all three saddles,
    saddles on the rails, caps on the channels, P4 and P5 on their pipes, P7 on the rails and pipes."""
    def touching(a, b, what):
        dist = parts[a].distance_to(parts[b])
        assert dist < 1e-6, f"{what}: {a} and {b} do not touch ({dist:.3f} mm)"
    for chain in (d["supply_chain"], d["bypass_chain"]):
        for a, b in zip(chain, chain[1:]):
            touching(a, b, "supply break")
    for c in d["channels"]:
        n = c["name"]
        touching(f"FEED-{n}", f"P5-{n}-tap", "feed line off its tap")
        touching(f"FEED-{n}", f"P2-{n}", "feed line off its feed cap")
        touching(f"P5-{n}-tap", "SUP-manifold", "P5 off the manifold")
        touching(f"P5-{n}-back", "SUP-manifold", "P5 back half off the manifold")
        touching(f"P2-{n}", f"{n}-body", "P2 off the channel")
        touching(f"P3-{n}", f"{n}-body", "P3 off the channel")
        for k in ("F", "M", "B"):
            touching(f"P1-{n}-{k}", f"{n}-body", "channel off its saddle")
            touching(f"P1-{n}-{k}", f"RAIL-{k}", "saddle off its rail")
        touching(f"P4-{n}-up", "RAIL-B", "P4 hanger off the back rail")
        side = "L" if c["xc"] < d["x_mid"] else "R"
        for h in ("up", "lo"):
            touching(f"P4-{n}-{h}", f"RET-coll-{side}", "P4 off the collector")
    for name, v, pl in d["p7_clips"]:
        rail = "RAIL-B" if abs(pl[1][1] - d["y_rail"]["B"]) < 1 else "RAIL-F" if abs(pl[1][1] - d["y_rail"]["F"]) < 1 else "RAIL-M"
        touching(name, rail, "P7 off its rail")
    ins = {}
    for male, female, r, want, mn, what in d["joints"]:
        touching(male, female, what)
        got = measure_insertion(d, male, female, r)
        ins[what] = got
        assert abs(got - want) < 0.05, f"{what}: inserted {got:.2f} mm, expected {want:.2f}"
        assert got >= mn - 1e-6, f"{what}: inserted {got:.2f} mm, below the minimum {mn:.2f}"
    return dict(insertion=ins)


def check_function(d: dict, parts: dict) -> dict:
    """Probes on the solids: channels on the ledges (material under the floor at each rail, air between the ledges),
    every P3 spout through its P4 ring and collector hole with air around it, each tap's passage over a drilled hole,
    the return falling all the way, the drop and bypass ending in the tote over the water."""
    L = d["L"]
    out = {}
    for c in d["channels"]:
        n = c["name"]
        F = c["frame"]
        from projects.nft_table.shapes import to_world
        cw, ct = spec("channel_w"), spec("channel_t")
        for k in ("F", "M", "B"):
            s_ = d["s_rail"][k]
            ledge = to_world(F, (cw / 2 - L["p1_ledge_w"] / 2, s_, -0.05))
            mid = to_world(F, (0.0, s_, -0.5))
            assert_material(parts[f"P1-{n}-{k}"], {f"{n} {k} ledge under the corner": (ledge, True),
                                                  f"{n} {k} relieved under the floor": (mid, False)})
        # spout: a point on its axis 1 mm above the tip is in the collector's bore, air in pipe, P4 and tote
        tip = c["spout_tip"]
        p_in = (tip[0], tip[1], tip[2] + 1.0)
        p_below = (tip[0], tip[1], tip[2] - 1.0)
        side = "L" if c["xc"] < d["x_mid"] else "R"
        assert_material(parts[f"RET-coll-{side}"], {f"{n} spout tip in the collector hole": (p_in, False),
                                                   f"{n} below the tip, inside the bore": (p_below, False)})
        assert_material(parts[f"P3-{n}"], {f"{n} spout wall at the tip": ((tip[0] + d["spout_od"] / 2 - 1.0, tip[1], tip[2] + 1.0), True)})
        assert tip[2] < d["z_coll"] + spec("channel_t") * 0 + (d["expect"][f"RET-coll-{side}"]["hi"][2] - d["z_coll"]), f"{n} spout tip above the collector"
        dist = parts[f"P3-{n}"].distance_to(parts[f"P4-{n}-up"])
        out[f"{n} spout to P4 ring"] = dist
        assert dist > 0.1, f"{n}: spout touches its P4 ring ({dist:.2f})"
        dist = parts[f"P3-{n}"].distance_to(parts[f"RET-coll-{side}"])
        out[f"{n} spout to collector"] = dist
        assert dist > 0.1, f"{n}: spout touches the collector ({dist:.2f})"
        # tap: the drilled hole in the manifold is air in the pipe and in the P5 passage
        from projects.nft_table.params import bv
        hole = (c["xc"], d["y_rail"]["F"] - (bv("pvc34", "od") / 2 - bv("pvc34", "wall") / 2), d["z_sup"])
        assert_material(parts["SUP-manifold"], {f"{n} tap hole drilled": (hole, False)})
        assert_material(parts[f"P5-{n}-tap"], {f"{n} tap passage open over the hole": ((hole[0], hole[1] - bv("pvc34", "wall"), hole[2]), False)})
    check_fall(d["return_paths"])
    # drop and bypass end inside the tote cavity, in air
    for nm, pt in (("drop", d["drop_end"]), ("bypass", (d["x_bp"], d["y_r"], d["z_bp_end"]))):
        q = (pt[0], pt[1], pt[2] - 1.0)
        for s_ in ("TOTE-body", "TOTE-lid", "PUMP"):
            assert_material(parts[s_], {f"{nm} end in air ({s_})": (q, False)})
    return out


def check_table(d: dict, parts: dict) -> dict:
    rep = check_geometry(d, parts)
    rep.update(check_contacts(d, parts))
    rep["function"] = check_function(d, parts)
    return rep


if __name__ == "__main__":
    from cacad import export, maybe_show
    OUT = __file__.rsplit("/", 1)[0] + "/out"   # a string: the MCP sandbox rejects os/pathlib/sys anywhere in this file (F23)
    d = derive()
    parts = build_table(d)
    rep = check_table(d, parts)
    bb = rep["assembly"].bounding_box()
    print(f"nft_table: bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm, solids {len(rep['assembly'].solids())}, "
          f"pairs checked {rep['pairs']}")
    for k, v in rep["insertion"].items():
        print(f"  inserted {v:6.2f} mm  {k}")
    for k, v in rep["function"].items():
        print(f"  {k}: {v:.2f} mm")
    export(rep["assembly"], "nft_table", OUT)
    maybe_show(rep["assembly"], names=["nft_table"])
