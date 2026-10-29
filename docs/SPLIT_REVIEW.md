# manifest.py Module Split — HIL Review

**Date:** 2026-06-05  
**Scope:** `src/manifest_manager/manifest.py` split from 1 file (~1 700 lines) into 6 files (~1 860 lines total, largest 435 lines)  
**Status:** ✅ Complete — 453 tests passing, 0 failures

---

## Why This Was Done

`manifest.py` had grown to 1 719 lines, more than double the project's 800-line flag threshold. The `Edit` tool was silently truncating the file on large writes, causing repeated corruption and repair cycles. Splitting into focused modules eliminates that risk and makes each file independently reviewable.

---

## What Moved Where

| File | Lines | Contents |
|------|-------|----------|
| `manifest.py` | 317 | Thin entry point: imports, `CHEATSHEET` string, `ManifestShell` class declaration, `main()` |
| `shell_base.py` | 423 | `SafeParser`, `ParserControl`, module-level helpers, `ShellBase` mixin (shared protected methods) |
| `shell_file.py` | 218 | `FileCommands` mixin: `load`, `save`, `backup`, `restore`, `merge` |
| `shell_node.py` | 435 | `NodeCommands` mixin: `add`, `edit`, `delete`/`del`/`remove`, `move`, `wrap`, `autoid`, `rebuild` |
| `shell_search.py` | 341 | `SearchCommands` mixin: `list`, `find`, `grep`, `search`, `show`, `verbose` |
| `shell_export.py` | 126 | `ExportCommands` mixin: `export-calendar` |

### ManifestShell MRO

```python
class ManifestShell(FileCommands, NodeCommands, SearchCommands, ExportCommands,
                    ShellBase, cmd.Cmd):
```

Resolution order: `FileCommands → NodeCommands → SearchCommands → ExportCommands → ShellBase → cmd.Cmd`. Each mixin is a plain class (no base); only `ManifestShell` inherits from `cmd.Cmd`, avoiding MRO conflicts.

---

## Decisions Made

**1. Re-exports in manifest.py**  
`manifest.py` re-imports everything from `shell_base.py` into its own namespace:
```python
from .shell_base import (ManifestRepository, NodeSpec, Config, ...)
```
This keeps all existing `patch("manifest_manager.manifest.X")` targets in tests valid. Zero test changes were required.

**2. `__init__` stays in manifest.py**  
`ManifestShell.__init__` is tiny (8 lines) and instantiates `ManifestRepository()` using the name from `manifest.py`'s namespace — exactly where tests patch it. Moving it to a mixin would break those patches without any benefit.

**3. `default()`, `do_exit()`, `do_EOF()`, `do_cheatsheet()` stay in manifest.py**  
These are shell-level lifecycle methods, not domain commands. They belong alongside `__init__` in the entry-point file.

**4. `@staticmethod` methods kept as static**  
`_build_xpath` and `_search_by_id_pattern` were already decorated `@staticmethod` in the original. They live in `ShellBase` and are called via `self._build_xpath(...)` / `self._search_by_id_pattern(...)` which Python resolves correctly through MRO.

**5. `do_verbose` implemented (was missing)**  
The original code initialised `self._verbose_attrs = False` with a comment "toggled by 'verbose' command", but `do_verbose` was never defined. It has been added to `SearchCommands` in `shell_search.py`.

**6. `import yaml` added to shell_base.py**  
`_load_shortcuts` calls `yaml.safe_load`. The original file imported yaml indirectly through another module; the explicit import makes the dependency clear.

---

## What Was Not Changed

- All command logic is identical to the pre-split code — no rewrites, only moves
- All test files are unchanged — patch targets continue to work
- `dataframe_commands.py` is still loaded dynamically in `__init__` (unchanged)
- `HIL_todo.md` entry for `do_export_scheduler` remains open

---

## Risks and What to Verify

| Risk | Likelihood | How to verify |
|------|-----------|---------------|
| A command was accidentally dropped | Low | `python -c "from manifest_manager.manifest import ManifestShell; print([m for m in dir(ManifestShell()) if m.startswith('do_')])"` — should list 27 commands |
| Circular import between shell_*.py files | Low | All shell_*.py import only from shell_base.py; none import from each other |
| Windows path issues in new test files | None | Already handled in test_hyphenated_commands.py (all paths quoted) |
| `do_verbose` behaviour differs from docs | Low | docs/API.md describes it as a session toggle; implementation matches |
| `export-scheduler` still not implemented | Confirmed | See `HIL_todo.md` — noted for future work |

---

## Smoke Test to Run After Pulling

```bash
pytest tests/ -q --ignore=tests/test_encryption.py
# Expected: 453 passed, 5 skipped
```

For a live sanity check:
```
manifest
(manifest) load test.xml
(manifest) add task "Smoke test"
(manifest) verbose
(manifest) list
(manifest) exit
```

---

## Files Added

```
src/manifest_manager/shell_base.py
src/manifest_manager/shell_file.py
src/manifest_manager/shell_node.py
src/manifest_manager/shell_search.py
src/manifest_manager/shell_export.py
```

## Files Modified

```
src/manifest_manager/manifest.py   (rewritten as thin entry point)
```

## Files Unchanged

All test files, all other source files, all documentation.
