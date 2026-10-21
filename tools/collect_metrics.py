"""Re-measure every published figure and write docs/metrics.json.

No figure here is transcribed by hand. Values come from the test suite's
machine readable reports, from the experiments' JSON, from the committed fixture
read back off disk, or from the project's own configuration. A sibling
repository hardcoded thirteen of its declared constants, which made its own
claim false and made each one a guard that could not notice the thing it was
guarding change.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "docs" / "experiments"
GENERATED_DIR = ROOT / "docs" / "generated"
METRICS_PATH = ROOT / "docs" / "metrics.json"
JUNIT_PATH = ROOT / "junit.xml"
COVERAGE_PATH = ROOT / "coverage.json"

EXPERIMENTS = (
    "exp01_what_cleaning_removes",
    "exp02_cleaning_against_the_model",
    "exp03_which_errors_are_findable",
)

ANCHORS: dict[str, list[str]] = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage"],
    "zscore_caught_pct": ["catches {}% of the errors"],
    "zscore_destroyed_pct": ["destroys {}% of the"],
    "iqr_caught_pct": ["catches {}% of them"],
    "iqr_destroyed_pct": ["and destroys {}%"],
    "worst_real_share_pct": ["{}% of what it removes"],
    "best_real_share_pct": ["That falls to {}% under"],
    "detector_spread_pts": [
        "the detector moves it {}\n  points",
        "with the\ndetector at {}",
    ],
    "treatment_spread_pts": [
        "the treatment {} points",
        "the treatment at {}",
    ],
    "model_spread_pts": [
        "moves the forecast {} points",
        "most, at {} points",
        "model's {} against",
    ],
    "detector_over_model_pct": ["{}% of the model's"],
    "zscore_at_doubling_pct": ["caught {}% of the time"],
    "zscore_at_thousandfold_pct": ["and {}% at a thousandfold"],
    "real_event_median_size": ["median promotion is {} times"],
    "real_event_band_pct": ["{}% of promotions fall"],
    "fixture_items": ["{} items"],
    "fixture_weeks": ["{} weeks"],
    "python_min_version": [],
}

FORMATS: dict[str, str] = {
    "tests_total": "{:d}",
    "coverage_line_pct": "{:.2f}",
    "zscore_caught_pct": "{:.1f}",
    "zscore_destroyed_pct": "{:.1f}",
    "iqr_caught_pct": "{:.1f}",
    "iqr_destroyed_pct": "{:.1f}",
    "worst_real_share_pct": "{:.1f}",
    "best_real_share_pct": "{:.1f}",
    "detector_spread_pts": "{:.2f}",
    "treatment_spread_pts": "{:.2f}",
    "model_spread_pts": "{:.2f}",
    "detector_over_model_pct": "{:.0f}",
    "zscore_at_doubling_pct": "{:.1f}",
    "zscore_at_thousandfold_pct": "{:.1f}",
    "real_event_median_size": "{:.2f}",
    "real_event_band_pct": "{:.1f}",
    "fixture_items": "{:d}",
    "fixture_weeks": "{:d}",
    "python_min_version": "{}",
}

GENERATED_BLOCKS = {
    "README.md": ("detection-table.md", "spread-table.md", "magnitude-table.md"),
}

CHECKED_DOCUMENTS = (
    "README.md",
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "docs" / "adr").glob("ADR-*.md")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "src" / "dcc").glob("*.py")),
    *sorted(str(path.relative_to(ROOT)) for path in (ROOT / "experiments").glob("exp*.py")),
)


def run_tests() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-q",
            f"--junitxml={JUNIT_PATH}",
            "--cov=tta",
            "--cov-report=json",
        ],
        cwd=ROOT,
        check=True,
    )


def run_experiments() -> None:
    env_path = f"{ROOT / 'src'}:{ROOT / 'experiments'}:{ROOT / 'tests'}"
    for name in EXPERIMENTS:
        subprocess.run(
            [sys.executable, str(ROOT / "experiments" / f"{name}.py")],
            cwd=ROOT,
            check=True,
            env={"PYTHONPATH": env_path, "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )


#: The one test file whose failure cannot block collection. Its tests read
#: ``docs/metrics.json`` and assert that every published figure is anchored, so
#: they are red by construction whenever the figures are stale, which is the
#: state collection exists to fix. Blocking on them deadlocks: the file cannot
#: be written until the tests pass and the tests cannot pass until it is
#: written. Every other failure still refuses, and ``make verify`` runs the full
#: suite *after* collection, so a real receipts regression still fails the
#: build. It just no longer stops the file that would clear it from being
#: written. See ADR-006.
RECEIPTS_SUITE = "tests/test_check_numbers.py"


def failing_tests(suite: ElementTree.Element) -> list[str]:
    """Names of the tests that failed or errored, as ``file::test``."""
    failures = []
    for case in suite.iter("testcase"):
        if case.find("failure") is None and case.find("error") is None:
            continue
        path = (case.get("classname") or "").split(".")
        name = case.get("name") or "?"
        failures.append(f"{'/'.join(path)}.py::{name}" if path else name)
    return failures


def read_suite() -> dict[str, float]:
    suite = ElementTree.parse(JUNIT_PATH).getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    failures = failing_tests(suite)
    blocking = [name for name in failures if not name.startswith(RECEIPTS_SUITE)]
    if blocking:
        raise SystemExit(
            f"refusing to publish metrics from a run with {len(blocking)} failing "
            f"tests outside {RECEIPTS_SUITE}: {', '.join(sorted(blocking))}"
        )
    if failures:
        print(
            f"warning: {len(failures)} receipts tests are red, which is expected "
            "while the figures are stale. Re-run the suite after this collection "
            "and treat a remaining failure as real",
            file=sys.stderr,
        )
    coverage = json.loads(COVERAGE_PATH.read_text())
    return {
        "tests_total": int(suite.get("tests")),
        "coverage_line_pct": float(coverage["totals"]["percent_covered"]),
    }


def read_experiment(name: str) -> dict:
    return json.loads((EXPERIMENT_DIR / f"{name}.json").read_text())


TEST_COUNT_DOCUMENTS = ("README.md",)


def sync_test_count(total: int) -> None:
    """Write the measured test count into the badge and the prose that quote it.

    The count moves whenever a test is added, so every commit that added one
    also carried three hand edits to keep the badge, the README sentence and the
    defense guide in step, and a missed edit showed up as a failing receipts
    check rather than as anything a reader would notice. A figure that has to be
    typed in three places is a figure that will eventually be wrong in one.

    The substitution is deliberately narrow: a tests badge, and the exact phrase
    "N tests" where N is some number. Anything looser would rewrite unrelated
    counts.
    """
    for document in TEST_COUNT_DOCUMENTS:
        path = ROOT / document
        body = path.read_text()
        body = re.sub(r"tests-\d+-brightgreen", f"tests-{total}-brightgreen", body)
        body = re.sub(r"\b\d+ tests\b", f"{total} tests", body)
        path.write_text(body)


def sync_generated_blocks(blocks: dict[str, str]) -> None:
    """Write each generated block into the documents that publish it.

    The blocks were pasted into the README by hand and checked for drift
    afterwards, which caught a stale table but left correcting it as a manual
    copy of generated output into prose, every time any figure moved. The paste
    is the step worth removing: a drift gate on a hand copied table tells you
    the copy is wrong, and a generated copy cannot be.

    The markers are HTML comments, so they are invisible in rendered Markdown
    and unambiguous to match, which the previous approach of matching the
    block's own text was not.
    """
    for document, names in GENERATED_BLOCKS.items():
        path = ROOT / document
        body = path.read_text()
        for name in names:
            start = f"<!-- generated: {name} -->"
            end = f"<!-- end generated: {name} -->"
            if start not in body or end not in body:
                raise SystemExit(
                    f"{document} has no markers for the generated block {name}; add "
                    f"{start} and {end} around it"
                )
            head, rest = body.split(start, 1)
            _, tail = rest.split(end, 1)
            body = f"{head}{start}\n{blocks[name]}\n{end}{tail}"
        path.write_text(body)


def derive() -> dict[str, float]:
    """Every published figure, read from a run rather than typed."""
    removes = read_experiment("exp01_what_cleaning_removes")
    spread = read_experiment("exp02_cleaning_against_the_model")
    findable = read_experiment("exp03_which_errors_are_findable")

    fixture = pd.read_csv(ROOT / "data" / "fixtures" / "panel.csv")
    requires = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]

    headline = removes["headline"]
    points = spread["spread_points"]

    metrics = dict(read_suite())
    metrics.update(
        {
            "zscore_caught_pct": headline["zscore"]["errors_caught"] * 100,
            "zscore_destroyed_pct": headline["zscore"]["real_events_destroyed"] * 100,
            "iqr_caught_pct": headline["iqr_rolling"]["errors_caught"] * 100,
            "iqr_destroyed_pct": headline["iqr_rolling"]["real_events_destroyed"] * 100,
            "worst_real_share_pct": (1 - removes["worst_share_of_flags_that_are_errors"]) * 100,
            "best_real_share_pct": (1 - removes["best_share_of_flags_that_are_errors"]) * 100,
            "detector_spread_pts": points["detector"]["mean"],
            "treatment_spread_pts": points["treatment"]["mean"],
            "model_spread_pts": points["model"]["mean"],
            "detector_over_model_pct": spread["detector_over_model"] * 100,
            "zscore_at_doubling_pct": findable["zscore_at_smallest"] * 100,
            "zscore_at_thousandfold_pct": findable["zscore_at_largest"] * 100,
            "real_event_median_size": findable["real_event_size_median"],
            "real_event_band_pct": findable["real_events_within_the_doubling_band"] * 100,
            "fixture_items": int(fixture["item"].nunique()),
            "fixture_weeks": int(fixture["week"].nunique()),
            "python_min_version": float(requires.lstrip(">=~^ ")),
        }
    )
    return metrics


def render_detection_block() -> str:
    """What each rule removes, graded against the labels."""
    removes = read_experiment("exp01_what_cleaning_removes")
    header = (
        "| Rule | Data errors caught | Real events destroyed | Share of what it removes "
        "that was real demand |\n| --- | --- | --- | --- |"
    )
    rows = [
        f"| {rule} | {row['errors_caught']:.1%} | {row['real_events_destroyed']:.1%} | "
        f"{1 - row['share_of_flags_that_are_errors']:.1%} |"
        for rule, row in sorted(removes["headline"].items())
    ]
    return "\n".join([header, *rows])


def render_spread_block() -> str:
    """How much each choice moves the forecast, three options against three."""
    spread = read_experiment("exp02_cleaning_against_the_model")
    header = (
        "| Choice, three options each | Spread in WMAPE points | Worst case |\n| --- | --- | --- |"
    )
    rows = [
        f"| {axis} | {values['mean']:.2f} | {values['max']:.2f} |"
        for axis, values in spread["spread_points"].items()
    ]
    return "\n".join([header, *rows])


def render_magnitude_block() -> str:
    """Detection by how big the error is."""
    findable = read_experiment("exp03_which_errors_are_findable")
    rules = list(findable["series"][0]["errors_caught"])
    header = "| Error size | " + " | ".join(rules) + " |\n| --- |" + " --- |" * len(rules)
    rows = [
        f"| {row['magnitude']:.0f}x | "
        + " | ".join(f"{row['errors_caught'][rule]:.1%}" for rule in rules)
        + " |"
        for row in findable["series"]
    ]
    return "\n".join([header, *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--skip-experiments", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        run_tests()
    if not args.skip_experiments:
        run_experiments()

    metrics = derive()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    blocks = {
        "detection-table.md": render_detection_block(),
        "spread-table.md": render_spread_block(),
        "magnitude-table.md": render_magnitude_block(),
    }
    for name, body in blocks.items():
        (GENERATED_DIR / name).write_text(body + "\n")
    sync_generated_blocks(blocks)
    sync_test_count(int(metrics["tests_total"]))

    formatted = {name: FORMATS.get(name, "{}").format(value) for name, value in metrics.items()}
    METRICS_PATH.write_text(
        json.dumps(
            {
                "metrics": metrics,
                "formatted": formatted,
                "anchors": ANCHORS,
                "formats": FORMATS,
                "checked_documents": list(CHECKED_DOCUMENTS),
                "generated_blocks": {
                    document: list(names) for document, names in GENERATED_BLOCKS.items()
                },
                "badge_only": ["python_min_version"],
                "note": (
                    "every value here is read from a run: the test suite, the "
                    "experiments, the committed fixture, or the project's own "
                    "configuration. No figure is transcribed by hand"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(f"wrote {METRICS_PATH.relative_to(ROOT)} with {len(metrics)} metrics")
    for name in sorted(metrics):
        print(f"  {name:38s} {formatted[name]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
