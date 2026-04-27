# Grove

**Version**: 2.0.0  
**Last Updated**: April 2026

---

## Overview

Grove is a unified command-line productivity suite combining two complementary tools in a single installable package:

**Manifest Manager v3.5** — hierarchical XML knowledge base for organizing anything with a tree structure: tasks, projects, locations, contacts, notes, and custom schemas. Queried via XPath; edited via an interactive shell.

**Smart Scheduler v2.0** — flat, project-oriented task manager with natural language date parsing, status workflows, and JSON storage. Optimized for daily task tracking with fast ID-based editing.

Both tools share a common infrastructure library (`shared`) for ID generation, file locking, calendar export, date parsing, and cross-tool integration.

---

## Installation

### Prerequisites

- Python 3.8+
- Dependencies: `lxml`, `py7zr`, `pyyaml`

### Setup

```bash
git clone <repository-url>
cd grove

pip install -e .

# Verify both CLIs are available
manifest --help
scheduler --help
```

### Configuration

**Manifest shortcuts** — `config/shortcuts.yaml`:
```yaml
shortcuts:
  - task
  - project
  - note
  - milestone
  - location
  - contact
  - reference

reserved_keywords:
  - help
  - exit
  - save
  - list
  - find
  - edit
  - delete
```

**Scheduler data directory** — set on first run or via `config location`:
```
scheduler
> config location "G:\My Drive\schedulers"
```

**Cross-tool integration** — `config/integration.yaml`:
```yaml
paths:
  scheduler_data_dir: "G:/My Drive/schedulers"
  # manifest_default_dir: "G:/My Drive/manifests"

status_mapping:
  to_scheduler:
    # active:  in_progress
    # pending: todo
    # blocked: waiting
```
All mappings are opt-in — nothing is converted silently until you uncomment them.

---

## Quick Start

### Manifest Manager

```bash
manifest

(manifest) load myproject.xml --autosc
(myproject.xml) add task "Review PR #42"
(myproject.xml) add task "Deploy" --due tomorrow --status active
(myproject.xml) find a3f
(myproject.xml) edit a3f7 --status done
(myproject.xml) save
```

### Smart Scheduler

```bash
scheduler

> new project work "Work Tasks"
> add task work "Deploy website" --due tomorrow --tags urgent,deploy
> list --all
> edit t30b0a --status in_progress
> export-json --all --output backup.json
> cleanup --done --execute
```

### Cross-tool: Manifest → Scheduler

```bash
# Export manifest tasks to the scheduler (from inside the manifest shell)
(myproject.xml) export-scheduler "//task[@due][@status='active']" --project q1-work

# Or pull from inside the scheduler shell
> import-manifest myproject.xml --project q1-work
```

Status mapping is controlled by `config/integration.yaml`. Without explicit mappings configured, all imported tasks arrive as `todo` — no silent coercion.

---

## Architecture

### Directory Structure

```
grove/
├── config/
│   ├── shortcuts.yaml              # Manifest shortcut configuration
│   └── integration.yaml            # Cross-tool integration settings
├── src/
│   ├── shared/                     # Shared infrastructure
│   │   ├── __init__.py
│   │   ├── id_generator.py         # Unified ID generation
│   │   ├── locking.py              # File locking
│   │   ├── dates.py                # Natural language date parsing
│   │   ├── status_map.py           # Bidirectional status conversion
│   │   ├── integration_config.py   # config/integration.yaml loader
│   │   ├── manifest_bridge.py      # Node → Task conversion + push
│   │   └── calendar/
│   │       ├── __init__.py
│   │       └── ics_writer.py       # ICS calendar export
│   ├── manifest_manager/           # Manifest Manager package
│   │   ├── __init__.py
│   │   ├── manifest.py             # CLI shell
│   │   ├── manifest_core.py        # Core repository logic
│   │   ├── storage.py              # XML / 7z storage
│   │   ├── calendar.py             # Calendar export helpers
│   │   ├── config.py               # Per-file config
│   │   ├── id_sidecar.py           # ID index
│   │   ├── dataframe_conversion.py # XML ↔ DataFrame
│   │   └── dataframe_commands.py   # to_df / find_df / from_df
│   └── smart_scheduler/            # Smart Scheduler package
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py                  # Interactive CLI
│       ├── config.py               # Data dir / preferences
│       ├── models.py               # Task, Project, Contact, TaskStatus
│       ├── services/
│       │   ├── task_service.py     # CRUD + global ID lookup
│       │   ├── calendar_service.py # ICS export (via shared.ICSWriter)
│       │   └── maintenance_service.py # Backup / restore
│       └── storage/
│           ├── base.py             # StorageStrategy ABC
│           ├── factory.py          # Engine selection
│           ├── json_store.py       # JSON storage (default)
│           └── sqlite_store.py     # SQLite storage
├── tests/
│   ├── shared/                     # Shared library tests
│   ├── smart_scheduler/            # Scheduler tests
│   ├── integration/                # Cross-package tests
│   └── test_*.py                   # Manifest tests
├── pyproject.toml
└── README.md
```

### `pyproject.toml`

```toml
[project]
name = "grove"
version = "2.0.0"
dependencies = ["lxml>=4.9.0", "py7zr>=0.20.0", "pyyaml>=6.0"]

[project.scripts]
manifest  = "manifest_manager.__main__:main"
scheduler = "smart_scheduler.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]
```

---

## Shared Infrastructure

### Date Parsing

Both tools accept natural language dates via `shared.dates.parse_date`. The `--due` flag in both shells resolves through this function.

```python
from shared.dates import parse_date

parse_date("tomorrow")   # "2026-04-15"
parse_date("+3")         # "2026-04-17"
parse_date("monday")     # next Monday as ISO date
parse_date("2026-06-15") # "2026-06-15" (passthrough)
```

### Status Mapping

Conversion between the tools' different status vocabularies is configured in `config/integration.yaml` and applied via `shared.status_map`. Returns `None` until the user explicitly enables mappings, so callers can default gracefully.

```python
from shared.status_map import to_scheduler_status, to_manifest_status

to_scheduler_status("active")      # "in_progress" if configured, else None
to_manifest_status("in_progress")  # "active" if configured, else None
```

### ID Generation

```python
from shared import generate_id, validate_id

generate_id()                      # "a3f7b2c1"  (manifest: 8-char, no prefix)
generate_id(prefix="t", length=5)  # "ta3f7b"    (scheduler task IDs)
generate_id(prefix="c", length=5)  # "ca3f7b"    (scheduler contact IDs)
```

### File Locking

```python
from shared import file_lock, LockTimeout

with file_lock(Path("data.json"), timeout=5):
    save_data()
```

### ICS Calendar Export

```python
from shared.calendar.ics_writer import CalendarEvent, ICSWriter

writer = ICSWriter("My Tasks")
writer.add_event(CalendarEvent(
    uid="t1a2b3", title="Annual review",
    start_date=date(2026, 9, 1), all_day=True,
))
writer.write("tasks.ics")
```

---

## Key Differences Between the Tools

| | Manifest Manager | Smart Scheduler |
|---|---|---|
| **Data format** | XML (hierarchical) | JSON (flat projects) |
| **Storage location** | Any path, per-file | Configured data dir |
| **Schema** | Flexible / arbitrary tags | Fixed: Project → Task, Contact |
| **Query style** | XPath or ID prefix | ID prefix or project slug |
| **ID format** | 8-char hex (`a3f7b2c1`) | Prefixed 6-char (`ta3f7b`) |
| **Dates** | `due` attribute, natural language | `due_date` field, natural language |
| **Calendar export** | `export-calendar` | `export <id> ics` |
| **Best for** | Knowledge base, complex hierarchies | Daily task tracking, status workflows |

---

## Testing

```bash
pytest                              # all 331 tests
pytest tests/shared/ -v
pytest tests/smart_scheduler/ -v   # parameterized: json + sqlite
pytest tests/integration/ -v

pytest --cov=manifest_manager --cov=smart_scheduler --cov=shared
```

### Test Count (April 2026)

| Suite | Tests |
|---|---|
| Manifest Manager | 172 |
| Smart Scheduler | 57 |
| Shared library | 12 |
| Integration | 59 |
| **Total** | **331** |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'smart_scheduler'`**  
Run `pip install -e .` from the repo root.

**`ModuleNotFoundError: No module named 'shared'`**  
Same fix. `shared` is under `src/` and requires the editable install.

**`export-scheduler` says scheduler data directory not configured**  
Set `paths.scheduler_data_dir` in `config/integration.yaml`, or set `SCHEDULER_DATA_DIR` environment variable.

**Manifest sidecar out of sync after manual XML edit**  
Run `rebuild` inside the manifest shell.

**Scheduler data not found after moving to Google Drive**  
Use `config location <new_path>` inside the scheduler shell, or update `config/integration.yaml`.

**Tests fail with import errors**  
Ensure `pythonpath = ["src"]` is in `pyproject.toml` under `[tool.pytest.ini_options]`, and that test directories do **not** contain `__init__.py` files.

**Integration config changes not taking effect**  
The config is cached per-process. Restart the shell after editing `integration.yaml`.

---

*Last updated: April 2026*
