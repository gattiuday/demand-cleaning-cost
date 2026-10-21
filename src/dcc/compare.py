"""Scoring a forecast against the demand that will actually recur.

The target matters more than anything else here. A forecast is scored against
`underlying`: the demand without the data errors but with the real events. That
is what a planner is trying to predict, because a promotion that recurs will
recur, and a forecast that has had promotions cleaned out of it will be short on
the next one.

Scoring against the raw observed series would reward predicting data errors,
which is not a thing anybody wants. Scoring against a series with the promotions
removed would reward exactly the cleaning this repository is measuring, which
would be assuming the conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np

from dcc.errors import UnusableHistory
from dcc.generator import History
from dcc.models import MODELS, SEASON, forecast
from dcc.outliers import DETECTORS, detect
from dcc.treatments import TREATMENTS, treat

__all__ = ["HOLDOUT", "Outcome", "pipeline_outcomes", "score_pipeline", "wmape"]

#: Weeks held out at the end of the history for scoring. One season, so every
#: week of the year is scored once.
HOLDOUT = SEASON


def wmape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Sum of absolute errors over the sum of actuals."""
    if actual.shape != predicted.shape:
        raise UnusableHistory(
            f"actual and predicted must have the same shape, got {actual.shape} "
            f"and {predicted.shape}"
        )
    total = float(np.abs(actual).sum())
    if total == 0:
        raise UnusableHistory("every actual in the holdout is zero, so WMAPE is undefined")
    return float(np.abs(actual - predicted).sum() / total)


@dataclass(frozen=True)
class Outcome:
    """One cleaning pipeline and one model, scored on one item."""

    item: str
    detector: str
    treatment: str
    model: str
    wmape: float
    flagged: int
    real_events_removed: int
    data_errors_removed: int


def score_pipeline(history: History, detector: str, treatment: str, model: str) -> Outcome:
    """Clean, fit, forecast and score, against the demand that will recur.

    `detect` and `treat` see only the observed series. The label counts in the
    result are computed afterwards, from the flags and the planted labels, and
    nothing upstream of the score reads them.
    """
    flags = detect(history.observed, detector)
    cleaned = treat(history.observed, flags, treatment)

    # Dropping shortens the series, so the holdout has to be taken from the end
    # of what is left rather than from a fixed position. The alternative, fixing
    # the index, scores a different set of weeks for this treatment than for the
    # others and makes the comparison meaningless.
    start = max(1, len(cleaned) - HOLDOUT)
    predictions = forecast(cleaned, model, start)
    target = history.underlying[-len(predictions) :]

    from dcc.generator import DATA_ERROR, REAL_EVENT

    return Outcome(
        item=history.item,
        detector=detector,
        treatment=treatment,
        model=model,
        wmape=wmape(target, predictions),
        flagged=int(flags.sum()),
        real_events_removed=int((flags & history.mask(REAL_EVENT)).sum()),
        data_errors_removed=int((flags & history.mask(DATA_ERROR)).sum()),
    )


def pipeline_outcomes(history: History) -> list[Outcome]:
    """Every detector, treatment and model combination on one item."""
    return [
        score_pipeline(history, detector, treatment, model)
        for detector, treatment, model in product(DETECTORS, TREATMENTS, MODELS)
    ]
