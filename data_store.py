"""
Local persistence for monthly spending summaries.

Stores data in data/history.json so month-over-month trend charts
can be generated even after the raw transactions are no longer needed.
"""

import json
import os
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
_HISTORY_FILE = _DATA_DIR / "history.json"


def _load_raw() -> list[dict]:
    if not _HISTORY_FILE.exists():
        return []
    with open(_HISTORY_FILE) as f:
        return json.load(f)


def _save_raw(records: list[dict]) -> None:
    _DATA_DIR.mkdir(exist_ok=True)
    with open(_HISTORY_FILE, "w") as f:
        json.dump(records, f, indent=2)


def save_month(year: int, month: int, summary: dict) -> None:
    """
    Persist or overwrite the summary for a given year/month.

    summary should contain:
        total (float), by_category (dict[str, float]), by_account (dict[str, float])
    """
    records = _load_raw()
    key = f"{year}-{month:02d}"
    # Remove existing entry for this month if present
    records = [r for r in records if r.get("key") != key]
    records.append({"key": key, "year": year, "month": month, **summary})
    records.sort(key=lambda r: r["key"])
    _save_raw(records)


def load_history() -> list[dict]:
    """
    Return all stored monthly summaries sorted oldest-first.

    Each record has: key, year, month, total, by_category, by_account.
    """
    return _load_raw()
