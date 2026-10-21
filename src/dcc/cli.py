"""Command line entry point: generate, detect, compare, grade."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from dcc.compare import pipeline_outcomes
from dcc.errors import CleaningError, UnusableHistory
from dcc.generator import DATA_ERROR, REAL_EVENT, History, generate_panel
from dcc.models import MODELS
from dcc.outliers import DETECTORS, detect
from dcc.treatments import TREATMENTS

__all__ = ["main", "read_panel", "write_panel"]

COLUMNS = ("item", "week", "observed", "underlying", "label")


def write_panel(panel: list[History], path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "item": history.item,
                "week": week,
                "observed": history.observed[week],
                "underlying": history.underlying[week],
                "label": history.labels[week],
            }
            for history in panel
            for week in range(history.periods)
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.3f")


def read_panel(path: Path) -> list[History]:
    frame = pd.read_csv(path)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise UnusableHistory(
            f"{path} is missing column(s) {', '.join(missing)}; this is not a history this "
            "tool can read"
        )
    if frame.empty:
        # Not an `UnusableHistory`. The file is well formed and contains no
        # items, which is a question this tool cannot answer rather than a file
        # it cannot read, and the two exit codes mean different things.
        raise CleaningError(
            f"{path} contains no items, so there is nothing to clean; this is undefined "
            "rather than a clean history"
        )
    out = []
    for name, group in frame.groupby("item", sort=True):
        ordered = group.sort_values("week")
        out.append(
            History(
                item=str(name),
                observed=ordered["observed"].to_numpy(),
                underlying=ordered["underlying"].to_numpy(),
                labels=ordered["label"].to_numpy(dtype=object),
            )
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dcc", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    make = sub.add_parser("generate", help="write a labelled panel")
    make.add_argument("--out", type=Path, required=True)
    make.add_argument("--items", type=int, default=20)
    make.add_argument("--error-rate", type=float, default=0.03)

    grade = sub.add_parser("grade", help="what each detector removes, against the labels")
    grade.add_argument("--panel", type=Path, required=True)

    run = sub.add_parser("compare", help="every cleaning pipeline and model, scored")
    run.add_argument("--panel", type=Path, required=True)
    run.add_argument("--top", type=int, default=8)

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            panel = generate_panel(items=args.items, error_rate=args.error_rate)
            write_panel(panel, args.out)
            print(f"wrote {len(panel)} items to {args.out}")
            return 0

        panel = read_panel(args.panel)
        if args.command == "grade":
            print(
                f"{'rule':14s} {'errors caught':>14s} {'events destroyed':>17s} {'flags real':>11s}"
            )
            print("-" * 60)
            worst = 1.0
            for rule in DETECTORS:
                errors = events = hits = losses = flagged = 0
                for history in panel:
                    flags = detect(history.observed, rule)
                    errors += history.data_errors
                    events += history.real_events
                    hits += int((flags & history.mask(DATA_ERROR)).sum())
                    losses += int((flags & history.mask(REAL_EVENT)).sum())
                    flagged += int(flags.sum())
                real_share = (flagged - hits) / flagged if flagged else 0.0
                worst = min(worst, 1.0 - real_share)
                print(
                    f"{rule:14s} {hits / errors if errors else 0:13.1%} "
                    f"{losses / events if events else 0:16.1%} {real_share:10.1%}"
                )
            print()
            print("the last column is the share of what the rule removes that was real demand")
            print("and is not computable without the labels, which a real history lacks")
            return 1 if worst < 0.5 else 0

        outcomes = [o for history in panel for o in pipeline_outcomes(history)]
        by = {}
        for outcome in outcomes:
            key = (outcome.detector, outcome.treatment, outcome.model)
            by.setdefault(key, []).append(outcome.wmape)
        ranked = sorted(by.items(), key=lambda item: float(np.mean(item[1])))
        print(f"{'detector':14s} {'treatment':10s} {'model':16s} {'WMAPE':>8s}")
        print("-" * 52)
        for (detector, treatment, model), values in ranked[: args.top]:
            print(f"{detector:14s} {treatment:10s} {model:16s} {float(np.mean(values)):8.4f}")
        print()
        print(f"{len(TREATMENTS) * len(DETECTORS) * len(MODELS)} pipelines, of which the")
        print("cleaning half is usually chosen once and never revisited")
        return 0
    except UnusableHistory as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except CleaningError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised by the console script
    raise SystemExit(main())
