"""
cli.py — Smart Scheduler CLI entry point (v2.1 split).

Provides the CLI REPL class and main().  All command implementations live
in the four submodules listed below; this file is intentionally thin so
the dispatch table and startup logic are easy to audit at a glance.

Module layout:
    cli.py              — CLI class, _COMMANDS dispatch, main()
    cli_tasks.py        — list, show, cleanup, new, add, edit, delete, search
    cli_data.py         — import-json, export, export-json, import-manifest
    cli_maintenance.py  — config, backup, restore, maintenance
    cli_help.py         — help
"""

import shlex

from .config import get_config
from .storage.factory import get_storage_engine
from .services.task_service import TaskService
from .services.maintenance_service import MaintenanceService
from .services.calendar_service import CalendarService

from .cli_tasks import (
    cmd_list, cmd_show, cmd_cleanup,
    cmd_new, cmd_add, cmd_edit, cmd_delete, cmd_search,
)
from .cli_data import (
    cmd_import_json, cmd_export, cmd_export_json, cmd_import_manifest,
)
from .cli_maintenance import cmd_config, cmd_backup, cmd_restore, cmd_maintenance
from .cli_help import cmd_help


class CLI:
    def __init__(self):
        self.cfg          = get_config()
        self.storage      = get_storage_engine(
            self.cfg.data_dir,
            self.cfg.preferences.get("storage_engine", "json"),
        )
        self.task_service  = TaskService(self.storage)
        self.maint_service = MaintenanceService(self.storage)
        self.cal_service   = CalendarService()
        self._needs_restart = False  # set True after restore so user must restart

    def run(self):
        print(f"\n\U0001f4cb Smart Scheduler 2.0 ({self.cfg.preferences.get('storage_engine', 'json')})")
        print(f"Data: {self.cfg.data_dir}")
        print("Type 'help' for commands, 'quit' or Ctrl+Z to exit.\n")
        print("Status Icons: \u25cb = todo, \u25b6 = in progress, \u23f3 = waiting, \u2713 = done, \u2717 = cancelled")

        while True:
            try:
                cmd = input("\n> ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("quit", "exit"):
                    break

                if self._needs_restart and cmd.lower() not in ("quit", "exit"):
                    print("\n\u26a0\ufe0f  ERROR: You must restart the scheduler after restore!")
                    print("Type 'quit' to exit, then restart the scheduler.")
                    continue

                self._execute(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _execute(self, cmd_str):
        parts = shlex.split(cmd_str)
        if not parts:
            return
        handler = _COMMANDS.get(parts[0].lower())
        if handler:
            handler(self, parts[1:])
        else:
            print(f"Unknown command: {parts[0]}")

    def _opts(self, args):
        """Parse arguments into (positional_list, options_dict).

        Flags without a following value are stored as True.  The first
        non-flag token after a flag is consumed as that flag's value.

        Example:
            _opts(["add", "task", "--due", "friday", "--all"])
            # → (["add", "task"], {"due": "friday", "all": True})
        """
        pos, opts = [], {}
        i = 0
        while i < len(args):
            if args[i].startswith("-"):
                k = args[i].lstrip("-")
                v = True
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    v = args[i + 1]
                    i += 1
                opts[k] = v
            else:
                pos.append(args[i])
            i += 1
        return pos, opts


_COMMANDS = {
    "list":             cmd_list,
    "show":             cmd_show,
    "new":              cmd_new,
    "add":              cmd_add,
    "edit":             cmd_edit,
    "delete":           cmd_delete,
    "cleanup":          cmd_cleanup,
    "backup":           cmd_backup,
    "restore":          cmd_restore,
    "maintenance":      cmd_maintenance,
    "export":           cmd_export,
    "export-json":      cmd_export_json,
    "import-json":      cmd_import_json,
    "import-manifest":  cmd_import_manifest,
    "search":           cmd_search,
    "config":           cmd_config,
    "help":             cmd_help,
}


def main():
    """Entry point for pip-installed 'scheduler' command."""
    CLI().run()
