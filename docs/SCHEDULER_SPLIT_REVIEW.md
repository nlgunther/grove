# smart_scheduler/cli.py Split — HIL Review

**Date:** 2026-06-05  
**Scope:** `src/smart_scheduler/cli.py` split from 1 file (1 883 lines) into 5 files (1 966 lines total, largest 713 lines)  
**Status:** ✅ Complete — 211 scheduler tests + 453 total tests passing, 0 failures

---

## Why This Was Done

`cli.py` had grown to 1 883 lines. The same Edit-tool truncation risk that affected `manifest.py` applies here. The file was also harder to navigate: `cmd_help` alone was 268 lines, and four `_import_*` helpers occupied another ~300 lines in the middle of the file, obscuring the main commands.

---

## Architecture Difference vs manifest_manager

`ManifestShell` used Python mixins (multiple inheritance via `cmd.Cmd`). That pattern doesn't apply here because `CLI` is **not** a `cmd.Cmd` subclass — it uses a hand-rolled REPL with a `_COMMANDS` dispatch dict. The split is therefore a straightforward **module extraction**: `cmd_*` functions and their private helpers move to domain modules; `cli.py` becomes a thin file that imports them all and builds the dispatch table.

No inheritance, no MRO. Adding a new command means: add the function to the appropriate domain module, import it in `cli.py`, add one line to `_COMMANDS`.

---

## What Moved Where

| File | Lines | Contents |
|------|-------|----------|
| `cli.py` | 132 | `CLI` class, `_COMMANDS` dict, `main()` |
| `cli_tasks.py` | 644 | `cmd_list`, `_print_task_detail`, `cmd_show`, `cmd_cleanup`, `cmd_new`, `cmd_add`, `cmd_edit`, `cmd_delete`, `cmd_search` |
| `cli_data.py` | 713 | `cmd_import_json`, `_import_task/contact/project/full_database`, `cmd_export`, `cmd_export_json`, `cmd_import_manifest` |
| `cli_maintenance.py` | 200 | `cmd_config`, `cmd_backup`, `cmd_restore`, `cmd_maintenance` |
| `cli_help.py` | 277 | `cmd_help` |

---

## Decisions Made

**1. Module grouping rationale**

- `cli_tasks.py` — everything a user does to tasks day-to-day: create, read, update, delete, search.
- `cli_data.py` — bulk moves: importing from JSON/manifest exports, exporting. These all deal with files and external schemas; they share the four `_import_*` helper functions.
- `cli_maintenance.py` — infrastructure commands that users run rarely: config, backup, restore, maintenance.
- `cli_help.py` — separated purely because `cmd_help` is 268 lines and would dominate any module it shared.

**2. `_print_task_detail` and `_is_upcoming` ownership**

Both helpers are only called from within `cmd_list`/`cmd_show`. They go in `cli_tasks.py`. `_is_upcoming` is defined as an inner function inside `cmd_list` in the original — it stays there.

**3. `_import_*` helpers stay in `cli_data.py`**

All four (`_import_task`, `_import_contact`, `_import_project`, `_import_full_database`) are only called from `cmd_import_json`. They stay co-located in `cli_data.py` rather than going into a separate `cli_import_helpers.py` — splitting them would add a file without reducing complexity.

**4. Deferred imports left in place**

The original file has many imports inside function bodies (lines 101, 656, 742, 1055, 1088–1091, 1225, 1748, 1754, 1770). These are correct as deferred imports — heavy dependencies (lxml, manifest_bridge, json, shutil) that should not load at startup. All were left exactly as-is.

**5. `_COMMANDS` dict stays in `cli.py`**

It maps string command names to functions from all four modules. Keeping it in `cli.py` makes the full command surface visible in one place — the same reason the thin `manifest.py` is the right place to read when you want to know what the shell can do.

**6. `CLI._opts()` docstring improved**

The `_opts` helper had no docstring. A brief example-based docstring was added per the code-quality standard.

---

## Size Flags

Two files exceed the 600-line target:

| File | Lines | Reason | Action |
|------|-------|--------|--------|
| `cli_data.py` | 713 | `cmd_export_json` is 230L alone; four `_import_*` helpers add ~300L | Monitor; further split only if `cmd_export_json` is refactored |
| `cli_tasks.py` | 644 | `cmd_list` (162L) + `cmd_search` (97L) + six other commands | Monitor; no natural split point without thin files |

Both are under the 800-line extraction-required threshold.

---

## What Was Not Changed

- All command logic is identical to the pre-split code
- All test files are unchanged — no mock targets moved
- `services/`, `storage/`, `models.py` are untouched
- `shared/manifest_bridge.py` reference from `cmd_import_manifest` is unchanged

---

## Risks and What to Verify

| Risk | Likelihood | How to verify |
|------|-----------|---------------|
| A command was dropped from `_COMMANDS` | Low | `python -c "from smart_scheduler.cli import _COMMANDS; print(sorted(_COMMANDS))"` — should list 17 commands |
| Deferred import now fails due to wrong context | Low | Run `scheduler import-json <file>` with a real export file |
| `cli_data.py` uses `TaskStatus` without importing it | Low | The `_import_*` functions use local `from scheduler.models import TaskStatus` — covered |

---

## Smoke Test to Run After Pulling

```bash
pytest tests/smart_scheduler/ tests/integration/ -q
# Expected: 211 passed

pytest tests/ -q --ignore=tests/test_encryption.py
# Expected: 453 passed, 5 skipped
```

---

## Files Added

```
src/smart_scheduler/cli_tasks.py
src/smart_scheduler/cli_data.py
src/smart_scheduler/cli_maintenance.py
src/smart_scheduler/cli_help.py
```

## Files Modified

```
src/smart_scheduler/cli.py   (rewritten as thin entry point)
```

## Files Unchanged

All test files, all service/storage/model files, all shared infrastructure.
