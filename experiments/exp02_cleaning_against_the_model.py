"""Does the cleaning choice move the forecast as much as the model choice?

A team choosing a forecasting model runs a bake off, writes it up and revisits
it. A team choosing an outlier rule picks the default and never looks again. This
measures whether that allocation of attention matches where the error is.

The comparison has to be like for like. Three detectors, three treatments and
three models, and the spread measured across one axis at a time with the other
two held fixed, because a range over nine options is wider than a range over
three for reasons that have nothing to do with the choice mattering. An earlier
version of this experiment compared nine cleaning pipelines against three models
and found cleaning ahead; it is behind on the comparison that is fair.
"""

from __future__ import annotations

import collections

import numpy as np
from _harness import HEADLINE_RATE, ITEMS, REPLICATIONS, emit

from dcc.compare import pipeline_outcomes
from dcc.generator import DEFAULT_SEED, generate_panel
from dcc.models import MODELS
from dcc.outliers import DETECTORS
from dcc.treatments import TREATMENTS


def main() -> None:
    spreads = {"detector": [], "treatment": [], "model": []}
    bests, worsts = [], []
    for replication in range(REPLICATIONS):
        panel = generate_panel(
            items=ITEMS, seed=DEFAULT_SEED + 4_441 * replication, error_rate=HEADLINE_RATE
        )
        scored = collections.defaultdict(list)
        for history in panel:
            for outcome in pipeline_outcomes(history):
                scored[(outcome.detector, outcome.treatment, outcome.model)].append(outcome.wmape)
        mean = {key: float(np.mean(values)) for key, values in scored.items()}

        for treatment in TREATMENTS:
            for model in MODELS:
                values = [mean[(d, treatment, model)] for d in DETECTORS]
                spreads["detector"].append(max(values) - min(values))
        for detector in DETECTORS:
            for model in MODELS:
                values = [mean[(detector, t, model)] for t in TREATMENTS]
                spreads["treatment"].append(max(values) - min(values))
        for detector in DETECTORS:
            for treatment in TREATMENTS:
                values = [mean[(detector, treatment, m)] for m in MODELS]
                spreads["model"].append(max(values) - min(values))

        bests.append(min(mean.values()))
        worsts.append(max(mean.values()))

    measured = {
        axis: {"mean": float(np.mean(values)), "max": float(max(values))}
        for axis, values in spreads.items()
    }
    emit(
        "exp02_cleaning_against_the_model",
        {
            "question": "does the cleaning choice move the forecast as much as the model choice",
            "replications": REPLICATIONS,
            "items_per_panel": ITEMS,
            "error_rate": HEADLINE_RATE,
            "spread_points": {
                axis: {"mean": values["mean"] * 100, "max": values["max"] * 100}
                for axis, values in measured.items()
            },
            "detector_over_model": measured["detector"]["mean"] / measured["model"]["mean"],
            "treatment_over_model": measured["treatment"]["mean"] / measured["model"]["mean"],
            "best_pipeline_wmape": float(np.mean(bests)),
            "worst_pipeline_wmape": float(np.mean(worsts)),
            "note": (
                "the model choice moves the forecast most, which is the opposite of what "
                "this experiment was built to show and is reported because it is what was "
                "measured. The detector choice moves it about four fifths as much and the "
                "treatment about half as much, on a like for like comparison of three "
                "options against three. That is the finding worth having: not that cleaning "
                "dominates, but that two undocumented defaults sit within the same order of "
                "magnitude as the decision a team spends a project on"
            ),
        },
        [
            (axis, f"{values['mean'] * 100:.2f}", f"{values['max'] * 100:.2f}")
            for axis, values in measured.items()
        ],
        ("choice, three options", "spread in WMAPE points", "worst case"),
    )


if __name__ == "__main__":
    main()
