# Grove 2.0 — API Documentation

**Version**: 2.0.0  
**Last Updated**: April 2026

---

## Table of Contents

1. [Manifest Manager Commands](#manifest-manager-commands)
2. [Manifest Shortcut System](#manifest-shortcut-system)
3. [Manifest DataFrame Commands](#manifest-dataframe-commands)
4. [Smart Scheduler Commands](#smart-scheduler-commands)
5. [Natural Language Date Parsing](#natural-language-date-parsing)
6. [Cross-Tool Integration](#cross-tool-integration)
7. [Shared Infrastructure](#shared-infrastructure)
8. [Python API](#python-api)
9. [Configuration](#configuration)

---

## Manifest Manager Commands

Start with `manifest` to enter the interactive shell, then `load <file>`.

---

### `load`

```
load <filename> [--autosc] [--rebuildsc]
```

| Option | Description |
|---|---|
| `--autosc` | Auto-create ID sidecar if missing |
| `--rebuildsc` | Force-rebuild sidecar from XML on load |

```bash
load myproject.xml --autosc
load backup.7z              # prompts for password
```

---

### `save`

```
save [filename]
```

Encrypts when filename ends in `.7z`.

---

### `backup`

```
backup [filename] [--timestamp] [--force] [--no-sidecar]
```

---

### `restore`

```
restore <filename>
```

Loads a backup into memory. Use `save <original>` afterward to persist.

---

### `add`

```
add <shortcut> ["Title"] [options]      # shortcut syntax
add --tag <n> [options]                  # full syntax
```

| Option | Description |
|---|---|
| `--tag <n>` | Tag name (required in full syntax) |
| `--topic <text>` | Topic / title attribute |
| `--status <value>` | Status |
| `--resp <n>` | Responsible party |
| `--due <date>` | Due date — natural language or `YYYY-MM-DD` |
| `--parent <selector>` | Parent XPath or ID prefix (default: `/*`) |
| `--id <value>` | Custom ID |
| `--id False` | Disable auto-ID |
| `-a <key=value>` | Custom attribute (repeatable) |

`--due` accepts all formats understood by `shared.dates.parse_date`: `today`, `tomorrow`, `+N`, weekday names, ISO, and US format.

Every new node is automatically stamped with a `last_modified` attribute set to the current date (`YYYY-MM-DD`). This attribute is managed by the repository layer and cannot be set via `--attr`.

```bash
add task "Review PR"
add task "Deploy" --status active --resp alice --due tomorrow
add task "Deploy" --due +3
add task "Deploy" --due friday
add --tag item --topic "Chair" -a colour=blue
```

---

### `edit`

```
edit <selector> [options]
```

| Option | Description |
|---|---|
| `--topic <text>` | Update topic |
| `--status <value>` | Update status |
| `--resp <n>` | Update responsible party |
| `--due <date>` | Update due date |
| `--text <text>` | Update body text |
| `-a <key=value>` | Add / update attribute |
| `--delete` | Delete matched node(s) |
| `--id` / `--xpath` | Force interpretation |

`last_modified` is automatically updated to today's date on every successful edit.

---

### `delete`

```
delete <selector> [--id] [--xpath]
```

Aliases: `del`, `remove`.

---

### `move`

```
move <src> <dest>
```

Both selectors accept ID prefix or XPath; each must match exactly one node.

---

### `show`

```
show <selector> [--id] [--xpath]
```

Displays all attributes including `last_modified`, regardless of the `verbose` setting.

---

### `find`

```
find <prefix> [--tree] [--depth N]
```

Requires sidecar index (load with `--autosc`). Tree output respects the current `verbose` setting.

---

### `list`

```
list [selector] [--style tree|table] [--depth N] [--id] [--xpath]
```

Output respects the current `verbose` setting.

---

### `verbose`

```
verbose
```

Toggles display of hidden attributes (`topic`, `status`, `resp`, `last_modified`) in `list` and `find --tree` output. These attributes are suppressed by default because they already appear in the formatted line. Toggle on to audit raw attribute values such as `last_modified` dates.

```bash
verbose        # → "Verbose attrs: ON"
verbose        # → "Verbose attrs: OFF"
```

The toggle is session-only and resets to OFF on next `manifest` invocation. To inspect timestamps on specific nodes without toggling, use `show <id>` which always displays all attributes, or use `search`:

```bash
search //*[@last_modified='2026-04-15']
search //*[not(@last_modified)]        # nodes not yet touched since upgrade
search /manifest//*[not(@last_modified)]  # same, excluding the root element
```

---

### `export-calendar`

```
export-calendar <selector> <output.ics> [--name NAME] [--id] [--xpath]
```

Nodes must have a `due="YYYY-MM-DD"` attribute.

---

### `export-scheduler`

Export manifest nodes directly into the Smart Scheduler as tasks.

```
export-scheduler [selector] --project <slug> [--name <n>] [--engine json|sqlite]
```

| Option | Description |
|---|---|
| `selector` | XPath or ID prefix. Defaults to `export_scheduler.default_xpath` in `integration.yaml`, or `//task[@due]` |
| `--project` | Scheduler project slug (required). Created if absent. |
| `--name` | Project display name (used only when creating) |
| `--engine` | `json` (default) or `sqlite` |

Requires `paths.scheduler_data_dir` in `config/integration.yaml`.  
Status conversion requires `status_mapping.to_scheduler` to be configured; otherwise tasks arrive as `todo`.

```bash
export-scheduler --project q1-work
export-scheduler "//task[@due][@status='active']" --project q1-work
export-scheduler a3f7 --project q1-work
```

---

### `wrap`

```
wrap --root <tag>
```

---

### `merge`

```
merge <filename>
```

---

### `autoid`

```
autoid [--overwrite]
```

---

### `rebuild`

Rebuild the ID sidecar from current in-memory XML. Use after manual XML edits.

---

### `exit`

Warns on unsaved changes; run twice to force quit. `Ctrl+D` also exits.

---

## Manifest Shortcut System

```
add task "Title"
# expands to:
add --tag task --topic "Title"
```

Title must come immediately after the shortcut noun, before any flags.

**Default shortcuts**: `task`, `project`, `item`, `note`, `milestone`, `idea`, `location`, `contact`, `reference`, `resource`

**Config**: `config/shortcuts.yaml`

```yaml
shortcuts:
  - task
  - my_custom_tag    # add yours here

reserved_keywords:
  - help
  - exit
  - save
```

---

## Manifest DataFrame Commands

Requires `pandas`. Injected at startup; silently unavailable if pandas is not installed.

### `to_df`

```
to_df [xpath] [--save FILE] [--no-text]
```

### `find_df`

```
find_df <xpath> [--save FILE]
```

### `from_df`

```
from_df <file> [--parent XPATH] [--dry-run]
```

---

---

## Smart Scheduler Commands

Start with `scheduler` to enter the interactive shell.

---

### `list`

```
list
list --all [--show-done]
list projects
list tasks [<project_slug>]
```

---

### `show`

```
show <task_id>
show <contact_id>
show <project_slug>
```

---

### `new`

```
new project <slug> <n> [--desc <text>]
```

---

### `add`

```
add task <project_slug> <title> [--due <date>] [--note <text>] [--tags <t1,t2>]
add contact <project_slug> <n> [--role <text>] [--email <email>] [--phone <phone>]
```

`--due` accepts all natural language formats.

---

### `edit`

```
edit <task_id> [options]
edit <project_slug> [options]
```

**Task options**: `--title`, `--due`, `--status`, `--note`, `--tags`  
**Project options**: `--name`, `--desc`  
**Valid statuses**: `todo` · `in_progress` · `waiting` · `done` · `cancelled`

No project slug needed — task ID is sufficient.

---

### `delete`

```
delete <task_id>
delete <project_slug>
```

Both prompt for confirmation.

---

### `cleanup`

```
cleanup                         # dry run
cleanup --done [--execute]
cleanup --cancelled [--execute]
cleanup --done --cancelled [--execute]
```

---

### `export`

```
export <task_id> ics
```

---

### `export-json`

```
export-json <task_id>
export-json <project_slug>
export-json --all [--output <filename>]
```

---

### `import-json`

```
import-json <file> [--to <project>] [--merge] [--dry-run]
```

---

### `import-manifest`

Import tasks from a Manifest Manager XML file.

```
import-manifest <file> --project <slug> [--xpath <expr>] [--engine json|sqlite]
```

| Option | Description |
|---|---|
| `file` | Path to manifest XML file |
| `--project` | Target project slug (required). Created if absent. |
| `--name` | Project display name (used only when creating) |
| `--xpath` | Node selector. Defaults to `import_manifest.default_xpath` in `integration.yaml`, or `//task[@due]` |
| `--engine` | `json` (default) or `sqlite` |

```bash
import-manifest projects.xml --project q1-work
import-manifest projects.xml --project q1-work --xpath "//task[@due][@status='active']"
```

---

### `backup`

```
backup [--name <n>] [--compress]
```

---

### `restore`

```
restore <path>
```

---

### `config`

```
config
config location <new_path>
config reset
```

Data dir priority: `SCHEDULER_DATA_DIR` env var → config file → `~/.scheduler`.

---

### `maintenance`

```
maintenance --optimize
```

---

## Natural Language Date Parsing

Both tools resolve `--due` values through `shared.dates.parse_date`.

| Input | Result |
|---|---|
| `today` | Current date |
| `tomorrow` | +1 day |
| `yesterday` | −1 day |
| `+N` | +N days |
| `monday` … `sunday` | Next occurrence (never today) |
| `2026-12-25` | ISO passthrough |
| `12/25/2026` | US format → ISO |
| anything else | `None` (original value preserved) |

Multi-word expressions require quotes: `--due "next friday"`.

---

---

## Cross-Tool Integration

### `export-scheduler` / `import-manifest`

Both commands use `shared.manifest_bridge` for conversion. The bridge:

1. Maps `topic` → `Task.title`, `due` → `Task.due_date`, `resp` → `Task.assignee`
2. Converts status via `shared.status_map` (returns `None` if not configured → task gets `todo`)
3. Stores the originating manifest node ID in `Task.notes` as `manifest:<id>` (configurable)
4. Locks the scheduler JSON file via `shared.locking` during write

Nodes without a `topic`/`title`/text, or without a `due` date (when `on_missing_due: skip`), are skipped and reported.

### `config/integration.yaml`

The single configuration file governing all cross-tool behaviour. Key sections:

```yaml
paths:
  scheduler_data_dir: "G:/My Drive/schedulers"

status_mapping:
  to_scheduler:      # manifest → scheduler
    active:    in_progress
    pending:   todo
    blocked:   waiting
  to_manifest:       # scheduler → manifest (for future use)
    in_progress: active

export_scheduler:
  default_xpath: ""          # fallback to //task[@due] if empty
  on_missing_due: skip       # skip | warn | export
  store_manifest_id: true

import_manifest:
  default_xpath: ""
  on_missing_due: skip
  store_manifest_id: true
```

All entries are opt-in. The file ships with everything commented out except `scheduler_data_dir`.

Config is resolved in order: `TASK_MANAGER_CONFIG` env var → `config/integration.yaml` → empty dict.  
Config is cached per-process; restart the shell after editing.

---

---

## Shared Infrastructure

### `shared.dates`

#### `today_str()`

```python
from shared.dates import today_str

today_str()   # "2026-04-15"
```

Single source of truth for `last_modified` stamping. Returns today's date as an ISO 8601 string.

#### `parse_date(date_str)`

```python
from shared.dates import parse_date

parse_date("tomorrow")   # "2026-04-15"
parse_date("+3")         # "2026-04-17"
parse_date("monday")     # next Monday
parse_date("2026-06-15") # "2026-06-15"
parse_date(None)         # None
```

---

### `shared.status_map`

#### `to_scheduler_status(manifest_status)` / `to_manifest_status(scheduler_status)`

Both return `None` if the mapping is not configured in `integration.yaml`. The caller decides the fallback (typically `"todo"` / `"active"`).

```python
from shared.status_map import to_scheduler_status, to_manifest_status
from smart_scheduler.models import TaskStatus

s = to_scheduler_status("active")          # "in_progress" or None
task.status = TaskStatus(s) if s else TaskStatus.TODO

m = to_manifest_status(TaskStatus.WAITING) # "blocked" or None
```

---

### `shared.id_generator`

#### `generate_id(prefix="", length=8)`

```python
from shared.id_generator import generate_id, validate_id

generate_id()                       # "a3f7b2c1"
generate_id(prefix="t", length=5)   # "ta3f7b"
validate_id("ta3f7b", prefix="t")   # True
```

---

### `shared.locking`

#### `file_lock(filepath, timeout=5, stale_threshold=300)`

Context manager for exclusive file access. Raises `LockTimeout` if lock cannot be acquired.

```python
from shared.locking import file_lock, LockTimeout

with file_lock(Path("data.json"), timeout=10):
    save_data()
```

---

### `shared.calendar.ics_writer`

#### `CalendarEvent` / `ICSWriter`

```python
from shared.calendar.ics_writer import CalendarEvent, ICSWriter
from datetime import date

writer = ICSWriter("My Tasks")
writer.add_event(CalendarEvent(
    uid="t1a2b3",
    title="Annual review",
    start_date=date(2026, 9, 1),
    all_day=True,
    description="Prepare slides",
))
writer.write("tasks.ics")
content = writer.to_string()
```

---

---

## Python API

### `ManifestRepository`

| Method | Description |
|---|---|
| `load(filepath, password, auto_sidecar, rebuild_sidecar)` | Load XML or 7z |
| `save(filepath, password)` | Save XML or 7z |
| `add_node(parent_xpath, spec, auto_id=True)` | Add a node; stamps `last_modified` automatically |
| `edit_node(xpath, spec, delete=False)` | Edit/delete by XPath; stamps `last_modified` on edit |
| `edit_node_by_id(elem_id, spec, delete=False)` | Edit/delete by ID; stamps `last_modified` on edit |
| `ensure_ids(overwrite=False)` | Assign IDs to nodes missing one |
| `search(xpath)` | Return list of matching elements |
| `search_by_id_prefix(prefix)` | Return elements matching ID prefix |
| `wrap_content(new_root_tag)` | Wrap top-level nodes |
| `merge_from(path, password)` | Merge another manifest |

All mutating methods return a `Result(success, message, data)`.

### `ManifestView`

```python
ManifestView.render(nodes, style="tree", max_depth=None, hide_attrs=True)
```

`hide_attrs=True` (default) suppresses `topic`, `status`, `resp`, and `last_modified` from the inline attrs bracket. Pass `hide_attrs=False` to show all attributes — equivalent to the `verbose` shell command.

### `NodeSpec`

```python
from manifest_manager.manifest_core import NodeSpec

spec = NodeSpec(
    tag="task", topic="Review PR",
    status="active", resp="alice",
    due="2026-03-15", attrs={"priority": "high"},
)
spec = NodeSpec.from_args(args, attributes=extra_attrs)
```

`last_modified` is not a `NodeSpec` field. It is set unconditionally by the repository layer on every create and edit operation.

### `TaskService`

```python
from smart_scheduler.services.task_service import TaskService

svc = TaskService(storage)
svc.create_project("work", "Work Tasks")
task = svc.add_task("work", "Deploy", due="tomorrow", tags=["urgent"])
svc.update_task("work", task.id, status="in_progress")

project, task = svc.find_task_by_id("t30b0a")   # cross-project lookup
svc.delete_task_by_id("t30b0a")
```

### `MaintenanceService`

```python
from smart_scheduler.services.maintenance_service import MaintenanceService

maint = MaintenanceService(storage)
backup_path = maint.backup("snap", compress=True)
maint.restore(str(backup_path))
```

### `manifest_bridge`

```python
from shared.manifest_bridge import build_tasks, push_tasks_to_scheduler

tasks, skipped = build_tasks(nodes)          # lxml elements → Task list
result = push_tasks_to_scheduler(
    tasks=tasks,
    project_slug="q1-work",
    project_name="Q1 Work",
    data_dir=Path("G:/My Drive/schedulers"),
)
print(result)   # "✓ Created 5 task(s). Skipped 2 node(s)."
```

---

## Configuration

### `pyproject.toml`

```toml
[project]
name = "grove"
version = "2.0.0"
requires-python = ">=3.8"
dependencies = ["lxml>=4.9.0", "py7zr>=0.20.0", "pyyaml>=6.0"]

[project.scripts]
manifest  = "manifest_manager.__main__:main"
scheduler = "smart_scheduler.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

### `config/shortcuts.yaml`

```yaml
shortcuts:
  - task
  - project
  - item
  - note
  - milestone
  - idea
  - location
  - contact
  - reference
  - resource

reserved_keywords:
  - help
  - exit
  - save
  - list
  - find
  - edit
  - delete
```

### `config/integration.yaml`

See [Cross-Tool Integration](#cross-tool-integration) above for full reference.

### Scheduler config — `~/.scheduler/config.json`

```json
{
  "data_dir": "G:\\My Drive\\schedulers",
  "preferences": { "storage_engine": "json" }
}
```

Override with `SCHEDULER_DATA_DIR` environment variable.

---

*Last updated: April 2026*
