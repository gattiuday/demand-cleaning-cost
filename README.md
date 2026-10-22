# demand-cleaning-cost

**An outlier in a demand history is either a promotion or a typo, and the series does not say which. On this fixture the commonest data error is twice a normal week and the median promotion is 2.44 times a normal week, so they are the same size. Every rule that catches most of the errors removes most of the promotions with them, and under the rule that catches the most, 85.5% of what it removes is real demand.**

[![CI](https://github.com/GITHUB_USERNAME/demand-cleaning-cost/actions/workflows/ci.yml/badge.svg)](https://github.com/GITHUB_USERNAME/demand-cleaning-cost/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Tests](https://img.shields.io/badge/tests-108-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## The thing a demand series cannot tell you

Two weeks both show four times the usual volume. One was a promotion, which will happen
again next time the promotion runs, and is therefore the most informative week in the
series. One was an order keyed in units rather than cases, which never happened at all.

A detection rule sees two large values. Whatever it decides, it decides for both, and no
amount of tuning changes that, because what separates them is not in the data. The
information that would separate them is a promotion calendar, which is not in the demand
table.

So the cleaning step at the front of every forecasting pipeline is making a decision it
cannot make, on every history, every week, with no record of having made it.

## The uncomfortable numbers

Measured across six independent panels of 20 items over 156 weeks each, with three weeks in
a hundred carrying a data error:

- **The textbook rule catches 34.9% of the errors and destroys 5.6% of the promotions. The
  rolling interquartile rule catches 77.2% of them and destroys 76.8%.** The trade off is
  close to one for one, and the three rules sit at different points on it rather than being
  of different quality.
- **Under the rule that catches the most errors, 85.5% of what it removes is real demand.**
  That falls to 35.7% under the gentlest rule, which also finds a third of the errors.
- **A doubled posting is caught 9.2% of the time and 95.2% at a thousandfold.** The errors
  a rule cannot find are the small ones, and a doubled posting is the commonest error in an
  order table. The median promotion is 2.44 times a normal week and 65.7% of promotions fall
  between one and a half and three times, which is the same band.
- **The model choice moves the forecast 4.86 points of WMAPE; the detector moves it 3.95
  points and the treatment 2.52 points.** On a like for like comparison the model dominates,
  and the detector is still 81% of the model's effect. One of those decisions gets a bake
  off and a write up. The other is a default.

108 tests, 100.00% line coverage, and every figure above is re-measured by CI and checked
against this document in both directions on every push.

## Claim 1: a rule cannot catch errors without removing signal

<!-- generated: detection-table.md -->
| Rule | Data errors caught | Real events destroyed | Share of what it removes that was real demand |
| --- | --- | --- | --- |
| iqr_rolling | 77.2% | 76.8% | 85.5% |
| mad | 49.7% | 59.6% | 81.1% |
| zscore | 34.9% | 5.6% | 35.7% |
<!-- end generated: detection-table.md -->

The last column is the one to read. It is the share of what each rule removes that was real
demand, and it is not computable from a real history, because it needs to know which weeks
were promotions.

The z score rule is the interesting case rather than the worst one. It is the textbook
default, it removes almost nothing, and it finds a third of the errors; it is gentle because
it is nearly blind. The rules that find errors find them by flagging more, and most of what
they flag is signal.

**Nothing here says cleaning should not be done.** The errors are real and leaving them in
costs something too. What follows is narrower and is the point of the repository: the
cleaning rule is a modelling decision with a measurable cost, and it is the one decision in
a forecasting pipeline that is never chosen, reviewed or revisited.

## Claim 2: the errors you cannot find are the ones you have

<!-- generated: magnitude-table.md -->
| Error size | iqr_rolling | mad | zscore |
| --- | --- | --- | --- |
| 2x | 59.7% | 32.9% | 9.2% |
| 5x | 94.1% | 98.9% | 76.3% |
| 20x | 97.1% | 100.0% | 93.8% |
| 100x | 97.1% | 100.0% | 95.2% |
| 1000x | 97.1% | 100.0% | 95.2% |
<!-- end generated: magnitude-table.md -->

This table was built to measure masking, the textbook objection that a z score rule divides
by a standard deviation the outlier inflates, so a large enough error hides itself. **It does
not happen here.** Detection rises with the size of the error and plateaus, for every rule,
and the experiment says so rather than quietly dropping the question.

What the sweep shows instead is more useful. The undetectable errors are the small ones, and
the small ones are the common ones: an order posted twice is the single most frequent error
in an order table and it is twice the week's demand. A promotion is between one and a half
and three times. **The error most worth catching and the signal most worth keeping are the
same magnitude**, and a rule reading only the series has nothing to prefer one with.

## Claim 3: the cleaning choice is of the same order as the model choice

<!-- generated: spread-table.md -->
| Choice, three options each | Spread in WMAPE points | Worst case |
| --- | --- | --- |
| detector | 3.95 | 9.17 |
| model | 4.86 | 9.18 |
| treatment | 2.52 | 9.29 |
<!-- end generated: spread-table.md -->

Three options on each axis, with the other two held fixed, because a range over nine options
is wider than a range over three for reasons that have nothing to do with the decision
mattering. The first version of this comparison put nine cleaning pipelines against three
models and found cleaning ahead;
[ADR-002](docs/adr/ADR-002-report-the-spread-across-equal-sized-choices.md) records the
reversal, because a reader who finds this result unsurprising should know that the obvious
way of measuring it gives the other answer.

The model wins. The detector is four fifths of it and the treatment half. The claim this
supports is not that cleaning dominates forecasting, it is that two undocumented defaults
sit in the same range as the decision a team spends a project on.

## What is in the fixture

20 items over 156 weeks of weekly demand, with a seasonal cycle, lognormal noise,
promotions drawn at four to fourteen weeks in a hundred, and data errors of three kinds that
really occur in order tables: a quantity keyed in units rather than cases, an order posted
twice, and a return booked against the sale. Every week carries its label.

Real events and data errors are disjoint sets, and the real events are in the series a
forecast is scored against while the errors are not. That target choice is what makes the
measurement mean anything and is
[ADR-001](docs/adr/ADR-001-label-the-two-kinds-of-outlier-and-never-let-a-rule-see-the-label.md).

## What this cannot measure

- **The one off real event.** A bulk order from a customer who has since left happened, so
  it is not an error, and predicting it is wrong, so it is not signal either. This fixture
  has no such category and that is its largest simplification.
- **Whether a promotion calendar would fix this.** It largely would. The problem here exists
  because the calendar is not in the demand table, which is the common case and not a
  necessary one.
- **Any real history's error mix.** Nothing here reads one.
  [ADR-003](docs/adr/ADR-003-what-a-generated-history-cannot-establish.md) separates the
  claims that follow from the shapes being identical, which transfer, from the rates, which
  do not.

## Layout

```
src/dcc/
  generator.py   demand with every unusual week labelled
  outliers.py    three detection rules, and what none of them can do
  treatments.py  three things to do with a flagged week
  models.py      three ordinary forecasters, so the choices can be compared
  compare.py     scoring against the demand that will recur
  cli.py         generate, grade, compare
experiments/     three experiments writing JSON to docs/experiments/
docs/adr/        three decision records
tools/           the metrics collector and the number checker
```

## Running it

```bash
make install
make verify        # lint, test, receipts, then the suite again
dcc grade --panel data/fixtures/panel.csv
dcc compare --panel data/fixtures/panel.csv
```

`dcc grade` exits 1 when any rule removes mostly real demand, so a scheduled job fails
rather than filing a cleaned history, and 2 when the panel is malformed. The distinction is
declared where the exception is raised: `UnusableHistory` subclasses both `CleaningError` and
`ValueError`, and the handler's `except` order resolves it.

## Receipts

Every figure in this README is read from a run. `tools/collect_metrics.py` reads the test
run, the coverage report and the three experiment outputs into `docs/metrics.json`;
`tools/check_numbers.py` checks the documents against it in both directions. A figure quoted
outside the sentence that claims it fails the build, and so does any number no anchor phrase
puts where it sits. The three tables above are generated into this file and compared by
equality.

A figure written in words is invisible to a digit scanner, and `#` comments and `tests/` are
outside the checked set.

## Decision records

- [ADR-001: Label the two kinds of outlier, and never let a rule see the label](docs/adr/ADR-001-label-the-two-kinds-of-outlier-and-never-let-a-rule-see-the-label.md)
- [ADR-002: Report the spread across equal sized choices](docs/adr/ADR-002-report-the-spread-across-equal-sized-choices.md)
- [ADR-003: What a generated demand history cannot establish](docs/adr/ADR-003-what-a-generated-history-cannot-establish.md)
