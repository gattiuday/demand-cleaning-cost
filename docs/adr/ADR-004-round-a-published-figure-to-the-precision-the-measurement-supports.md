# ADR-004: Round a published figure to the precision the measurement supports

Status: accepted

## Context

CI runs the experiments on three Python versions and then requires the committed output to
match the run, byte for byte. That gate is the one check that notices a receipt drifting
away from the run that produced it, and everything the README claims about its figures being
re-measured rests on it.

It began failing on a difference of one unit in the last place. The same mean, over the same
committed inputs, was written as `0.23424355257555993` by one runner and
`0.23424355257555995` by another. Nothing had changed and nothing was stale: a sum does not
associate identically under every build of the numerical stack, so a mean over a simulation
does not land on the same final bit everywhere.

The failure looked like a drift failure, which is the expensive part. A gate that fires for
a reason unrelated to what it guards teaches the person reading it to disregard it, and a
gate that is disregarded is not protecting anything.

Two repairs were available and only one of them is honest. The gate could have been loosened
to compare at display precision, which gives up the property that a committed figure traces
to a run. Or the figures could stop carrying digits that were never a claim.

Keeping seventeen digits of a simulated mean was never a precision claim. Nothing published
in this repository carries more than six, and a simulation of this size does not resolve
anything near that, so the digits that differed between runners were describing the runner.

## Decision

Every float written to a published file is rounded to six significant digits, at the two
points where published files are written: the experiment harness and the metrics collector.
Counts are left alone, because a count is exact and rounding one would misdescribe it.

Six is not a tuning parameter chosen until the build went green. It is above everything this
repository publishes and far above what the measurement resolves, and it is coarse enough
that the difference between two builds cannot reach it, by several orders of magnitude.

The gate itself is unchanged. It still demands byte equality, and it still fails when a
committed figure stops following from the code.

## Consequences

The property the gate needs is now a property of the files, so it is asserted directly rather
than hoped for. `tests/test_stability.py` takes every float in every published file, nudges
it by one unit in the last place in both directions, and requires the published value not to
move. It also requires every committed file to already equal its own stabilised form, which
is what makes a rerun elsewhere land in the same place, and it requires a difference large
enough to matter to still show, so the rounding cannot become a way of not noticing.

A figure sitting exactly on a rounding boundary would defeat this, and that is the case the
nudge test exists to catch. None of the figures published here sit on one.

An exactly zero measurement is excluded from the nudge test rather than quietly passed. The
claim is about relative error, and a nudge off zero changes every digit rather than the last
one. A figure that is exactly zero here is planted rather than summed.
