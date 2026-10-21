# ADR-001: Label the two kinds of outlier, and never let a rule see the label

Status: accepted

## Context

An unusual observation in a demand history is one of two things. It is a real event, which
happened and will happen again on the same occasions: a promotion, a bulk order, a
competitor out of stock. Or it is a data error, which did not happen at all: a quantity
keyed in units rather than cases, an order posted twice, a return booked against a sale.

A cleaning step removes unusual observations. It cannot distinguish the two, because from
the series they are the same shape, and the thing that separates them is why they happened.

Measuring what cleaning costs therefore requires knowing which is which, which requires
planting both.

## Decision

`generator.py` plants real events and data errors as disjoint sets and records the label of
every week. The real events are in `underlying`, which is the series a forecast is scored
against, and the data errors are not. That target choice is the one that makes the
measurement mean anything: a promotion that recurs is signal, so a forecast that has had
promotions cleaned out of it will be short on the next one.

`outliers.py` and `treatments.py` never see the labels or `underlying`. A test reads their
source and fails if either mentions `label`, `REAL_EVENT`, `DATA_ERROR` or `underlying`,
because a rule graded against an input it has already seen is not graded at all.

## Consequences

Every figure about detection is a comparison against ground truth rather than against another
rule, which is the only comparison worth making: two rules that both remove mostly real
demand agree with each other.

The cost is that nothing here runs on a real history and produces a detection figure. What
a real history supports is `dcc compare`, which ranks the pipelines by forecast error without
needing labels, and that ranking is exactly the thing exp02 shows to be a weaker guide than
it looks.

What this does not model is a third category that certainly exists: an observation that is a
real event nobody will ever repeat. A one off bulk order from a customer who has since left
is signal in the sense that it happened and noise in the sense that predicting it is wrong.
Treating it as either would be a decision this fixture does not make, and it is the largest
simplification here.
