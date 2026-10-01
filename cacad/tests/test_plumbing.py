"""cacad.plumbing: the analytic volume and box of legs and sweeps against OCC (from archive/nft_rack_v1 tests)."""
import math

import pytest

from cacad import plumbing as P


@pytest.mark.parametrize("bend", [90.0, 87.0, 60.0, 30.0])
def test_mitred_leg_formulas_against_occ(bend):
    """The hand volume and box of a mitred stepped elbow, at four bends spanning the parameter, against OCC."""
    phi = math.radians(180 - bend)
    o1 = P.unit((0.3, 1.0, -0.2))
    p = P.perp(o1)
    o2 = tuple(math.cos(phi) * x + math.sin(phi) * y for x, y in zip(o1, p))
    lg = P.elbow((10.0, 20.0, 30.0), o1, [(None, 20.0, 22.0, 14.0), (20.0, 45.0, 22.0, 16.0)], o2, [(None, 60.0, 16.0, 13.0)])
    e = P.legs_expect("fitting", lg)
    solid = P.build_geom(e)
    assert len(solid.solids()) == 1 and solid.is_valid
    assert solid.volume == pytest.approx(e["volume"], rel=1e-6)
    bb = solid.bounding_box()
    assert (*tuple(bb.min), *tuple(bb.max)) == pytest.approx((*e["lo"], *e["hi"]), abs=1e-3)


def test_straight_leg_builds_one_solid():
    """build_leg returns one valid solid for a straight stepped part (t = 0)."""
    lg = P.straight((0, 0, 0), (0, 0.1, -1), [(30.0, 20.0, 15.0), (20.0, 25.0, 10.0)])[0]
    s = P.build_leg(lg)
    assert len(s.solids()) == 1 and s.volume == pytest.approx(P.leg_volume(lg), rel=1e-9)


def test_filled_leg_has_no_bore():
    lg = P.straight((0, 0, 0), (0, 0, 1), [(30.0, 20.0, 15.0)])[0]
    assert P.build_leg(lg, filled=True).volume == pytest.approx(math.pi * 20.0 ** 2 * 30.0, rel=1e-9)


def test_sweep_volume_matches_pappus():
    pts = [(0, 0, 0), (0, 0, 100), (80, 0, 100), (80, 120, 100)]
    e = P.sweep_expect("hose", pts, 12.7, 9.5, 30.0)
    s = P.build_geom(e)
    assert s.is_valid and len(s.solids()) == 1
    assert s.volume == pytest.approx(e["volume"], rel=1e-4)
    bb = s.bounding_box()
    assert (*tuple(bb.min), *tuple(bb.max)) == pytest.approx((*e["lo"], *e["hi"]), abs=1e-2)
