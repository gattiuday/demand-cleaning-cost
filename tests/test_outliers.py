"""The three detection rules and their edges."""

from __future__ import annotations

import numpy as np
import pytest

from dcc.errors import UnusableHistory
from dcc.outliers import DETECTORS, detect, iqr_rolling, mad_rule, zscore_rule


def test_a_flat_series_has_no_outliers_under_any_rule():
    flat = np.full(60, 42.0)
    for rule in DETECTORS:
        assert not detect(flat, rule).any(), rule


def test_the_zscore_rule_flags_a_value_far_from_the_mean():
    values = np.concatenate([np.full(60, 10.0), [10_000.0]])
    assert zscore_rule(values)[-1]


def test_the_mad_rule_is_not_inflated_by_the_value_it_is_looking_for():
    """The reason it exists. A single huge value cannot move a median much."""
    values = np.concatenate([np.random.default_rng(0).normal(100, 5, 80), [100_000.0]])
    assert mad_rule(values)[-1]


def test_the_mad_rule_reports_nothing_when_more_than_half_the_series_is_identical():
    """No spread in the middle means no scale to judge against.

    Flagging everything that differs would flag ordinary variation, so this
    reports nothing found rather than everything found.
    """
    values = np.concatenate([np.full(40, 7.0), [9.0, 11.0, 13.0]])
    assert not mad_rule(values).any()


def test_the_rolling_rule_needs_four_observations_before_it_judges_anything():
    values = np.arange(1.0, 40.0)
    flags = iqr_rolling(values)
    assert not flags[:4].any()


def test_a_rolling_window_without_quartiles_is_refused():
    with pytest.raises(UnusableHistory, match="has no quartiles"):
        iqr_rolling(np.arange(20.0), window=3)


def test_an_empty_history_has_no_outliers_to_find():
    with pytest.raises(UnusableHistory, match="empty history"):
        zscore_rule(np.array([]))


def test_a_two_dimensional_input_is_refused():
    with pytest.raises(UnusableHistory, match="one dimensional"):
        zscore_rule(np.ones((3, 3)))


def test_an_unknown_detector_is_refused_by_name():
    with pytest.raises(UnusableHistory, match="unknown detector"):
        detect(np.arange(10.0), "hampel")


def test_a_single_observation_has_no_spread_and_flags_nothing():
    assert not zscore_rule(np.array([5.0])).any()
