"""
shell_export.py — Export commands for ManifestShell.

Commands: export-calendar (dispatched as export_calendar).
export-scheduler is documented but not yet implemented; see HIL_todo.md.
"""

import shlex
import os

from .shell_base import SafeParser, ParserControl


class ExportCommands:
    """Mixin providing export do_* methods."""

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

