"""
Tests for text_to_ics.heuristic_extractor.
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from text_to_ics.heuristic_extractor import HeuristicExtractor

TZ = ZoneInfo("America/Los_Angeles")
REFERENCE = datetime(2026, 9, 16, 8, 0, tzinfo=TZ)  # a Wednesday


def test_single_line_with_explicit_time():
    specs = HeuristicExtractor().extract("dentist tomorrow at 3pm", reference=REFERENCE)
    assert len(specs) == 1
    assert specs[0].title == "dentist"
    assert specs[0].start == datetime(2026, 9, 17, 15, 0, tzinfo=TZ)


def test_line_without_time_defaults_to_9am():
    specs = HeuristicExtractor().extract("call the vet monday", reference=REFERENCE)
    assert specs[0].start == datetime(2026, 9, 21, 9, 0, tzinfo=TZ)


def test_multiple_lines_are_multiple_events():
    text = "lunch with bob today at noon\nteam sync tomorrow 9:30am"
    specs = HeuristicExtractor().extract(text, reference=REFERENCE)
    assert len(specs) == 2
    assert specs[0].start == datetime(2026, 9, 16, 12, 0, tzinfo=TZ)
    assert specs[1].start == datetime(2026, 9, 17, 9, 30, tzinfo=TZ)


def test_relative_dates_resolve_against_reference_not_real_today():
    # reference is fixed above regardless of when the test actually runs
    specs = HeuristicExtractor().extract("standup +2", reference=REFERENCE)
    assert specs[0].start.date().isoformat() == "2026-09-18"


def test_line_with_no_date_raises():
    with pytest.raises(ValueError):
        HeuristicExtractor().extract("buy milk", reference=REFERENCE)


def test_blank_lines_are_skipped():
    specs = HeuristicExtractor().extract("\n\ndentist tomorrow\n\n", reference=REFERENCE)
    assert len(specs) == 1


def test_compact_date_with_24_hour_time():
    # The exact shape of a scheduleitems.txt line.
    text = "Dentist piscotta 20270419 12:55\nTrial Vax blood draw 20261130 10:30"
    specs = HeuristicExtractor().extract(text, reference=REFERENCE)
    assert [s.title for s in specs] == ["Dentist piscotta", "Trial Vax blood draw"]
    assert specs[0].start == datetime(2027, 4, 19, 12, 55, tzinfo=TZ)
    assert specs[1].start == datetime(2026, 11, 30, 10, 30, tzinfo=TZ)


@pytest.mark.parametrize("line, expected_hour, expected_minute", [
    ("meeting 2026-10-01 15:00", 15, 0),
    ("meeting 2026-10-01 at 0:05", 0, 5),
    ("meeting 2026-10-01 at 12:30am", 0, 30),
    ("meeting 2026-10-01 at 12pm", 12, 0),
    ("meeting 2026-10-01 3pm", 15, 0),
])
def test_time_formats(line, expected_hour, expected_minute):
    start = HeuristicExtractor().extract(line, reference=REFERENCE)[0].start
    assert (start.hour, start.minute) == (expected_hour, expected_minute)


def test_bare_number_is_not_a_time():
    # "2" in the title must not become 02:00; no colon and no am/pm.
    spec = HeuristicExtractor().extract("table for 2 tomorrow", reference=REFERENCE)[0]
    assert spec.title == "table for 2"
    assert spec.start.hour == 9


@pytest.mark.parametrize("line", [
    "meeting 2026-10-01 25:00",
    "meeting 2026-10-01 10:75",
    "meeting 20271399 10:00",
])
def test_invalid_time_or_date_raises_value_error(line):
    with pytest.raises(ValueError):
        HeuristicExtractor().extract(line, reference=REFERENCE)
