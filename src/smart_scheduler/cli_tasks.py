"""
cli_tasks.py — Task and search commands for the Smart Scheduler CLI.

Commands: list, show, cleanup, new, add, edit, delete, search.

Each function receives the CLI instance as its first argument so it can
access cli.task_service, cli.maint_service, cli._opts(), etc.
"""

import re

from .models import TaskStatus


def cmd_list(cli, args):
    """List projects and tasks with comprehensive detail.
    
    Usage:
        list                      List all projects (summary)
        list --all                List all projects with all tasks (default: hide done)
        list --all --show-done    List everything including completed tasks
        list projects             List only projects (summary)
        list tasks                List all tasks across all projects
        list tasks <project>      List tasks in specific project
        list tasks --upcoming     Active tasks with no due date or a future due date
    """
    pos, opts = cli._opts(args)
    
    show_done = "show-done" in opts or "show_done" in opts
    show_all = "all" in opts
    upcoming = "upcoming" in opts

    # Filter function: upcoming = not done/cancelled AND (no due date OR due date >= today)
    def _is_upcoming(t):
        from datetime import date
        if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            return False
        if t.due_date:
            try:
                return date.fromisoformat(t.due_date) >= date.today()
            except ValueError:
                return True  # unparseable date — include rather than silently drop
        return True  # no due date — always included
    
    # Determine what to list
    what = pos[0] if pos else ("all" if show_all else "projects")
    
    if what == "projects" or (what == "all" and not show_all):
        # Summary view: Just list projects
        projects = cli.storage.load_all_projects()
        if not projects:
            return print("No projects.")
        
        print("\n=== PROJECTS ===\n")
        for p in projects:
            active_tasks = [t for t in p.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]
            done_tasks = [t for t in p.tasks if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED)]
            
            print(f"[{p.name}]")
            print(f"  Slug: {p.slug}")
            if p.description:
                print(f"  Description: {p.description}")
            print(f"  Tasks: {len(active_tasks)} active, {len(done_tasks)} done, {len(p.tasks)} total")
            if p.contacts:
                print(f"  Contacts: {len(p.contacts)}")
            print()
    
    elif what == "all":
        # Detailed hierarchical view
        projects = cli.storage.load_all_projects()
        if not projects:
            return print("No projects.")
        
        print("\n=== ALL PROJECTS & TASKS ===")
        if not show_done:
            print("(Hiding completed tasks. Use --show-done to see all)\n")
        
        for p in projects:
            # Filter tasks based on show_done flag
            if show_done:
                tasks = p.tasks
            else:
                tasks = [t for t in p.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]
            
            print(f"\n[{p.name}] ({p.slug})")
            if p.description:
                print(f"  Description: {p.description}")
            
            if tasks:
                print(f"  Tasks ({len(tasks)}):")
                for t in tasks:
                    status_icon = t.status.icon
                    due_str = f" [Due: {t.due_date}]" if t.due_date else ""
                    tags_str = f" #{','.join(t.tags)}" if t.tags else ""
                    print(f"    {status_icon} {t.title} ({t.id}){due_str}{tags_str}")
                    if t.notes:
                        # Indent notes
                        for line in t.notes.split('\n'):
                            print(f"       Note: {line}")
            else:
                print(f"  Tasks: {len(p.tasks)} (all completed)" if p.tasks else "  Tasks: 0")
            
            if p.contacts:
                print(f"  Contacts ({len(p.contacts)}):")
                for c in p.contacts:
                    role_str = f" - {c.role}" if c.role else ""
                    print(f"    • {c.name} ({c.id}){role_str}")
            
            print()
    
    elif what == "tasks":
        # List tasks (all or for specific project)
        project_slug = pos[1] if len(pos) > 1 else None
        
        if project_slug:
            # Tasks for specific project
            p = cli.storage.load_project(project_slug)
            if not p:
                return print(f"Project '{project_slug}' not found")
            
            if upcoming:
                tasks = [t for t in p.tasks if _is_upcoming(t)]
            elif show_done:
                tasks = p.tasks
            else:
                tasks = [t for t in p.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]
            
            if not tasks:
                return print(f"No {'upcoming ' if upcoming else 'active ' if not show_done else ''}tasks in '{p.name}'")
            
            print(f"\n=== TASKS IN {p.name} ===")
            if upcoming:
                print("(Showing upcoming: active tasks with no due date or future due date)\n")
            elif not show_done:
                print("(Hiding completed tasks. Use --show-done to see all)\n")
            
            for t in tasks:
                _print_task_detail(t)
        else:
            # All tasks across all projects
            projects = cli.storage.load_all_projects()
            all_tasks = []
            
            for p in projects:
                for t in p.tasks:
                    if upcoming:
                        include = _is_upcoming(t)
                    else:
                        include = show_done or t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
                    if include:
                        t._project_slug = p.slug
                        t._project_name = p.name
                        all_tasks.append(t)
            
            # Sort by due date: tasks with a due date first (ascending), then no due date
            from datetime import date
            all_tasks.sort(key=lambda t: (
                t.due_date is None,
                t.due_date or ""
            ))

            if not all_tasks:
                return print("No upcoming tasks." if upcoming else "No tasks.")
            
            print(f"\n=== {'UPCOMING ' if upcoming else ''}ALL TASKS ===")
            if upcoming:
                print("(Active tasks with no due date or a future due date)\n")
            elif not show_done:
                print("(Hiding completed tasks. Use --show-done to see all)\n")
            
            for t in all_tasks:
                project_str = f" [{t._project_name}]" if hasattr(t, '_project_name') else ""
                status_icon = t.status.icon
                due_str = f" [Due: {t.due_date}]" if t.due_date else ""
                print(f"  {status_icon} {t.title} ({t.id}){project_str}{due_str}")

def _print_task_detail(task):
    """Helper to print task with full details."""
    status_icon = task.status.icon
    print(f"\n  {status_icon} {task.title}")
    print(f"     ID:     {task.id}")
    print(f"     Status: {task.status.value}")
    if task.due_date:
        print(f"     Due:    {task.due_date}")
    if task.assignee:
        print(f"     Assign: {task.assignee}")
    if task.tags:
        print(f"     Tags:   {', '.join(task.tags)}")
    if task.notes:
        for line in task.notes.split('\n'):
            print(f"     Note:   {line}")
    if task.outcome:
        print(f"     Result: {task.outcome}")

def cmd_show(cli, args):
    """Show comprehensive details of a task, contact, or project.
    
    Usage:
        show <task_id>       Show full task details
        show <contact_id>    Show contact details  
        show <project_slug>  Show project details with all tasks/contacts
    """
    if not args:
        return print("Usage: show <task_id or contact_id or project_slug>")
    
    identifier = args[0]
    
    # Try as task ID (starts with 't')
    if identifier.startswith('t'):
        result = cli.task_service.find_task_by_id(identifier)
        if result:
            project, task = result
            print(f"\n{'='*60}")
            print(f"TASK: {task.title}")
            print(f"{'='*60}")
            print(f"ID:           {task.id}")
            print(f"Project:      {project.name} ({project.slug})")
            print(f"Status:       {task.status.value} {task.status.icon}")
            print(f"Created:      {task.created_at}")
            print(f"Updated:      {task.updated_at}")
            if task.due_date:
                print(f"Due Date:     {task.due_date}")
            if task.reminder_date:
                print(f"Reminder:     {task.reminder_date}")
            if task.assignee:
                print(f"Assignee:     {task.assignee}")
            if task.contact_id:
                print(f"Contact:      {task.contact_id}")
            if task.tags:
                print(f"Tags:         {', '.join(task.tags)}")
            if task.notes:
                print(f"\nNotes:")
                for line in task.notes.split('\n'):
                    print(f"  {line}")
            if task.outcome:
                print(f"\nOutcome:")
                for line in task.outcome.split('\n'):
                    print(f"  {line}")
            print(f"{'='*60}\n")
            return
    
    # Try as contact ID (starts with 'c')
    if identifier.startswith('c'):
        result = cli.task_service.find_contact_by_id(identifier)
        if result:
            project, contact = result
            print(f"\n{'='*60}")
            print(f"CONTACT: {contact.name}")
            print(f"{'='*60}")
            print(f"ID:           {contact.id}")
            print(f"Project:      {project.name} ({project.slug})")
            if contact.role:
                print(f"Role:         {contact.role}")
            if contact.email:
                print(f"Email:        {contact.email}")
            if contact.phone:
                print(f"Phone:        {contact.phone}")
            if contact.notes:
                print(f"\nNotes:")
                for line in contact.notes.split('\n'):
                    print(f"  {line}")
            print(f"{'='*60}\n")
            return
    
    # Try as project slug
    p = cli.storage.load_project(identifier)
    if p:
        print(f"\n{'='*60}")
        print(f"PROJECT: {p.name}")
        print(f"{'='*60}")
        print(f"Slug:         {p.slug}")
        if p.description:
            print(f"Description:  {p.description}")
        print(f"Created:      {p.created_at}")
        print(f"Updated:      {p.updated_at}")
        
        # Task summary
        active = [t for t in p.tasks if t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)]
        done = [t for t in p.tasks if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED)]
        print(f"\nTasks:        {len(active)} active, {len(done)} done, {len(p.tasks)} total")
        
        if active:
            print("\nActive Tasks:")
            for t in active:
                due_str = f" [Due: {t.due_date}]" if t.due_date else ""
                print(f"  {t.status.icon} {t.title} ({t.id}){due_str}")
        
        if done:
            print("\nCompleted Tasks:")
            for t in done:
                print(f"  {t.status.icon} {t.title} ({t.id})")
        
        if p.contacts:
            print(f"\nContacts ({len(p.contacts)}):")
            for c in p.contacts:
                role_str = f" - {c.role}" if c.role else ""
                print(f"  • {c.name} ({c.id}){role_str}")
        
        print(f"{'='*60}\n")
        return
    
    print(f"Not found: {identifier}")

def cmd_cleanup(cli, args):
    """Delete all completed tasks and/or cancelled tasks.
    
    NOTE: This removes tasks with status='done' or status='cancelled'.
    It does NOT remove tasks based on any "confirmed" status - that doesn't exist.
    
    Usage:
        cleanup                      Show what would be deleted (dry run)
        cleanup --done               Delete all tasks marked status='done'
        cleanup --cancelled          Delete all tasks marked status='cancelled'
        cleanup --done --cancelled   Delete both done and cancelled tasks
        cleanup --execute            Actually perform the deletion (safer than --confirm)
    
    Safety: Always previews first. Use --execute to actually delete.
    """
    pos, opts = cli._opts(args)
    
    delete_done = "done" in opts
    delete_cancelled = "cancelled" in opts
    execute = "execute" in opts or "confirm" in opts  # Support both flags
    
    # If neither specified, delete both (but require execute flag)
    if not delete_done and not delete_cancelled:
        delete_done = True
        delete_cancelled = True
    
    # Collect tasks to delete
    to_delete = []
    projects = cli.storage.load_all_projects()
    
    for project in projects:
        for task in project.tasks:
            should_delete = False
            if delete_done and task.status == TaskStatus.DONE:
                should_delete = True
            if delete_cancelled and task.status == TaskStatus.CANCELLED:
                should_delete = True
            
            if should_delete:
                to_delete.append((project, task))
    
    if not to_delete:
        return print("No completed tasks to delete.")
    
    # Show what will be deleted
    print(f"\nFound {len(to_delete)} completed task(s) to delete:\n")
    for project, task in to_delete:
        print(f"  {task.status.icon} {task.title} ({task.id}) [{task.status.value}] from '{project.name}'")
    
    if not execute:
        print(f"\nDry run - no tasks deleted.")
        print(f"To actually delete, add --execute flag:")
        if delete_done and delete_cancelled:
            print(f"  cleanup --done --cancelled --execute")
        elif delete_done:
            print(f"  cleanup --done --execute")
        else:
            print(f"  cleanup --cancelled --execute")
        return
    
    # Confirm deletion
    response = input(f"\nPermanently delete {len(to_delete)} task(s)? (yes/no): ")
    if response.lower() != 'yes':
        return print("Deletion cancelled.")
    
    # Delete tasks
    deleted_count = 0
    for project, task in to_delete:
        project.tasks = [t for t in project.tasks if t.id != task.id]
        cli.storage.save_project(project)
        deleted_count += 1
    
    print(f"\n✓ Deleted {deleted_count} task(s).")

def cmd_new(cli, args):
    """Create a new project.
    
    Usage:
        new project <slug> <name> [--desc <description>]
    """
    if len(args) < 2 or args[0] != "project":
        return print("Usage: new project <slug> <name> [--desc <description>]")
    
    pos, opts = cli._opts(args[1:])
    if len(pos) < 2:
        return print("Usage: new project <slug> <name>")
    
    slug, name = pos[0], pos[1]
    cli.task_service.create_project(slug, name)
    
    if "desc" in opts or "description" in opts:
        desc = opts.get("desc") or opts.get("description")
        cli.task_service.update_project(slug, desc=desc)
    
    print(f"✓ Project '{name}' created with slug '{slug}'")

def cmd_add(cli, args):
    """Add a task or contact.
    
    Usage:
        add task <project_slug> <title> [--due <date>] [--note <text>] [--tags <tag1,tag2>]
        add contact <project_slug> <name> [--role <role>] [--email <email>] [--phone <phone>]
    """
    if len(args) < 2:
        return print("Usage: add task <project> <title> [options]\n"
                    "       add contact <project> <name> [options]")
    
    kind = args[0]
    if kind == "task":
        if len(args) < 3:
            return print("Usage: add task <project_slug> <title> [--due <date>] [--note <text>] [--tags <tag1,tag2>]")
        
        slug, title = args[1], args[2]
        pos, opts = cli._opts(args[3:])
        
        # Validate flags - catch common mistakes
        valid_task_flags = {'due', 'd', 'note', 'notes', 'tags', 'g'}
        invalid_flags = set(opts.keys()) - valid_task_flags
        
        if invalid_flags:
            # Specific helpful error for --desc
            if 'desc' in invalid_flags or 'description' in invalid_flags:
                return print("Error: --desc is not a valid option for tasks.\n"
                           "       Did you mean --note? (Use --note for task descriptions/notes)")
            else:
                invalid_list = ', '.join('--' + f for f in invalid_flags)
                return print(f"Error: Unknown option(s): {invalid_list}\n"
                           f"       Valid options: --due, --note, --tags")
        
        task = cli.task_service.add_task(
            slug, title,
            due=opts.get("due") or opts.get("d"),
            notes=opts.get("note") or opts.get("notes"),
            tags=opts.get("tags", "").split(",") if opts.get("tags") else None
        )
        print(f"✓ Task added: {task.title} ({task.id})")
    
    elif kind == "contact":
        if len(args) < 3:
            return print("Usage: add contact <project_slug> <name> [--role <role>] [--email <email>]")
        
        slug, name = args[1], args[2]
        pos, opts = cli._opts(args[3:])
        
        contact = cli.task_service.add_contact(
            slug, name,
            role=opts.get("role"),
            note=opts.get("note")
        )
        print(f"✓ Contact added: {contact.name} ({contact.id})")

def cmd_edit(cli, args):
    """Edit a task or project by ID.
    
    Usage:
        edit <task_id> [--title <title>] [--due <date>] [--note <text>] [--status <status>] [--tags <tags>]
        edit <project_slug> [--name <name>] [--desc <description>]
        
    Valid statuses: todo, in_progress, waiting, done, cancelled
    """
    if not args:
        return print("Usage: edit <task_id or project_slug> [options]\n"
                    "Task options: --title, --due, --note, --status, --tags\n"
                    "Project options: --name, --desc")
    
    identifier = args[0]
    pos, opts = cli._opts(args[1:])
    
    # Try as task ID
    if identifier.startswith('t'):
        result = cli.task_service.find_task_by_id(identifier)
        if result:
            project, task = result
            
            # Validate flags before processing
            valid_flags = {'title', 't', 'due', 'd', 'note', 'notes', 'status', 's', 'tags'}
            invalid_flags = set(opts.keys()) - valid_flags
            
            if invalid_flags:
                if 'desc' in invalid_flags or 'description' in invalid_flags:
                    return print("Error: --desc is not a valid option for tasks.\n"
                               "       Did you mean --note? (Use --note for task descriptions/notes)")
                else:
                    invalid_list = ', '.join('--' + f for f in invalid_flags)
                    return print(f"Error: Unknown option(s): {invalid_list}\n"
                               f"       Valid task options: --title, --due, --note, --status, --tags")
            
            updates = {}
            
            if "title" in opts or "t" in opts:
                updates["title"] = opts.get("title") or opts.get("t")
            if "due" in opts or "d" in opts:
                updates["due_date"] = opts.get("due") or opts.get("d")
            if "note" in opts or "notes" in opts:
                updates["notes"] = opts.get("note") or opts.get("notes")
            if "status" in opts or "s" in opts:
                updates["status"] = opts.get("status") or opts.get("s")
            if "tags" in opts:
                updates["tags"] = opts.get("tags").split(",")
            
            if not updates:
                return print("No updates specified. Use --title, --due, --note, --status, or --tags")
            
            cli.task_service.update_task(project.slug, task.id, **updates)
            print(f"✓ Task '{task.title}' updated.")
            return
    
    # Try as project slug
    p = cli.storage.load_project(identifier)
    if p:
        updates = {}
        if "name" in opts:
            updates["name"] = opts["name"]
        if "desc" in opts or "description" in opts:
            updates["desc"] = opts.get("desc") or opts.get("description")
        
        if not updates:
            return print("No updates specified. Use --name or --desc")
        
        cli.task_service.update_project(identifier, **updates)
        print(f"✓ Project '{p.name}' updated.")
        return
    
    print(f"Not found: {identifier}")

def cmd_delete(cli, args):
    """Delete a task or project by ID.
    
    Usage:
        delete <task_id>       Delete a task
        delete <project_slug>  Delete a project (and all its tasks)
    """
    if not args:
        return print("Usage: delete <task_id or project_slug>")
    
    identifier = args[0]
    
    # Try as task ID
    if identifier.startswith('t'):
        result = cli.task_service.find_task_by_id(identifier)
        if result:
            project, task = result
            confirm = input(f"Delete task '{task.title}' from '{project.name}'? (yes/no): ")
            if confirm.lower() == 'yes':
                cli.task_service.delete_task_by_id(identifier)
                print(f"✓ Task deleted.")
            else:
                print("Deletion cancelled.")
            return
    
    # Try as project
    p = cli.storage.load_project(identifier)
    if p:
        confirm = input(f"Delete project '{p.name}' and ALL its {len(p.tasks)} task(s)? (yes/no): ")
        if confirm.lower() == 'yes':
            if cli.task_service.delete_project(identifier):
                print(f"✓ Project '{identifier}' deleted.")
        else:
            print("Deletion cancelled.")
        return
    
    print(f"Not found: {identifier}")


def cmd_search(cli, args):
    """Full-text search across all tasks and fields.

    Usage:
        search <term> [--all] [--field title|notes|tags|outcome|assignee]
                      [--project <slug>] [--regexp]

    Reports which fields matched so you can follow up with targeted filters.
    Search is case-insensitive by default.
    --all includes done/cancelled tasks.
    --regexp treats <term> as a case-insensitive regular expression.

    Examples:
        search vermont
        search "Green Mountain" --all
        search water --field notes
        search "plumber|electrician" --regexp
        search inn --project vermont
    """
    pos, opts = cli._opts(args)
    if not pos:
        print("Usage: search <term> [--all] [--field title|notes|tags|outcome|assignee]"
              " [--project <slug>] [--regexp]")
        return

    term = pos[0]
    include_inactive = "all" in opts
    field = opts.get("field")
    project_slug = opts.get("project")
    use_regexp = "regexp" in opts

    valid_fields = {"title", "notes", "tags", "outcome", "assignee"}
    if field and field not in valid_fields:
        print(f"Unknown field '{field}'. Valid fields: {', '.join(sorted(valid_fields))}")
        return

    try:
        results = cli.task_service.search(term, include_inactive, field, project_slug, use_regexp)
    except re.error as e:
        print(f"Invalid regexp: {e}")
        return

    if not results:
        print(f'No matches for "{term}".')
        return

    # Group by project slug, preserving order of first appearance.
    by_project = {}
    for r in results:
        by_project.setdefault(r["project_slug"], []).append(r)

    _MAX = 120   # truncate long field values at this many characters

    for slug, group in by_project.items():
        print(f"\n[{slug}]")
        for r in group:
            task = r["task"]
            fields_str = ", ".join(r["matched_fields"])
            print(f"  {task.id} {task.status.icon}  {task.title}")
            print(f"           Matched in: {fields_str}")
            for f in r["matched_fields"]:
                if f == "title":
                    continue   # already shown on the task line
                elif f == "notes" and task.notes:
                    val = task.notes.replace("\n", " ")
                    val = val[:_MAX] + ("…" if len(val) > _MAX else "")
                    print(f'           Notes: "{val}"')
                elif f == "outcome" and task.outcome:
                    val = task.outcome.replace("\n", " ")
                    val = val[:_MAX] + ("…" if len(val) > _MAX else "")
                    print(f'           Outcome: "{val}"')
                elif f == "assignee" and task.assignee:
                    print(f"           Assignee: {task.assignee}")
                elif f == "tags" and task.tags:
                    print(f"           Tags: {', '.join(task.tags)}")


