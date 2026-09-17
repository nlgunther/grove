"""
text_to_ics/heuristic_extractor.py

Offline, no-API extractor built on shared.dates.parse_date. Handles the
simple case well ("call the dentist tomorrow at 3pm") and nothing more
ambiguous than that — it's the free/fast/deterministic option, meant to
be swappable with an LLM-backed extractor (see llm_extractor.py) rather
than a lesser version of it.

Contract: one event per non-blank input line. Each line must contain a
recognizable date phrase (today/tomorrow/+N/a weekday name/an ISO or
US-format date); a time-of-day phrase ("3pm", "15:00", "noon",
"midnight") is optional and defaults to 9:00 AM local time when absent.
Anything else in the line becomes the title.
"""
import re
from datetime import date, datetime, time

from shared.dates import parse_date
from .models import EventSpec

# "+2" doesn't get a \b before the "+" (a space and a "+" are both
# non-word characters, so there's no word-boundary transition between
# them) -- so it's pulled out of the \b(...)\b group as its own
# alternative rather than silently failing to match.
_DATE_TOKEN_RE = re.compile(
    r"\b(?:today|tomorrow|yesterday|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b|\+\d+",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
_NOON_RE = re.compile(r"\bnoon\b", re.IGNORECASE)
_MIDNIGHT_RE = re.compile(r"\bmidnight\b", re.IGNORECASE)

_DEFAULT_HOUR = 9  # when a line gives a date but no time


class HeuristicExtractor:
    """No-API extractor: date-table + regex, one event per line."""

    def extract(self, text: str, *, reference: datetime) -> list[EventSpec]:
        specs = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                specs.append(self._extract_line(line, reference))
        return specs

    def _extract_line(self, line: str, reference: datetime) -> EventSpec:
        date_match = _DATE_TOKEN_RE.search(line)
        if not date_match:
            raise ValueError(
                f"No recognizable date in: {line!r} "
                "(try today/tomorrow/+N/a weekday name/an ISO or US date)"
            )
        iso_date = parse_date(date_match.group(0), today=reference.date())
        event_date = date.fromisoformat(iso_date)

        event_time, time_span = self._extract_time(line)
        title = self._strip_tokens(line, date_match.span(), time_span)

        start = datetime.combine(event_date, event_time, tzinfo=reference.tzinfo)
        return EventSpec(title=title, start=start, all_day=False)

    def _extract_time(self, line: str):
        m = _TIME_RE.search(line)
        if m:
            hour = int(m.group(1)) % 12
            minute = int(m.group(2) or 0)
            if m.group(3).lower() == "pm":
                hour += 12
            return time(hour, minute), m.span()
        m = _NOON_RE.search(line)
        if m:
            return time(12, 0), m.span()
        m = _MIDNIGHT_RE.search(line)
        if m:
            return time(0, 0), m.span()
        return time(_DEFAULT_HOUR, 0), None

    @staticmethod
    def _strip_tokens(line: str, *spans) -> str:
        for span in sorted((s for s in spans if s), reverse=True):
            line = line[: span[0]] + line[span[1]:]
        # tidy up connector words and stray whitespace left behind
        line = re.sub(r"\b(on|at)\b", "", line, flags=re.IGNORECASE)
        return re.sub(r"\s{2,}", " ", line).strip(" ,.-")
