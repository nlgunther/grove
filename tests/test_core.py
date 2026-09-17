"""
test_core.py
============
Tests for ManifestRepository, Validation, and Logic.
"""
import pytest
from unittest.mock import MagicMock, patch
from lxml import etree
from manifest_manager.manifest_core import ManifestRepository, NodeSpec, TaskStatus

@pytest.fixture
def mock_storage():
    """Mock storage to avoid disk I/O."""
    return MagicMock()

@pytest.fixture
def repo(mock_storage):
    """Repo with mocked storage and empty in-memory tree."""
    r = ManifestRepository()
    r.storage = mock_storage
    r.root = etree.Element("manifest")
    r.tree = etree.ElementTree(r.root)
    r.filepath = "test.xml"
    return r

def test_add_node_simple(repo):
    spec = NodeSpec(tag="task", topic="Unit Test", status="active")
    res = repo.add_node("/*", spec)
    assert res.success
    assert len(repo.root) == 1
    assert repo.root[0].get("topic") == "Unit Test"

def test_add_node_validation_error(repo):
    """Ensure invalid tags are rejected."""
    spec = NodeSpec(tag="Invalid Tag") 
    with pytest.raises(ValueError):
        repo.add_node("/*", spec)

def test_edit_node_update(repo):
    etree.SubElement(repo.root, "item", topic="Old", id="1")
    spec = NodeSpec("ignored", topic="New", status="done")
    
    res = repo.edit_node("//item", spec, delete=False)
    assert res.success
    assert repo.root[0].get("topic") == "New"
    assert repo.root[0].get("status") == "done"

def test_edit_node_delete(repo):
    etree.SubElement(repo.root, "item", id="1")
    res = repo.edit_node("//item", None, delete=True)
    assert res.success
    assert len(repo.root) == 0

def test_wrap_content(repo):
    etree.SubElement(repo.root, "item1")
    etree.SubElement(repo.root, "item2")
    
    res = repo.wrap_content("archive")
    assert res.success
    assert len(repo.root) == 1
    assert repo.root[0].tag == "archive"
    assert len(repo.root[0]) == 2

def test_merge_from(repo, mock_storage):
    mock_storage.load.return_value = b'<manifest><imported/></manifest>'
    res = repo.merge_from("other.xml")
    assert res.success
    assert len(repo.root) == 1
    assert repo.root[0].tag == "imported"

def test_transaction_rollback(repo):
    """Ensure repo stays clean if an error occurs."""
    etree.SubElement(repo.root, "existing")
    initial_len = len(repo.root)
    
    # Patch internal method to force a crash during add
    # FIX: We must catch the exception because transaction() re-raises it after rollback
    with patch.object(repo, '_safe_xpath', side_effect=Exception("Boom")):
        with pytest.raises(Exception, match="Boom"):
            repo.add_node("//any", NodeSpec("task"))
            
    # Assert state was restored (only 'existing' remains)
    assert len(repo.root) == initial_len
    assert repo.root[0].tag == "existing"

def test_generate_id(repo):
    """Test ID generation produces 8-char hex strings."""
    id1 = repo.generate_id()
    assert len(id1) == 8
    assert all(c in '0123456789abcdef' for c in id1)
    
    # IDs should be unique
    id2 = repo.generate_id()
    assert id1 != id2

def test_generate_id_uniqueness(repo):
    """Test ID generation avoids collisions with existing IDs."""
    existing = {"aaaaaaaa", "bbbbbbbb"}
    new_id = repo.generate_id(existing)
    assert new_id not in existing

def test_add_node_auto_id(repo):
    """Test that add_node auto-generates ID by default."""
    spec = NodeSpec(tag="task", topic="Test")
    repo.add_node("/*", spec, auto_id=True)
    
    assert len(repo.root) == 1
    assert repo.root[0].get("id") is not None
    assert len(repo.root[0].get("id")) == 8

def test_add_node_custom_id(repo):
    """Test that custom ID is preserved."""
    spec = NodeSpec(tag="task", topic="Test", attrs={"id": "CUSTOM-123"})
    repo.add_node("/*", spec, auto_id=False)
    
    assert repo.root[0].get("id") == "CUSTOM-123"

def test_add_node_no_id(repo):
    """Test that auto_id=False prevents ID generation."""
    spec = NodeSpec(tag="task", topic="Test")
    repo.add_node("/*", spec, auto_id=False)
    
    assert repo.root[0].get("id") is None

def test_search_by_id_prefix(repo):
    """Test searching by ID prefix."""
    etree.SubElement(repo.root, "item", id="abc123")
    etree.SubElement(repo.root, "item", id="abc456")
    etree.SubElement(repo.root, "item", id="xyz789")
    
    result = repo.search_by_id_prefix("abc")
    assert result.success
    assert len(result.data) == 2

def test_search_by_id_prefix_not_found(repo):
    """Test search with no matches."""
    etree.SubElement(repo.root, "item", id="abc123")
    
    result = repo.search_by_id_prefix("xyz")
    assert not result.success
    assert "No IDs" in result.message

def test_ensure_ids(repo):
    """Test bulk ID assignment."""
    # Add elements without IDs
    etree.SubElement(repo.root, "item1")
    etree.SubElement(repo.root, "item2")
    etree.SubElement(repo.root, "item3", id="existing")
    
    result = repo.ensure_ids(overwrite=False)
    assert result.success
    
    # Should have added IDs to item1 and item2, skipped item3
    assert repo.root[0].get("id") is not None
    assert repo.root[1].get("id") is not None
    assert repo.root[2].get("id") == "existing"  # Preserved

def test_ensure_ids_overwrite(repo):
    """Test bulk ID assignment with overwrite."""
    etree.SubElement(repo.root, "item", id="old_id")
    
    result = repo.ensure_ids(overwrite=True)
    assert result.success
    assert repo.root[0].get("id") != "old_id"  # Replaced

def test_manifest_view_depth_limit(repo):
    """Test ManifestView respects max_depth parameter."""
    from manifest_manager.manifest_core import ManifestView
    
    # Build tree: project > task > step > note
    project = etree.SubElement(repo.root, "project", id="p1", topic="Test")
    task = etree.SubElement(project, "task", id="t1", topic="Task1")
    step = etree.SubElement(task, "step", id="s1")
    etree.SubElement(step, "note", id="n1")
    
    # Render with depth=2 (should show project and task, not step/note)
    output = ManifestView.render([project], style="tree", max_depth=2)
    
    assert "Test" in output  # Project shown
    assert "Task1" in output  # Task shown
    # Step and note should not appear (depth limit reached)
    assert "s1" not in output or output.count("s1") == 0

def test_manifest_view_depth_zero(repo):
    """Test depth=1 shows only the root node (depth=0 shows nothing)."""
    from manifest_manager.manifest_core import ManifestView
    
    project = etree.SubElement(repo.root, "project", id="p1", topic="Root")
    etree.SubElement(project, "task", id="t1", topic="Child")
    
    # depth=1 shows root level only
    output = ManifestView.render([project], style="tree", max_depth=1)
    
    assert "Root" in output
    assert "Child" not in output  # Child should be hidden

def test_manifest_view_email_style_hides_ids_and_uses_name(repo):
    """Email style renders readable prose: headings from topic, numbered
    items from name/text, and never leaks raw IDs."""
    from manifest_manager.manifest_core import ManifestView

    project = etree.SubElement(repo.root, "project", id="p1", topic="restaurants")
    city = etree.SubElement(project, "city", id="c1", topic="san francisco")
    task = etree.SubElement(city, "task", id="t1", name="Kin Kaho", status="active")
    task.text = "Incredible Thai food near Powell Street BART."

    output = ManifestView.render([project], style="email")

    assert "Restaurants" in output or "restaurants" in output
    assert "San Francisco" in output or "san francisco" in output
    assert "Kin Kaho" in output
    assert "Incredible Thai food near Powell Street BART." in output
    assert "1." in output
    assert "p1" not in output
    assert "c1" not in output
    assert "t1" not in output


def test_manifest_view_email_style_shows_extra_attrs(repo):
    """Attributes without dedicated handling still surface, just phrased
    as 'key: value' instead of being dropped."""
    from manifest_manager.manifest_core import ManifestView

    project = etree.SubElement(repo.root, "project", id="p1", topic="restaurants")
    task = etree.SubElement(project, "task", id="t1", name="Kin Kaho", cuisine="thai")
    task.text = "Great food."

    output = ManifestView.render([project], style="email")

    assert "cuisine: thai" in output
