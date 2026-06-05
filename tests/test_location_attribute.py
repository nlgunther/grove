#!/usr/bin/env python3
"""Tests for --location / -l as a first-class attribute on add."""

import os
import sys
import tempfile
from argparse import Namespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from manifest_manager.manifest_core import ManifestRepository, NodeSpec


# ---------------------------------------------------------------------------
# NodeSpec unit tests
# ---------------------------------------------------------------------------

def test_nodespec_location_field():
    """NodeSpec accepts location and includes it in to_xml_attrs()."""
    spec = NodeSpec(tag="task", topic="Board meeting", location="Room 4B")

    assert spec.location == "Room 4B"

    attrs = spec.to_xml_attrs()
    assert attrs.get("location") == "Room 4B"


def test_nodespec_from_args_with_location():
    """from_args() maps args.location onto NodeSpec.location."""
    args = Namespace(
        tag="task",
        topic="Site visit",
        status="active",
        resp="alice",
        due="2026-06-10",
        location="123 Main St",
        text=None,
    )
    spec = NodeSpec.from_args(args)

    assert spec.location == "123 Main St"
    assert spec.to_xml_attrs().get("location") == "123 Main St"


def test_nodespec_from_args_without_location():
    """from_args() works when args has no location attribute (backward compat)."""
    args = Namespace(tag="task", topic="No location", status=None, resp=None,
                     due=None, text=None)
    # Deliberately omit 'location' from the Namespace to simulate an old caller.
    spec = NodeSpec.from_args(args)

    assert spec.location is None
    assert "location" not in spec.to_xml_attrs()


# ---------------------------------------------------------------------------
# Repository integration tests
# ---------------------------------------------------------------------------

def test_add_node_with_location():
    """add_node() stores the location attribute in XML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ManifestRepository()
        repo.load(os.path.join(tmpdir, "test.xml"), auto_sidecar=True)

        spec = NodeSpec(tag="task", topic="Field trip", location="Central Park")
        result = repo.add_node("/*", spec, auto_id=True)
        assert result.success

        task = repo.search("//task")[0]
        assert task.get("location") == "Central Park"
        assert task.get("topic") == "Field trip"


def test_edit_node_with_location():
    """edit_node_by_id() can add and update the location attribute."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ManifestRepository()
        repo.load(os.path.join(tmpdir, "test.xml"), auto_sidecar=True)

        # Create without location
        repo.add_node("/*", NodeSpec(tag="task", topic="Meeting"), auto_id=True)
        task_id = list(repo.root)[0].get("id")

        # Add location via edit
        result = repo.edit_node_by_id(
            task_id, NodeSpec(tag="task", location="Room 4B"), delete=False
        )
        assert result.success
        assert repo.search(f"//task[@id='{task_id}']")[0].get("location") == "Room 4B"

        # Update location
        result = repo.edit_node_by_id(
            task_id, NodeSpec(tag="task", location="Room 5A"), delete=False
        )
        assert result.success
        assert repo.search(f"//task[@id='{task_id}']")[0].get("location") == "Room 5A"


def test_location_xpath_query():
    """Nodes with location are queryable via XPath."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ManifestRepository()
        repo.load(os.path.join(tmpdir, "test.xml"), auto_sidecar=True)

        repo.add_node("/*", NodeSpec(tag="task", topic="On-site", location="HQ"), auto_id=True)
        repo.add_node("/*", NodeSpec(tag="task", topic="Remote"), auto_id=True)

        located = repo.search("//task[@location]")
        assert len(located) == 1
        assert located[0].get("location") == "HQ"

        exact = repo.search("//task[@location='HQ']")
        assert len(exact) == 1


def test_location_backward_compat():
    """NodeSpec without location still works; attribute is absent from XML."""
    spec = NodeSpec(tag="task", topic="No location", status="pending")

    assert spec.location is None
    assert "location" not in spec.to_xml_attrs()


# ---------------------------------------------------------------------------
# -a equivalence test
# ---------------------------------------------------------------------------

def test_location_flag_equivalent_to_attr():
    """-l/--location produces the same XML as -a location=<value>."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = ManifestRepository()
        repo.load(os.path.join(tmpdir, "test.xml"), auto_sidecar=True)

        # Via named flag
        spec_named = NodeSpec(tag="task", topic="Via flag", location="Warehouse")
        repo.add_node("/*", spec_named, auto_id=True)

        # Via attrs dict (what -a location=Warehouse produces)
        spec_attr = NodeSpec(tag="task", topic="Via attr", attrs={"location": "Warehouse"})
        repo.add_node("/*", spec_attr, auto_id=True)

        tasks = repo.search("//task[@location='Warehouse']")
        assert len(tasks) == 2, "Both paths must produce an identical location attribute"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
