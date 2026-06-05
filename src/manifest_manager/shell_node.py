"""
shell_node.py — Node manipulation commands for ManifestShell.

Commands: add, edit, delete (del, remove), move, wrap, autoid, rebuild.
"""

import shlex
import os

from .shell_base import SafeParser, ParserControl, NodeSpec, _is_id_selector


class NodeCommands:
    """Mixin providing node-manipulation do_* methods."""

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
          --location <s>       Location string; shorthand for -a location=<s>
        
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
        p.add_argument("-l", "--location", help="Location string (shorthand for -a location=<value>)")
        # -a/--attr sets arbitrary XML attributes not covered by the named flags
        # above.  Repeatable: each -a key=value adds one attribute.
        # See _parse_attrs for full semantics (= in values, duplicate handling).
        p.add_argument("-a", "--attr", action="append", help="key=value — repeatable; sets arbitrary XML attributes")
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
            
            # Use factory method (v3.4)
            spec = NodeSpec.from_args(args, attributes=attrs)
            result = self.repo.add_node(parent_xpath, spec, auto_id=auto_id)
            
            # Display ID if available (new in v3.6)
            if result.success and result.data and result.data.get('id'):
                node_id = result.data['id']
                print(f"✓ Added node with ID: {node_id}")
                
                # Show details if attributes were set
                if args.topic or args.status or args.resp or args.due or args.location:
                    if args.topic:
                        print(f"  topic: {args.topic}")
                    if args.status:
                        print(f"  status: {args.status}")
                    if args.resp:
                        print(f"  resp: {args.resp}")
                    if args.due:
                        print(f"  due: {args.due}")
                    if args.location:
                        print(f"  location: {args.location}")
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
        # -a/--attr adds or updates arbitrary XML attributes (not just the named
        # ones above).  Repeatable.  To remove an attribute, set it to an empty
        # string: -a key=   (XML has no null; empty string is the convention).
        p.add_argument("-a", "--attr", action="append", help="key=value — repeatable; adds/updates arbitrary XML attributes")
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

