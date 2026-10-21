"""What to do with a flagged observation, which is a second choice nobody records.

A cleaning step is two decisions and planning systems document the first. Having
flagged a week, the system drops it, caps it at a percentile, or replaces it with
a local median, and each of those does something different to a forecast fitted
afterwards.

Dropping shortens the series, which matters for anything seasonal. Capping keeps
the week and keeps part of the signal, which is the point and also means a real
promotion is still partly there. Replacing by the median keeps the week and
removes the signal entirely.
"""

from __future__ import annotations

import numpy as np

from dcc.errors import UnusableHistory

__all__ = ["TREATMENTS", "cap_at_percentile", "drop", "replace_with_median", "treat"]

#: Percentile the capping treatment caps at. A convention.
CAP_PERCENTILE = 95.0

#: Half width of the window the median replacement uses.
MEDIAN_WINDOW = 6


def drop(values: np.ndarray, flags: np.ndarray) -> np.ndarray:
    """Remove the flagged weeks, returning a shorter series.

    The only treatment that changes the length, which is why it is the one that
    quietly breaks a seasonal model: the weeks that remain are no longer evenly
    spaced and a method indexing by position is now indexing the wrong weeks.
    """
    _validate(values, flags)
    if flags.all():
        raise UnusableHistory("every observation is flagged, so dropping leaves nothing")
    return values[~flags]


def cap_at_percentile(
    values: np.ndarray, flags: np.ndarray, percentile: float = CAP_PERCENTILE
) -> np.ndarray:
    """Cap the flagged weeks at a percentile of the unflagged ones."""
    _validate(values, flags)
    if flags.all():
        raise UnusableHistory("every observation is flagged, so there is no level to cap at")
    ceiling = float(np.percentile(values[~flags], percentile))
    out = values.astype(float).copy()
    out[flags] = np.minimum(out[flags], ceiling)
    return out


def replace_with_median(
    values: np.ndarray, flags: np.ndarray, window: int = MEDIAN_WINDOW
) -> np.ndarray:
    """Replace each flagged week with the median of the unflagged weeks around it."""
    _validate(values, flags)
    if flags.all():
        raise UnusableHistory("every observation is flagged, so there is no median to use")
    out = values.astype(float).copy()
    for index in np.flatnonzero(flags):
        start, stop = max(0, index - window), min(len(values), index + window + 1)
        local = values[start:stop][~flags[start:stop]]
        out[index] = float(np.median(local)) if len(local) else float(np.median(values[~flags]))
    return out


def _validate(values: np.ndarray, flags: np.ndarray) -> None:
    if values.shape != flags.shape:
        raise UnusableHistory(
            f"values and flags must have the same shape, got {values.shape} and {flags.shape}"
        )


TREATMENTS = {
    "drop": drop,
    "cap": cap_at_percentile,
    "median": replace_with_median,
}


def treat(values: np.ndarray, flags: np.ndarray, treatment: str) -> np.ndarray:
    if treatment not in TREATMENTS:
        raise UnusableHistory(
            f"unknown treatment '{treatment}'; expected one of {', '.join(TREATMENTS)}"
        )
    return TREATMENTS[treatment](values, flags)
