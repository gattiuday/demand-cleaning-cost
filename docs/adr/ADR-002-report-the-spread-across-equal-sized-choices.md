# ADR-002: Report the spread across equal sized choices

Status: accepted

## Context

This repository's second claim compares how much the forecast moves when the cleaning
changes against how much it moves when the model changes. The first version of that
comparison put nine cleaning pipelines, being three detectors times three treatments,
against three models, and reported that cleaning moved the forecast more.

That comparison is invalid and the direction of the invalidity is predictable. The range of
a set of options grows with the number of options for reasons that have nothing to do with
the decision mattering, so nine against three favours nine. Measured that way the cleaning
spread ran ahead of the model's 4.86 against, and the result reversed when the comparison was
made fairly.

## Decision

Measure the spread across one axis at a time with the other two held fixed, so every
comparison is three options against three options. The detector spread is measured for each
of the nine treatment and model combinations and averaged, the treatment spread for each of
the nine detector and model combinations, and the model spread for each of the nine
detector and treatment combinations.

Measured that way the model choice moves the forecast most, at 4.86 points, with the
detector at 3.95 and the treatment at 2.52.

## Consequences

The claim this repository can make is weaker than the one it was built to make, and is
stated as the weaker one. The model choice dominates. What survives is still worth saying:
two choices that no team documents, reviews or revisits sit within the same order of
magnitude as the one a team spends a project on, and one of them is four fifths of it.

The experiment's own docstring records the reversal, because a reader who finds the result
unsurprising should know that the obvious way of measuring it gives the other answer.

A fuller treatment would decompose the variance properly rather than comparing ranges, which
would also handle the interaction between the axes. Ranges are used here because they are
what a team comparing options actually experiences, and because a variance decomposition
over three levels per factor and twenty items per panel would be reporting a quantity with
wider error bars than the differences being compared.
