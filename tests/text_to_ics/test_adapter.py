"""
Tests for text_to_ics.adapter.
"""
from datetime import datetime, date, timezone

from text_to_ics.adapter import to_calendar_event
from text_to_ics.models import EventSpec


def test_timed_event_maps_fields_and_gets_z_suffix():
    spec = EventSpec(
        title="Standup",
        start=datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc),
        end=datetime(2026, 6, 1, 17, 30, tzinfo=timezone.utc),
        location="Zoom",
    )
    event = to_calendar_event(spec)
    ics = event.to_ics()
    assert "SUMMARY:Standup" in ics
    assert "DTSTART:20260601T170000Z" in ics
    assert "DTEND:20260601T173000Z" in ics
    assert "LOCATION:Zoom" in ics


def test_all_day_event_uses_date_not_datetime():
    spec = EventSpec(
        title="Vermont trip",
        start=datetime(2026, 7, 4, 0, 0, tzinfo=timezone.utc),
        all_day=True,
    )
    event = to_calendar_event(spec)
    assert event.start_date == date(2026, 7, 4)
    assert "DTSTART;VALUE=DATE:20260704" in event.to_ics()


def test_uid_is_deterministic():
    spec = EventSpec(title="Dentist", start=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc))
    event_a = to_calendar_event(spec)
    event_b = to_calendar_event(spec)
    assert event_a.uid == event_b.uid


def test_uid_differs_for_different_events():
    spec_a = EventSpec(title="Dentist", start=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc))
    spec_b = EventSpec(title="Vet", start=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc))
    assert to_calendar_event(spec_a).uid != to_calendar_event(spec_b).uid
