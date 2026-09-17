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
