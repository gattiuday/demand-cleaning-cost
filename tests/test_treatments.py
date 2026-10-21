"""What each treatment does to a flagged week."""

from __future__ import annotations

import numpy as np
import pytest

from dcc.errors import UnusableHistory
from dcc.treatments import TREATMENTS, cap_at_percentile, drop, replace_with_median, treat


def test_dropping_shortens_the_series():
    values = np.array([1.0, 99.0, 2.0])
    flags = np.array([False, True, False])
    assert list(drop(values, flags)) == [1.0, 2.0]


def test_capping_keeps_the_length_and_lowers_the_flagged_week():
    values = np.array([10.0, 12.0, 11.0, 900.0])
    flags = np.array([False, False, False, True])
    out = cap_at_percentile(values, flags)
    assert len(out) == 4
    assert out[-1] < values[-1]


def test_capping_never_raises_an_observation():
    """A cap is a cap. A flagged week below the ceiling must be left alone."""
    values = np.array([10.0, 12.0, 11.0, 1.0])
    flags = np.array([False, False, False, True])
    assert cap_at_percentile(values, flags)[-1] == 1.0


def test_the_median_replacement_uses_the_unflagged_weeks_around_the_week():
    values = np.array([10.0, 10.0, 900.0, 10.0, 10.0])
    flags = np.array([False, False, True, False, False])
    assert replace_with_median(values, flags)[2] == pytest.approx(10.0)


def test_the_median_replacement_falls_back_to_the_whole_series():
    """When the local window is entirely flagged there is nothing local to use."""
    values = np.array([10.0, 900.0, 900.0, 900.0, 11.0, 12.0, 10.0])
    flags = np.array([False, True, True, True, False, False, False])
    out = replace_with_median(values, flags, window=1)
    assert np.all(out[1:4] < 900.0)


@pytest.mark.parametrize("treatment", list(TREATMENTS))
def test_a_fully_flagged_series_is_refused_by_every_treatment(treatment):
    values = np.array([1.0, 2.0, 3.0])
    with pytest.raises(UnusableHistory):
        treat(values, np.ones(3, dtype=bool), treatment)


def test_mismatched_shapes_are_refused():
    with pytest.raises(UnusableHistory, match="same shape"):
        drop(np.ones(3), np.ones(2, dtype=bool))


def test_an_unknown_treatment_is_refused_by_name():
    with pytest.raises(UnusableHistory, match="unknown treatment"):
        treat(np.ones(3), np.zeros(3, dtype=bool), "interpolate")
