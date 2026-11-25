# KT — Grove

> Last updated: 2026-11-24T19:15:00-08:00 | Trigger: manual | Staleness: Fresh

---

## 1. Project Overview
Grove is a Python CLI productivity suite (package `grove`, v2.0.0) that bundles three tools over shared infrastructure: **Manifest Manager** (hierarchical XML knowledge base, XPath queries, interactive shell; v3.5.0), **Smart Scheduler** (flat task manager with natural-language dates, status workflow, JSON/SQLite storage), and **text2ics** (free text to Google-Calendar-ready `.ics`; heuristic extractor by default, optional Claude-backed extractor). Manifest and Scheduler are integrated through `shared/manifest_bridge.py`.
Current status: Active Development

## 2. Goals & Constraints
**Goals:**
- Single installable package exposing `manifest`/`mnft`, `scheduler`/`schd`, and `text2ics` commands.
- Manifest and Scheduler interoperate (export from manifest to scheduler and ICS calendar, shared IDs and status mapping).
- Every documented feature is implemented and tested (428 test functions under `tests/`).

**Constraints:**
- Python >= 3.10 (`pyproject.toml`; `docs/README.md` still says 3.8+).
- Runtime deps: `lxml`, `py7zr`, `pyyaml`; `tzdata` on Windows; `anthropic` only via the optional `text2ics` extra.
- Environment managed with uv (`uv.lock`); source under `src/`, tests under `tests/` with `pythonpath = ["src"]`.
- Behavior driven by `config/integration.yaml` and `config/shortcuts.yaml`.

**Non-goals:** *(inferred)* no GUI or web front end; no multi-user server.

## 3. Prototypes & Examples
Prototypes in untracked `dev/`: `fts_index_prototype.py`, `synthesize_prototype.py`, `xml_to_relational_prototype.py`, plus sample data (`basic_manifest.txt`, `locations.odt`, a journal sqlite index). Canonical usage lives in `docs/CHEATSHEET.md` and `docs/README.md`. `docs/SEARCH_DECISIONS.md` and the `search` implementation brief record the search design.

## 4. Architecture & Key Files
```
src/
  manifest_manager/   # XML tree KB, v3.5.0
    manifest.py       # shell entry; assembled from mixin modules (split in v3.6 refactor)
    manifest_core.py  # core tree/XPath operations
    shell_base.py / shell_file.py / shell_node.py / shell_export.py / shell_search.py   # shell command mixins
    storage.py, config.py, id_sidecar.py, calendar.py, verify_package.py
    dataframe_commands.py, dataframe_conversion.py
  smart_scheduler/    # flat task manager
    cli.py + cli_tasks / cli_data / cli_maintenance / cli_help   # CLI split into domain modules (v2.1)
    models.py, config.py
    services/         # task_service, calendar_service, maintenance_service
    storage/          # base, factory, json_store, sqlite_store
  shared/             # dates, id_generator, locking, status_map, integration_config,
                      # manifest_bridge (manifest -> scheduler), calendar/ics_writer
  text_to_ics/        # cli, adapter, extractor, heuristic_extractor, llm_extractor, models
tests/                # flat manifest tests + smart_scheduler/, shared/, text_to_ics/, integration/
docs/                 # README, API, CHEATSHEET, TEST_GUIDE, SPLIT_REVIEW, SCHEDULER_SPLIT_REVIEW, SEARCH_DECISIONS
config/               # integration.yaml (incl. named_files autoload), shortcuts.yaml
```
Non-obvious: Manifest autoloads a file by path from a user config (`AppData\Roaming\manifest\config.yaml`); `shared/status_map.py` converts manifest status to scheduler `TaskStatus` (unmapped defaults to TODO). Documented counterpart `docs/ARCHITECTURE.html` exists on disk but is untracked/ignored.

## 5. Recent Decisions & Rationale
- Recent: text2ics accepts YYYYMMDD dates and 24-hour times (c22bc06); heuristic extractor added as default backend, Claude extractor optional (5a10f3d, 39782da).
- Added `--style email` flag affecting two manifest modules (a4177c4).
- Split `smart_scheduler/cli.py` into domain modules (v2.1) and `manifest.py` into shell mixins (v3.6) to keep modules reviewable (5509412, 86d4261).
- Added `location` as a preferred attribute and tied docs to implemented features (7eb8a92).
- Search capability added with tests; design in `docs/SEARCH_DECISIONS.md` (18325f5).
- Added `named_files` in `integration.yaml` so `load basic` works without typing filenames (77a387c).
- Short names for manifest/scheduler; `list --upcoming` (739d727).

## 6. Open Questions & Blockers
1. `export-scheduler` is documented in CHEATSHEET.md and referenced in `shared/manifest_bridge.py`, but `do_export_scheduler` does not exist in `src/` (checked by grep). Tracked in `HIL_todo.md`. Added 2026-06-05; still open as of 2026-11-24.
2. Version labels disagree: `pyproject.toml` 2.0.0, Manifest `__version__` 3.5.0, commit messages say v3.6; `docs/README.md` says Manifest v3.5 and Python 3.8+ vs `requires-python >=3.10`. Needs a decision on which is authoritative.
3. `MANIFEST.txt` last modified 2026-09-17, before many later commits; likely stale hashes. Regenerate before next delivery.
4. Working-tree clutter in repo root (see Next Steps).

## 7. Next Steps
1. Implement `do_export_scheduler` in the manifest shell (delegate to `shared/manifest_bridge.py`), add tests, then move the HIL item to Resolved.
2. Reconcile version numbers and Python requirement across `pyproject.toml`, `__init__.py`, and docs.
3. Clean the repo root: zero-byte files `git` and `main`, stray `.ics`/`date2026_06_03_*.txt` files, `schedule_*.bkp/zip`, `pytest-cache-files-*`; decide what to commit or add to `.gitignore`. Two tracked docs (`GIT_AMEND_AND_SQUASH.md`, `VIM_CHEATSHEET.md`) are deleted in the working tree.
4. Regenerate `MANIFEST.txt`.
5. Decide whether `dev/` and `misc_docs/` should be tracked.

## 8. Last Updated
2026-11-24T19:15:00-08:00 | manual | Fresh | Initial KT.md created from file scan, git log (20 commits), and HIL_todo.md; no prior KT existed. No conversation context beyond the \ukt command, so the file scan carried most of the weight. Docstrings were not read, so module purposes are inferred from file names and commit messages.
