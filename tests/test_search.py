"""
Tests for ManifestRepository.full_text_search().

Tree used throughout:

    <manifest>
      <category topic="travel">
        <inn topic="Green Mountain Inn" status="active">3pm check-in</inn>
        <task topic="Book flight" id="a1b2c3d4" status="done"/>
      </category>
      <task topic="Replace water heater" id="e5f6a7b8">call plumber</task>
    </manifest>
"""

import re
import pytest
from lxml import etree

from manifest_manager.manifest_core import ManifestRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo():
    r = ManifestRepository()
    r.root = etree.Element("manifest")
    r.tree = etree.ElementTree(r.root)
    r.filepath = "test.xml"
    return r


@pytest.fixture
def tree(repo):
    """Populate repo with a small but varied tree."""
    travel = etree.SubElement(repo.root, "category", topic="travel")
    inn = etree.SubElement(travel, "inn", topic="Green Mountain Inn", status="active")
    inn.text = "3pm check-in"
    flight = etree.SubElement(travel, "task", topic="Book flight", status="done")
    flight.set("id", "a1b2c3d4")
    heater = etree.SubElement(repo.root, "task", topic="Replace water heater")
    heater.set("id", "e5f6a7b8")
    heater.text = "call plumber"
    return repo


# ---------------------------------------------------------------------------
# Guard: unloaded repository
# ---------------------------------------------------------------------------

def test_returns_empty_when_no_manifest_loaded():
    r = ManifestRepository()   # never loaded
    assert r.full_text_search("anything") == []


# ---------------------------------------------------------------------------
# Basic matching
# ---------------------------------------------------------------------------

def test_no_match_returns_empty(tree):
    assert tree.full_text_search("xyzzy") == []


def test_matches_attribute_value(tree):
    results = tree.full_text_search("Green Mountain Inn")
    assert len(results) == 1
    assert results[0]["tag"] == "inn"


def test_matches_text_content(tree):
    results = tree.full_text_search("plumber")
    assert len(results) == 1
    assert results[0]["elem"].get("topic") == "Replace water heater"


def test_matched_fields_reports_attribute(tree):
    results = tree.full_text_search("Green Mountain Inn")
    assert "attr:topic" in results[0]["matched_fields"]


def test_matched_fields_reports_text(tree):
    results = tree.full_text_search("plumber")
    assert "text" in results[0]["matched_fields"]


# ---------------------------------------------------------------------------
# Scoring and sort order
# ---------------------------------------------------------------------------

def test_attribute_match_scores_2(tree):
    results = tree.full_text_search("travel")   # matches attr:topic of <category>
    assert results[0]["score"] == 2


def test_text_match_scores_1(tree):
    results = tree.full_text_search("plumber")
    assert results[0]["score"] == 1


def test_results_sorted_by_score_descending(repo):
    """Node with attr match (score=2) must come before node with text match (score=1)."""
    attr_node = etree.SubElement(repo.root, "task", topic="needle")
    text_node = etree.SubElement(repo.root, "note")
    text_node.text = "needle"
    results = repo.full_text_search("needle")
    assert len(results) == 2
    assert results[0]["score"] == 2
    assert results[1]["score"] == 1


def test_multiple_attribute_matches_on_one_node_cumulate(repo):
    """Each matching attribute adds 2 to the score."""
    node = etree.SubElement(repo.root, "task", topic="keyword", resp="keyword")
    results = repo.full_text_search("keyword")
    assert results[0]["score"] == 4   # attr:topic + attr:resp


# ---------------------------------------------------------------------------
# Result dict contents
# ---------------------------------------------------------------------------

def test_elem_id_populated(tree):
    results = tree.full_text_search("plumber")
    assert results[0]["elem_id"] == "e5f6a7b8"


def test_elem_id_none_when_no_id(tree):
    results = tree.full_text_search("travel")   # <category> has no id attr
    assert results[0]["elem_id"] is None


def test_tag_in_result(tree):
    results = tree.full_text_search("Green Mountain Inn")
    assert results[0]["tag"] == "inn"


def test_breadcrumb_reflects_ancestor_chain(tree):
    # <inn> is inside <category topic="travel">, so breadcrumb = "travel"
    results = tree.full_text_search("3pm check-in")
    assert results[0]["breadcrumb"] == "travel"


def test_breadcrumb_empty_for_top_level_node(tree):
    # <task topic="Replace water heater"> is a direct child of <manifest>
    results = tree.full_text_search("plumber")
    assert results[0]["breadcrumb"] == ""


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

def test_scope_excludes_nodes_outside_subtree(tree):
    # "plumber" lives under root, not under //category
    results = tree.full_text_search("plumber", scope_xpath="//category")
    assert results == []


def test_scope_finds_nodes_inside_subtree(tree):
    # "Book flight" is inside //category
    results = tree.full_text_search("Book flight", scope_xpath="//category")
    assert len(results) == 1
    assert results[0]["elem"].get("topic") == "Book flight"


def test_scope_xpath_matching_nothing_returns_empty(tree):
    results = tree.full_text_search("travel", scope_xpath="//nonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# Plain substring: case-sensitive
# ---------------------------------------------------------------------------

def test_plain_match_is_case_sensitive(tree):
    assert len(tree.full_text_search("travel")) == 1        # exact case
    assert tree.full_text_search("Travel") == []            # wrong case


# ---------------------------------------------------------------------------
# Regexp mode
# ---------------------------------------------------------------------------

def test_regexp_alternation_matches_multiple_nodes(tree):
    # "Green Mountain" matches inn; "plumber" matches heater task
    results = tree.full_text_search("Green Mountain|plumber", use_regexp=True)
    assert len(results) == 2


def test_regexp_inline_ignore_case_flag(tree):
    results = tree.full_text_search("(?i)green mountain inn", use_regexp=True)
    assert len(results) == 1


def test_regexp_without_ignore_case_is_case_sensitive(tree):
    results = tree.full_text_search("green mountain inn", use_regexp=True)
    assert results == []


def test_invalid_regexp_raises_re_error(tree):
    with pytest.raises(re.error):
        tree.full_text_search("[unclosed", use_regexp=True)
