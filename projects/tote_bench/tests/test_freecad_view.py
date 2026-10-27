"""freecad_view.py without FreeCAD: the position and exploded-view checks agree with params, catch a 1 mm shift,
agree with the real STEP read back by build123d, the exploded parts do not overlap (and EXPLODE's bounding-box pair
filter keeps every pair that could), the BOM matches params, and every FreeCAD-side script compiles. The RPC path itself needs FreeCAD and is not run here. Self-contained: no fixtures."""
from __future__ import annotations

import ast
import functools
import json
from types import SimpleNamespace

import pytest
from build123d import Compound, Location, import_step

from cacad import export, interference_volume
from projects.tote_bench import freecad_view as fv
from projects.tote_bench.bench import build_bench
from projects.tote_bench.params import DESIGN, derive, tape


@functools.cache
def _d():
    return derive()


@functools.cache
def _parts():
    return build_bench()


def _got_from_params(d):
    return {n: [*bb, 1] for n, bb in fv.expected_bboxes(d).items()}


def _got_from_shapes(shapes: dict) -> dict:
    out = {}
    for n, sh in shapes.items():
        bb = sh.bounding_box()
        out[n] = [*tuple(bb.min), *tuple(bb.size), len(sh.solids())]
    return out


def _bbox_touch(a, b, tol=0.5):
    ba, bb = a.bounding_box(), b.bounding_box()
    return all(tuple(ba.min)[i] <= tuple(bb.max)[i] + tol and tuple(bb.min)[i] <= tuple(ba.max)[i] + tol for i in range(3))


# --- check_positions ---------------------------------------------------------------------------------------------

def test_positions_agree_with_params():
    d = _d()
    got = _got_from_params(d)
    assert len(got) == len(d["boards"]) + len(d["prisms"]) + 1
    assert fv.check_positions(d, got) == []


@pytest.mark.parametrize("name", ["LEG-FL", "SIDE-R-SHELF", "POST", "BACK", "BRACE-L", "SHELF", "PEGBOARD", "TOP"])
@pytest.mark.parametrize("axis", [0, 1, 2])
def test_one_mm_shift_is_reported(name, axis):
    d = _d()
    got = _got_from_params(d)
    got[name][axis] += 1.0
    bad = fv.check_positions(d, got)
    assert len(bad) == 1 and bad[0].startswith(f"{name}:"), bad


def test_missing_part_and_extra_solid_are_reported():
    d = _d()
    got = _got_from_params(d)
    del got["BRACE-R"]
    got["TOP"][6] = 2
    bad = fv.check_positions(d, got)
    assert any("missing ['BRACE-R']" in b for b in bad), bad
    assert any(b.startswith("TOP:") for b in bad), bad


def test_shifted_expectation_control_disagrees():
    """The control main() runs: shift one board's expectation, the same `got` must now disagree."""
    d = _d()
    got = _got_from_params(d)
    name = next(iter(d["boards"]))
    kind, size, lo = d["boards"][name]
    shifted = dict(d, boards=dict(d["boards"], **{name: (kind, size, (lo[0] + 1.0, lo[1], lo[2]))}))
    assert fv.check_positions(shifted, got)


def test_positions_agree_with_the_exported_step(tmp_path):
    """bench.py's solids, exported to STEP and read back with build123d (labels as FreeCAD would see them)."""
    d = _d()
    export(Compound(children=list(_parts().values())), "tote_bench", str(tmp_path))
    c = import_step(str(tmp_path / "tote_bench.step"))
    shapes = {ch.label: ch for ch in c.children}
    assert len(shapes) == len(list(c.children)), "duplicate labels in the STEP"
    got = _got_from_shapes(shapes)
    assert fv.check_positions(d, got) == []
    name = next(iter(d["boards"]))
    kind, size, lo = d["boards"][name]
    shifted = dict(d, boards=dict(d["boards"], **{name: (kind, size, (lo[0] + 1.0, lo[1], lo[2]))}))
    assert fv.check_positions(shifted, got), "control: a 1 mm shift was not detected"


def test_expected_volume_matches_solids():
    d = _d()
    v = sum(p.volume for p in _parts().values())
    want = fv.expected_volume(d)
    assert abs(v - want) < 1e-6 * want, f"solids {v:.0f}, params {want:.0f}"


def test_kinds_cover_every_part_and_have_colours():
    d = _d()
    k = fv.kinds(d)
    assert set(k) == set(fv.expected_bboxes(d)) == set(_parts())
    assert set(k.values()) == {"x2x4", "x2x2", "plywood", "pegboard"}, set(k.values())
    assert set(k.values()) <= set(fv.COLOURS) and "tote" in fv.COLOURS
    assert all(len(c) == 3 and all(0 <= x <= 1 for x in c) for c in fv.COLOURS.values())
    assert k["TOP"] == "plywood" and k["PEGBOARD"] == "pegboard" and fv.GROUND in k


# --- exploded view -----------------------------------------------------------------------------------------------

def _synthetic_explode(d):
    before = {n: list(bb[:3]) for n, bb in fv.expected_bboxes(d).items()}
    exploded = {n: [lo[a] + d["explode_offset"][n][a] for a in range(3)] for n, lo in before.items()}
    return dict(moves=len(d["explode_moves"]), before=before, exploded=exploded,
                after={n: list(v) for n, v in before.items()}, overlap=0.0)


def test_explode_params_shape():
    d = _d()
    v = DESIGN["explode"]
    assert len(v) == 3 and v[1] == "DESIGN" and "display only" in v[2], v
    names = set(fv.expected_bboxes(d))
    assert set(d["explode_offset"]) == names
    for mv, parts, vec in d["explode_moves"]:
        assert parts and set(parts) <= names, mv
        assert len(vec) == 3
    for n, off in d["explode_offset"].items():
        assert off == tuple(sum(v[a] for _, ps, v in d["explode_moves"] if n in ps) for a in range(3))
    off = d["explode_offset"]
    assert off["TOP"][2] > 0 and off["SHELF"][2] > 0 and off["LIP"] == off["SHELF"]
    assert off["LEG-FL"][0] < 0 and off["SIDE-L-TOP"][0] < 0 and off["LEG-BR"][0] > 0 and off["SIDE-R-FLOOR"][0] > 0
    for n in ("HUTCH", "ARM-L", "BRACE-R", "PEGBOARD", "CLEAT-L"):
        assert off[n][1] < 0 and off[n][2] > 0, n
    # REFERENCE is exactly the parts params leaves in place
    assert {n for n, o in off.items() if not any(o)} == fv.REFERENCE


def test_check_exploded_accepts_params_offsets():
    d = _d()
    fv.check_exploded(d, _synthetic_explode(d))
    json.dumps(d["explode_moves"])   # goes over the wire as JSON


@pytest.mark.parametrize("case", ["exploded off", "not restored", "move count", "overlap", "reference moved",
                                  "mover left in place"])
def test_check_exploded_rejects(case):
    d = _d()
    ex = _synthetic_explode(d)
    if case == "exploded off":
        ex["exploded"]["BRACE-R"][1] += 1.0
    elif case == "not restored":
        ex["after"]["TOP"][2] += 1.0
    elif case == "move count":
        ex["moves"] -= 1
    elif case == "overlap":
        ex["overlap"] = 5.0
    elif case == "mover left in place":   # a part params moves given no offset, FreeCAD agreeing: still refused
        off = dict(d["explode_offset"], **{"PEGBOARD": (0.0, 0.0, 0.0)})
        d = dict(d, explode_offset=off)
        ex = _synthetic_explode(d)
    else:   # a reference part given an offset in params and FreeCAD agreeing: still refused
        off = dict(d["explode_offset"], **{"APRON-F": (0.0, 0.0, 10.0)})
        d = dict(d, explode_offset=off)
        ex = _synthetic_explode(d)
    with pytest.raises(AssertionError):
        fv.check_exploded(d, ex)


def test_exploded_parts_do_not_overlap():
    """What EXPLODE asserts in FreeCAD (max pairwise common < 1e-3 mm^3), checked here on bench.py's solids."""
    d = _d()
    moved = {n: p.moved(Location(d["explode_offset"][n])) for n, p in _parts().items()}
    names = list(moved)
    worst = (0.0, None, None)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = moved[names[i]], moved[names[j]]
            if _bbox_touch(a, b):
                v = interference_volume(a, b)
                if v > worst[0]:
                    worst = (v, names[i], names[j])
    assert worst[0] < 1e-3, f"exploded {worst[1]} and {worst[2]} overlap by {worst[0]:.3f} mm^3"
    got = _got_from_shapes(moved)
    for n, g in got.items():
        lo = fv.expected_bboxes(d)[n][:3]
        assert all(abs(g[a] - lo[a] - d["explode_offset"][n][a]) < 0.01 for a in range(3)), n


def _explode_touch():
    """The `touch` filter EXPLODE runs in FreeCAD, lifted out of the script source and run here."""
    tree = ast.parse(fv.EXPLODE % dict(d=json.dumps(dict(doc="tote_bench"))))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "touch")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<EXPLODE.touch>", "exec"), ns)
    return ns["touch"]


def _fc_box(sh):
    bb = sh.bounding_box()
    return SimpleNamespace(XMin=bb.min.X, YMin=bb.min.Y, ZMin=bb.min.Z, XMax=bb.max.X, YMax=bb.max.Y, ZMax=bb.max.Z)


def test_explode_overlap_filter_keeps_every_touching_pair():
    """EXPLODE runs `common` only on pairs whose boxes touch. On the exploded solids that filter must select the same
    pairs as the build123d check above (so no pair that could share volume is skipped), and fewer than all of them."""
    d = _d()
    touch = _explode_touch()
    moved = {n: p.moved(Location(d["explode_offset"][n])) for n, p in _parts().items()}
    names = list(moved)
    fc = {n: _fc_box(sh) for n, sh in moved.items()}
    pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
    kept = {(a, b) for a, b in pairs if touch(fc[a], fc[b])}
    assert kept == {(a, b) for a, b in pairs if _bbox_touch(moved[a], moved[b])}
    assert 0 < len(kept) < len(pairs) / 2, f"{len(kept)} of {len(pairs)} pairs"
    # disjoint boxes are skipped, boxes 0.5 mm apart are kept, overlapping boxes are kept
    box = lambda x0: SimpleNamespace(XMin=x0, YMin=0, ZMin=0, XMax=x0 + 1, YMax=1, ZMax=1)
    assert touch(box(0), box(1.5)) and touch(box(0), box(0.5)) and not touch(box(0), box(1.6))


# --- BOM and the FreeCAD-side scripts ----------------------------------------------------------------------------

def test_bom_rows():
    d = _d()
    rows = fv.bom_rows(d)
    names = list(d["boards"]) + list(d["prisms"]) + ["TOP"]
    assert [r[0] for r in rows[1:1 + len(names)]] == names
    assert rows[1 + len(names)] == []
    buy = rows.index(["Buy", "Qty", "Note", "", ""])
    assert [r[0] for r in rows[buy + 1:]] == [item for item, _, _ in d["shopping"]]
    assert [r[1] for r in rows[buy + 1:]] == [n for _, n, _ in d["shopping"]]
    assert all(len(r) <= len("ABCDEFG") for r in rows)
    json.dumps(rows)
    by = {r[0]: r for r in rows[1:1 + len(names)]}
    assert not any(n.startswith("DIAG") or "diag" in str(r).lower() for n, r in by.items())
    L = tape(d["brace_long_point"])
    for n in d["prisms"]:
        assert by[n][2] == L and by[n][4] == f"recut to a {L} long point, 45\N{DEGREE SIGN} both ends", by[n]
    W, D, t = d["W"], d["D"], d["t"]
    assert by["SHELF"][1] == "23/32 plywood" and by["SHELF"][2] == f"{tape(W - 2 * t)} x {tape(D)}", by["SHELF"]
    assert by["HUTCH"][2] == f"{tape(W)} x {tape(d['hutch_shelf_d'])}", by["HUTCH"]
    assert by["PEGBOARD"][1] == "1/4 pegboard" and by["PEGBOARD"][2] == f"{tape(W - 2 * t)} x {tape(d['peg_h'])}", \
        by["PEGBOARD"]
    assert by["TOP"][2] == f"{tape(W)} x {tape(D)}" and "2 back legs" in by["TOP"][4], by["TOP"]
    for n, (kind, size, _) in d["boards"].items():
        if kind in ("x2x4", "x2x2"):
            assert by[n][2] == tape(max(size)), by[n]


def test_freecad_scripts_compile():
    dummy = json.dumps(dict(doc="tote_bench"))
    subs = {
        "IMPORT": dict(doc="tote_bench", step="/x/tote_bench.step"),
        "ASSEMBLE": dict(d=dummy), "TOTES": dict(d=dummy), "SCREWS": dict(d=dummy),
        "EXPLODE": dict(d=dummy), "BOM": dict(d=dummy),
    }
    for name, sub in subs.items():
        src = getattr(fv, name) % sub
        compile(src, f"<{name}>", "exec")


def test_freecad_scripts_compile_with_the_real_payloads():
    """The %r-substituted JSON payloads main() sends, so a quote in a part name or note cannot break a script."""
    d = _d()
    sc = [(sn, head, u, ln) for sn, _, _, head, u, ln, _ in d["screws"]]
    payloads = {
        "ASSEMBLE": dict(doc="tote_bench", kinds=fv.kinds(d), colours=fv.COLOURS, ground=fv.GROUND),
        "TOTES": dict(doc="tote_bench", totes=d["totes"], colour=fv.COLOURS["tote"]),
        "SCREWS": dict(doc="tote_bench", screws=sc, r=1.0),
        "EXPLODE": dict(doc="tote_bench", moves=d["explode_moves"]),
        "BOM": dict(doc="tote_bench", rows=fv.bom_rows(d), fcstd="/x/tote_bench.FCStd"),
    }
    for name, p in payloads.items():
        src = getattr(fv, name) % dict(d=json.dumps(p))
        compile(src, f"<{name}>", "exec")
        # the literal the script parses is the payload, round-tripped
        lit = src.split("json.loads(", 1)[1].split(")\n", 1)[0]
        assert json.loads(ast.literal_eval(lit)) == json.loads(json.dumps(p)), name
