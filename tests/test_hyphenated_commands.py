"""
test_hyphenated_commands.py
===========================

Regression tests for hyphenated shell commands (export-calendar, etc.).

cmd.Cmd dispatches via do_<first_word>, but Python method names can't contain
hyphens.  ManifestShell.default() translates hyphens to underscores before
retrying, so these tests exercise that dispatch path end-to-end through
onecmd() — the same path a user takes.

Without the default() fix, every test here would fail with:
    *** Unknown syntax: export-calendar ...
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from manifest_manager.manifest import ManifestShell
from manifest_manager.manifest_core import NodeSpec


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def shell(tmp_path):
    """Shell with a small loaded manifest containing tasks with due dates."""
    with patch("manifest_manager.manifest.Config") as mock_cfg:
        mock_cfg.return_value.get.return_value = None
        s = ManifestShell()

    xml_file = tmp_path / "test.xml"
    xml_file.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?><manifest/>')
    s.onecmd(f'load "{xml_file}"')

    s.repo.add_node("/manifest", NodeSpec(tag="task", topic="Meeting", due="2026-07-01", status="active"), auto_id=True)
    s.repo.add_node("/manifest", NodeSpec(tag="task", topic="Report",  due="2026-07-15", status="active"), auto_id=True)
    s.repo.add_node("/manifest", NodeSpec(tag="task", topic="No due date"), auto_id=True)
    return s


# ---------------------------------------------------------------------------
# Dispatch smoke tests — these fail with "Unknown syntax" without the fix
# ---------------------------------------------------------------------------

def test_export_calendar_hyphen_dispatches(shell, tmp_path, capsys):
    """export-calendar (hyphenated) must reach do_export_calendar, not default()."""
    ics = str(tmp_path / "out.ics")
    shell.onecmd(f'export-calendar "//task[@due]" "{ics}"')
    out = capsys.readouterr().out
    assert "Unknown syntax" not in out, "Hyphen dispatch failed — hit default() instead of do_export_calendar"


def test_export_calendar_produces_output_file(shell, tmp_path, capsys):
    """export-calendar must write an .ics file when tasks with due dates exist."""
    ics = str(tmp_path / "tasks.ics")
    shell.onecmd(f'export-calendar "//task[@due]" "{ics}"')
    out = capsys.readouterr().out
    assert "Unknown syntax" not in out
    assert os.path.exists(ics), "No .ics file was written"


def test_export_calendar_reports_count(shell, tmp_path, capsys):
    """export-calendar must report how many events were exported."""
    ics = str(tmp_path / "tasks.ics")
    shell.onecmd(f'export-calendar "//task[@due]" "{ics}"')
    out = capsys.readouterr().out
    assert "Exported 2 event" in out


def test_export_calendar_no_due_dates_reports_hint(shell, tmp_path, capsys):
    """export-calendar on nodes without due dates must explain the problem."""
    ics = str(tmp_path / "empty.ics")
    shell.onecmd(f'export-calendar "//task[@topic=\'No due date\']" "{ics}"')
    out = capsys.readouterr().out
    assert "Unknown syntax" not in out
    assert "due" in out.lower()  # should mention due dates in the hint


def test_export_calendar_no_file_loaded(tmp_path, capsys):
    """export-calendar before load must print an error, not crash."""
    with patch("manifest_manager.manifest.Config") as mock_cfg:
        mock_cfg.return_value.get.return_value = None
        s = ManifestShell()

    ics = str(tmp_path / "out.ics")
    s.onecmd(f'export-calendar "//task[@due]" "{ics}"')
    out = capsys.readouterr().out
    assert "Unknown syntax" not in out
    assert "Error" in out or "No file" in out


# ---------------------------------------------------------------------------
# default() translation logic — direct unit tests
# ---------------------------------------------------------------------------

def test_default_translates_hyphen_to_underscore(capsys):
    """default() must convert the first word's hyphens and re-dispatch."""
    with patch("manifest_manager.manifest.Config") as mock_cfg:
        mock_cfg.return_value.get.return_value = None
        s = ManifestShell()

    called_with = []
    s.do_fake_command = lambda arg: called_with.append(arg)

    s.default("fake-command some args")
    assert called_with == ["some args"], "default() did not re-dispatch correctly"


def test_default_unknown_command_prints_error(capsys):
    """default() must print 'Unknown syntax' for genuinely unknown commands."""
    with patch("manifest_manager.manifest.Config") as mock_cfg:
        mock_cfg.return_value.get.return_value = None
        s = ManifestShell()

    s.default("totally_unknown_command arg1")
    out = capsys.readouterr().out
    assert "Unknown syntax" in out


def test_default_hyphen_unknown_command_prints_error(capsys):
    """default() must still print 'Unknown syntax' if the translated name also doesn't exist."""
    with patch("manifest_manager.manifest.Config") as mock_cfg:
        mock_cfg.return_value.get.return_value = None
        s = ManifestShell()

    s.default("no-such-command arg1")
    out = capsys.readouterr().out
    assert "Unknown syntax" in out
