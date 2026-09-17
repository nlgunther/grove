"""
text_to_ics/extractor.py

The extraction interface. Text understanding is the one fuzzy part of
this package, and backends for it are genuinely different tools (a
regex/date-table heuristic vs. an LLM call) — so this is a dispatch
point, not a single implementation. Adding a new backend means adding
a class here, not editing one.
"""
from datetime import datetime
from typing import List, Protocol

from .models import EventSpec


class EventExtractor(Protocol):
    def extract(self, text: str, *, reference: datetime) -> List[EventSpec]:
        """Turn free text into one or more EventSpecs.

        ``reference`` anchors relative phrasing ("tomorrow", "next
        Tuesday") and must be tz-aware; extractors resolve all
        returned EventSpec.start/end against its timezone.

        Raises:
            ValueError: if a line/event has no resolvable date. Silently
                guessing a date is worse than failing loud here.
        """
        ...
