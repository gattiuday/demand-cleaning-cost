"""Exceptions, with the exit code each one means carried by the class."""

from __future__ import annotations

__all__ = ["CleaningError", "UnusableHistory"]


class CleaningError(Exception):
    """A question this history cannot answer. Exit code 1."""


class UnusableHistory(CleaningError, ValueError):
    """A history that is malformed rather than merely uninformative. Exit code 2."""
