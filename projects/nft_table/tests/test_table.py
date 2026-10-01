"""table: geometry, contacts and insertion measured on the solids, function probes, print checks; must-fail controls."""
import math

import pytest
from build123d import Location

from cacad import interference_volume
from projects.nft_table import build as B
from projects.nft_table import params as P
from projects.nft_table import printcheck as PC
from projects.nft_table import table as T


def test_geometry_contacts_and_function(report):
    assert report["pairs"] > 250
    assert len(report["insertion"]) == len(P.derive()["joints"])


def test_every_solid_counted(d, parts):
    assert len(parts) == len(d["expect"])
    assert sum(1 for n in parts if n.startswith("P1-")) == 3 * d["L"]["n_ch"]


@pytest.mark.parametrize("variant", list(P.print_parts(P.derive())))
def test_print_checks(d, variant):
    PC.build_and_check([variant], d)


# ---- must-fail controls ----
def test_control_channel_1mm_low_is_caught(parts):
    """The channel lowered 1 mm sinks into its saddle ledges."""
    low = parts["C1-body"].moved(Location((0, 0, -1.0)))
    assert interference_volume(low, parts["P1-C1-M"]) > 1.0
    assert interference_volume(parts["C1-body"], parts["P1-C1-M"]) < 1e-3


def test_control_saddle_3mm_high_is_caught(parts):
    high = parts["P1-C3-F"].moved(Location((0, 0, 3.0)))
    assert interference_volume(high, parts["C3-body"]) > 1.0


def test_control_shifted_envelope_is_caught(d, parts, monkeypatch):
    """A params envelope off by 1 mm in X fails check_geometry, naming the part."""
    exp = dict(d["expect"])
    e = dict(exp["C3-lid"])
    e["lo"] = (e["lo"][0] + 1.0, *e["lo"][1:])
    e["hi"] = (e["hi"][0] + 1.0, *e["hi"][1:])
    exp["C3-lid"] = e
    d2 = dict(d, expect=exp)
    with pytest.raises(AssertionError, match="C3-lid bbox"):
        T.check_geometry(d2, parts)


def test_control_fitting_seated_1mm_off_is_caught(d):
    """The bypass valve moved 1 mm along its axis: measured insertion changes by 1 mm on one socket."""
    e = d["expect"]["SUP-valve"]
    lg = [dict(x, c=P.P.add(x["c"], (0, 0, -1.0))) for x in e["geom"][1]]
    d2 = dict(d, expect=dict(d["expect"], **{"SUP-valve": dict(e, geom=("legs", lg))}))
    male, female, r, want, _, what = next(j for j in d["joints"] if j[0] == "SUP-bp-2" and j[1] == "SUP-valve")
    got = T.measure_insertion(d2, male, female, r)
    assert got == pytest.approx(want - 1.0, abs=0.02)
    assert T.measure_insertion(d, male, female, r) == pytest.approx(want, abs=0.02)


def test_control_spout_moved_off_its_hole_is_caught(d, parts):
    """A P3 moved 3 mm across the collector hits its P4 ring."""
    moved = parts["P3-C2"].moved(Location((0, 3.0, 0)))
    assert moved.distance_to(parts["P4-C2-up"]) < 1e-6 or interference_volume(moved, parts["P4-C2-up"]) > 0
