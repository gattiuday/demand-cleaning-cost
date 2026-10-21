"""Which data errors can a rule actually find, by how big they are?

This was built to measure masking: the textbook objection that a z score rule
divides by a standard deviation the error itself inflates, so a large enough
error hides. At the error rates here that does not happen. Detection rises with
the size of the error and plateaus, for every rule.

What the sweep found instead is the more useful result and it is the reason this
experiment kept its place. The errors a rule cannot find are the small ones, and
the smallest error modelled here is a doubled posting, which is the single most
common error in an order table. It is also almost exactly the size of a
promotion. So the error most worth catching and the signal most worth keeping
are the same magnitude, and no rule reading only the series can prefer one.

The experiment also measures that overlap directly, because the claim above is
about this fixture's promotion sizes and should not be left as an assertion.
"""

from __future__ import annotations

import numpy as np
from _harness import ITEMS, REPLICATIONS, emit

from dcc.generator import DATA_ERROR, DEFAULT_SEED, REAL_EVENT, generate_panel
from dcc.outliers import DETECTORS, detect

#: Multipliers applied to a week's demand by a unit keying error.
MAGNITUDES = (2.0, 5.0, 20.0, 100.0, 1_000.0)


def panel_with_magnitude(magnitude: float, seed: int) -> list:
    """A panel whose data errors are all of one magnitude.

    The generator mixes three error kinds, so for this experiment the errors are
    reapplied at a single size. The labels come from the generator and are not
    recomputed, so an error is still an error wherever it was planted.
    """
    panel = generate_panel(items=ITEMS, seed=seed, error_rate=0.03)
    out = []
    for history in panel:
        mask = history.mask(DATA_ERROR)
        observed = history.underlying.copy()
        observed[mask] = history.underlying[mask] * magnitude
        out.append(
            type(history)(
                item=history.item,
                observed=np.round(observed, 3),
                underlying=history.underlying,
                labels=history.labels,
                promo_weeks=history.promo_weeks,
            )
        )
    return out


def main() -> None:
    series, rows = [], []
    for magnitude in MAGNITUDES:
        caught = {rule: [] for rule in DETECTORS}
        for replication in range(REPLICATIONS):
            panel = panel_with_magnitude(magnitude, DEFAULT_SEED + 4_441 * replication)
            for rule in DETECTORS:
                hits = total = 0
                for history in panel:
                    flags = detect(history.observed, rule)
                    mask = history.mask(DATA_ERROR)
                    hits += int((flags & mask).sum())
                    total += int(mask.sum())
                caught[rule].append(hits / total if total else float("nan"))
        entry = {
            "magnitude": magnitude,
            "errors_caught": {rule: float(np.nanmean(values)) for rule, values in caught.items()},
        }
        series.append(entry)
        rows.append((f"{magnitude:.0f}x", *(f"{entry['errors_caught'][r]:.1%}" for r in DETECTORS)))

    # How big a real event is on this fixture, against its own item's ordinary
    # level. The claim that the small errors and the real events are the same
    # size is about these numbers and is measured rather than asserted.
    sizes = []
    for replication in range(REPLICATIONS):
        for history in generate_panel(
            items=ITEMS, seed=DEFAULT_SEED + 4_441 * replication, error_rate=0.03
        ):
            ordinary = history.underlying[history.labels == "ordinary"]
            if len(ordinary) == 0:
                continue
            level = float(np.median(ordinary))
            if level > 0:
                sizes.extend(list(history.underlying[history.mask(REAL_EVENT)] / level))
    sizes = np.array(sizes)

    first, last = series[0]["errors_caught"], series[-1]["errors_caught"]
    emit(
        "exp03_which_errors_are_findable",
        {
            "question": "does a larger data error become easier or harder for a rule to find",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "magnitudes": list(MAGNITUDES),
            "series": series,
            "zscore_at_smallest": first["zscore"],
            "zscore_at_largest": last["zscore"],
            "mad_at_largest": last["mad"],
            "zscore_detection_falls_with_magnitude": bool(last["zscore"] < first["zscore"]),
            "real_event_size_median": float(np.median(sizes)),
            "real_event_size_p10": float(np.percentile(sizes, 10)),
            "real_event_size_p90": float(np.percentile(sizes, 90)),
            "real_events_within_the_doubling_band": float(((sizes > 1.5) & (sizes < 3.0)).mean()),
            "note": (
                "masking does not appear at these error rates: detection rises with the "
                "size of the error and plateaus, for every rule, which is the opposite of "
                "what this experiment was built to find. What it shows instead is that the "
                "undetectable errors are the small ones, and a doubled posting at twice the "
                "week's demand is both the commonest error in an order table and almost "
                "exactly the size of a promotion on this fixture. A rule reading only the "
                "series has nothing to prefer one with"
            ),
        },
        rows,
        ("error size", *DETECTORS),
    )


if __name__ == "__main__":
    main()
