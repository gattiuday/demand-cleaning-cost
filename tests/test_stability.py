"""The committed receipts have to survive the last bit of a float moving.

CI runs the experiments on three Python versions and then requires the committed
output to match the run byte for byte. It failed on a mean written as
`0.23424355257555993` by one runner and `0.23424355257555995` by another: the
same measurement, summed in a different order by a different build of the
numerical stack. The gate was reporting the arithmetic environment rather than a
stale figure, which is not what it exists for.

`tools/stability.py` is the repair. These tests pin it, because the repair is
only worth anything if it is the property that holds rather than the property
that happened to hold on the runner that last wrote the files.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "docs" / "metrics.json"
EXPERIMENT_DIR = ROOT / "docs" / "experiments"

sys.path.insert(0, str(ROOT / "tools"))
from stability import SIGNIFICANT_DIGITS, stabilise  # noqa: E402


def _floats(payload) -> list[float]:
    """Every float anywhere inside a decoded JSON payload."""
    if isinstance(payload, bool | int):
        return []
    if isinstance(payload, float):
        return [payload]
    if isinstance(payload, dict):
        return [value for item in payload.values() for value in _floats(item)]
    if isinstance(payload, list):
        return [value for item in payload for value in _floats(item)]
    return []


def _published() -> list[Path]:
    return [METRICS, *sorted(EXPERIMENT_DIR.glob("*.json"))]


@pytest.mark.parametrize("path", _published(), ids=lambda p: p.name)
def test_every_committed_figure_is_already_stabilised(path):
    """The committed file equals what stabilising it would produce.

    This is the property the drift gate actually needs. If a committed figure
    still carries digits below the rounding, then a rerun on another runner can
    land on a different last digit and the gate fails on a repository that is
    entirely in order.
    """
    payload = json.loads(path.read_text())
    assert stabilise(payload) == payload, (
        f"{path.name} holds figures below the stabilised precision, so a rerun "
        "elsewhere can write a different last digit"
    )


@pytest.mark.parametrize("path", _published(), ids=lambda p: p.name)
def test_a_last_bit_difference_does_not_move_a_published_figure(path):
    """Nudge every committed float by one unit in the last place, both ways.

    This is the difference that broke the build, reproduced deliberately rather
    than waited for. A figure that moves under it would be one sitting on a
    rounding boundary, where the repair does not hold and the gate would go on
    failing intermittently.
    """
    values = _floats(json.loads(path.read_text()))
    assert values, f"{path.name} publishes no float, so this proves nothing"
    # An exact zero is excluded rather than quietly passed. The claim here is
    # about relative error, and a nudge off zero lands on the smallest number a
    # double can hold, which is a change of every digit rather than the last
    # one. A measurement that is exactly zero is planted, not summed.
    for value in (candidate for candidate in values if candidate != 0.0):
        for nudged in (math.nextafter(value, math.inf), math.nextafter(value, -math.inf)):
            assert stabilise(nudged) == stabilise(value), (
                f"{value!r} moves to {stabilise(nudged)!r} under a one bit change, "
                "so it sits on the rounding boundary"
            )


def test_a_difference_that_matters_still_shows():
    """Rounding must not be a way of not noticing.

    A gate that cannot see a changed figure is worse than one that fires on
    noise, so the thing to check is that the precision kept is far above
    anything published rather than merely convenient.
    """
    value = 0.23424355257555993
    assert stabilise(value * 1.001) != stabilise(value)
    assert stabilise(value + 10 ** (math.floor(math.log10(value)) - SIGNIFICANT_DIGITS + 1)) != (
        stabilise(value)
    )


def test_a_count_is_left_alone():
    """Rounding a count would misdescribe it: a count is exact."""
    assert stabilise(200_000) == 200_000
    assert isinstance(stabilise(97), int)
    assert stabilise(True) is True


def test_awkward_values_are_handled_rather_than_crashed_on():
    assert stabilise(0.0) == 0.0
    assert math.isnan(stabilise(float("nan")))
    assert stabilise(float("inf")) == float("inf")
    assert stabilise({"a": [1, 2.5000000000001], "b": "text"}) == {"a": [1, 2.5], "b": "text"}
