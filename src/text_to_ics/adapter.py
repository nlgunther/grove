"""
text_to_ics/adapter.py

Maps an EventSpec (extraction's output) onto a CalendarEvent
(shared.calendar's input) — the one place the two halves meet.
"""
import hashlib

from shared.calendar.ics_writer import CalendarEvent
from .models import EventSpec

_UID_NAMESPACE = "text-to-ics"


def to_calendar_event(spec: EventSpec) -> CalendarEvent:
    """Convert an EventSpec to a CalendarEvent with a deterministic UID.

    The UID is a hash of title + start time, not a random UUID — running
    the same input twice produces the same UID, so re-importing the
    resulting .ics into Google Calendar updates the existing event
    instead of duplicating it.

    Example:
        to_calendar_event(EventSpec("Dentist", datetime(2026, 6, 1, 15, 0)))
        # → CalendarEvent(uid="a1b2c3...@text-to-ics", title="Dentist", ...)
    """
    return CalendarEvent(
        uid=_deterministic_uid(spec),
        title=spec.title,
        start_date=spec.start.date() if spec.all_day else spec.start,
        end_date=_end_date(spec),
        description=spec.description,
        location=spec.location,
        all_day=spec.all_day,
    )


def _end_date(spec: EventSpec):
    if spec.end is None:
        return None
    return spec.end.date() if spec.all_day else spec.end


def _deterministic_uid(spec: EventSpec) -> str:
    basis = f"{spec.title}|{spec.start.isoformat()}"
    digest = hashlib.sha256(basis.encode()).hexdigest()[:16]
    return f"{digest}@{_UID_NAMESPACE}"
