"""Three ordinary forecasters, so the model choice can be compared to the cleaning choice.

The point of this module is the comparison and not the models. They are the
cheapest three a planner would try, they are implemented plainly, and none of
them is tuned. If the cleaning rule moves the forecast more than switching
between these does, that is a statement about cleaning rather than about any of
them being bad.

Each takes a history and returns one step ahead forecasts over a holdout.
"""

from __future__ import annotations

import numpy as np

from dcc.errors import UnusableHistory

__all__ = ["MODELS", "SEASON", "damped_trend", "forecast", "seasonal_naive", "trailing_mean"]

#: Weeks in a season. Weekly data, so 52.
SEASON = 52

#: Weeks the trailing mean averages.
MEAN_WINDOW = 13

#: Damping applied to the fitted trend. A convention, and the reason this model
#: is not simply linear regression.
DAMPING = 0.85


def seasonal_naive(values: np.ndarray, index: int) -> float:
    """Last year's same week, which is the baseline every forecast is judged against."""
    if index >= SEASON:
        return float(values[index - SEASON])
    return float(values[:index].mean()) if index else float(values[0])


def trailing_mean(values: np.ndarray, index: int) -> float:
    """The mean of the last thirteen weeks."""
    window = values[max(0, index - MEAN_WINDOW) : index]
    return float(window.mean()) if len(window) else float(values[0])


def damped_trend(values: np.ndarray, index: int) -> float:
    """A level and a damped linear trend fitted to the last two seasons."""
    window = values[max(0, index - 2 * SEASON) : index]
    if len(window) < 4:
        return float(window.mean()) if len(window) else float(values[0])
    positions = np.arange(len(window))
    slope, intercept = np.polyfit(positions, window, 1)
    return float(max(0.0, intercept + slope * (len(window) - 1 + DAMPING)))


MODELS = {
    "seasonal_naive": seasonal_naive,
    "trailing_mean": trailing_mean,
    "damped_trend": damped_trend,
}


def forecast(values: np.ndarray, model: str, start: int) -> np.ndarray:
    """One step ahead forecasts from `start` to the end of `values`."""
    if model not in MODELS:
        raise UnusableHistory(f"unknown model '{model}'; expected one of {', '.join(MODELS)}")
    if start >= len(values):
        raise UnusableHistory(
            f"a holdout starting at {start} leaves nothing to forecast in {len(values)} weeks"
        )
    method = MODELS[model]
    return np.array([method(values, index) for index in range(start, len(values))])
