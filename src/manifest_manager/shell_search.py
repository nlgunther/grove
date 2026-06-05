"""
shell_search.py — Search and display commands for ManifestShell.

Commands: list, find, grep, search, show, verbose.
"""

import shlex
import os

from .shell_base import SafeParser, ParserControl, ManifestView, _is_id_selector


class SearchCommands:
    """Mixin providing search and display do_* methods."""

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
                    print(ManifestView.render([elem], "tree", max_depth=args.depth))
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


    def do_search(self, arg):
        """Full-text search: search <term> [--regexp] [--scope <xpath>] [--expand]

        Substring search (default) or regexp search (--regexp) across every
        attribute and text node in the loaded manifest.  Reports which fields
        matched so you can follow up with a precise XPath query.

        Examples:
            search vermont
            search "Green Mountain" --expand
            search "(?i)vermont" --regexp
            search task --scope //travel --expand
        """
        p = SafeParser(prog="search")
        p.add_argument("term", help="Substring or regexp pattern to find")
        p.add_argument("--regexp", action="store_true",
                       help="Treat term as a regular expression")
        p.add_argument("--scope", help="XPath to restrict search to a subtree")
        p.add_argument("--expand", action="store_true",
                       help="Show matched node's children in output")

        def _run():
            import re as _re
            args = p.parse_args(shlex.split(arg))

            if not self.repo.tree:
                print("No manifest loaded.")
                return

            try:
                results = self.repo.full_text_search(
                    args.term,
                    scope_xpath=args.scope,
                    use_regexp=args.regexp,
                )
            except _re.error as e:
                print(f"Invalid regexp: {e}")
                return

            if not results:
                print(f'No matches for "{args.term}".')
                return

            max_depth = None if args.expand else 1

            for i, r in enumerate(results):
                if i > 0:
                    print()
                breadcrumb = r["breadcrumb"] or "(top level)"
                print(f'[score={r["score"]}] {breadcrumb}')
                tag_str = f"  Tag: {r['tag']}"
                if r["elem_id"]:
                    tag_str += f"  ID: {r['elem_id']}"
                print(tag_str)
                print(f"  Matched in: {', '.join(r['matched_fields'])}")
                rendered = ManifestView.render([r["elem"]], max_depth=max_depth)
                if rendered and rendered.strip() != "No data.":
                    print(rendered)

        self._exec(_run)


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
                max_depth=args.depth
            ))
        
        self._exec(_run)


    def do_grep(self, arg):
        """Search the manifest for a term across tag names, attributes, and text.

        Runs three passes in order and reports matches at each stage:
            1. Tag names   — elements whose tag equals the term
            2. Attributes  — elements with any attribute value containing the term
            3. Text        — elements whose text content contains the term

        Usage:
            grep <term>
            grep <term> --ignore-case

        Examples:
            grep tax
            grep "New York"
            grep todo --ignore-case
        """
        p = SafeParser(prog="grep")
        p.add_argument("term", help="Search term")
        p.add_argument("--ignore-case", "-i", action="store_true",
                       help="Case-insensitive search")

        def _run():
            args = p.parse_args(shlex.split(arg))

            if not self.repo.tree:
                print("Error: No file loaded.")
                return

            term = args.term
            # For case-insensitive XPath we lower-case both sides via translate().
            _UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            _LOWER = "abcdefghijklmnopqrstuvwxyz"

            def ci(xpath_expr: str) -> str:
                """Wrap an XPath string expression in translate() for case-insensitive match."""
                return f"translate({xpath_expr},'{_UPPER}','{_LOWER}')"

            if args.ignore_case:
                t = term.lower()
                tag_xpath   = f"//*[translate(local-name(),'{_UPPER}','{_LOWER}')='{t}']"
                attr_xpath  = f"//*[@*[contains({ci('.')},'{t}')]]"
                text_xpath  = f"//*[contains({ci('text()')},'{t}')]"
            else:
                tag_xpath   = f"//*[local-name()='{term}']"
                attr_xpath  = f"//*[@*[contains(.,'{term}')]]"
                text_xpath  = f"//*[contains(text(),'{term}')]"

            sections = [
                ("Tag names",  tag_xpath),
                ("Attributes", attr_xpath),
                ("Text",       text_xpath),
            ]

            any_found = False
            for label, xpath in sections:
                matches = self.repo.search(xpath)
                print(f"\n── {label} ({'1 match' if len(matches)==1 else f'{len(matches)} matches'}) ──")
                if matches:
                    any_found = True
                    print(ManifestView.render(
                        matches, "tree",
                        hide_attrs=not self._verbose_attrs,
                    ))
                else:
                    print("  (none)")

            if not any_found:
                print(f"\nNo matches for '{term}'.")

        self._exec(_run)


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


    def do_verbose(self, _):
        """Toggle verbose attribute display in list/find/grep output.

        When ON, attributes normally suppressed (topic, status, resp,
        last_modified) appear in their raw XML form.  Useful for auditing
        timestamps and exact attribute values.

        Session-only: resets to OFF on next shell start.

        Usage:
            verbose        # → "Verbose attrs: ON"
            verbose        # → "Verbose attrs: OFF"
        """
        self._verbose_attrs = not self._verbose_attrs
        state = "ON" if self._verbose_attrs else "OFF"
        print(f"Verbose attrs: {state}")
