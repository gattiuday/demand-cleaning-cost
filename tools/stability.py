"""Round a measured figure to a precision the measurement actually supports.

CI runs the experiments on three Python versions and then requires the committed
output to match the run byte for byte. That gate failed on a difference of one
unit in the last place: the same mean, over the same inputs, written as
`0.23424355257555993` by one runner and `0.23424355257555995` by another. A sum
does not associate identically under every build of the numerical stack, and
nothing here had ever claimed it would.

Keeping seventeen digits of a simulated mean was not a precision claim in the
first place. No figure published in this repository carries more than six, so
the digits that differed were describing the runner rather than the result, and
a gate meant to catch a stale figure was reporting the floating point
environment instead. Loosening the gate would have been the wrong repair: it is
the one check that notices a committed receipt drifting away from the run that
produced it.

Six significant digits is more than anything published here and more than a
simulation of this size resolves, and it is coarse enough that the difference
between two builds cannot reach it. Integers are left alone, because a count is
exact and rounding one would misdescribe what it is.
"""

from __future__ import annotations

import math

#: Past this, a figure describes the arithmetic rather than the world.
SIGNIFICANT_DIGITS = 6


def stabilise(value):
    """Return `value` with every float inside it rounded to `SIGNIFICANT_DIGITS`.

    Walks dicts and lists, so an experiment payload can be passed whole.
    """
    if isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or value == 0.0:
            return value
        return round(value, SIGNIFICANT_DIGITS - 1 - math.floor(math.log10(abs(value))))
    if isinstance(value, dict):
        return {key: stabilise(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [stabilise(item) for item in value]
    return value
