"""
Tests for TaskService.search().

Two projects are used throughout:

    home/
        "Replace water heater"  [active]  notes="Call Green Mountain Inn for plumber referral"
        "Buy groceries"         [active]  tags=["errand", "urgent"]
        "Fix leaky faucet"      [active]  assignee="alice"

    vermont/
        "Call Green Mountain Inn"  [done]  outcome="Confirmed, rate locked in"
"""

import re
import pytest
import shutil
import tempfile
from pathlib import Path

from smart_scheduler.models import Task, Project, TaskStatus
from smart_scheduler.storage.factory import get_storage_engine
from smart_scheduler.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(params=["json", "sqlite"])
def storage(request, temp_dir):
    return get_storage_engine(temp_dir, request.param)


@pytest.fixture
def svc(storage):
    return TaskService(storage)


@pytest.fixture
def populated_svc(svc):
    svc.create_project("home", "Home")
    svc.create_project("vermont", "Vermont Trip")

    svc.add_task("home", "Replace water heater",
                 notes="Call Green Mountain Inn for plumber referral")
    svc.add_task("home", "Buy groceries", tags=["errand", "urgent"])

    # Build the assignee task directly so we can set assignee (add_task doesn't expose it)
    home = svc.storage.load_project("home")
    faucet = Task.create("Fix leaky faucet")
    faucet.assignee = "alice"
    home.tasks.append(faucet)
    svc.storage.save_project(home)

    # Done task with outcome — update_task doesn't handle outcome, so set directly
    vermont = svc.storage.load_project("vermont")
    call = Task.create("Call Green Mountain Inn")
    call.status = TaskStatus.DONE
    call.outcome = "Confirmed, rate locked in"
    vermont.tasks.append(call)
    svc.storage.save_project(vermont)

    return svc


# ---------------------------------------------------------------------------
# Basic matching
# ---------------------------------------------------------------------------

class TestBasicMatching:
    def test_no_match_returns_empty(self, populated_svc):
        assert populated_svc.search("xyzzy") == []

    def test_matches_title(self, populated_svc):
        results = populated_svc.search("water heater")
        assert len(results) == 1
        assert results[0]["task"].title == "Replace water heater"
        assert "title" in results[0]["matched_fields"]

    def test_matches_notes(self, populated_svc):
        results = populated_svc.search("plumber")
        assert len(results) == 1
        assert "notes" in results[0]["matched_fields"]

    def test_matches_tags(self, populated_svc):
        results = populated_svc.search("urgent")
        assert len(results) == 1
        assert "tags" in results[0]["matched_fields"]

    def test_matches_assignee(self, populated_svc):
        results = populated_svc.search("alice")
        assert len(results) == 1
        assert "assignee" in results[0]["matched_fields"]

    def test_matches_outcome_when_include_inactive(self, populated_svc):
        results = populated_svc.search("rate locked", include_inactive=True)
        assert len(results) == 1
        assert "outcome" in results[0]["matched_fields"]


# ---------------------------------------------------------------------------
# Active-only default vs include_inactive
# ---------------------------------------------------------------------------

class TestActiveFilter:
    def test_active_only_by_default(self, populated_svc):
        # "Green Mountain Inn" appears in active notes AND done title;
        # default should exclude the done task
        results = populated_svc.search("Green Mountain Inn")
        assert all(
            r["task"].status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
            for r in results
        )

    def test_include_inactive_returns_done_tasks(self, populated_svc):
        results = populated_svc.search("Green Mountain Inn", include_inactive=True)
        statuses = {r["task"].status for r in results}
        assert TaskStatus.DONE in statuses

    def test_empty_project_returns_nothing(self, svc):
        svc.create_project("empty", "Empty")
        assert svc.search("anything") == []


# ---------------------------------------------------------------------------
# Field restriction
# ---------------------------------------------------------------------------

class TestFieldRestriction:
    def test_field_notes_excludes_title_match(self, populated_svc):
        # "Green Mountain Inn" is in both notes (active) and title (done);
        # restricting to notes should only surface the notes match
        results = populated_svc.search(
            "Green Mountain Inn", field="notes", include_inactive=True
        )
        assert all("notes" in r["matched_fields"] for r in results)
        assert all("title" not in r["matched_fields"] for r in results)

    def test_field_outcome_only(self, populated_svc):
        results = populated_svc.search(
            "Confirmed", field="outcome", include_inactive=True
        )
        assert len(results) == 1
        assert results[0]["matched_fields"] == ["outcome"]

    def test_field_tags_only(self, populated_svc):
        results = populated_svc.search("errand", field="tags")
        assert len(results) == 1
        assert results[0]["matched_fields"] == ["tags"]


# ---------------------------------------------------------------------------
# Project restriction
# ---------------------------------------------------------------------------

class TestProjectRestriction:
    def test_project_slug_limits_results(self, populated_svc):
        # "Green Mountain Inn" appears in home (notes) and vermont (title, done)
        results = populated_svc.search(
            "Green Mountain Inn", project_slug="home", include_inactive=True
        )
        assert all(r["project_slug"] == "home" for r in results)

    def test_nonexistent_project_returns_empty(self, populated_svc):
        assert populated_svc.search("anything", project_slug="nosuchproject") == []


# ---------------------------------------------------------------------------
# Case-insensitivity (plain string)
# ---------------------------------------------------------------------------

class TestCaseInsensitivity:
    def test_plain_search_is_case_insensitive(self, populated_svc):
        lower = populated_svc.search("water heater")
        upper = populated_svc.search("WATER HEATER")
        mixed = populated_svc.search("Water Heater")
        assert len(lower) == len(upper) == len(mixed) == 1


# ---------------------------------------------------------------------------
# Result dict structure
# ---------------------------------------------------------------------------

class TestResultStructure:
    def test_result_dict_keys(self, populated_svc):
        results = populated_svc.search("groceries")
        assert len(results) == 1
        r = results[0]
        assert set(r.keys()) == {"project_slug", "task", "matched_fields"}

    def test_project_slug_correct(self, populated_svc):
        results = populated_svc.search("groceries")
        assert results[0]["project_slug"] == "home"

    def test_matched_fields_is_list(self, populated_svc):
        results = populated_svc.search("groceries")
        assert isinstance(results[0]["matched_fields"], list)


# ---------------------------------------------------------------------------
# Regexp mode
# ---------------------------------------------------------------------------

class TestRegexp:
    def test_regexp_alternation(self, populated_svc):
        # "groceries" matches title; "plumber" matches notes — different tasks
        results = populated_svc.search("groceries|plumber", use_regexp=True)
        assert len(results) == 2

    def test_regexp_is_case_insensitive(self, populated_svc):
        # Regexp mode applies IGNORECASE, consistent with plain-string behaviour
        results_lower = populated_svc.search("water heater", use_regexp=True)
        results_upper = populated_svc.search("WATER HEATER", use_regexp=True)
        assert len(results_lower) == len(results_upper) == 1

    def test_invalid_regexp_raises_re_error(self, populated_svc):
        with pytest.raises(re.error):
            populated_svc.search("[unclosed", use_regexp=True)
