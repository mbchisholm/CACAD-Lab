"""Three layers for the base, the clamp and the layouts: geometry + function
(check_base, check_clamp, check_layout), manufacturability (walls, declared
orientation, overhang: none anywhere, the groove roofs are 45 deg), and the
arithmetic of every row. Planted defects prove the function checks bite."""
import pytest
from build123d import Location

from cacad.checks.orientation import check_declared_orientation
from cacad.checks.overhang import check_overhang
from cacad.checks.printability import check_walls_vs_nozzle
from projects.module_grid import params
from projects.module_grid.base import check_base
from projects.module_grid.clamp import _seated, build_hardware, check_clamp, place_jaw


def _no_overhang(part, o, d):
    rep = check_overhang(part, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"],
                                    nozzle_d=d["nozzle_d"], exceptions=o["overhang_exceptions"]))
    assert not rep["exceptions_found"] and not rep["offenders"], rep
    return rep


def test_every_row_validates():
    for name in params.BASES:
        params.validate_base(name)
    for name in params.CLAMPS:
        params.validate_clamp(name)
    for name in params.LAYOUTS:
        params.validate_layout(name)


def test_insert_screw_window():
    """Any clamp from 2.0 to 6.2 mm has a stocked M3 that passes the whole insert and stops above the bore floor
    (past 6.2 the ladder jumps 12 -> 16, wider than the bore's spare depth)."""
    depth = params.insert_bore_depth()
    for k in range(20, 63, 2):
        clamp = k / 10
        L = params.insert_screw(clamp)
        assert L - clamp >= params.INSERT["length"] and L - clamp <= depth - params.COMMON["insert_tip_clear"] + 1e-9


def test_base(base_name, base):
    d = params.derive_base(base_name)
    check_base(base_name, base)
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))
    check_declared_orientation(base, d["print_orientation"]["base"])
    _no_overhang(base, d["print_orientation"]["base"], d)


def test_clamp(clamp_name, clamp_parts):
    d = params.derive_clamp(clamp_name)
    tile, jaw = clamp_parts
    check_clamp(clamp_name, tile, jaw)
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))
    for part, key in ((tile, "clamp_tile"), (jaw, "clamp_jaw")):
        check_declared_orientation(part, d["print_orientation"][key])
        rep = _no_overhang(part, d["print_orientation"][key], d)
        assert rep["worst_ok"] == pytest.approx(45.0, abs=0.5), rep   # the groove roofs, nothing steeper


def test_planted_loose_jaw_is_caught(clamp_name, clamp_parts):
    """The jaw opened 0.2 past the derived face: the board no longer meets its roof."""
    d = params.derive_clamp(clamp_name)
    tile, jaw = clamp_parts
    w, t = d["board_w"][0], d["board_t"][1]
    hw = build_hardware(clamp_name, w, t)
    loose = place_jaw(d, jaw, w, t).moved(Location((0.2, 0, 0)))
    with pytest.raises(AssertionError, match="sliding jaw roof"):
        _seated(d, tile, loose, hw, t)


def test_planted_wide_board_runs_the_jaw_off_its_track(clamp_name):
    """A board 4 mm past the clamp's range: the sliding jaw's foot would overhang the end of the track."""
    d = params.derive_clamp(clamp_name)
    x = params.jaw_face(d, d["board_w"][1] + 4.0, d["board_t"][1])
    assert x + d["foot_len"] > d["track_x"][1]


def test_planted_off_grid_tile_is_refused(monkeypatch):
    """A tile half a cell off its grid: its holes miss the inserts."""
    layouts = dict(params.LAYOUTS)
    layouts["BAD"] = dict(base="B8x6", tiles=(("clamp", "DS18B20", (0, 0)),))
    monkeypatch.setattr(params, "LAYOUTS", layouts)
    real = params.corner_inset
    monkeypatch.setattr(params, "corner_inset", lambda: real() + params.GRID["pitch"] / 2)
    with pytest.raises(AssertionError, match="misses every insert"):
        params.validate_layout("BAD")


def test_layouts():
    from projects.module_grid.assembly import build_layout, check_layout
    for name in params.ACTIVE_LAYOUTS:
        check_layout(name, build_layout(name))
