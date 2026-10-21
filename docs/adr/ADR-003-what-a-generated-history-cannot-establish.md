# ADR-003: What a generated demand history cannot establish

Status: accepted

## Context

The labels are planted. A real demand history has one quantity column and nothing that says
which unusual weeks were promotions. This is the inventory of which claims survive leaving
the fixture.

## Claims the fixture establishes

- **A cleaning rule reading only the series cannot separate a real event from a data error.**
  Definitional, and the sizes measured here show why: the commonest error is the same
  magnitude as the signal.
- **Removing a real event makes a forecast of recurring demand worse.** Follows from the
  target being the demand that recurs, which is ADR-001.
- **A rule that catches more errors removes more events.** The trade off is close to one for
  one on this fixture and its existence follows from the shapes being identical.

## Claims the fixture establishes only conditionally

- **The specific detection rates.** A third of errors caught by the z score rule and three
  quarters by the rolling interquartile rule are properties of this error mix, this
  promotion rate and these thresholds.
- **That the small errors are undetectable while the large ones are trivial.** The direction
  is general; the crossover sits where the error size stops overlapping the promotion size,
  and both are this fixture's.
- **The spread comparison in ADR-002.** Three particular detectors against three particular
  models. A team with a well tuned seasonal model and a single crude cleaning default would
  find a larger gap; one with the reverse, smaller.
- **That masking does not occur.** It did not at these error rates and it is a real
  phenomenon. A series with one enormous error and a short window would show it.

## Claims this repository does not make

- **That any real history has this error mix.** Nothing here reads a real history.
- **That cleaning should not be done.** The errors are real and leaving them in is also
  costly; this measures the cost of the usual remedy rather than recommending against it.
  What follows is narrower: the cleaning rule is a modelling decision and should be chosen
  and reviewed like one.
- **That a promotion calendar would not solve this.** It largely would, and that is the
  obvious fix: a system that knows which weeks were promoted can protect them and clean the
  rest. The problem this repository measures is the one that exists because the calendar is
  not in the demand table, which is the common case rather than a necessary one.
- **Anything about the one off real event.** ADR-001 names it as the largest simplification
  here.

## Consequences

A team wanting to know whether this applies to them can run `dcc grade` on a history where
the promoted weeks are known from a calendar, treating the calendar as the labels. That is
the real world version of this fixture and it needs no generated data.
