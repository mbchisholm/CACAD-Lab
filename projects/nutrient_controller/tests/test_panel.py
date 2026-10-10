"""Concept D (instrument panel): the layout validates and the build passes its concept checks, and each check
fails when its defect is planted. The displays and the encoder come from Adafruit's STEPs when ref/ has them,
their envelopes otherwise; the checks are the same either way."""
import pytest

from projects.nutrient_controller import panel, panel_params


def test_layout_validates():
    panel_params.validate()


def test_build_passes_concept_checks():
    r = panel.build_all()
    rep = panel.check(r["parts"], r["d"])
    assert rep["pairs"] > 50
    for name, p in r["printed"].items():
        assert p.is_valid and len(p.solids()) == 1, name


def test_planted_shallow_case_hits_the_motors():
    with pytest.raises(AssertionError, match="motor ends"):
        panel_params.validate(depth=48.0)


def test_planted_small_legend_is_refused():
    with pytest.raises(AssertionError, match="legend size"):
        panel_params.validate(small_size=5.0)


def test_planted_knob_on_the_bushing_overlaps():
    """The knob's gap over the encoder bushing taken away: the pairwise check finds knob and encoder in one place."""
    r = panel.build_all(knob=dict(gap=-1.0))
    with pytest.raises(AssertionError, match="knob x encoder"):
        panel.check(r["parts"], r["d"])
