"""
cli_help.py — Help command for the Smart Scheduler CLI.

Contains cmd_help, which renders the comprehensive reference for all
commands.  Kept in its own module because at 268 lines it is large
enough to affect readability of any file it shares.
"""


def cmd_help(cli, args):
    """Show comprehensive help documentation."""
    if not args:
        print(f"""
{'='*70}
SMART SCHEDULER 2.0 - COMPREHENSIVE COMMAND REFERENCE
{'='*70}

STATUS ICONS:
  ○ = todo         Task is pending/not started
  ▶ = in_progress  Task is actively being worked on
  ⏳ = waiting      Task is blocked/waiting for something
  ✓ = done         Task is completed
  ✗ = cancelled    Task was cancelled/abandoned

LISTING & VIEWING:
  list                      Quick project summary
  list --all                Show all projects with tasks (hides completed)
  list --all --show-done    Show everything including completed tasks
  list projects             Same as 'list'
  list tasks                List all tasks across all projects
  list tasks <project>      List tasks in specific project
  
  show <id>                 Show full details of task/contact/project

CREATING:
  new project <slug> <name> [--desc <text>]
                            Create a new project
  
  add task <project> <title> [--due <date>] [--note <text>] [--tags <t1,t2>]
                            Add a task to a project
  
  add contact <project> <name> [--role <role>] [--email <email>]
                            Add a contact to a project

EDITING:
  edit <task_id> [--title <title>] [--due <date>] [--note <text>] 
                 [--status <status>] [--tags <tag1,tag2>]
                            Edit a task (no project needed!)
  
  edit <project> [--name <name>] [--desc <description>]
                            Edit a project

DELETING:
  delete <task_id>          Delete a task (with confirmation)
  delete <project>          Delete a project and all its tasks
  
  cleanup                   Show completed tasks (dry run)
  cleanup --done            Delete all tasks with status='done'
  cleanup --cancelled       Delete all tasks with status='cancelled'  
  cleanup --execute         Actually perform the deletion

EXPORTING:
  export <id> ics           Export task to calendar format
  
  export-json <task_id>     Export task to JSON file
  export-json <project>     Export project to JSON file
  export-json --all         Export entire database to JSON
  export-json --all --output <file>
                            Export to specific filename

IMPORTING:
  import-json <file>        Import from JSON file (auto-detect type)
  import-json <file> --to <project>
                            Import task/contact to specific project
  import-json <file> --merge
                            Merge with existing (don't replace)
  import-json <file> --dry-run
                            Preview without importing

MAINTENANCE:
  backup [--name <n>]       Create a backup (read-only by default)
  backup --writable         Create a writable backup
  restore <path>            Restore from backup
  maintenance --optimize    Optimize database
  config                    Show configuration
  config location <path>    Move data directory
  config reset              Reset to default configuration

SEARCHING:
  search <term>             Full-text search across all tasks and fields
  search <term> --all       Include done/cancelled tasks
  search <term> --field notes|title|tags|outcome|assignee
                            Restrict to one field
  search <term> --project <slug>
                            Restrict to one project
  search <term> --regexp    Treat term as a regexp (case-insensitive)

UTILITY:
  export <id> <format>      Export to ICS/JSON/CSV
  help [command]            Show this help or command-specific help
  quit                      Exit scheduler

{'='*70}

EXAMPLES:

  # List everything with full details
  list --all
  
  # List everything including completed tasks
  list --all --show-done
  
  # Add a task
  add task myproject "Fix bug #123" --due tomorrow --tags bug,urgent
  
  # Edit a task (no project needed!)
  edit t30b0a --note "Updated specs from client" --status in_progress
  
  # Show full task details
  show t30b0a
  
  # Delete completed tasks (preview first)
  cleanup
  cleanup --done --cancelled --execute
  
  # Create and configure project
  new project work "Work Tasks" --desc "Professional projects"
  edit work --desc "Updated description"

{'='*70}

For command-specific help: help <command>
Example: help edit, help list, help cleanup
""")
    else:
        # Command-specific help
        cmd = args[0].lower()
        help_docs = {
            "list": """
LIST - Display projects and tasks

Usage:
  list                      Quick project summary
  list --all                All projects with tasks (hides completed)
  list --all --show-done    Everything including completed tasks
  list projects             Project summary only
  list tasks                All tasks across all projects
  list tasks <project>      Tasks in specific project
  list tasks --upcoming     Active tasks with no due date or a future due date

Examples:
  list --all               # Detailed view, hides completed
  list --all --show-done   # Show everything
  list tasks work          # Tasks in 'work' project
""",
            "show": """
SHOW - Display full details

Usage:
  show <task_id>       Full task details with all fields
  show <contact_id>    Contact information
  show <project_slug>  Project with all tasks and contacts

Examples:
  show t30b0a          # Show task details
  show c5f9a2          # Show contact
  show myproject       # Show project with all tasks
""",
            "edit": """
EDIT - Modify tasks or projects

Usage:
  edit <task_id> [options]
    Options: --title, --due, --note, --status, --tags
  
  edit <project_slug> [options]
    Options: --name, --desc

Valid statuses: todo, in_progress, waiting, done, cancelled

Examples:
  edit t30b0a --note "Client called with update"
  edit t30b0a --due tomorrow --status in_progress
  edit t30b0a --title "New title" --tags urgent,bug
  edit myproject --name "Updated Name" --desc "New description"
""",
            "cleanup": """
CLEANUP - Delete completed tasks in bulk

Usage:
  cleanup                      Preview (dry run) - shows what would be deleted
  cleanup --done               Delete tasks with status='done'
  cleanup --cancelled          Delete tasks with status='cancelled'
  cleanup --done --cancelled   Delete both done and cancelled
  cleanup --execute            Actually delete (requires 'yes' confirmation)

Note: This deletes tasks based on their STATUS field:
  - status='done'      Tasks marked as completed
  - status='cancelled' Tasks marked as cancelled/abandoned

There is NO "confirmed" status. The valid statuses are:
  todo, in_progress, waiting, done, cancelled

Safety:
  1. Run without --execute to preview what will be deleted
  2. Add --execute and type 'yes' at prompt to actually delete

Examples:
  cleanup                              # Preview all completed tasks
  cleanup --done --execute             # Delete only 'done' tasks
  cleanup --done --cancelled --execute # Delete all completed
""",
            "add": """
ADD - Create new tasks or contacts

Usage:
  add task <project> <title> [--due <date>] [--note <text>] [--tags <t1,t2>]
  add contact <project> <name> [--role <role>] [--email <email>]

Examples:
  add task work "Deploy website" --due "2026-03-01" --tags deploy,urgent
  add task work "Fix bug" --note "Issue reported by client"
  add contact work "John Doe" --role "Client" --email "john@example.com"
""",
            "search": """
SEARCH - Full-text search across all tasks

Usage:
  search <term>                         Search all active tasks, all fields
  search <term> --all                   Include done/cancelled tasks
  search <term> --field <field>         Restrict to one field
  search <term> --project <slug>        Restrict to one project
  search <term> --regexp                Treat term as regexp (IGNORECASE)

Valid fields: title, notes, tags, outcome, assignee

Results are grouped by project. Each match shows which field(s) matched
and the matched field value (truncated at 120 chars).

Examples:
  search vermont
  search "Green Mountain" --all
  search water --field notes --project home
  search "plumber|electrician" --regexp
""",
            "config": """
CONFIG - View and modify configuration

Usage:
  config                    Show current configuration
  config location <path>    Move data to new location
  config reset              Reset to default configuration

Examples:
  config                                    # View current settings
  config location ~/Documents/scheduler     # Move data directory
  config location /mnt/external/scheduler   # Move to external drive
  config reset                              # Reset to defaults

Reset behavior:
  • Deletes config file to restore defaults
  • Reverts data_dir to ~/.scheduler/
  • Resets all preferences to defaults
  • Does NOT move or delete existing data files
  • Requires typing 'yes' to confirm
  • Restart scheduler after reset

Default configuration:
  Data Directory: ~/.scheduler/
  Storage Engine: json
"""
        }
        
        help_text = help_docs.get(cmd, f"No detailed help available for '{cmd}'")
        print(help_text)


