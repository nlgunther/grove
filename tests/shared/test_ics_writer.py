"""
Tests for shared.calendar.ics_writer module.
"""
import pytest
from datetime import datetime, date, timezone
from shared.calendar.ics_writer import CalendarEvent, ICSWriter


def test_create_simple_event():
    """Test creating a basic event."""
    event = CalendarEvent(
        uid="test123",
        title="Test Event",
        start_date=date(2026, 2, 15)
    )
    
    ics = event.to_ics()
    assert "UID:test123" in ics
    assert "SUMMARY:Test Event" in ics
    assert "DTSTART;VALUE=DATE:20260215" in ics


def test_event_with_description():
    """Test event with description."""
    event = CalendarEvent(
        uid="test456",
        title="Meeting",
        start_date=date(2026, 3, 1),
        description="Discuss Q1 results; review metrics"
    )
    
    ics = event.to_ics()
    assert "DESCRIPTION:" in ics
    assert "\\;" in ics  # Semicolon escaped


def test_ics_writer():
    """Test full ICS file generation."""
    writer = ICSWriter("My Calendar")
    
    writer.add_event(CalendarEvent(
        uid="1",
        title="Event 1",
        start_date=date(2026, 2, 10)
    ))
    
    ics_content = writer.to_string()
    
    assert "BEGIN:VCALENDAR" in ics_content
    assert "END:VCALENDAR" in ics_content
    assert "Event 1" in ics_content


def test_datetime_not_deprecated():
    """Test that we use timezone-aware datetime (no deprecation)."""
    event = CalendarEvent(
        uid="dt_test",
        title="DateTime Test",
        start_date=datetime.now(timezone.utc),
        all_day=False
    )
    
    # Should not raise DeprecationWarning
    ics = event.to_ics()
    assert "DTSTART:" in ics
    assert "Z" in ics  # UTC indicator


def test_timed_event_with_utc_datetime_gets_z_suffix():
    """A tz-aware UTC datetime must produce an unambiguous DTSTART, not a
    floating time Google Calendar has no fixed instant for."""
    event = CalendarEvent(
        uid="tz_test",
        title="Standup",
        start_date=datetime(2026, 6, 1, 17, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 1, 17, 30, tzinfo=timezone.utc),
    )

    ics = event.to_ics()
    assert "DTSTART:20260601T170000Z" in ics
    assert "DTEND:20260601T173000Z" in ics


def test_timed_event_with_naive_datetime_stays_floating():
    """A naive datetime is emitted as floating local time on purpose —
    no Z suffix, since there's no timezone to convert from."""
    event = CalendarEvent(
        uid="naive_test",
        title="Standup",
        start_date=datetime(2026, 6, 1, 9, 0),
    )

    ics = event.to_ics()
    assert "DTSTART:20260601T090000" in ics
    assert "DTSTART:20260601T090000Z" not in ics
