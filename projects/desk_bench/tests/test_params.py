import pytest

from projects.desk_bench import params
from projects.desk_bench.desk import build, check


def test_validates():
    params.validate()


def test_every_number_has_a_source():
    for table in (params.LUMBER, params.DESIGN):
        for key, (value, tag, source) in table.items():
            assert tag and source, key


def test_model_has_no_overlaps_and_right_extent():
    check(build())


def test_all_on_hand_sticks_used():
    d = params.derive()
    assert len(d["cuts"]["72 in"]) == 4 and len(d["cuts"]["31 in"]) == 4


def test_too_tall_leg_fails(monkeypatch):
    monkeypatch.setitem(params.DESIGN, "leg", (40 * params.IN, "DESIGN", "test"))
    with pytest.raises(AssertionError):
        params.validate()
