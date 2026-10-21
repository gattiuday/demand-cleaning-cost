"""Fixtures shared across the suite."""

from __future__ import annotations

import pytest

from dcc.generator import generate_history, generate_panel


@pytest.fixture(scope="session")
def panel():
    return generate_panel(items=20)


@pytest.fixture
def history():
    return generate_history("SKU-TEST")


@pytest.fixture
def clean_history():
    """A history with no data errors at all, where cleaning can only do harm."""
    return generate_history("SKU-CLEAN", error_rate=0.0)
