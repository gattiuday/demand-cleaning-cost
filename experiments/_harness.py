"""Shared plumbing: deterministic setup, JSON output, a printed table."""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "experiments"

#: Items per panel and panels per measurement. Every figure is a mean over
#: independent panels, because a cleaning rule evaluated once on one assortment
#: is one draw.
ITEMS = 20
REPLICATIONS = 6

#: Share of weeks carrying a data error, swept because every figure here is a
#: function of how many there are to find.
ERROR_RATES = (0.0, 0.01, 0.03, 0.06, 0.10)

#: The rate the headline figures are quoted at.
HEADLINE_RATE = 0.03


def emit(name: str, payload: dict, rows: list[tuple] | None = None, headers=()) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / f"{name}.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if rows:
        widths = [
            max(len(str(header)), *(len(str(row[i])) for row in rows))
            for i, header in enumerate(headers)
        ]
        line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths, strict=True))
        print(line)
        print("-" * len(line))
        for row in rows:
            print("  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True)))
    print(f"\nwrote {target.relative_to(OUTPUT_DIR.parents[1])}")
