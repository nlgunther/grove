"""
shared/dates.py
===============
Natural language date parsing, shared by both tools.

Previously lived in smart_scheduler/services/task_service.py.
Manifest Manager's --due flag now resolves through this module so
both tools accept the same date expressions.

Supported formats
-----------------
  today / tomorrow / yesterday
  +N                           (N days from today)
  monday … sunday              (next occurrence of that weekday)
  YYYY-MM-DD                   (ISO 8601, returned as-is)
  MM/DD/YYYY                   (US format)

All other input returns None; callers decide how to handle it.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional


def today_str() -> str:
    """Return today's date as ISO 8601 (``"YYYY-MM-DD"``).

    Single source of truth for all last_modified stamping.

    Example::

        today_str()  # "2026-04-15"
    """
    return datetime.now().date().isoformat()


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse a natural language or formatted date string to ISO 8601.

    Args:
        date_str: Input date expression (case-insensitive).

    Returns:
        ISO date string ``"YYYY-MM-DD"``, or ``None`` if unrecognised.

    Examples::

        parse_date("today")        # "2026-04-14"
        parse_date("tomorrow")     # "2026-04-15"
        parse_date("+3")           # "2026-04-17"
        parse_date("monday")       # next Monday
        parse_date("2026-06-15")   # "2026-06-15"
        parse_date("06/15/2026")   # "2026-06-15"
        parse_date("not-a-date")   # None
        parse_date(None)           # None
    """
    if not date_str:
        return None

    date_str = str(date_str).strip().lower()
    today = datetime.now().date()

    # Relative keywords
    if date_str == "today":
        return today.isoformat()
    if date_str == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if date_str == "yesterday":
        return (today - timedelta(days=1)).isoformat()

    # +N days
    if date_str.startswith("+") and date_str[1:].isdigit():
        return (today + timedelta(days=int(date_str[1:]))).isoformat()

    # Weekday names — always returns the *next* occurrence, never today
    _WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
                 "friday", "saturday", "sunday"]
    if date_str in _WEEKDAYS:
        target = _WEEKDAYS.index(date_str)
        current = today.weekday()
        days_ahead = (target - current) % 7 or 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # ISO 8601
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass

    # US format
    try:
        return datetime.strptime(date_str, "%m/%d/%Y").date().isoformat()
    except ValueError:
        pass

    return None
