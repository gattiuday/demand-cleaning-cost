"""Of what a cleaning rule removes, how much is error and how much is signal?

The question every outlier step answers implicitly and no outlier step is asked.
A promotion and a mis-keyed quantity are the same shape in a demand series, so a
rule that flags one flags the other, and the only way to know the split is to
have the labels. This fixture has them.

The two numbers worth reading are the share of the data errors a rule catches
and the share of the real events it destroys. Neither is interesting alone: a
rule that flags everything catches every error.
"""

from __future__ import annotations

import numpy as np
from _harness import ERROR_RATES, HEADLINE_RATE, ITEMS, REPLICATIONS, emit

from dcc.generator import DATA_ERROR, DEFAULT_SEED, REAL_EVENT, generate_panel
from dcc.outliers import DETECTORS, detect


def measure(rule: str, error_rate: float) -> dict:
    caught, destroyed, flagged, precision = [], [], [], []
    for replication in range(REPLICATIONS):
        panel = generate_panel(
            items=ITEMS, seed=DEFAULT_SEED + 4_441 * replication, error_rate=error_rate
        )
        errors = events = hits = losses = total = 0
        for history in panel:
            flags = detect(history.observed, rule)
            errors += history.data_errors
            events += history.real_events
            hits += int((flags & history.mask(DATA_ERROR)).sum())
            losses += int((flags & history.mask(REAL_EVENT)).sum())
            total += int(flags.sum())
        caught.append(hits / errors if errors else float("nan"))
        destroyed.append(losses / events if events else float("nan"))
        flagged.append(total)
        precision.append(hits / total if total else float("nan"))
    return {
        "errors_caught": float(np.nanmean(caught)) if error_rate > 0 else None,
        "real_events_destroyed": float(np.nanmean(destroyed)),
        "weeks_flagged": float(np.mean(flagged)),
        "share_of_flags_that_are_errors": float(np.nanmean(precision)) if error_rate > 0 else None,
    }


def main() -> None:
    series, rows = [], []
    for rate in ERROR_RATES:
        for rule in DETECTORS:
            entry = {"error_rate": rate, "rule": rule, **measure(rule, rate)}
            series.append(entry)
            if rate == HEADLINE_RATE:
                rows.append(
                    (
                        rule,
                        f"{entry['errors_caught']:.1%}",
                        f"{entry['real_events_destroyed']:.1%}",
                        f"{entry['share_of_flags_that_are_errors']:.1%}",
                        f"{entry['weeks_flagged']:.0f}",
                    )
                )

    headline = {row["rule"]: row for row in series if row["error_rate"] == HEADLINE_RATE}
    emit(
        "exp01_what_cleaning_removes",
        {
            "question": "of what a cleaning rule removes, how much is error and how much signal",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "headline_error_rate": HEADLINE_RATE,
            "series": series,
            "headline": headline,
            "best_at_catching_errors": max(
                headline, key=lambda rule: headline[rule]["errors_caught"]
            ),
            "gentlest_rule": min(
                headline, key=lambda rule: headline[rule]["real_events_destroyed"]
            ),
            # Real events destroyed for every data error caught, which is the
            # trade off stated as one number. This experiment originally
            # asserted that every rule destroys more events than it catches
            # errors; the z score rule does not, so the assertion was replaced
            # by the quantity it was trying to express.
            "events_destroyed_per_error_caught": {
                rule: row["real_events_destroyed"] / row["errors_caught"]
                for rule, row in headline.items()
            },
            "worst_share_of_flags_that_are_errors": min(
                row["share_of_flags_that_are_errors"] for row in headline.values()
            ),
            "best_share_of_flags_that_are_errors": max(
                row["share_of_flags_that_are_errors"] for row in headline.values()
            ),
            "note": (
                "the trade off is close to one for one and the rules sit at different "
                "points on it rather than at different qualities. The z score rule "
                "destroys the least and catches a third of the errors; the rolling "
                "interquartile rule catches three quarters and destroys three quarters. "
                "Under the two rules that catch most of the errors, the large majority of "
                "what is removed is real demand. That is not a tuning failure: a promotion "
                "and a mis keyed quantity are the same shape and a rule that sees only the "
                "series cannot separate them"
            ),
        },
        rows,
        (
            "rule",
            "errors caught",
            "real events destroyed",
            "flags that are errors",
            "weeks flagged",
        ),
    )


if __name__ == "__main__":
    main()
