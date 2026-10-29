"""
Tests for text_to_ics.cli — the heuristic path only (no API dependency).
"""
import io
from zoneinfo import ZoneInfo

from text_to_ics.cli import main, run
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


def test_timezone_database_is_available():
    # Windows has no system tz database; this fails there unless the
    # `tzdata` package is installed (declared in pyproject.toml).
    ZoneInfo("America/Los_Angeles")


def test_main_converts_scheduleitems_style_file_from_stdin(monkeypatch, tmp_path):
    lines = "Dentist piscotta 20270419 12:55\nTrial Vax blood draw 20261130 10:30\n"
    out = tmp_path / "scheduleitems.ics"
    monkeypatch.setattr("sys.stdin", io.StringIO(lines))

    assert main(["-o", str(out)]) == 0

    ics = out.read_text(encoding="utf-8")
    assert ics.count("BEGIN:VEVENT") == 2
    assert "SUMMARY:Dentist piscotta" in ics
    # 12:55 PDT = 19:55 UTC; 10:30 PST = 18:30 UTC
    assert "DTSTART:20270419T195500Z" in ics
    assert "DTSTART:20261130T183000Z" in ics


def test_main_reports_unparseable_line_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("buy milk\n"))
    assert main([]) == 1
    assert "No recognizable date" in capsys.readouterr().err
