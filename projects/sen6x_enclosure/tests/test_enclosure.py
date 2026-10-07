"""Arithmetic (validate), function (nothing the sensor needs is printed over, probe pairs on the windows and groove)
and manufacturability (overhangs in the declared print orientation, walls vs nozzle)."""
from projects.sen6x_enclosure import params
from projects.sen6x_enclosure.enclosure import check
from cacad.checks.overhang import check_overhang
from cacad.checks.printability import check_walls_vs_nozzle


def test_validate():
    params.validate()


def test_every_value_is_tagged():
    for k, v in params.SPEC.items():
        assert v[1] in params.TAGS and v[2], k


def test_function(built):
    base, lid, hw, keep = built
    got = check(base, lid, hw, keep)
    assert all(v < 1e-3 for k, v in got.items() if " x " in k)


def test_walls_vs_nozzle():
    d = params.derive()
    check_walls_vs_nozzle(d["walls"], dict(nozzle_d=d["nozzle_d"]))


def test_overhangs_in_print_orientation(built):
    base, lid, _, _ = built
    d = params.derive()
    for name, part in (("base", base), ("lid", lid)):
        o = d["print_orientation"][name]
        check_overhang(part, dict(up=o["up"], bed_z=o["bed_z"], max_deg=d["max_overhang_deg"], nozzle_d=d["nozzle_d"],
                                  exceptions=o["exceptions"]))


def test_validate_is_not_vacuous():
    """An unprintable wall and a bridge longer than the window's must each fail validate()."""
    import pytest
    for bad in (dict(wall=1.0), dict(max_bridge=10.0)):
        with pytest.raises(AssertionError):
            params.validate(**bad)
