"""
shell_base.py — Shared infrastructure for ManifestShell mixins.

Contains SafeParser, ParserControl, module-level helper functions, and the
ShellBase mixin class which provides the protected methods (_exec, _parse_attrs,
_resolve_selector_to_xpath, etc.) that every command mixin relies on via self.
"""

import sys
import cmd
import shlex
import argparse
import getpass
import os
import shutil
import yaml

# --- Package imports ---
try:
    from .manifest_core import ManifestRepository, NodeSpec, ManifestView, Validator
    from .storage import PasswordRequired
    from .config import Config
except ImportError as e:
    print(f"Critical Error: Missing core modules. {e}")
    sys.exit(1)


# --- Parser helpers ---

class ParserControl(Exception): pass

class SafeParser(argparse.ArgumentParser):
    """Prevents argparse from killing the shell on error."""
    def error(self, message):
        print(f"ArgError: {{message}}\n")
        self.print_help()
        raise ParserControl()
    def exit(self, status=0, message=None):
        if message: print(message)
        raise ParserControl()


# --- Module-level helpers ---

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


# --- ShellBase mixin ---

class ShellBase:
    """Shared protected methods for all ManifestShell command mixins.

    Not instantiated directly.  ManifestShell inherits from ShellBase along
    with the command mixins so every do_* method has access to these helpers
    via self.
    """

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
        """Parse the repeated -a/--attr flags into an XML attribute dict.

        argparse collects each `-a key=value` into a list; this method
        turns that list into a dict suitable for passing to NodeSpec.

        Args:
            attr_list: Values collected by argparse `action="append"`, e.g.
                       ["colour=blue", "size=large"].  None when the flag
                       was not supplied at all.

        Returns:
            Dict mapping attribute names to values, e.g.
            {"colour": "blue", "size": "large"}.

        Behaviour worth noting:
        - `=` in the value is fine: `expr=a=b` → {"expr": "a=b"}.
          split("=", 1) ensures only the first `=` is the delimiter.
        - Duplicate keys: last value wins — `colour=red -a colour=blue`
          yields {"colour": "blue"}.  This lets callers override earlier
          flags without an error.
        - No `=` in the item: silently skipped.  argparse never produces
          this from well-formed `-a key=value` input, but guards against
          programmatic misuse.

        Example:
            _parse_attrs(["colour=blue", "size=large"])
            # → {"colour": "blue", "size": "large"}

            _parse_attrs(["expr=a=b+c"])
            # → {"expr": "a=b+c"}
        """
        if not attr_list:
            return {}

        attrs = {}
        for item in attr_list:
            if "=" not in item:
                continue  # guard: well-formed input always has '='
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

