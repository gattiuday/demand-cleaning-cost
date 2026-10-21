"""The checks that make the figures mean anything, written before the prose."""

from __future__ import annotations

import numpy as np
import pytest

from dcc.compare import score_pipeline
from dcc.generator import DATA_ERROR, ORDINARY, REAL_EVENT, generate_panel
from dcc.models import MODELS
from dcc.outliers import DETECTORS, detect
from dcc.treatments import TREATMENTS


def test_every_observation_carries_exactly_one_label(panel):
    for history in panel:
        assert set(history.labels) <= {ORDINARY, REAL_EVENT, DATA_ERROR}
        assert history.real_events + history.data_errors < history.periods


def test_a_real_event_is_in_the_underlying_series_and_an_error_is_not(panel):
    """The distinction the whole package rests on.

    A promotion happened and will recur, so it belongs in what a forecast should
    predict. A mis keyed quantity did not happen at all, so it does not. The
    generator puts the first in `underlying` and keeps the second out of it.
    """
    for history in panel:
        events = history.mask(REAL_EVENT)
        errors = history.mask(DATA_ERROR)
        assert np.all(history.observed[events] == history.underlying[events])
        if errors.any():
            assert not np.all(history.observed[errors] == history.underlying[errors])


def test_no_week_is_both_a_promotion_and_an_error(panel):
    """They are generated as disjoint sets, and a grader needs them to be.

    A week that was both would be counted in each rate and the two would no
    longer be a partition of what a rule removes.
    """
    for history in panel:
        assert not (history.mask(REAL_EVENT) & history.mask(DATA_ERROR)).any()


@pytest.mark.parametrize("rule", list(DETECTORS))
def test_no_rule_separates_the_two_kinds(rule, panel):
    """The finding, pinned. Every rule that catches errors also removes events.

    The z score rule is the exception at the gentle end: it removes almost no
    events and catches only a third of the errors. What no rule does is catch
    most of the errors while leaving the events alone, and that is the claim.
    """
    errors = events = hits = losses = 0
    for history in panel:
        flags = detect(history.observed, rule)
        errors += history.data_errors
        events += history.real_events
        hits += int((flags & history.mask(DATA_ERROR)).sum())
        losses += int((flags & history.mask(REAL_EVENT)).sum())
    caught = hits / errors
    destroyed = losses / events
    assert not (caught > 0.6 and destroyed < 0.2), (
        f"{rule} caught {caught:.1%} of errors while destroying only {destroyed:.1%} of "
        "events, which would refute this repository's central claim"
    )


def test_cleaning_a_history_with_no_errors_can_only_remove_signal(clean_history):
    """The control. With nothing to find, everything found is a loss.

    If a rule flagged nothing here it would be doing no harm, and none of them
    flag nothing.
    """
    assert clean_history.data_errors == 0
    flagged = {rule: int(detect(clean_history.observed, rule).sum()) for rule in DETECTORS}
    assert sum(flagged.values()) > 0, "no rule flags anything on a clean history"


def test_the_score_target_is_the_demand_that_will_recur(history):
    """Scoring against `underlying` rather than `observed` or a cleaned series.

    Against `observed` a forecast would be rewarded for predicting data errors.
    Against a cleaned series it would be rewarded for whatever the cleaning did,
    which is the thing being measured, so the comparison would assume its answer.
    """
    outcome = score_pipeline(history, "mad", "median", "trailing_mean")
    assert 0.0 < outcome.wmape < 5.0
    assert outcome.real_events_removed + outcome.data_errors_removed <= outcome.flagged


def test_nothing_in_the_detectors_or_treatments_reads_a_label():
    """Enforced by reading the source, because the grading depends on it."""
    import inspect

    from dcc import outliers, treatments

    for module in (outliers, treatments):
        code = inspect.getsource(module)
        for token in ("label", "REAL_EVENT", "DATA_ERROR", "underlying"):
            assert token not in code, f"{module.__name__} mentions {token}"


def test_every_pipeline_produces_a_score_on_every_item(panel):
    """Nine cleaning pipelines times three models, and none of them may error.

    A pipeline that raised on some items would be scored on a different subset
    from the others and the comparison in exp02 would be between samples.
    """
    expected = len(DETECTORS) * len(TREATMENTS) * len(MODELS)
    for history in panel[:5]:
        from dcc.compare import pipeline_outcomes

        outcomes = pipeline_outcomes(history)
        assert len(outcomes) == expected
        assert all(np.isfinite(outcome.wmape) for outcome in outcomes)


def test_the_small_errors_are_the_same_size_as_the_real_events():
    """Why no rule can separate them, measured rather than argued.

    A doubled posting is twice the week's demand. A promotion on this fixture is
    between one and a half and three and a half times the item's ordinary level.
    The commonest error and the signal most worth keeping overlap.
    """
    sizes = []
    for history in generate_panel(items=30):
        ordinary = history.underlying[history.labels == ORDINARY]
        level = float(np.median(ordinary))
        if level > 0:
            sizes.extend(list(history.underlying[history.mask(REAL_EVENT)] / level))
    sizes = np.array(sizes)
    assert np.percentile(sizes, 10) < 2.0 < np.percentile(sizes, 90)


def test_a_history_whose_columns_disagree_in_length_is_refused():
    from dcc.errors import UnusableHistory
    from dcc.generator import History

    with pytest.raises(UnusableHistory, match="same length"):
        History(
            item="SKU-X",
            observed=np.array([1.0, 2.0]),
            underlying=np.array([1.0, 2.0]),
            labels=np.array([ORDINARY], dtype=object),
        )


def test_an_empty_history_is_refused():
    from dcc.errors import UnusableHistory
    from dcc.generator import History

    with pytest.raises(UnusableHistory, match="empty history"):
        History(
            item="SKU-X",
            observed=np.array([]),
            underlying=np.array([]),
            labels=np.array([], dtype=object),
        )


def test_a_history_shorter_than_a_year_is_refused():
    """A seasonal pattern cannot be separated from the level in less than one."""
    from dcc.errors import UnusableHistory
    from dcc.generator import generate_history

    with pytest.raises(UnusableHistory, match="less than a year"):
        generate_history("SKU-SHORT", periods=20)


@pytest.mark.parametrize("rate", [0.8, -0.1])
def test_an_implausible_event_rate_is_refused(rate):
    from dcc.errors import UnusableHistory
    from dcc.generator import generate_history

    with pytest.raises(UnusableHistory, match="not a plausible share"):
        generate_history("SKU-X", error_rate=rate)
