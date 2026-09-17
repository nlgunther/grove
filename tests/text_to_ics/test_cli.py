"""
Tests for text_to_ics.cli — the heuristic path only (no API dependency).
"""
from text_to_ics.cli import run
from text_to_ics.heuristic_extractor import HeuristicExtractor


def test_run_produces_valid_vcalendar_for_heuristic_backend():
    ics = run(
        "dentist tomorrow at 3pm",
        extractor=HeuristicExtractor(),
        tz="America/Los_Angeles",
        calendar_name="Test Calendar",
    )
    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert "SUMMARY:dentist" in ics
    assert "X-WR-CALNAME:Test Calendar" in ics
