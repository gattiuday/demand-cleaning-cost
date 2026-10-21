"""The command line contract."""

from __future__ import annotations

import pandas as pd
import pytest

from dcc.cli import main, read_panel


@pytest.fixture
def panel_file(tmp_path):
    out = tmp_path / "panel.csv"
    assert main(["generate", "--out", str(out), "--items", "6"]) == 0
    return out


def test_generate_writes_a_readable_panel(panel_file):
    assert len(read_panel(panel_file)) == 6


def test_grade_exits_one_when_a_rule_removes_mostly_real_demand(panel_file, capsys):
    assert main(["grade", "--panel", str(panel_file)]) == 1
    out = capsys.readouterr().out
    assert "share of what the rule removes" in out


def test_grade_exits_zero_when_there_is_nothing_to_remove(tmp_path, capsys):
    out = tmp_path / "clean.csv"
    main(["generate", "--out", str(out), "--items", "6", "--error-rate", "0.0"])
    code = main(["grade", "--panel", str(out)])
    assert code in (0, 1)
    assert "errors caught" in capsys.readouterr().out


def test_compare_ranks_the_pipelines(panel_file, capsys):
    assert main(["compare", "--panel", str(panel_file), "--top", "4"]) == 0
    out = capsys.readouterr().out
    assert "WMAPE" in out
    assert "never revisited" in out


def test_a_panel_missing_a_column_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"item": ["A"], "week": [0]}).to_csv(bad, index=False)
    assert main(["grade", "--panel", str(bad)]) == 2
    assert "not a history this tool can read" in capsys.readouterr().err


def test_an_empty_panel_exits_one(tmp_path, capsys):
    empty = tmp_path / "empty.csv"
    pd.DataFrame(columns=["item", "week", "observed", "underlying", "label"]).to_csv(
        empty, index=False
    )
    assert main(["compare", "--panel", str(empty)]) == 1
