# Manifest Manager Cheatsheet

**Version**: 3.5.0 | **Quick Reference**

---

## Shortcut Syntax (v3.5+)

```bash
add task "Title"                        # → add --tag task --topic "Title"
add project "Q1 Goals" --status active
add location "Room 203" --parent a3f7
add note "Remember this"
```

**Title must come immediately after the shortcut, before any flags.**

Default shortcuts: `task`, `project`, `item`, `note`, `milestone`, `idea`, `location`, `contact`, `reference`, `resource`

Add custom shortcuts in `config/shortcuts.yaml`.

---

<<<<<<< HEAD

## File Operations

=======

## 📝 Full Syntax (Always Works)

```bash
# Traditional format
add --tag task --topic "Buy milk"
add --tag project --title "Q1 Goals" --status planning
add --tag item --topic "Chair" --parent a3f7
```

**Note**: Use `--topic` or `--title` (they're aliases)

---

## 🔍 Finding Nodes

### By XPath

```bash
find //task
find "//task[@status='active']"
find "//project[@title='Website']//task"
```

### By ID

```bash
find a3f7b2c1              # Full ID
find a3f7                  # Prefix (shows selection if multiple)
```

### With View Formats

```bash
find //task --view tree    # Hierarchical (default)
find //task --view table   # Tabular
find //task --view compact # Minimal
```

---

## ✏️ Editing Nodes

### By ID

```bash
edit a3f7 --status done
edit a3f7 --status done --assignee charlie
edit a3f7 --clear-due      # Remove attribute
```

### By XPath

```bash
edit "//task[@title='Review']" --status in_progress
```

---

# Move:

```bash
move <src> <dest>     Move node + subtree to a new parent
src               ID, ID-prefix, or XPath (must match exactly 1 node)
dest              ID, ID-prefix, or XPath of the new parent (must match exactly 1 node)
```

## EXAMPLES:

```bash
  move a3f7 b1c2                         # Move by ID
  move a3f //archive                     # ID source, XPath destination
  move "//task[@status='done']" //done   # XPath to XPath (1 match required)
```

## 📂 File Operations

### Load

```bash
load project.xml
load project.xml --autosc       # create sidecar if missing
load project.xml --rebuildsc    # force-rebuild sidecar on load
load backup.7z                  # encrypted (prompts for password)

save                            # overwrite current file
save backup.xml                 # save to new file
save backup.7z                  # save encrypted

backup                          # → project.bkp.xml
backup --timestamp              # → project.20260301_143022.xml
backup mybackup.xml             # custom name
backup --force                  # overwrite without prompting

restore project.bkp.xml         # load backup; then use save to write back
```

---

## Add Nodes

```bash
# Shortcut
add task "Review PR"
add task "Deploy" --status active --resp alice --due 2026-03-15
add task "Subtask" --parent a3f7
add task "In project" --parent "//project[@topic='Q1']"

# Full syntax
add --tag task --topic "Review PR"
add --tag item --topic "Chair" -a colour=blue -a condition=new

# Custom / disable ID
add task "No ID" --id False
add task "Custom" --id my-id-123
```

---

## Edit & Delete

```bash
# Edit
edit a3f7 --status done
edit a3f --topic "Updated"          # ID prefix (interactive if multiple)
edit "//task[@status='pending']" --status active
edit a3f7 --text "New body text"
edit a3f7 -a priority=high

# Delete (three equivalent forms)
delete a3f7
del a3f7
remove a3f7
delete "//task[@status='cancelled']"

# Delete via edit
edit a3f7 --delete
```

---

## View & Search

```bash
# List
list                                # full tree
list --style table
list --depth 2
list "//task[@status='active']"

# Find by ID prefix (needs sidecar)
find a3f
find a3f --tree                     # show full subtrees
find a3f --tree --depth 2

# Show single node in detail
show a3f7
show "//project[1]"
```

---

## Calendar Export

```bash
export-calendar "//task[@due]" tasks.ics
export-calendar "//task[@due][@status='active']" active.ics --name "Active Tasks"
export-calendar a3f my-task.ics     # by ID prefix
export-calendar a3f7b2c1 task.ics   # by full ID
```

Elements must have a `due="YYYY-MM-DD"` attribute to be exported.

---

## DataFrame Commands

Requires `pip install pandas`.

```bash
to_df                               # preview entire manifest as DataFrame
to_df --save all.csv
to_df "//task[@status='active']" --save active.csv
to_df --no-text --save meta.csv     # faster, metadata only

find_df "//task[@status='active']"
find_df "//task[@due]" --save due.csv

from_df updated.csv
from_df updated.csv --parent "//project[@id='p1']"
from_df updated.csv --dry-run       # preview only
```

---

## Structure & Maintenance

```bash
wrap --root archive                 # wrap all top-level nodes under <archive>
merge other.xml                     # import all nodes from another file
autoid                              # add IDs to nodes that lack one
autoid --overwrite                  # replace all IDs
rebuild                             # sync sidecar with current XML
cheatsheet                          # print this sheet
```

---

## XPath Quick Reference

```bash
/*                                  # all top-level nodes
//task                              # all task elements
//task[@status='active']            # tasks with status=active
//task[@due]                        # tasks that have a due attribute
//project//task                     # tasks anywhere inside a project
//task[@status='active'][@resp='alice']   # multiple conditions
//*[contains(@topic,'bug')]         # topic contains 'bug'
```

---

## ID Selector Rules

A string is treated as an ID prefix when it is 3–8 hex characters with no `/`, `[`, `@`, `*`, or `=`.  
Use `--id` or `--xpath` to force interpretation.

```bash
edit a3f --status done              # ID prefix → auto-detects
edit "//task[@id='a3f7b2c1']" ...   # XPath → explicit
edit a3f7b2c1 --id --status done    # force ID
```

---

## Status Values

`active` · `done` · `pending` · `blocked` · `cancelled`

---

## Tips

- Load with `--autosc` to enable `find` and ID-based `edit`/`delete`/`show`
- After loading an old file without `--autosc`, run `rebuild` to enable ID lookups
- `exit` warns on unsaved changes; run it again to force-quit
- Ctrl+D also exits

---

*Last updated: March 2026*
