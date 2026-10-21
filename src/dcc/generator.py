"""A demand history with every unusual observation labelled, so cleaning can be graded.

An outlier in a demand history is one of two things and the series does not say
which. It is a real event, which happened and will happen again on the same
occasions: a promotion, a bulk order, a competitor out of stock. Or it is a data
error, which did not happen at all: a quantity keyed in the wrong unit, an order
posted twice, a return booked as a sale.

The two look identical. Both are a large value next to small ones. A cleaner
sees the value and nothing else, and whatever it does it does to both.

This generator plants both kinds and records which is which. `outliers.py` and
`treatments.py` never see the labels; `experiments/exp02` grades the detection
against them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from dcc.errors import UnusableHistory

__all__ = ["DEFAULT_SEED", "History", "generate_history", "generate_panel"]

DEFAULT_SEED = 20261021

#: Labels. `none` is an ordinary observation; the other two are the pair the
#: whole repository is about.
ORDINARY = "ordinary"
REAL_EVENT = "real_event"
DATA_ERROR = "data_error"


@dataclass(frozen=True)
class History:
    """One item's weekly demand, with the truth about every observation.

    `observed` is what a planning system holds. `underlying` is the demand
    without the data errors but with the real events, which is what a forecast
    should be trying to predict: a promotion that will recur is signal, and
    removing it makes the forecast wrong on the next promotion.
    """

    item: str
    observed: np.ndarray
    underlying: np.ndarray
    labels: np.ndarray
    promo_weeks: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))

    def __post_init__(self) -> None:
        lengths = {len(self.observed), len(self.underlying), len(self.labels)}
        if len(lengths) != 1:
            raise UnusableHistory(
                f"{self.item}: observed, underlying and labels must be the same length, "
                f"got {sorted(lengths)}"
            )
        if len(self.observed) == 0:
            raise UnusableHistory(f"{self.item}: an empty history cannot be cleaned")

    @property
    def periods(self) -> int:
        return len(self.observed)

    def mask(self, label: str) -> np.ndarray:
        return self.labels == label

    @property
    def real_events(self) -> int:
        return int(self.mask(REAL_EVENT).sum())

    @property
    def data_errors(self) -> int:
        return int(self.mask(DATA_ERROR).sum())


def generate_history(
    item: str,
    periods: int = 156,
    base: float = 220.0,
    seasonal_amplitude: float = 0.25,
    noise: float = 0.18,
    promo_rate: float = 0.08,
    promo_lift: float = 2.4,
    error_rate: float = 0.03,
    seed: int = DEFAULT_SEED,
) -> History:
    """Three years of weekly demand with promotions and data errors planted.

    `promo_rate` and `error_rate` are deliberately of the same order. A history
    where errors vastly outnumbered real events would make cleaning obviously
    right, and one where they were rare would make it obviously harmless. The
    interesting case is the ordinary one, where both happen and a detector
    cannot distinguish them.
    """
    if periods < 52:
        raise UnusableHistory(
            f"{item}: {periods} weeks is less than a year, so a seasonal pattern cannot be "
            "separated from the level and any cleaning rule is measuring the window"
        )
    for name, rate in (("promo_rate", promo_rate), ("error_rate", error_rate)):
        if not 0.0 <= rate < 0.5:
            raise UnusableHistory(f"{name} of {rate} is not a plausible share of weeks")

    rng = np.random.default_rng(seed)
    week = np.arange(periods)
    seasonal = 1.0 + seasonal_amplitude * np.sin(2 * np.pi * week / 52.0)
    level = base * seasonal * rng.lognormal(0.0, noise, periods)

    labels = np.full(periods, ORDINARY, dtype=object)

    # Real events: promotions, which recur and are signal. The weeks are
    # recorded because a forecaster that knows the promotion calendar is a
    # different and much easier problem, and this repository is about the one
    # where the calendar is not in the demand table.
    promo = rng.random(periods) < promo_rate
    level = np.where(promo, level * promo_lift, level)
    labels[promo] = REAL_EVENT

    underlying = level.copy()

    # Data errors: three kinds, each of which really happens in order tables.
    errors = (rng.random(periods) < error_rate) & ~promo
    kinds = rng.integers(0, 3, periods)
    observed = underlying.copy()
    observed[errors & (kinds == 0)] *= 1000.0  # a quantity keyed in units not cases
    observed[errors & (kinds == 1)] *= 2.0  # an order posted twice
    observed[errors & (kinds == 2)] *= 0.1  # a return booked against the sale
    labels[errors] = DATA_ERROR

    return History(
        item=item,
        observed=np.round(observed, 3),
        underlying=np.round(underlying, 3),
        labels=labels,
        promo_weeks=np.flatnonzero(promo),
    )


def generate_panel(
    items: int = 40, periods: int = 156, seed: int = DEFAULT_SEED, error_rate: float = 0.03
) -> list[History]:
    """A panel whose items differ in level, volatility and promotion intensity."""
    rng = np.random.default_rng(seed)
    return [
        generate_history(
            item=f"SKU-{index:03d}",
            periods=periods,
            base=float(rng.uniform(60.0, 900.0)),
            seasonal_amplitude=float(rng.uniform(0.1, 0.4)),
            noise=float(rng.uniform(0.12, 0.3)),
            promo_rate=float(rng.uniform(0.04, 0.14)),
            promo_lift=float(rng.uniform(1.8, 3.2)),
            error_rate=error_rate,
            seed=seed + 601 * index,
        )
        for index in range(items)
    ]
