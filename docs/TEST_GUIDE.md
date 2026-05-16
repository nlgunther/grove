# Grove — Test Suite Reference

Quick reference for adding new tests. Update this file whenever a new test
file is created or a significant pattern changes.

---

## Layout

```
tests/
├── test_*.py                      # Manifest Manager unit tests (flat)
├── smart_scheduler/
│   └── test_*.py                  # Smart Scheduler tests
├── shared/
│   └── test_*.py                  # Shared infrastructure tests
└── integration/
    └── test_*.py                  # Cross-package integration tests
```

**Framework:** pytest  
**Config:** `pyproject.toml` → `[tool.pytest.ini_options]`  
`testpaths = ["tests"]`, `pythonpath = ["src"]`  
No `conftest.py` — fixtures are defined per file.

---

## Fixture Patterns

### Manifest (in-memory, no disk I/O)

```python
@pytest.fixture
def repo():
    r = ManifestRepository()
    r.root = etree.Element("manifest")
    r.tree = etree.ElementTree(r.root)
    r.filepath = "test.xml"
    return r
```

Add nodes with `etree.SubElement(repo.root, "tag", attr="val")`.  
Use `repo.root.xpath(...)` to assert tree state after operations.

### Manifest (disk, with sidecar)

```python
@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as d:
        r = ManifestRepository()
        r.load(os.path.join(d, "test.xml"), auto_sidecar=True)
        yield r
```

### Scheduler (parametrized over both storage backends)

```python
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
```

Always parametrize scheduler tests over both backends — the existing suite
does this and storage behaviour can differ.

### Building scheduler test data

`Task.create()` sets `id`, `created_at`, `updated_at` correctly.  
`update_task()` handles: `title`, `due_date`, `assignee`, `notes`, `status`, `tags`.  
Fields **not** handled by `update_task` (e.g. `outcome`, `assignee` on create):
set directly on the model and `storage.save_project(project)`.

```python
project = svc.storage.load_project("slug")
t = Task.create("Title")
t.outcome = "Done"
t.status = TaskStatus.DONE
project.tasks.append(t)
svc.storage.save_project(project)
```

---

## Test File Inventory

### Manifest Manager (`tests/test_*.py`)

| File | What it covers |
|---|---|
| `test_manifest.py` | Core CRUD: add_node, edit_node, delete, search (XPath); wrap_content, merge_from; transaction rollback; tag validation (parametrized) |
| `test_core.py` | ID generation/uniqueness; search_by_id_prefix; ensure_ids; ManifestView depth limiting |
| `test_manifest_core_integration.py` | Sidecar persistence; load with/without --autosc; rebuild_sidecar; edit_node_by_id |
| `test_storage.py` | File I/O; path validation (null bytes, control chars); 7z roundtrip; unicode filenames |
| `test_encryption.py` | Password-protected archives; decryption failure modes |
| `test_add_returns_id.py` | Result.data id/count fields; auto_id vs custom ID |
| `test_move_node.py` | move_node; cycle guard; sidecar refresh after move |
| `test_search.py` | **full_text_search**: attribute/text matching, scoring, sort, breadcrumbs, scope, regexp, case-sensitivity, re.error propagation |
| `test_config.py` | Config loading |
| `test_id_sidecar.py` | IDSidecar CRUD |
| `test_due_attribute.py` | Due date attribute parsing |
| `test_last_modified.py` | _stamp() / last_modified tracking |
| `test_load_aliases.py` | named_files alias resolution |
| `test_export_calendar_ids.py` | export_to_ics with ID-prefix selector |
| `test_parent_id_shortcut.py` | --parent with ID prefix |
| `test_phase3_shortcuts.py` | add shortcut expansion (v3.5) |
| `test_shell.py` | ManifestShell: do_load, do_add, do_edit, do_list integration |
| `test_dataframe_conversion.py` | to_df / from_df round-trips |
| `test_integration_v34.py` | v3.4 compatibility (prefix matching, rebuild) |

### Smart Scheduler (`tests/smart_scheduler/`)

| File | What it covers |
|---|---|
| `test_scheduler.py` | Models (Task/Project/Contact, IDs, status, encoder); date parsing; storage CRUD for both backends; TaskService CRUD; CalendarService ICS generation; MaintenanceService backup/restore |
| `test_scheduler_search.py` | **TaskService.search**: all five fields, active-only default, include_inactive, field restriction, project restriction, case-insensitivity, regexp, re.error — all parametrized over json + sqlite |

### Shared (`tests/shared/`)

| File | What it covers |
|---|---|
| `test_id_generator.py` | generate_id prefix/length; validate_id; extract/shorten |
| `test_locking.py` | file_lock acquire/release; concurrent prevention; stale lock cleanup |
| `test_ics_writer.py` | CalendarEvent / ICSWriter serialization; special-char escaping |

### Integration (`tests/integration/`)

| File | What it covers |
|---|---|
| `test_integration.py` | Cross-package imports; scheduler ID passes shared validate_id; file_lock integration |
| `test_integration_features.py` | Feature-level cross-tool scenarios |

---

## Conventions

- **File names:** `test_<feature>.py` — one concern per file for focused areas,
  broader files (`test_manifest.py`, `test_scheduler.py`) for foundational CRUD.
- **Class grouping:** `class TestModels`, `class TestStorage`, etc. — group by
  logical domain within a file; flat functions are fine for small files.
- **Naming:** `test_<subject>_<expected_outcome>` or `test_<subject>_<condition>`.
- **Assertions:** Plain `assert`; no `assertEqual`. Match strings with
  `"substring" in result.message`; prefer exact equality where possible.
- **Expected exceptions:** `with pytest.raises(SomeError):` — add `match=` only
  when the message is part of the contract.
- **No global state:** every fixture yields and cleans up.
- **Parametrize for equivalence classes**, not for exhaustive enumeration.

---

## Common Imports

```python
# Manifest
import pytest, re, tempfile, os
from unittest.mock import MagicMock, patch
from lxml import etree
from manifest_manager.manifest_core import ManifestRepository, NodeSpec, ManifestView, TaskStatus, Result

# Scheduler
import pytest, re, shutil, tempfile
from pathlib import Path
from smart_scheduler.models import Task, Project, Contact, TaskStatus
from smart_scheduler.storage.factory import get_storage_engine
from smart_scheduler.services.task_service import TaskService
```

---

*Last updated: 2026-05-16 — added test_search.py, test_scheduler_search.py*
