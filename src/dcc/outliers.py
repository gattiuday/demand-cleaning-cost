"""Three detection rules, and the one thing none of them can do.

Each rule flags observations that are far from the rest. None of them can tell a
promotion from a typo, because the two are the same shape: a large value next to
small ones. What separates them is why it happened, and that is not in the
series.

The rules are the ones planning systems actually use. A z score on the level is
the textbook rule and the worst behaved, because the outliers it is looking for
inflate the standard deviation it measures them against. A median absolute
deviation rule fixes that by using statistics the outliers cannot move much. A
rolling interquartile rule handles a series whose level shifts, at the cost of a
window length nobody can justify from the data.
"""

from __future__ import annotations

import numpy as np

from dcc.errors import UnusableHistory

__all__ = ["DETECTORS", "detect", "iqr_rolling", "mad_rule", "zscore_rule"]

#: Threshold in standard deviations for the z score rule. Three is the number
#: everyone uses and nobody defends.
Z_THRESHOLD = 3.0

#: Threshold in median absolute deviations. 3.5 is Iglewicz and Hoaglin's
#: recommendation and is a declared convention, not a measurement.
MAD_THRESHOLD = 3.5

#: Multiplier on the interquartile range, and the window it is computed over.
IQR_MULTIPLIER = 1.5
IQR_WINDOW = 13

#: Scaling that makes a median absolute deviation comparable to a standard
#: deviation under normality. The assumption is normality and the data here is
#: lognormal with spikes, which is the usual situation and is why the constant
#: is named rather than inlined.
MAD_TO_SIGMA = 0.6745


def zscore_rule(values: np.ndarray, threshold: float = Z_THRESHOLD) -> np.ndarray:
    """Flag observations more than `threshold` standard deviations from the mean.

    Note what inflates the standard deviation: the observations being looked
    for. One value a thousand times the others raises the mean and raises the
    standard deviation more, so the rule can fail to flag the thing that broke
    it while flagging ordinary weeks around it. That is masking, it is the
    textbook objection to this rule, and `experiments/exp02` measures it rather
    than asserting it.
    """
    _validate(values)
    spread = values.std(ddof=1) if len(values) > 1 else 0.0
    if spread == 0:
        return np.zeros(len(values), dtype=bool)
    return np.abs(values - values.mean()) > threshold * spread


def mad_rule(values: np.ndarray, threshold: float = MAD_THRESHOLD) -> np.ndarray:
    """Flag by median absolute deviation, which the outliers cannot inflate."""
    _validate(values)
    median = np.median(values)
    deviation = np.median(np.abs(values - median))
    if deviation == 0:
        # More than half the observations are identical. A rule based on the
        # spread of the middle has no spread to work with, and flagging
        # everything that differs would flag ordinary variation. Reported as
        # nothing detected rather than as everything.
        return np.zeros(len(values), dtype=bool)
    return np.abs(values - median) / (deviation / MAD_TO_SIGMA) > threshold


def iqr_rolling(
    values: np.ndarray, window: int = IQR_WINDOW, multiplier: float = IQR_MULTIPLIER
) -> np.ndarray:
    """Flag against the interquartile range of a trailing window.

    Handles a level that shifts, which the other two do not. The window length
    is the problem: short enough to track a shift is short enough that a cluster
    of promotions becomes the normal range and stops being flagged, and long
    enough to be stable is long enough to miss the shift.
    """
    _validate(values)
    if window < 4:
        raise UnusableHistory(f"an interquartile window of {window} has no quartiles")
    flags = np.zeros(len(values), dtype=bool)
    for index in range(len(values)):
        start = max(0, index - window)
        past = values[start:index]
        if len(past) < 4:
            continue
        lower, upper = np.percentile(past, [25, 75])
        spread = upper - lower
        flags[index] = values[index] < lower - multiplier * spread or (
            values[index] > upper + multiplier * spread
        )
    return flags


def _validate(values: np.ndarray) -> None:
    if values.ndim != 1:
        raise UnusableHistory(f"a demand history must be one dimensional, got shape {values.shape}")
    if len(values) == 0:
        raise UnusableHistory("an empty history has no outliers")


DETECTORS = {
    "zscore": zscore_rule,
    "mad": mad_rule,
    "iqr_rolling": iqr_rolling,
}


def detect(values: np.ndarray, rule: str) -> np.ndarray:
    if rule not in DETECTORS:
        raise UnusableHistory(f"unknown detector '{rule}'; expected one of {', '.join(DETECTORS)}")
    return DETECTORS[rule](values)
