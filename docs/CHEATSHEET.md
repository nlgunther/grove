# Grove 2.0 — Cheatsheet

**Version**: 2.0.0 | **Quick Reference**

---

## Launch

```bash
manifest       # Manifest Manager interactive shell
scheduler      # Smart Scheduler interactive shell
```

---

# MANIFEST MANAGER

## File Operations

```bash
load myproject.xml              # Load (creates if missing)
load basic                      # Load by alias (defined in integration.yaml)
load basic --autosc             # Load alias + create sidecar
load myproject.xml --autosc     # Load + create sidecar if missing
load myproject.xml --rebuildsc  # Load + force-rebuild sidecar
load backup.7z                  # Load encrypted (prompts password)

save                            # Overwrite current file
save backup.xml                 # Save to new file
save backup.7z                  # Save encrypted (prompts password)

backup                          # → project.bkp.xml
backup --timestamp              # → project.20260301_143022.xml
backup mybackup.xml

restore project.bkp.xml         # Load backup; use save to write back
```

---

## Add Nodes

```bash
# Shortcut syntax (recommended)
add task "Review PR"
add task "Deploy" --status active --resp alice --due tomorrow
add task "Deploy" --due +3
add task "Deploy" --due friday
add task "Subtask" --parent a3f7
add project "Q1 Goals" --status planning

# Full syntax (always works)
add --tag task --topic "Review PR"
add --tag item --topic "Chair" -a colour=blue

# ID control
add task "No ID" --id False
add task "Custom" --id my-id-123
```

`--due` accepts natural language: `today`, `tomorrow`, `yesterday`, `+N`, weekday names, `YYYY-MM-DD`, `MM/DD/YYYY`.

**Default shortcuts**: `task`, `project`, `item`, `note`, `milestone`, `idea`, `location`, `contact`, `reference`, `resource`  
Add custom shortcuts in `config/shortcuts.yaml`.

---

## Edit & Delete

```bash
edit a3f7 --status done
edit a3f7 --topic "Updated title"
edit a3f7 --due tomorrow
edit a3f7 --resp alice
edit a3f7 --text "New body text"
edit a3f7 -a priority=high
edit "//task[@status='pending']" --status active

delete a3f7
delete "//task[@status='cancelled']"
del a3f7 / remove a3f7         # aliases

move a3f7 b1c2                 # by ID
move a3f //archive             # ID → XPath
```

---

## View & Search

```bash
list                            # full tree
list --style table
list --depth 2
list "//task[@status='active']"

find a3f                        # by ID prefix (requires sidecar)
find a3f --tree --depth 2

show a3f7
show "//project[1]"
```

---

## Export to Scheduler

```bash
export-scheduler --project q1-work
export-scheduler "//task[@due][@status='active']" --project q1-work
export-scheduler a3f7 --project q1-work
```

Requires `paths.scheduler_data_dir` set in `config/integration.yaml`.  
Status mapping is opt-in — tasks arrive as `todo` until mappings are configured.

---

## Calendar Export

```bash
export-calendar "//task[@due]" tasks.ics
export-calendar "//task[@due][@status='active']" active.ics --name "Active Tasks"
export-calendar a3f my-task.ics
```

Nodes must have a `due="YYYY-MM-DD"` attribute to be exported.

---

## DataFrame Commands

Requires `pip install pandas`.

```bash
to_df                           # preview entire manifest
to_df --save all.csv
to_df "//task[@status='active']" --save active.csv

find_df "//task[@due]" --save due.csv

from_df updated.csv
from_df updated.csv --parent "//project[@id='p1']"
from_df updated.csv --dry-run
```

---

## Structure & Maintenance

```bash
wrap --root archive
merge other.xml
autoid / autoid --overwrite
rebuild                         # resync sidecar with XML
cheatsheet
```

---

## XPath Quick Reference

```bash
/*                              # all top-level nodes
//task                          # all task elements
//task[@status='active']        # filtered by attribute
//task[@due]                    # nodes with a due attribute
//task[@status='active'][@resp='alice']
//*[contains(@topic,'bug')]
```

---

## Manifest ID Rules

Hex string of 3–8 chars with no `/`, `[`, `@`, `*`, or `=` is treated as an ID prefix.

```bash
edit a3f --status done          # auto-detected as ID prefix
edit "//task[@id='a3f7b2c1']"   # explicit XPath
```

## Manifest Status Values

`active` · `done` · `pending` · `blocked` · `cancelled`

---

---

# SMART SCHEDULER

## Status Icons

| Icon | Status | `--status` value |
|------|--------|-----------------|
| ○ | todo | `todo` |
| ▶ | in progress | `in_progress` |
| ⏳ | waiting | `waiting` |
| ✓ | done | `done` |
| ✗ | cancelled | `cancelled` |

---

## View

```bash
list                            # project summary
list --all                      # detailed (hides completed)
list --all --show-done
list tasks / list tasks work

list tasks --upcoming           # active tasks: no due date or due date >= today
list tasks work --upcoming      # same, scoped to one project

show t30b0a / show work
```

---

## Create

```bash
new project work "Work Tasks" --desc "Description"

add task work "Title" --due tomorrow --tags urgent,bug
add task work "Title" --due friday --note "Detail"

add contact work "Name" --role "Client" --email "e@example.com"
```

`--due` accepts the same natural language as the manifest.

---

## Edit

```bash
edit t30b0a --status in_progress
edit t30b0a --due "next friday"
edit t30b0a --note "Updated"
edit t30b0a --title "New title" --tags urgent,backend

edit work --name "New Name" --desc "Updated"
```

No project slug needed — task ID is enough.

---

## Delete & Cleanup

```bash
delete t30b0a
delete work

cleanup                                 # preview
cleanup --done --execute
cleanup --done --cancelled --execute
```

---

## Export & Import

```bash
export t30b0a ics                       # task → .ics

export-json t30b0a / export-json work
export-json --all --output backup.json

import-manifest myproject.xml --project q1-work
import-manifest myproject.xml --project q1-work --xpath "//task[@due][@status='active']"
```

---

## Backup & Config

```bash
backup / backup --name snap / backup --compress
restore /path/to/backup.zip

config
config location "G:\My Drive\schedulers"
config reset
```

---

## Scheduler Tips

- No project needed for edits: `edit t30b0a` works anywhere
- Preview before deleting: run `cleanup` without `--execute` first
- Multi-word dates need quotes: `--due "next friday"`
- Tags have no spaces: `--tags urgent,bug` not `urgent, bug`

---

---

# SHARED INFRASTRUCTURE

```python
from shared import generate_id, validate_id, file_lock, LockTimeout
from shared.dates import parse_date
from shared.status_map import to_scheduler_status, to_manifest_status
from shared.calendar.ics_writer import CalendarEvent, ICSWriter

generate_id()                       # "a3f7b2c1"
generate_id(prefix="t", length=5)   # "ta3f7b"
parse_date("tomorrow")              # "2026-04-15"
to_scheduler_status("active")       # "in_progress" if configured, else None

with file_lock(Path("data.json"), timeout=5):
    save_data()
```

---

# CROSS-TOOL INTEGRATION

**Config file**: `config/integration.yaml`

```yaml
paths:
  scheduler_data_dir: "G:/My Drive/schedulers"

named_files:
  basic: "G:/My Drive/manifests/todo2026.xml"
  work:  "G:/My Drive/manifests/work.xml"

status_mapping:
  to_scheduler:
    active:  in_progress   # uncomment to enable
    pending: todo
    blocked: waiting
```

`named_files` entries can be used anywhere the manifest `load` command accepts a filename. Add as many as you like — names are case-sensitive.

Changes take effect on next shell start (config is cached per-process).

---

*Last updated: April 2026*
