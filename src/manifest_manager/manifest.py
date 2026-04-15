#!/usr/bin/env python3
"""
Manifest Manager CLI v3.5
==========================

Interactive shell for hierarchical XML data management.
Supports plain XML and encrypted 7z archives.

Usage:
    python manifest.py
    
Commands:
    load, save, add, edit, list, find, wrap, merge, autoid, rebuild, cheatsheet, exit

Example Session:
    (manifest) load myproject --autosc
    (myproject.xml) add --tag task --topic "New feature"
    (myproject.xml) find a3f
    (myproject.xml) edit a3f --status done        # v3.4: ID prefix matching!
    (myproject.xml) rebuild                       # v3.4: Sync sidecar
    (myproject.xml) save backup.7z

Features:
    - XPath-based querying with CSS selector support
    - Fast ID lookups via sidecar index (O(1))
    - Smart edit: auto-detects ID vs XPath
    - ID prefix matching with interactive selection (v3.4)
    - In-memory sidecar rebuild command (v3.4)
    - Encrypted backups via 7z with password protection
    - Transaction support with automatic rollback on errors
    - Multiple view formats (tree, table)
    - Configuration files for customization
    - Merge multiple manifest files
    - Wrap top-level nodes under new containers

Security:
    - Password retry with maximum attempt limits
    - Path validation prevents injection attacks
    - XML validation prevents malformed documents
    - Unsaved changes warning on exit
"""

import sys
import cmd
import shlex
import argparse
import getpass
import os

# --- Imports ---
try:
    from .manifest_core import ManifestRepository, NodeSpec, ManifestView, Validator
    from .storage import PasswordRequired
except ImportError as e:
    print(f"Critical Error: Missing core modules. {e}")
    sys.exit(1)


# --- Helper Functions for v3.3 ---

def _is_id_selector(selector: str, repo) -> bool:
    """Detect if selector is an ID or XPath.
    
    Detection heuristics:
        1. Contains XPath syntax (/, [, @, *, =) → XPath
        2. Hex-like string (3-8 chars) → ID prefix
        3. Exists in sidecar → ID
        4. Default → XPath (safe fallback)
    
    Args:
        selector: User-provided selector string
        repo: Repository to check sidecar
        
    Returns:
        True if selector is likely an ID, False if XPath
        
    Examples:
        >>> _is_id_selector('a3f', repo)
        True  # Hex-like, 3 chars
        >>> _is_id_selector('a3f7b2c1', repo)
        True  # Hex-like, 8 chars
        >>> _is_id_selector('7d0d', repo)
        True  # Hex-like, 4 chars
        >>> _is_id_selector('//task[@status="active"]', repo)
        False  # Has XPath syntax
    """
    # XPath syntax indicators (check first - most definitive)
    if any(c in selector for c in ['/', '[', '@', '*', '=']):
        return False
    
    # Hex-like string (any length 3-8 chars) - likely an ID prefix
    if 3 <= len(selector) <= 8 and all(c in '0123456789abcdef' for c in selector.lower()):
        return True
    
    # Check sidecar (definitive proof)
    if repo and hasattr(repo, 'id_sidecar') and repo.id_sidecar:
        if repo.id_sidecar.exists(selector):
            return True
    
    # Default to XPath for safety (backward compatible)
    return False


# --- Backup Helper Functions ---

def generate_bkp_name(original_path: str) -> str:
    """Generate .bkp filename for backup.
    
    Args:
        original_path: Original file path
        
    Returns:
        Backup filename with .bkp before extension
        
    Examples:
        >>> generate_bkp_name("project.xml")
        'project.bkp.xml'
        >>> generate_bkp_name("data.7z")
        'data.bkp.7z'
        >>> generate_bkp_name("/home/user/tasks.xml")
        '/home/user/tasks.bkp.xml'
    """
    base, ext = os.path.splitext(original_path)
    return f"{base}.bkp{ext}"


def generate_timestamped_name(original_path: str) -> str:
    """Generate timestamped filename for backup.
    
    Args:
        original_path: Original file path
        
    Returns:
        Backup filename with timestamp before extension
        
    Examples:
        >>> generate_timestamped_name("project.xml")
        'project.20260127_143022.xml'
    """
    from datetime import datetime
    base, ext = os.path.splitext(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base}.{timestamp}{ext}"


def backup_sidecar(original_path: str, backup_path: str) -> bool:
    """Copy sidecar file for backup.
    
    Args:
        original_path: Original manifest path
        backup_path: Backup manifest path
        
    Returns:
        True if sidecar was copied, False if no sidecar exists
        
    Example:
        >>> backup_sidecar("project.xml", "project.bkp.xml")
        True  # Copied project.xml.ids to project.bkp.xml.ids
    """
    import shutil
    
    original_sidecar = f"{original_path}.ids"
    backup_sidecar_path = f"{backup_path}.ids"
    
    if os.path.exists(original_sidecar):
        try:
            shutil.copy2(original_sidecar, backup_sidecar_path)
            return True
        except Exception as e:
            logger.warning(f"Failed to backup sidecar: {e}")
            return False
    return False


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
      -a key=value      Custom attribute (repeatable)
      "body text"       Text content of node

  edit <id_or_xpath>    Modify or delete nodes (auto-detects ID vs XPath)
      --text "new"      Update text content
      --topic "new"     Update topic attribute
      --status <s>      Update status
      -a key=value      Add/update attribute
      --delete          Remove matching nodes
      --id              Force ID interpretation
      --xpath           Force XPath interpretation

SEARCHING & VIEWING
───────────────────
  find <prefix>         Find by ID prefix (fast sidecar lookup)
      --tree            Show full subtrees for matches
      --depth N         Limit tree depth

  list [xpath]          Display nodes (default: /* = all top-level)
      --style tree      Hierarchical view (default)
      --style table     Tabular view
      --depth N         Limit tree depth

  autoid                Add IDs to elements that lack them
      --overwrite       Replace ALL existing IDs

  rebuild               Rebuild ID sidecar from current XML (v3.4 NEW!)

  verbose               Toggle display of hidden attributes in list/find output
                        (topic, status, resp, last_modified hidden by default)
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

class ParserControl(Exception): pass

class SafeParser(argparse.ArgumentParser):
    """Prevents argparse from killing the shell on error."""
    def error(self, message):
        print(f"ArgError: {message}\n")
        self.print_help()
        raise ParserControl()
    def exit(self, status=0, message=None):
        if message: print(message)
        raise ParserControl()

class ManifestShell(cmd.Cmd):
    intro = "Manifest Manager v3.5. Type 'help' or 'cheatsheet' for commands."
    prompt = "(manifest) "

    def __init__(self):
        super().__init__()
        self.repo = ManifestRepository()
        self._confirm_exit = False
        self._verbose_attrs = False  # When True, all attributes shown in list/find output
        try:
            from .dataframe_commands import add_dataframe_commands
            add_dataframe_commands(self)
        except ImportError:
            pass  # DataFrame support optional

    def _exec(self, func):
        """Safe execution wrapper."""
        try: func()
        except ParserControl: pass
        except ValueError as e: print(f"Input Error: {e}")
        except Exception as e: print(f"System Error: {e}")

    def _get_pass(self, prompt="Password: "):
        try: return getpass.getpass(prompt)
        except KeyboardInterrupt: return None

    def _with_password_retry(self, operation, filepath, success_callback=None):
        """Execute operation with password retry loop.
        
        Args:
            operation: Callable(filepath, password) -> Result
            filepath: Path to pass to operation
            success_callback: Optional callable(result) on success
        
        Returns:
            Result object from operation, or None if cancelled
        """
        pwd = None
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            try:
                result = operation(filepath, pwd)
                print(result.message)
                if result.success:
                    if success_callback:
                        success_callback(result)
                    return result
                else:
                    # Operation failed for non-password reason
                    return result
            except PasswordRequired:
                attempts += 1
                if attempts >= max_attempts:
                    print(f"Maximum password attempts ({max_attempts}) exceeded.")
                    return None
                pwd = self._get_pass(f"Enter password for {filepath} (attempt {attempts}/{max_attempts}): ")
                if pwd is None:
                    return None

    @staticmethod
    def _parse_attrs(attr_list: list | None) -> dict:
        """Parse attribute list into dictionary.
        
        Args:
            attr_list: List like ['-a', 'k=v', '-a', 'k2=v2']
            
        Returns:
            Dict like {'k': 'v', 'k2': 'v2'}
            
        Note:
            - Items without '=' are silently ignored
            - Later values override earlier for same key
            - Uses split("=", 1) to allow '=' in values
        """
        if not attr_list:
            return {}
        
        attrs = {}
        for item in attr_list:
            if "=" not in item:
                continue  # Skip malformed items
            key, value = item.split("=", 1)
            attrs[key] = value
        
        return attrs

    # --- Commands ---

    def _load_shortcuts(self) -> set:
        """Load valid shortcuts from config file."""
        defaults = {'task', 'project', 'item', 'note', 'milestone', 'idea', 'location'}
        
        try:
            import yaml
            from pathlib import Path
            config_path = Path(__file__).parent.parent.parent / "config" / "shortcuts.yaml"
            
            if not config_path.exists():
                return defaults
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            shortcuts = set(config.get('shortcuts', []))
            reserved = set(config.get('reserved_keywords', []))
            return shortcuts - reserved
            
        except Exception:
            return defaults


    def do_load(self, arg):
        """Load manifest: load <file> [--auto-sidecar] [--rebuild-sidecar]
        
        Examples:
            load myfile.xml
            load myfile.xml --autosc          # Create sidecar if missing
            load myfile.xml --rebuildsc       # Force rebuild sidecar
        """
        p = SafeParser(prog="load")
        p.add_argument("filename")
        p.add_argument("--auto-sidecar", "--autosc", action="store_true",
                       help="Auto-create sidecar if missing")
        p.add_argument("--rebuild-sidecar", "--rebuildsc", action="store_true",
                       help="Force rebuild sidecar")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            def on_success(result):
                self.prompt = f"({os.path.basename(self.repo.filepath)}) "
            
            # Call load with sidecar flags
            def load_with_flags(filepath, password):
                return self.repo.load(
                    filepath,
                    password,
                    auto_sidecar=args.auto_sidecar,
                    rebuild_sidecar=args.rebuild_sidecar
                )
            
            self._with_password_retry(load_with_flags, args.filename, on_success)
        
        self._exec(_run)

    def do_save(self, arg):
        """Save file: save [filename]"""
        pwd = self.repo.password
        if arg and arg.endswith(".7z") and not pwd:
             pwd = self._get_pass(f"Set password for {arg}: ")
        print(self.repo.save(arg, pwd).message)

    def do_backup(self, arg):
        """Create a backup of the current manifest.
        
        Usage:
            backup [filename] [options]
        
        Arguments:
            filename            Optional custom backup filename
        
        Options:
            --force, -f        Overwrite existing backup without prompting
            --timestamp, -t    Use timestamp instead of .bkp
            --no-sidecar       Skip sidecar backup
        
        Examples:
            backup                          # Create filename.bkp.xml
            backup mybackup.xml             # Custom name
            backup --timestamp              # filename.20260127_143022.xml
            backup --force                  # Overwrite without asking
            backup --timestamp --no-sidecar # Timestamped, no sidecar
        """
        p = SafeParser(prog="backup", description="Create manifest backup")
        p.add_argument("filename", nargs="?", help="Custom backup filename")
        p.add_argument("--force", "-f", action="store_true",
                       help="Overwrite without prompting")
        p.add_argument("--timestamp", "-t", action="store_true",
                       help="Use timestamp instead of .bkp")
        p.add_argument("--no-sidecar", action="store_true",
                       help="Skip sidecar backup")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # 1. Validate preconditions
            if not self.repo.tree:
                print("Error: No file loaded. Use 'load <file>' first.")
                return
            
            if not self.repo.filepath:
                print("Error: No file path set.")
                return
            
            # 2. Generate backup filename
            if args.filename:
                backup_path = args.filename
                # Add .xml if no extension provided
                if "." not in os.path.basename(backup_path):
                    backup_path += ".xml"
            elif args.timestamp:
                backup_path = generate_timestamped_name(self.repo.filepath)
            else:
                backup_path = generate_bkp_name(self.repo.filepath)
            
            # 3. Check for overwrite
            if os.path.exists(backup_path) and not args.force:
                try:
                    response = input(f"File exists: {backup_path}\nOverwrite? [y/N]: ")
                    if response.strip().lower() not in ('y', 'yes'):
                        print("Cancelled.")
                        return
                except KeyboardInterrupt:
                    print("\nCancelled.")
                    return
            
            # 4. Show warning if unsaved changes
            if self.repo.modified:
                print("⚠ Warning: Backup includes unsaved changes")
            
            # 5. Save backup (current in-memory state)
            # Note: save() will change self.repo.filepath to backup_path
            original_filepath = self.repo.filepath
            original_password = self.repo.password

            try:
                result = self.repo.save(backup_path, self.repo.password)
                if not result.success:
                    print(f"Error: {result.message}")
                    return

                # Show success message
                if args.force and os.path.exists(backup_path):
                    print(f"✓ Backup saved to {backup_path} (overwritten)")
                else:
                    print(f"✓ Backup saved to {backup_path}")

                # 6. Backup sidecar if exists and not disabled
                if self.repo.id_sidecar and not args.no_sidecar:
                    if backup_sidecar(original_filepath, backup_path):
                        print(f"✓ Sidecar backed up to {backup_path}.ids")
            finally:
                # 7. Restore original filepath (save() changes it)
                # This ALWAYS runs, even if save() fails or we return early
                self.repo.filepath = original_filepath
                self.repo.password = original_password
            
            # Update prompt if needed
            if self.prompt.startswith("("):
                self.prompt = f"({os.path.basename(original_filepath)}) "
        
        self._exec(_run)

    def do_add(self, arg):
        """Add node: add task "Desc" (Shortcut) OR add --tag task "Desc" (Full)
        
        Shortcuts (v3.5+):
          add task "Title"      → add --tag task --topic "Title"
          add location "Place"  → add --tag location --topic "Place"
          (See config/shortcuts.yaml)
        
        Options:
          --parent <selector>  Parent location (XPath or ID shortcut, default: /*)
          --id <value>         Custom ID (default: auto-generated 8-char hex)
          --id False           Disable auto-ID generation
          --resp <n>           Responsible party (v3.4)
        
        Smart parent detection (v3.4.1):
          --parent "//project"         XPath (has /)
          --parent a3f                 ID prefix (hex-like, shows selection if multiple)
          --parent a3f7b2c1            Full ID (exact match)
        
        Examples:
          add --tag task --topic "New task"
          add --tag task --topic "Subtask" --parent a3f
          add --tag task --topic "In project" --parent "//project[@topic='Q1']"
        """
        p = SafeParser(prog="add", description="Add node")
        p.add_argument("--tag", required=True, help="Tag name")
        p.add_argument("--parent", default="/*", help="Parent XPath or ID")
        p.add_argument("--parent-xpath", dest="force_parent_xpath", action="store_true",
                       help="Force XPath interpretation of --parent")
        p.add_argument("--parent-id", dest="force_parent_id", action="store_true",
                       help="Force ID interpretation of --parent")
        p.add_argument("--topic", help="Topic/Title")
        p.add_argument("--status", help="Status")
        p.add_argument("--resp", help="Responsible party")
        p.add_argument("--due", help="Due date (YYYY-MM-DD format)")
        p.add_argument("--id", dest="node_id", help="ID (or 'False' to disable auto-ID)")
        p.add_argument("-a", "--attr", action="append", help="k=v attrs")
        p.add_argument("text", nargs="?", help="Body text")

        def _run():
            # --- Phase 3: Shortcut Expansion ---
            parts = shlex.split(arg)
            shortcuts = self._load_shortcuts()
            
            # Detect shortcut: <noun> "Title" [--flags]
            if parts and parts[0] in shortcuts and not parts[0].startswith('-'):
                # Expand: task "Title" -> --tag task --topic "Title"
                tag = parts[0]
                new_parts = ['--tag', tag]
                
                # If next item is not a flag, treat it as topic
                if len(parts) > 1 and not parts[1].startswith('-'):
                    new_parts.extend(['--topic', parts[1]])
                    new_parts.extend(parts[2:])  # Remaining flags
                else:
                    new_parts.extend(parts[1:])  # No topic, just flags
                
                args = p.parse_args(new_parts)
            else:
                # Standard full-syntax parsing
                args = p.parse_args(parts)
            # -----------------------------------
            attrs = self._parse_attrs(args.attr)
            
            # Resolve parent selector to XPath (supports ID shortcuts)
            parent_xpath, error = self._resolve_selector_to_xpath(
                args.parent,
                force_id=args.force_parent_id,
                force_xpath=args.force_parent_xpath
            )
            
            if error:
                print(f"Error: {error}")
                return
            
            # Handle --id parameter
            auto_id = True
            if args.node_id:
                if args.node_id.lower() in ('false', 'no', 'off', '0'):
                    auto_id = False  # Explicitly disable
                else:
                    attrs['id'] = args.node_id  # Custom ID
                    auto_id = False  # Don't auto-generate if custom provided
            
            # Resolve natural language --due (e.g. "tomorrow", "+3", "monday")
            if args.due:
                from shared.dates import parse_date as _parse_date
                args.due = _parse_date(args.due) or args.due

            # Use factory method (v3.4)
            spec = NodeSpec.from_args(args, attributes=attrs)
            result = self.repo.add_node(parent_xpath, spec, auto_id=auto_id)
            
            # Display ID if available (new in v3.6)
            if result.success and result.data and result.data.get('id'):
                node_id = result.data['id']
                print(f"✓ Added node with ID: {node_id}")
                
                # Show details if attributes were set
                if args.topic or args.status or args.resp or args.due:
                    if args.topic:
                        print(f"  topic: {args.topic}")
                    if args.status:
                        print(f"  status: {args.status}")
                    if args.resp:
                        print(f"  resp: {args.resp}")
                    if args.due:
                        print(f"  due: {args.due}")
            else:
                print(result.message)
        
        self._exec(_run)


    def do_wrap(self, arg):
        """
        Wrap all top-level items under a new root tag.
        Usage: wrap --root <new_tag_name>
        """
        p = SafeParser(prog="wrap", description="Reparent top items")
        p.add_argument("--root", default="root", help="New root tag name")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            print(self.repo.wrap_content(args.root).message)
        self._exec(_run)

    def do_merge(self, arg):
        """Merge external file: merge <filename>"""
        if not arg: return print("Usage: merge <filename>")
        self._with_password_retry(self.repo.merge_from, arg)

    def do_find(self, arg):
        """Find nodes by ID prefix: find <prefix> [--tree] [--depth N]
        
        Examples:
          find a3f              # Find IDs starting with 'a3f' (flat view)
          find a3f --tree       # Show full subtrees
          find a3f --tree --depth 2  # Limit depth
        """
        p = SafeParser(prog="find")
        p.add_argument("prefix", help="ID prefix to search")
        p.add_argument("--tree", action="store_true", help="Show tree view")
        p.add_argument("--depth", type=int, help="Limit tree depth")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # Use DRY helper for ID search
            matches = self._search_by_id_pattern(self.repo, args.prefix)
            
            if not matches:
                print(f"No IDs found matching '{args.prefix}'")
                return
            
            print(f"\nFound {len(matches)} match(es)")
            
            if args.tree:
                # Tree view - show full subtrees
                for i, elem in enumerate(matches, 1):
                    if i > 1:
                        print("\n" + "─" * 60)
                    print(f"Match {i}: {self._build_xpath(elem)}")
                    print("─" * 60)
                    print(ManifestView.render([elem], "tree", max_depth=args.depth,
                                              hide_attrs=not self._verbose_attrs))
            else:
                # Flat view - show IDs prominently (v3.3)
                for elem in matches:
                    # Build XPath
                    xpath = self._build_xpath(elem)
                    
                    # Display with ID first and prominent
                    elem_id = elem.get("id", "")
                    topic = elem.get("topic", "")
                    status = elem.get("status", "")
                    
                    print()  # Blank line before each result
                    if elem_id:
                        print(f"  ID: {elem_id}")  # ID first, easy to copy
                    print(f"     Path: {xpath}")
                    if topic:
                        print(f"     Topic: {topic}")
                    if status:
                        print(f"     Status: {status}")
        
        self._exec(_run)

    @staticmethod
    def _build_xpath(elem) -> str:
        """Build XPath for an element."""
        path_parts = []
        current = elem
        while current is not None and current.tag != "manifest":
            tag = current.tag
            elem_id = current.get("id", "")
            if elem_id:
                tag = f"{tag}[@id='{elem_id}']"
            path_parts.insert(0, tag)
            current = current.getparent()
        
        return "/" + "/".join(path_parts) if path_parts else f"/{elem.tag}"
    
    @staticmethod
    def _search_by_id_pattern(repo, pattern: str) -> list:
        """Search for IDs matching pattern (prefix match).
        
        DRY helper used by both find and edit commands.
        
        Args:
            repo: Repository instance
            pattern: ID prefix to match
            
        Returns:
            List of matching elements
            
        Examples:
            >>> _search_by_id_pattern(repo, 'a3f')
            [<Element task>, <Element note>]  # All IDs starting with 'a3f'
        """
        if not repo.id_sidecar:
            return []
        
        # Find all IDs matching the prefix
        matching_ids = [
            elem_id for elem_id in repo.id_sidecar.all_ids() 
            if elem_id.startswith(pattern)
        ]
        
        # Get elements for matching IDs
        elements = []
        for elem_id in matching_ids:
            xpath = repo.id_sidecar.get(elem_id)
            if xpath:
                try:
                    matches = repo.root.xpath(xpath)
                    if matches:
                        elements.append(matches[0])
                except:
                    pass  # Skip invalid XPaths
        
        return elements
    
    def _resolve_selector_to_xpath(self, selector: str, force_id: bool = False, force_xpath: bool = False) -> tuple:
        """Resolve selector (ID or XPath) to XPath expression.
        
        DRY helper for consistent ID/XPath handling across commands.
        Provides interactive selection for ID prefix matches.
        
        Args:
            selector: User-provided selector (ID prefix, full ID, or XPath)
            force_id: Force interpretation as ID
            force_xpath: Force interpretation as XPath
            
        Returns:
            Tuple of (xpath: str or None, error_message: str or None)
            - (xpath, None) on success
            - (None, error_msg) on failure/cancellation
            
        Examples:
            >>> xpath, err = self._resolve_selector_to_xpath("a3f")
            >>> if err:
            ...     print(err)
            ...     return
            >>> # Use xpath for operation
        """
        # Determine if selector is ID or XPath
        if force_id:
            is_id = True
        elif force_xpath:
            is_id = False
        else:
            is_id = _is_id_selector(selector, self.repo)
        
        # XPath mode - return as-is
        if not is_id:
            return (selector, None)
        
        # ID mode - resolve to XPath
        if not self.repo.id_sidecar:
            return (None, "ID sidecar not enabled. Load with --autosc to enable ID shortcuts.")
        
        # Try exact match first
        if self.repo.id_sidecar.exists(selector):
            xpath = self.repo.id_sidecar.get(selector)
            return (xpath, None)
        
        # Try prefix match
        matches = self._search_by_id_pattern(self.repo, selector)
        
        if len(matches) == 0:
            return (None, f"No IDs found matching '{selector}'\n"
                          f"Tip: Use 'find <prefix>' to search, or 'rebuild' to sync sidecar")
        
        if len(matches) == 1:
            # Single match - use automatically
            elem_id = matches[0].get('id')
            print(f"Matched ID: {elem_id}")
            xpath = self.repo.id_sidecar.get(elem_id)
            return (xpath, None)
        
        # Multiple matches - interactive selection
        print(f"\nMultiple IDs match '{selector}':")
        for i, elem in enumerate(matches, 1):
            elem_id = elem.get('id')
            topic = elem.get('topic', '(no topic)')
            status = elem.get('status', '')
            status_str = f" [{status}]" if status else ""
            print(f"  [{i}] {elem_id}{status_str} - {topic}")
        
        try:
            choice = input(f"\nSelect [1-{len(matches)}] or 'c' to cancel: ").strip()
            if choice.lower() == 'c':
                return (None, "Cancelled.")
            
            idx = int(choice) - 1
            if idx < 0 or idx >= len(matches):
                return (None, "Invalid selection.")
            
            elem_id = matches[idx].get('id')
            xpath = self.repo.id_sidecar.get(elem_id)
            return (xpath, None)
        except (ValueError, KeyboardInterrupt):
            return (None, "\nCancelled.")

    def do_autoid(self, arg):
        """Auto-generate IDs for elements that lack them.
        
        Usage: 
          autoid              # Add IDs to elements without them
          autoid --overwrite  # Replace ALL IDs with new ones
        
        Examples:
          autoid              # Safe: only adds missing IDs
          autoid --overwrite  # Caution: replaces existing IDs
        """
        p = SafeParser(prog="autoid", description="Add IDs to elements")
        p.add_argument("--overwrite", action="store_true", 
                      help="Replace existing IDs (default: skip elements with IDs)")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            result = self.repo.ensure_ids(overwrite=args.overwrite)
            print(result.message)
            if result.success and not args.overwrite:
                print("Tip: Use 'autoid --overwrite' to replace existing IDs")
        self._exec(_run)

    def do_rebuild(self, arg):
        """Rebuild ID sidecar from current XML (NEW in v3.4).
        
        Use this when:
          - IDs exist in XML but sidecar is missing/outdated
          - After loading old files without --autosc
          - "ID not found" errors for IDs that exist
        
        Usage:
          rebuild             # Rebuild sidecar from memory
        
        Examples:
          (manifest) load old_file.xml
          (old_file.xml) list
          # You see IDs in output
          (old_file.xml) edit a3f --delete
          # Error: ID not found
          (old_file.xml) rebuild
          # ✓ Rebuilt sidecar with 47 IDs
          (old_file.xml) edit a3f --delete
          # Success!
        """
        if not self.repo.tree:
            return print("Error: No file loaded.")
        
        if not self.repo.id_sidecar:
            print("Error: Sidecar not enabled.")
            print("Tip: Exit and reload with --autosc flag:")
            print(f"     load \"{self.repo.filepath}\" --autosc")
            return
        
        print("Rebuilding sidecar from current XML...")
        self.repo.id_sidecar.rebuild(self.repo.root)
        self.repo.id_sidecar.save()
        
        count = len(self.repo.id_sidecar.index)
        print(f"✓ Rebuilt sidecar with {count} ID(s)")
        
        if count == 0:
            print("Tip: Use 'autoid' to add IDs to elements")

    def do_list(self, arg):
        """View data: list [id_or_xpath] [--style tree|table] [--depth N]
        
        Smart detection:
            - 8-char hex (e.g., 'a3f7b2c1') → Exact ID match
            - Shorter hex (e.g., 'a3f') → ID prefix search (shows all matches)
            - XPath syntax (e.g., '//task') → XPath query
            - Use --xpath to force XPath, --id to force ID
        
        Examples:
            list                              # Show entire tree
            list a3f                          # Show subtree(s) for IDs matching 'a3f'
            list a3f7b2c1                     # Show subtree for exact ID
            list "//task"                     # Show all tasks (XPath)
            list "//task[@status='done']"     # XPath query
            list --id BUG-123                 # Force ID interpretation
        """
        p = SafeParser(prog="list")  # ← This line needs proper indentation!
        p.add_argument("selector", nargs="?", default="/*", 
                    help="Element ID/prefix or XPath (default: /*)")
        p.add_argument("--xpath", dest="force_xpath", action="store_true",
                    help="Force XPath interpretation")
        p.add_argument("--id", dest="force_id", action="store_true",
                    help="Force ID interpretation")
        p.add_argument("--style", default="tree", choices=["tree", "table"])
        p.add_argument("--depth", type=int, help="Limit tree depth")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # Determine if selector is ID or XPath
            if args.force_id:
                is_id = True
            elif args.force_xpath:
                is_id = False
            else:
                is_id = _is_id_selector(args.selector, self.repo)
            
            # Get elements to display
            if is_id:
                # ID mode - search by prefix
                matches = self._search_by_id_pattern(self.repo, args.selector)
                
                if not matches:
                    print(f"No IDs found matching '{args.selector}'")
                    if self.repo.id_sidecar:
                        print("Tip: Use 'find <prefix>' to search, or 'rebuild' to sync sidecar")
                    else:
                        print("Tip: Load with --autosc to enable ID search")
                    return
                
                if len(matches) > 1:
                    print(f"Found {len(matches)} matching IDs:\n")
                
                elements = matches
            else:
                # XPath mode
                elements = self.repo.search(args.selector)
                if not elements:
                    print(f"No elements found matching XPath: {args.selector}")
                    return
            
            # Display
            print(ManifestView.render(
                elements, 
                args.style, 
                max_depth=args.depth,
                hide_attrs=not self._verbose_attrs,
            ))
        
        self._exec(_run)

    def do_export_calendar(self, arg):
        """Export tasks with due dates to iCalendar (.ics) format.
        
        Usage:
            export-calendar <selector> <output.ics> [options]
        
        Arguments:
            selector        XPath query or ID/ID prefix to select elements
            output          Output .ics filename
        
        Options:
            --name NAME     Calendar name (default: "Manifest Tasks")
            --xpath         Force XPath interpretation
            --id            Force ID interpretation
        
        Selector can be:
            - XPath: "//task[@due]" or "//task[@due][@status='active']"
            - Full ID: a3f7b2c1 (exports single task)
            - ID prefix: a3f (exports matching tasks, interactive if multiple)
        
        Examples:
            export-calendar "//task[@due]" tasks.ics
            export-calendar a3f tasks.ics                    # Export task by ID prefix
            export-calendar a3f7b2c1 my-task.ics            # Export specific task
            export-calendar "//task[@due][@status='active']" active.ics
            export-calendar "//*[@due]" all-due.ics --name "All Tasks"
        
        Date format: Elements must have due="YYYY-MM-DD" attribute
        
        Exported events include:
            - Summary: topic attribute
            - Description: element text content
            - Status: mapped from status attribute
            - Categories: parent project name, element tag
        """
        p = SafeParser(prog="export-calendar", description="Export to iCalendar format")
        p.add_argument("selector", help="XPath query or ID/ID prefix")
        p.add_argument("output", help="Output .ics filename")
        p.add_argument("--name", default="Manifest Tasks", help="Calendar name")
        p.add_argument("--xpath", dest="force_xpath", action="store_true",
                       help="Force XPath interpretation")
        p.add_argument("--id", dest="force_id", action="store_true",
                       help="Force ID interpretation")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            if not self.repo.tree:
                print("Error: No file loaded.")
                return
            
            # Resolve selector to XPath (supports ID shortcuts)
            xpath, error = self._resolve_selector_to_xpath(
                args.selector,
                force_id=args.force_id,
                force_xpath=args.force_xpath
            )
            
            if error:
                print(f"Error: {error}")
                return
            
            # Execute XPath query
            try:
                elements = self.repo.root.xpath(xpath)
            except Exception as e:
                print(f"Error: Invalid XPath - {e}")
                return
            
            if not elements:
                print(f"No elements found matching: {args.selector}")
                return
            
            # Filter to only elements with due dates
            with_due = [e for e in elements if e.get("due")]
            
            if not with_due:
                print(f"Found {len(elements)} element(s), but none have 'due' attribute.")
                print("Hint: Add due dates like: due=\"2026-03-15\"")
                return
            
            # Export to ICS
            from .calendar import export_to_ics
            
            try:
                count = export_to_ics(with_due, args.output, args.name)
                print(f"✓ Exported {count} event(s) to {args.output}")
                print(f"  Calendar name: {args.name}")
                
                # Show which items were exported
                if count <= 5:
                    print(f"\nExported items:")
                    for elem in with_due:
                        topic = elem.get("topic", elem.tag)
                        due = elem.get("due")
                        elem_id = elem.get("id", "-")
                        print(f"  • {topic} (due: {due}, id: {elem_id[:8]})")
                
                print(f"\nTo import into Google Calendar:")
                print(f"  1. Open Google Calendar")
                print(f"  2. Click Settings (gear icon) → Import & Export")
                print(f"  3. Choose {args.output}")
                print(f"  4. Select destination calendar")
            except Exception as e:
                print(f"Error exporting calendar: {e}")
                import traceback
                traceback.print_exc()
        
        self._exec(_run)

    def do_edit(self, arg):
        """Edit/Delete: edit <id_or_xpath> [options]
        
        Smart detection:
            - 8-char hex (e.g., 'a3f7b2c1') → Exact ID match
            - Shorter hex (e.g., 'a3f') → ID prefix search (interactive if multiple)
            - XPath syntax (e.g., '//task') → XPath query
            - Use --xpath to force XPath, --id to force ID
        
        Examples:
            edit a3f7b2c1 --topic "Updated"           # By exact ID
            edit a3f --topic "Updated"                # By prefix (interactive if multiple)
            edit --id BUG-123 --topic "Fixed"         # By ID (explicit)
            edit "//task[@status='pending']" --status active  # By XPath
        """
        p = SafeParser(prog="edit")
        p.add_argument("selector", help="Element ID/prefix or XPath")
        p.add_argument("--xpath", dest="force_xpath", action="store_true",
                       help="Force XPath interpretation")
        p.add_argument("--id", dest="force_id", action="store_true",
                       help="Force ID interpretation")
        p.add_argument("--topic", help="New topic")
        p.add_argument("--status", help="New status")
        p.add_argument("--resp", help="Responsible party")
        p.add_argument("--due", help="Due date (YYYY-MM-DD format)")
        p.add_argument("--text", help="New body text")
        p.add_argument("-a", "--attr", action="append", help="k=v attributes")
        p.add_argument("--delete", action="store_true", help="Delete node")
        
        def _run():
            args = p.parse_args(shlex.split(arg))
            
            # Build NodeSpec using factory method (v3.4)
            attrs = self._parse_attrs(args.attr)
            spec = NodeSpec.from_args(args, tag="ignored", attributes=attrs)
            
            # Determine if selector is ID or XPath
            if args.force_id:
                is_id = True
            elif args.force_xpath:
                is_id = False
            else:
                is_id = _is_id_selector(args.selector, self.repo)
            
            # Execute edit
            if is_id:
                # ID mode - try exact match first, then prefix
                if self.repo.id_sidecar and self.repo.id_sidecar.exists(args.selector):
                    # Exact ID match
                    result = self.repo.edit_node_by_id(args.selector, spec, args.delete)
                    print(result.message)
                else:
                    # Try prefix match (NEW in v3.4)
                    matches = self._search_by_id_pattern(self.repo, args.selector)
                    
                    if len(matches) == 0:
                        print(f"Error: No IDs found matching '{args.selector}'")
                        if self.repo.id_sidecar:
                            print("Tip: Use 'find <prefix>' to search, or 'rebuild' to sync sidecar")
                        else:
                            print("Tip: Load with --autosc to enable ID search")
                    elif len(matches) == 1:
                        # Single match - use it automatically
                        elem_id = matches[0].get('id')
                        print(f"Matched ID: {elem_id}")
                        result = self.repo.edit_node_by_id(elem_id, spec, args.delete)
                        print(result.message)
                    else:
                        # Multiple matches - interactive selection (NEW in v3.4)
                        print(f"\nMultiple IDs match '{args.selector}':")
                        for i, elem in enumerate(matches, 1):
                            elem_id = elem.get('id')
                            topic = elem.get('topic', '(no topic)')
                            status = elem.get('status', '')
                            status_str = f" [{status}]" if status else ""
                            print(f"  [{i}] {elem_id}{status_str} - {topic}")
                        
                        try:
                            choice = input(f"\nSelect [1-{len(matches)}] or 'c' to cancel: ").strip()
                            if choice.lower() == 'c':
                                print("Cancelled.")
                                return
                            
                            idx = int(choice) - 1
                            if idx < 0 or idx >= len(matches):
                                print("Invalid selection.")
                                return
                            
                            elem_id = matches[idx].get('id')
                            result = self.repo.edit_node_by_id(elem_id, spec, args.delete)
                            print(result.message)
                        except (ValueError, KeyboardInterrupt):
                            print("\nCancelled.")
                            return
            else:
                # XPath mode
                result = self.repo.edit_node(args.selector, spec, args.delete)
                print(result.message)
        
        self._exec(_run)

    def do_move(self, arg):
        """Move a node (and its subtree) under a new parent.

        Usage:
            move <src> <dest>

        Arguments:
            src   ID, ID-prefix, or XPath of the node to move.
            dest  ID, ID-prefix, or XPath of the new parent.

        Both selectors must resolve to exactly one node.
        The entire subtree rooted at <src> moves with it.

        Examples:
            move a3f7 b1c2              # move by ID
            move a3f //archive          # ID src, XPath dest
            move "//task[@status='done']" //archive  # XPath → XPath (must be 1 match)
        """
        p = SafeParser(prog="move", description="Move a node under a new parent")
        p.add_argument("src",  help="Source node: ID, ID-prefix, or XPath")
        p.add_argument("dest", help="Destination parent: ID, ID-prefix, or XPath")

        def _run():
            args = p.parse_args(shlex.split(arg))
            result = self.repo.move_node(args.src, args.dest)
            print(result.message)

        self._exec(_run)
    
    def do_delete(self, arg):
        """Delete node(s): delete <id_or_xpath>

        Aliases: del, remove

        Deletes the matched node and all its descendants.
        Removes corresponding entries from sidecar if enabled.

        Smart detection (same as edit):
            - Hex-like string → ID prefix match
            - XPath syntax   → XPath query
            - --id / --xpath  to force interpretation

        Examples:
            delete a3f              # Delete by ID prefix
            delete a3f7b2c1         # Delete by exact ID
            delete "//task[@status='cancelled']"  # Delete by XPath
        """
        p = SafeParser(prog="delete", description="Delete node(s)")
        p.add_argument("selector", help="Element ID/prefix or XPath")
        p.add_argument("--xpath", dest="force_xpath", action="store_true",
                       help="Force XPath interpretation")
        p.add_argument("--id", dest="force_id", action="store_true",
                       help="Force ID interpretation")

        def _run():
            args = p.parse_args(shlex.split(arg))

            # Re-use edit's ID/XPath resolution
            if args.force_id:
                is_id = True
            elif args.force_xpath:
                is_id = False
            else:
                is_id = _is_id_selector(args.selector, self.repo)

            if is_id:
                # Exact match first
                if self.repo.id_sidecar and self.repo.id_sidecar.exists(args.selector):
                    result = self.repo.edit_node_by_id(args.selector, None, delete=True)
                    print(result.message)
                else:
                    matches = self._search_by_id_pattern(self.repo, args.selector)
                    if not matches:
                        print(f"Error: No IDs found matching '{args.selector}'")
                        if self.repo.id_sidecar:
                            print("Tip: Use 'find <prefix>' to search, or 'rebuild' to sync sidecar")
                        else:
                            print("Tip: Load with --autosc to enable ID search")
                        return
                    if len(matches) == 1:
                        elem_id = matches[0].get("id")
                        print(f"Matched ID: {elem_id}")
                        result = self.repo.edit_node_by_id(elem_id, None, delete=True)
                        print(result.message)
                    else:
                        print(f"\nMultiple IDs match '{args.selector}':")
                        for i, elem in enumerate(matches, 1):
                            elem_id = elem.get("id")
                            topic = elem.get("topic", "(no topic)")
                            status = elem.get("status", "")
                            status_str = f" [{status}]" if status else ""
                            print(f"  [{i}] {elem_id}{status_str} - {topic}")
                        try:
                            choice = input(f"\nSelect [1-{len(matches)}] or 'c' to cancel: ").strip()
                            if choice.lower() == "c":
                                print("Cancelled.")
                                return
                            idx = int(choice) - 1
                            if idx < 0 or idx >= len(matches):
                                print("Invalid selection.")
                                return
                            elem_id = matches[idx].get("id")
                            result = self.repo.edit_node_by_id(elem_id, None, delete=True)
                            print(result.message)
                        except (ValueError, KeyboardInterrupt):
                            print("\nCancelled.")
            else:
                result = self.repo.edit_node(args.selector, None, delete=True)
                print(result.message)

        self._exec(_run)

    # Aliases
    def do_del(self, arg):
        """Alias for delete."""
        return self.do_delete(arg)

    def do_remove(self, arg):
        """Alias for delete."""
        return self.do_delete(arg)

    def do_show(self, arg):
        """Show a single node in detail: show <id_or_xpath>

        Displays full attributes and text of the matched node,
        plus a tree view of its children.

        Examples:
            show a3f              # Show node matching ID prefix
            show a3f7b2c1         # Show node by exact ID
            show "//project[1]"   # Show first project
        """
        p = SafeParser(prog="show", description="Show node details")
        p.add_argument("selector", help="Element ID/prefix or XPath")
        p.add_argument("--xpath", dest="force_xpath", action="store_true")
        p.add_argument("--id", dest="force_id", action="store_true")

        def _run():
            args = p.parse_args(shlex.split(arg))

            xpath, error = self._resolve_selector_to_xpath(
                args.selector,
                force_id=args.force_id,
                force_xpath=args.force_xpath,
            )
            if error:
                print(f"Error: {error}")
                return

            elements = self.repo.search(xpath)
            if not elements:
                print(f"No elements found matching: {args.selector}")
                return

            elem = elements[0]
            print()
            print(f"  Tag:    {elem.tag}")
            for attr, val in elem.attrib.items():
                print(f"  {attr+':':<10} {val}")
            if elem.text and elem.text.strip():
                print(f"  text:      {elem.text.strip()}")
            if len(elem):
                print(f"\n  Children ({len(elem)}):")
                print(ManifestView.render([elem], "tree", max_depth=2))

        self._exec(_run)

    def do_restore(self, arg):
        """Restore manifest from a backup file: restore <backup_file>

        Loads the backup file into memory and marks the session as modified.
        Use 'save' (with your original filename) to persist the restoration.

        Examples:
            restore project.bkp.xml
            restore project.20260127_143022.xml
        """
        p = SafeParser(prog="restore", description="Restore from backup")
        p.add_argument("filename", help="Backup file to restore from")

        def _run():
            args = p.parse_args(shlex.split(arg))

            original_filepath = self.repo.filepath

            def do_load(filepath, password):
                return self.repo.load(filepath, password)

            result = self._with_password_retry(do_load, args.filename)
            if result and result.success:
                self.prompt = f"({os.path.basename(self.repo.filepath)}) "
                print(f"✓ Restored from {args.filename}")
                if original_filepath:
                    print(f"Tip: Use 'save {original_filepath}' to write back to original file.")

        self._exec(_run)

    def do_export_scheduler(self, arg):
        """Export manifest nodes to Smart Scheduler as tasks.

        Usage:
            export-scheduler [xpath] --project <slug> [--name <n>] [--engine json|sqlite]

        Arguments:
            xpath        XPath or ID selector for nodes to export.
                         Defaults to config/integration.yaml export_scheduler.default_xpath,
                         or "//task[@due]" if that is also empty.

        Options:
            --project    Scheduler project slug (required).
                         Created automatically if it does not exist.
            --name       Display name for the project (used only when creating).
                         Defaults to the slug if omitted.
            --engine     Storage engine: json (default) or sqlite.

        Status conversion is driven by config/integration.yaml.
        Until you configure status_mapping.to_scheduler, all exported
        tasks will have status 'todo'.

        Examples:
            export-scheduler --project q1-work
            export-scheduler "//task[@due][@status='active']" --project q1-work
            export-scheduler a3f7 --project q1-work
        """
        p = SafeParser(prog="export-scheduler",
                       description="Export manifest nodes to Smart Scheduler")
        p.add_argument("selector", nargs="?", default="",
                       help="XPath or ID prefix (default: from integration.yaml)")
        p.add_argument("--project", required=True,
                       help="Scheduler project slug")
        p.add_argument("--name", default="",
                       help="Project display name (only used when creating)")
        p.add_argument("--engine", default="json", choices=["json", "sqlite"],
                       help="Storage engine (default: json)")

        def _run():
            args = p.parse_args(shlex.split(arg))

            if not self.repo.tree:
                print("Error: No manifest loaded. Use 'load <file>' first.")
                return

            from shared.integration_config import (
                load_integration_config, get_scheduler_data_dir,
            )
            cfg = load_integration_config()
            export_cfg = cfg.get("export_scheduler", {})

            selector = args.selector.strip()
            if not selector:
                selector = export_cfg.get("default_xpath", "") or "//task[@due]"

            xpath, error = self._resolve_selector_to_xpath(selector)
            if error:
                print(f"Error: {error}")
                return

            nodes = self.repo.search(xpath)
            if not nodes:
                print(f"No nodes matched: {selector}")
                return
            print(f"Found {len(nodes)} node(s) matching '{selector}'.")

            data_dir = get_scheduler_data_dir()
            if data_dir is None:
                print(
                    "Error: Scheduler data directory not configured.\n"
                    "Set paths.scheduler_data_dir in config/integration.yaml\n"
                    "or set the SCHEDULER_DATA_DIR environment variable."
                )
                return

            from shared.manifest_bridge import build_tasks, push_tasks_to_scheduler

            tasks, skip_reasons = build_tasks(nodes)
            result = push_tasks_to_scheduler(
                tasks=tasks,
                project_slug=args.project,
                project_name=args.name or args.project,
                data_dir=data_dir,
                storage_engine=args.engine,
            )
            result.skipped = len(skip_reasons)
            result.skipped_reasons = skip_reasons
            print(result)

        self._exec(_run)

    def do_verbose(self, _):
        """Toggle display of hidden attributes (topic, status, resp, last_modified).

        By default these attributes are suppressed in list/find output since
        they appear in the formatted line already. Turn verbose on to see the
        raw attribute values, e.g. when auditing last_modified dates.

        Examples:
            verbose        # toggle on  → "Verbose attrs: ON"
            verbose        # toggle off → "Verbose attrs: OFF"
        """
        self._verbose_attrs = not self._verbose_attrs
        state = "ON" if self._verbose_attrs else "OFF"
        print(f"Verbose attrs: {state}")

    def do_cheatsheet(self, _):
        """Display comprehensive command reference."""
        print(CHEATSHEET)
    
    def do_exit(self, _):
        if self.repo.modified and not self._confirm_exit:
            print("Unsaved changes! Type 'save' or 'exit' again.")
            self._confirm_exit = True
            return False
        return True
    def do_EOF(self, _): return self.do_exit(_)


def main():
    """Entry point for pip-installed command."""
    try:
        ManifestShell().cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()