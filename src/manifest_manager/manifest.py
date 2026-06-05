#!/usr/bin/env python3
"""
Manifest Manager CLI v3.5
==========================

Interactive shell for hierarchical XML data management.
Supports plain XML and encrypted 7z archives.

Usage:
    python manifest.py

Commands:
    load, save, add, edit, delete, move, list, find, grep, search, show,
    wrap, merge, autoid, rebuild, export-calendar, verbose, cheatsheet, exit

Example Session:
    (manifest) load myproject --autosc
    (myproject.xml) add task "New feature"
    (myproject.xml) find a3f
    (myproject.xml) edit a3f --status done
    (myproject.xml) export-calendar "//task[@due]" tasks.ics
    (myproject.xml) save backup.7z

Module layout (v3.6 split):
    manifest.py      — thin entry point (this file)
    shell_base.py    — SafeParser, ShellBase helpers
    shell_file.py    — FileCommands  (load, save, backup, restore, merge)
    shell_node.py    — NodeCommands  (add, edit, delete, move, wrap, autoid, rebuild)
    shell_search.py  — SearchCommands (list, find, grep, search, show, verbose)
    shell_export.py  — ExportCommands (export-calendar)
"""

import sys
import cmd

# --- Imports (re-exported here so existing patch targets remain valid) ---
try:
    from .shell_base import (
        ShellBase, SafeParser, ParserControl,
        ManifestRepository, NodeSpec, ManifestView, Validator,
        PasswordRequired, Config,
    )
    from .shell_file import FileCommands
    from .shell_node import NodeCommands
    from .shell_search import SearchCommands
    from .shell_export import ExportCommands
except ImportError as e:
    print(f"Critical Error: Missing shell modules. {e}")
    sys.exit(1)


# =============================================================================
# COMPREHENSIVE CHEATSHEET
# =============================================================================

CHEATSHEET = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                      MANIFEST MANAGER v3.5 CHEATSHEET                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

FILE OPERATIONS
───────────────
  load <file>           Load XML or 7z file (auto-creates if missing)
  load <file> --autosc  Load and auto-create ID sidecar if missing
  save [file]           Save to current or new file
  merge <file>          Import all nodes from another manifest

NODE OPERATIONS
───────────────
  add --tag <n>      Create new node
      --parent <xpath>  Where to add (default: /* = root's children)
      --topic "text"    Set topic attribute  
      --status <s>      Set status: active|done|pending|blocked|cancelled
      --id <value>      Custom ID (or 'False' to disable auto-ID)
      --location <s>    Location string (shorthand for -a location=<s>)
      -a key=value      Custom attribute (repeatable; '=' allowed in value)
      "body text"       Text content of node

  edit <id_or_xpath>    Modify or delete nodes (auto-detects ID vs XPath)
      --text "new"      Update text content
      --topic "new"     Update topic attribute
      --status <s>      Update status
      -a key=value      Add/update attribute (-a key= to remove)
      --delete          Remove matching nodes
      --id              Force ID interpretation
      --xpath           Force XPath interpretation

SEARCHING & VIEWING
───────────────────
  search <term>         Full-tree substring search across all attributes and text.
      --regexp          Treat <term> as a regular expression (use (?i) for case-insensitive)
      --scope <xpath>   Restrict walk to a subtree (e.g. --scope //travel)
      --expand          Show matched node's children in output
                        Reports matched fields so you can follow up with XPath.

  find <prefix>         Find by ID prefix (fast sidecar lookup)
      --tree            Show full subtrees for matches
      --depth N         Limit tree depth

  grep <term>           Search tag names, attributes, and text (three passes)
      --ignore-case     Case-insensitive search

  list [xpath]          Display nodes (default: /* = all top-level)
      --style tree      Hierarchical view (default)
      --style table     Tabular view
      --depth N         Limit tree depth

  autoid                Add IDs to elements that lack them
      --overwrite       Replace ALL existing IDs

  rebuild               Rebuild ID sidecar from current XML (v3.4 NEW!)
                        Use when IDs exist but sidecar is out of sync

STRUCTURE
─────────
  wrap --root <tag>     Wrap all top-level nodes under new container

XPATH QUICK REFERENCE
─────────────────────
  /*                    All direct children of root
  /manifest/*           Same as above (explicit root)
  //task                All <task> elements anywhere
  //task[@status]       Tasks that have a status attribute
  //task[@status='done'] Tasks with status="done"  
  //*[@topic]           Any element with topic attribute
  //project/task        Tasks directly inside projects
  //task[1]             First task element
  //task[last()]        Last task element
  //task[contains(@topic,'bug')]  Tasks with 'bug' in topic

v3.3 NEW FEATURES
─────────────────
  ID Sidecar:
    - Fast O(1) ID lookups
    - Auto-syncs on save
    - Created with --autosc flag

  Smart Edit:
    - edit a3f7b2c1 --topic "New"     # By ID (auto-detected)
    - edit //task --status active      # By XPath (auto-detected)
    - edit --id BUG-123 --topic "Fix"  # Custom ID (explicit)

  Prominent IDs:
    - find command shows IDs first
    - Easy copy/paste workflow

  Configuration:
    - Per-file: myfile.xml.config
    - Global: ~/.config/manifest/config.yaml

v3.4 NEW FEATURES
─────────────────
  ID Prefix Matching in Edit:
    - edit a3f --delete               # Matches all IDs starting with 'a3f'
    - Interactive selection if multiple matches
    - Single match: applies automatically

  Rebuild Command:
    - rebuild                         # Sync sidecar with current XML
    - Fixes "ID not found" errors
    - No need to exit and reload

  DRY Architecture:
    - find and edit share same ID search logic
    - Consistent behavior across commands

STATUS VALUES
─────────────
  active                In progress
  done                  Completed  
  pending               Not yet started
  blocked               Waiting on dependency
  cancelled             Abandoned

COMMON WORKFLOWS
────────────────
  Quick Task Management with IDs (v3.4):
    1. load tasks.xml --autosc
    2. add --tag task --status active "Today's work"
    3. find a3f                        # Find by prefix
    4. edit a3f --status done          # Edit by prefix (auto-selects if unique)
    5. save
  
  Fix "ID not found" errors (v3.4):
    1. load old_file.xml               # File has IDs but no sidecar
    2. list                            # See IDs in output
    3. edit a3f --delete               # Error: ID not found
    4. rebuild                         # Sync sidecar with XML
    5. edit a3f --delete               # Success!
  
  Weekly Archive:
    1. load weekly.xml
    2. edit "//task[@status='done']" --topic "Week-01"
    3. wrap --root "archive_2026_w01"
    4. save archive_2026_w01.7z
  
  Merge Team Updates:
    1. load main.xml
    2. merge alice.xml
    3. merge bob.xml
    4. list //task --style table
    5. save team_combined.xml

EXAMPLES
────────
  # Start new project with sidecar
  load myproject --autosc
  add --tag project --topic "Q1 Planning"
  add --tag task --parent "//project" --status active "Define roadmap"
  save

  # Edit by ID prefix (v3.4)
  find def                             # Find IDs starting with 'def'
  edit def --status done               # Auto-selects if unique, prompts if multiple

  # Edit by exact ID
  edit def456ab --status done

  # Edit by XPath (still works!)
  edit "//task[contains(text(),'roadmap')]" --status done

  # Create encrypted backup
  save archive.7z

  # Reorganize: wrap loose items
  load old_tasks.xml
  wrap --root archive
  save

  # Fix sidecar issues (v3.4)
  load myfile.xml                      # Old file with IDs but no sidecar
  rebuild                              # Sync sidecar
  edit a3f --delete                    # Now works!

TIPS
────
  • NEW v3.4: Use 'rebuild' command to fix "ID not found" errors
  • NEW v3.4: Edit by ID prefix - no need to type full ID!
  • IDs shown first in find results for easy copy/paste
  • Use ID prefixes: 'edit a3f' instead of 'edit a3f7b2c1'
  • Multiple matches? Edit will prompt you to select
  • XPath is case-sensitive: //Task ≠ //task
  • Use quotes around text with spaces: --topic "My Topic"
  • Tab completion works for commands
  • Ctrl+D or 'exit' to quit (warns if unsaved changes)
  • Maximum 3 password attempts for encrypted files
  • Tags cannot start with 'xml' (any case) - XML specification
  • Config files: see DOCUMENTATION_v3.4.md for full guide
"""


# =============================================================================
# Shell
# =============================================================================

class ManifestShell(FileCommands, NodeCommands, SearchCommands, ExportCommands,
                    ShellBase, cmd.Cmd):
    """Interactive shell for hierarchical XML data management.

    Inherits command methods from five mixins:
        FileCommands    — load, save, backup, restore, merge
        NodeCommands    — add, edit, delete, move, wrap, autoid, rebuild
        SearchCommands  — list, find, grep, search, show, verbose
        ExportCommands  — export-calendar
        ShellBase       — shared helpers (_exec, _parse_attrs, etc.)
    """

    intro  = "Manifest Manager v3.5. Type 'help' or 'cheatsheet' for commands."
    prompt = "(manifest) "

    def __init__(self):
        super().__init__()
        self.repo             = ManifestRepository()
        self._confirm_exit    = False
        self._verbose_attrs   = False  # toggled by 'verbose' command
        try:
            from .dataframe_commands import add_dataframe_commands
            add_dataframe_commands(self)
        except ImportError:
            pass  # DataFrame support is optional

    # --- Shell-level commands (not delegated to a mixin) ---

    def default(self, line):
        # cmd.Cmd dispatches via do_<word>, so hyphens in command names
        # (export-calendar, export-scheduler) never resolve — Python method
        # names can't contain hyphens.  Translate and retry before giving up.
        first, _, rest = line.partition(' ')
        if '-' in first:
            return self.onecmd(first.replace('-', '_') + (' ' + rest if rest else ''))
        print(f'*** Unknown syntax: {line}')

    def do_cheatsheet(self, _):
        """Display comprehensive command reference."""
        print(CHEATSHEET)

    def do_exit(self, _):
        if self.repo.modified and not self._confirm_exit:
            print("Unsaved changes! Type 'save' or 'exit' again.")
            self._confirm_exit = True
            return False
        return True

    def do_EOF(self, _):
        return self.do_exit(_)


def main():
    """Entry point for pip-installed command."""
    try:
        ManifestShell().cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
