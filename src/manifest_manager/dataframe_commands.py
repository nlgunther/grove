"""
dataframe_commands.py
=====================
CLI commands for DataFrame conversion, injected into ManifestShell at startup.

Adds three commands to the shell:
    to_df    Convert loaded manifest (or XPath subset) to DataFrame / CSV
    find_df  XPath search → DataFrame / CSV
    from_df  Import CSV back into manifest

Usage (in manifest.py __init__):
    try:
        from .dataframe_commands import add_dataframe_commands
        add_dataframe_commands(self)
    except ImportError:
        pass
"""

import shlex


def add_dataframe_commands(shell_instance):
    """Inject do_to_df, do_find_df, do_from_df into a ManifestShell instance."""
    shell_instance.do_to_df = lambda arg, _s=shell_instance: _do_to_df(_s, arg)
    shell_instance.do_find_df = lambda arg, _s=shell_instance: _do_find_df(_s, arg)
    shell_instance.do_from_df = lambda arg, _s=shell_instance: _do_from_df(_s, arg)

    # Help strings picked up by cmd.Cmd
    shell_instance.do_to_df.__doc__ = (
        "Export manifest to DataFrame/CSV: to_df [xpath] [--save FILE] [--no-text]\n\n"
        "  xpath       Optional XPath to export a subtree (default: entire manifest)\n"
        "  --save FILE Write CSV to FILE instead of printing preview\n"
        "  --no-text   Omit text column (faster for metadata-only exports)\n\n"
        "Examples:\n"
        "  to_df\n"
        "  to_df --save tasks.csv\n"
        "  to_df \"//task[@status='active']\" --save active.csv\n"
        "  to_df --no-text --save meta.csv"
    )
    shell_instance.do_find_df.__doc__ = (
        "XPath search → DataFrame/CSV: find_df <xpath> [--save FILE]\n\n"
        "  xpath       XPath expression to select nodes\n"
        "  --save FILE Write CSV to FILE instead of printing preview\n\n"
        "Examples:\n"
        "  find_df \"//task[@status='active']\"\n"
        "  find_df \"//task[@due]\" --save due_tasks.csv"
    )
    shell_instance.do_from_df.__doc__ = (
        "Import CSV into manifest: from_df <file> [--parent XPATH] [--dry-run]\n\n"
        "  file          CSV file previously exported by to_df or find_df\n"
        "  --parent      XPath of parent node to attach imported nodes\n"
        "                (default: replace entire manifest content)\n"
        "  --dry-run     Preview what would be imported without changing anything\n\n"
        "Examples:\n"
        "  from_df tasks.csv\n"
        "  from_df active.csv --parent \"//project[@id='p1']\"\n"
        "  from_df updated.csv --dry-run"
    )


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def _do_to_df(shell, arg):
    """Implementation of to_df command."""
    from .manifest_core import ManifestView  # noqa: F401 (used indirectly)

    try:
        from .dataframe_conversion import to_dataframe, find_to_dataframe
        import pandas as pd
    except ImportError as e:
        print(f"DataFrame support unavailable: {e}")
        print("Install with: pip install pandas")
        return

    p = _make_parser("to_df")
    p.add_argument("xpath", nargs="?", default=None,
                   help="XPath to select a subtree (default: entire manifest)")
    p.add_argument("--save", metavar="FILE", help="Write CSV to file")
    p.add_argument("--no-text", dest="no_text", action="store_true",
                   help="Omit text column")

    def _run():
        if not shell.repo.tree:
            print("Error: No file loaded.")
            return
        args = p.parse_args(shlex.split(arg))
        include_text = not args.no_text

        if args.xpath:
            df = find_to_dataframe(shell.repo.tree, args.xpath,
                                   include_text=include_text)
            source_desc = f"XPath '{args.xpath}'"
        else:
            df = to_dataframe(shell.repo.root, include_text=include_text)
            source_desc = "entire manifest"

        if df.empty:
            print(f"No nodes found in {source_desc}.")
            return

        if args.save:
            df.to_csv(args.save, index=False)
            print(f"✓ Exported {len(df)} rows from {source_desc} to {args.save}")
        else:
            print(f"DataFrame: {len(df)} rows from {source_desc}\n")
            with pd.option_context("display.max_columns", None,
                                   "display.width", None):
                print(df.to_string(index=False))

    shell._exec(_run)


def _do_find_df(shell, arg):
    """Implementation of find_df command."""
    try:
        from .dataframe_conversion import find_to_dataframe
        import pandas as pd
    except ImportError as e:
        print(f"DataFrame support unavailable: {e}")
        print("Install with: pip install pandas")
        return

    p = _make_parser("find_df")
    p.add_argument("xpath", help="XPath expression")
    p.add_argument("--save", metavar="FILE", help="Write CSV to file")

    def _run():
        if not shell.repo.tree:
            print("Error: No file loaded.")
            return
        args = p.parse_args(shlex.split(arg))
        df = find_to_dataframe(shell.repo.tree, args.xpath)

        if df.empty:
            print(f"No nodes matched: {args.xpath}")
            return

        if args.save:
            df.to_csv(args.save, index=False)
            print(f"✓ {len(df)} rows saved to {args.save}")
        else:
            print(f"Found {len(df)} nodes\n")
            with pd.option_context("display.max_columns", None,
                                   "display.width", None):
                print(df.to_string(index=False))

    shell._exec(_run)


def _do_from_df(shell, arg):
    """Implementation of from_df command."""
    try:
        from .dataframe_conversion import from_dataframe
        import pandas as pd
    except ImportError as e:
        print(f"DataFrame support unavailable: {e}")
        print("Install with: pip install pandas")
        return

    p = _make_parser("from_df")
    p.add_argument("file", help="CSV file to import")
    p.add_argument("--parent", default=None,
                   help="XPath of parent node (default: replace manifest root children)")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview without modifying")

    def _run():
        if not shell.repo.tree:
            print("Error: No file loaded.")
            return
        args = p.parse_args(shlex.split(arg))

        try:
            df = pd.read_csv(args.file)
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}")
            return
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return

        if df.empty:
            print("CSV is empty — nothing to import.")
            return

        missing = [c for c in ("id", "parent_id", "tag") if c not in df.columns]
        if missing:
            print(f"Error: CSV is missing required columns: {missing}")
            print("Expected columns: id, parent_id, tag (produced by to_df / find_df)")
            return

        new_root = from_dataframe(df)
        child_count = len(list(new_root))

        if args.dry_run:
            print(f"Dry run — would import {len(df)} rows ({child_count} top-level nodes)")
            print(f"Source: {args.file}")
            if args.parent:
                print(f"Target parent: {args.parent}")
            else:
                print("Would replace manifest root children.")
            return

        if args.parent:
            parents = shell.repo.root.xpath(args.parent)
            if not parents:
                print(f"Error: Parent XPath matched nothing: {args.parent}")
                return
            target = parents[0]
            for child in list(new_root):
                target.append(child)
            print(f"✓ Imported {child_count} nodes under {args.parent}")
        else:
            # Replace root children
            for child in list(shell.repo.root):
                shell.repo.root.remove(child)
            for child in list(new_root):
                shell.repo.root.append(child)
            print(f"✓ Replaced manifest content with {child_count} top-level nodes "
                  f"({len(df)} total rows)")

        shell.repo.modified = True
        print("Tip: Use 'save' to persist changes.")

    shell._exec(_run)


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _make_parser(prog):
    """Return a SafeParser-compatible parser without importing from manifest."""
    import argparse

    class _SafeParser(argparse.ArgumentParser):
        def error(self, message):
            print(f"ArgError: {message}\n")
            self.print_help()
            from manifest_manager.manifest import ParserControl
            raise ParserControl()

        def exit(self, status=0, message=None):
            if message:
                print(message)
            from manifest_manager.manifest import ParserControl
            raise ParserControl()

    return _SafeParser(prog=prog)
