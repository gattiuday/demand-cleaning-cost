"""The three forecasters and the holdout."""

from __future__ import annotations

import numpy as np
import pytest

from dcc.compare import wmape
from dcc.errors import UnusableHistory
from dcc.models import MODELS, SEASON, damped_trend, forecast, seasonal_naive, trailing_mean


def test_the_seasonal_naive_returns_last_years_week():
    values = np.arange(120.0)
    assert seasonal_naive(values, 60) == pytest.approx(values[60 - SEASON])


def test_the_seasonal_naive_falls_back_before_a_full_season():
    values = np.arange(120.0)
    assert seasonal_naive(values, 10) == pytest.approx(values[:10].mean())
    assert seasonal_naive(values, 0) == pytest.approx(values[0])


def test_the_trailing_mean_averages_the_recent_window():
    values = np.concatenate([np.full(20, 5.0), np.full(20, 11.0)])
    assert trailing_mean(values, 40) == pytest.approx(11.0)


def test_the_damped_trend_follows_a_rising_series():
    values = np.arange(1.0, 80.0)
    assert damped_trend(values, 79) > values[-5]


def test_the_damped_trend_never_returns_a_negative_forecast():
    values = np.arange(80.0, 1.0, -1.0)
    assert damped_trend(values, 78) >= 0.0


def test_a_very_short_series_falls_back_to_its_mean():
    assert damped_trend(np.array([4.0, 6.0]), 2) == pytest.approx(5.0)


def test_an_unknown_model_is_refused_by_name():
    with pytest.raises(UnusableHistory, match="unknown model"):
        forecast(np.arange(100.0), "croston", 60)


def test_a_holdout_with_nothing_to_forecast_is_refused():
    with pytest.raises(UnusableHistory, match="leaves nothing to forecast"):
        forecast(np.arange(10.0), "trailing_mean", 10)


@pytest.mark.parametrize("model", list(MODELS))
def test_every_model_returns_one_forecast_per_held_out_week(model):
    values = np.arange(120.0)
    assert len(forecast(values, model, 60)) == 60


def test_wmape_over_all_zero_actuals_is_undefined():
    with pytest.raises(UnusableHistory, match="undefined"):
        wmape(np.zeros(4), np.ones(4))


def test_wmape_refuses_mismatched_shapes():
    with pytest.raises(UnusableHistory, match="same shape"):
        wmape(np.ones(3), np.ones(2))
