"""
text_to_ics/models.py

The contract between extraction and generation.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EventSpec:
    """One calendar event, as understood from free text.

    ``start`` (and ``end``, if set) should be tz-aware — extractors are
    responsible for resolving relative/ambiguous phrasing ("tomorrow at
    3pm") against a reference timezone before producing an EventSpec.
    """
    title: str
    start: datetime
    end: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    description: Optional[str] = None
