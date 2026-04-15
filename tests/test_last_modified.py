"""
test_last_modified.py
=====================

Tests for automatic last_modified stamping on create and edit operations.

Covers:
    - add_node stamps last_modified with today's date
    - edit_node updates last_modified
    - edit_node_by_id updates last_modified (via delegation)
    - delete operations do not stamp (node is gone)
    - untouched siblings are not stamped
    - last_modified is absent on nodes that predate the feature
    - sidecar rebuild preserves last_modified values
    - last_modified is suppressed in rendered tree output
    - today_str() returns a valid ISO 8601 date
"""

import pytest
from datetime import date
from lxml import etree
from unittest.mock import patch

from manifest_manager.manifest_core import ManifestRepository, NodeSpec, ManifestView, _HIDDEN_ATTRS
from shared.dates import today_str


TODAY = date.today().isoformat()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    """Bare repo with a minimal loaded manifest — no sidecar."""
    r = ManifestRepository()
    xml = b'<?xml version="1.0" encoding="UTF-8"?><manifest/>'
    p = tmp_path / "test.xml"
    p.write_bytes(xml)
    r.load(str(p))
    return r


@pytest.fixture
def repo_with_sidecar(tmp_path):
    """Repo loaded with sidecar enabled for ID-based edit tests."""
    r = ManifestRepository()
    xml = b'<?xml version="1.0" encoding="UTF-8"?><manifest/>'
    p = tmp_path / "test.xml"
    p.write_bytes(xml)
    r.load(str(p), auto_sidecar=True)
    return r


@pytest.fixture
def repo_with_existing_node(tmp_path):
    """Repo containing a node that predates the last_modified feature."""
    r = ManifestRepository()
    xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<manifest>'
        b'  <project id="aabbccdd" topic="old"/>'
        b'</manifest>'
    )
    p = tmp_path / "test.xml"
    p.write_bytes(xml)
    r.load(str(p), auto_sidecar=True)
    return r


# ---------------------------------------------------------------------------
# today_str()
# ---------------------------------------------------------------------------

def test_today_str_is_valid_iso_date():
    result = today_str()
    parsed = date.fromisoformat(result)   # raises if malformed
    assert parsed == date.today()


# ---------------------------------------------------------------------------
# add_node stamps last_modified
# ---------------------------------------------------------------------------

def test_add_node_stamps_last_modified(repo):
    repo.add_node("/manifest", NodeSpec(tag="task", topic="New"))
    nodes = repo.root.xpath("//task")
    assert len(nodes) == 1
    assert nodes[0].get("last_modified") == TODAY


def test_add_node_last_modified_matches_today_str(repo):
    """Stamp value equals today_str() — single source of truth check."""
    repo.add_node("/manifest", NodeSpec(tag="item", topic="x"))
    node = repo.root.xpath("//item")[0]
    assert node.get("last_modified") == today_str()


# ---------------------------------------------------------------------------
# edit_node updates last_modified
# ---------------------------------------------------------------------------

def test_edit_node_updates_last_modified(repo_with_existing_node):
    repo = repo_with_existing_node
    # Node has no last_modified before edit
    node = repo.root.xpath("//*[@id='aabbccdd']")[0]
    assert node.get("last_modified") is None

    repo.edit_node("//*[@id='aabbccdd']", NodeSpec(tag="project", topic="updated"), delete=False)

    node = repo.root.xpath("//*[@id='aabbccdd']")[0]
    assert node.get("last_modified") == TODAY


def test_edit_node_by_id_updates_last_modified(repo_with_existing_node):
    repo = repo_with_existing_node
    repo.edit_node_by_id("aabbccdd", NodeSpec(tag="project", topic="via-id"), delete=False)
    node = repo.root.xpath("//*[@id='aabbccdd']")[0]
    assert node.get("last_modified") == TODAY


def test_edit_node_delete_removes_node_entirely(repo_with_existing_node):
    """Delete should not stamp — the node is gone."""
    repo = repo_with_existing_node
    repo.edit_node("//*[@id='aabbccdd']", None, delete=True)
    assert repo.root.xpath("//*[@id='aabbccdd']") == []


# ---------------------------------------------------------------------------
# Untouched siblings are not stamped
# ---------------------------------------------------------------------------

def test_edit_does_not_stamp_siblings(repo_with_existing_node):
    repo = repo_with_existing_node
    # Add a second node, then edit only the first
    repo.add_node("/manifest", NodeSpec(tag="other", topic="sibling"))
    other = repo.root.xpath("//other")[0]
    # Clear its stamp so it looks like a pre-feature node
    del other.attrib["last_modified"]

    repo.edit_node("//*[@id='aabbccdd']", NodeSpec(tag="project", topic="changed"), delete=False)

    assert other.get("last_modified") is None


# ---------------------------------------------------------------------------
# Pre-feature nodes lack the attribute until touched
# ---------------------------------------------------------------------------

def test_existing_node_has_no_last_modified_before_edit(repo_with_existing_node):
    node = repo_with_existing_node.root.xpath("//*[@id='aabbccdd']")[0]
    assert node.get("last_modified") is None


def test_xpath_finds_unstamped_nodes(repo_with_existing_node):
    """search //*[not(@last_modified)] should find the old node."""
    results = repo_with_existing_node.search("//*[not(@last_modified)]")
    ids = [n.get("id") for n in results]
    assert "aabbccdd" in ids


def test_xpath_finds_no_unstamped_nodes_after_add(repo):
    """After adding fresh nodes, all non-root nodes have last_modified.
    The root <manifest> element is never stamped — it is structural, not data."""
    repo.add_node("/manifest", NodeSpec(tag="task", topic="t"))
    unstamped = repo.search("/manifest//*[not(@last_modified)]")
    assert unstamped == []


# ---------------------------------------------------------------------------
# Sidecar rebuild preserves last_modified
# ---------------------------------------------------------------------------

def test_rebuild_preserves_last_modified(repo_with_sidecar):
    repo = repo_with_sidecar
    repo.add_node("/manifest", NodeSpec(tag="task", topic="t"))
    node = repo.root.xpath("//task")[0]
    stamped_value = node.get("last_modified")
    assert stamped_value == TODAY

    # Simulate a rebuild
    repo.id_sidecar.rebuild(repo.root)

    # Attribute lives in the XML — rebuild cannot touch it
    node_after = repo.root.xpath("//task")[0]
    assert node_after.get("last_modified") == stamped_value


# ---------------------------------------------------------------------------
# last_modified suppressed in rendered output
# ---------------------------------------------------------------------------

def test_last_modified_hidden_in_tree_render(repo):
    repo.add_node("/manifest", NodeSpec(tag="task", topic="visible", attrs={"due": "2026-05-01"}))
    output = ManifestView.render(repo.root.xpath("//task"), style="tree")
    assert "last_modified" not in output


def test_last_modified_in_hidden_attrs_constant():
    assert "last_modified" in _HIDDEN_ATTRS


def test_known_display_attrs_still_hidden():
    """Existing hidden attrs were not accidentally removed."""
    for attr in ("topic", "status", "resp"):
        assert attr in _HIDDEN_ATTRS


# ---------------------------------------------------------------------------
# hide_attrs=False reveals suppressed attributes
# ---------------------------------------------------------------------------

def test_hide_attrs_false_shows_last_modified(repo):
    # Render a child node — root items take the header path which skips the attrs bracket.
    repo.add_node("/manifest", NodeSpec(tag="project", topic="p"))
    repo.add_node("//project", NodeSpec(tag="task", topic="t"))
    output = ManifestView.render(repo.root.xpath("//task"), style="tree", hide_attrs=False)
    assert "last_modified" in output


def test_hide_attrs_false_shows_all_hidden_attrs(repo):
    """When verbose, topic/status/resp also appear in the attrs bracket."""
    repo.add_node("/manifest", NodeSpec(tag="project", topic="p"))
    repo.add_node("//project", NodeSpec(tag="task", topic="mytopic", status="active", resp="alice"))
    # Render the task as a non-root item so the attrs bracket is produced.
    output = ManifestView.render(repo.root.xpath("//task"), style="tree", hide_attrs=False)
    assert "topic=mytopic" in output
    assert "status=active" in output
    assert "resp=alice" in output


def test_hide_attrs_true_still_suppresses_all(repo):
    """Default render suppresses all _HIDDEN_ATTRS from the attrs bracket — regression guard."""
    repo.add_node("/manifest", NodeSpec(tag="project", topic="p"))
    repo.add_node("//project", NodeSpec(tag="task", topic="t", status="active", resp="bob"))
    output = ManifestView.render(repo.root.xpath("//task"), style="tree", hide_attrs=True)
    # None of the hidden attrs should appear in the bracketed attrs section.
    # Check for the key=value form to avoid false matches on formatted line content.
    for attr in _HIDDEN_ATTRS:
        assert f"{attr}=" not in output


def test_render_default_is_hide_attrs_true(repo):
    """Calling render() without hide_attrs should behave as hide_attrs=True."""
    repo.add_node("/manifest", NodeSpec(tag="project", topic="p"))
    repo.add_node("//project", NodeSpec(tag="task", topic="t"))
    nodes = repo.root.xpath("//task")
    default_output = ManifestView.render(nodes, style="tree")
    explicit_output = ManifestView.render(nodes, style="tree", hide_attrs=True)
    assert default_output == explicit_output
