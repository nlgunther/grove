"""
cli_data.py — Data import and export commands for the Smart Scheduler CLI.

Commands: import-json, export, export-json, import-manifest.
Private helpers: _import_task, _import_contact, _import_project,
                 _import_full_database.

Heavy imports (lxml, manifest_bridge) are deferred inside each function
so the scheduler starts quickly even when those deps are absent.
"""

from pathlib import Path


def cmd_import_json(cli, args):
    """Import tasks, projects, or entire database from JSON.
    
    Usage:
        import-json <file>               Import from JSON file (auto-detect type)
        import-json <file> --to <project>   Import tasks to specific project
        import-json <file> --merge       Merge with existing data (don't replace)
        import-json <file> --dry-run     Preview without importing
    
    Import types (auto-detected from export_type field):
        - task: Add task to specified project or original project
        - contact: Add contact to specified project or original project
        - project: Create new project with all tasks/contacts
        - full_database: Import all projects (with merge or replace)
    
    Examples:
        import-json backup.json                    # Import whatever is in the file
        import-json task.json --to work            # Import task to 'work' project
        import-json project.json                   # Import entire project
        import-json full_backup.json               # Import all projects
        import-json full_backup.json --merge       # Merge with existing
        import-json backup.json --dry-run          # Preview only
    """
    import json
    from datetime import datetime
    
    pos, opts = cli._opts(args)
    
    if not pos:
        return print("Usage: import-json <file> [--to <project>] [--merge] [--dry-run]")
    
    filename = pos[0]
    target_project = opts.get("to")
    merge = "merge" in opts
    dry_run = "dry-run" in opts or "dry_run" in opts
    
    # Load JSON file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return print(f"Error: File not found: {filename}")
    except json.JSONDecodeError as e:
        return print(f"Error: Invalid JSON file: {e}")
    except Exception as e:
        return print(f"Error reading file: {e}")
    
    # Validate required fields
    if "export_type" not in data:
        return print("Error: Invalid export file - missing 'export_type' field.\n"
                    "       This doesn't appear to be a valid scheduler export.")
    
    export_type = data["export_type"]
    
    if dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - No changes will be made")
        print(f"{'='*60}")
    
    # Route to appropriate import handler
    if export_type == "task":
        _import_task(cli, data, target_project, dry_run)
    elif export_type == "contact":
        _import_contact(cli, data, target_project, dry_run)
    elif export_type == "project":
        _import_project(cli, data, dry_run)
    elif export_type == "full_database":
        _import_full_database(cli, data, merge, dry_run)
    else:
        print(f"Error: Unknown export_type '{export_type}'")

def _import_task(cli, data, target_project, dry_run):
    """Import a single task."""
    from datetime import datetime
    
    if "task" not in data:
        return print("Error: Invalid task export - missing 'task' field")
    
    task_data = data["task"]
    source_project = data.get("project", {}).get("slug")
    
    # Determine target project
    if target_project:
        project_slug = target_project
    elif source_project:
        project_slug = source_project
    else:
        return print("Error: No target project specified and no source project in export.\n"
                    "       Use --to <project_slug> to specify target project.")
    
    # Check if project exists
    project = cli.storage.load_project(project_slug)
    if not project:
        return print(f"Error: Project '{project_slug}' not found.\n"
                    f"       Create it first with: new project {project_slug} \"Project Name\"")
    
    # Check for ID conflict
    existing_task = next((t for t in project.tasks if t.id == task_data["id"]), None)
    if existing_task:
        print(f"Warning: Task with ID {task_data['id']} already exists in project.")
        if not dry_run:
            response = input("Overwrite existing task? (yes/no): ")
            if response.lower() != 'yes':
                return print("Import cancelled.")
            # Remove existing task
            project.tasks = [t for t in project.tasks if t.id != task_data["id"]]
    
    # Create task from data
    # Use models that are already imported in the CLI module
    from scheduler.models import Task, TaskStatus
    
    # Convert status string to enum
    try:
        status = TaskStatus(task_data.get("status", "todo"))
    except ValueError:
        status = TaskStatus.TODO
    
    task = Task(
        id=task_data["id"],
        title=task_data["title"],
        status=status,
        assignee=task_data.get("assignee"),
        due_date=task_data.get("due_date"),
        reminder_date=task_data.get("reminder_date"),
        contact_id=task_data.get("contact_id"),
        tags=task_data.get("tags", []),
        notes=task_data.get("notes"),
        outcome=task_data.get("outcome"),
        created_at=task_data.get("created_at", datetime.now().isoformat()),
        updated_at=task_data.get("updated_at", datetime.now().isoformat())
    )
    
    if dry_run:
        print(f"\nWould import task:")
        print(f"  ID:      {task.id}")
        print(f"  Title:   {task.title}")
        print(f"  Status:  {task.status.value}")
        print(f"  Project: {project_slug}")
        return
    
    # Add task to project
    project.tasks.append(task)
    cli.storage.save_project(project)
    
    print(f"✓ Imported task '{task.title}' ({task.id}) to project '{project_slug}'")

def _import_contact(cli, data, target_project, dry_run):
    """Import a single contact."""
    if "contact" not in data:
        return print("Error: Invalid contact export - missing 'contact' field")
    
    contact_data = data["contact"]
    source_project = data.get("project", {}).get("slug")
    
    # Determine target project
    if target_project:
        project_slug = target_project
    elif source_project:
        project_slug = source_project
    else:
        return print("Error: No target project specified and no source project in export.\n"
                    "       Use --to <project_slug> to specify target project.")
    
    # Check if project exists
    project = cli.storage.load_project(project_slug)
    if not project:
        return print(f"Error: Project '{project_slug}' not found.")
    
    # Check for ID conflict
    existing = next((c for c in project.contacts if c.id == contact_data["id"]), None)
    if existing:
        print(f"Warning: Contact with ID {contact_data['id']} already exists.")
        if not dry_run:
            response = input("Overwrite? (yes/no): ")
            if response.lower() != 'yes':
                return print("Import cancelled.")
            project.contacts = [c for c in project.contacts if c.id != contact_data["id"]]
    
    from scheduler.models import Contact
    
    contact = Contact(
        id=contact_data["id"],
        name=contact_data["name"],
        phone=contact_data.get("phone"),
        email=contact_data.get("email"),
        role=contact_data.get("role"),
        notes=contact_data.get("notes")
    )
    
    if dry_run:
        print(f"\nWould import contact:")
        print(f"  ID:      {contact.id}")
        print(f"  Name:    {contact.name}")
        print(f"  Project: {project_slug}")
        return
    
    project.contacts.append(contact)
    cli.storage.save_project(project)
    
    print(f"✓ Imported contact '{contact.name}' ({contact.id}) to project '{project_slug}'")

def _import_project(cli, data, dry_run):
    """Import an entire project."""
    from datetime import datetime
    from scheduler.models import Task, Contact, Project, TaskStatus
    
    if "project" not in data:
        return print("Error: Invalid project export - missing 'project' field")
    
    proj_data = data["project"]
    slug = proj_data["slug"]
    
    # Check if project exists
    existing = cli.storage.load_project(slug)
    if existing:
        print(f"Warning: Project '{slug}' already exists.")
        if not dry_run:
            response = input("Overwrite entire project? (yes/no): ")
            if response.lower() != 'yes':
                return print("Import cancelled.")
    
    # Create project
    project = Project(
        slug=slug,
        name=proj_data["name"],
        description=proj_data.get("description", ""),
        created_at=proj_data.get("created_at", datetime.now().isoformat()),
        updated_at=proj_data.get("updated_at", datetime.now().isoformat())
    )
    
    # Import tasks
    for task_data in proj_data.get("tasks", []):
        try:
            status = TaskStatus(task_data.get("status", "todo"))
        except ValueError:
            status = TaskStatus.TODO
        
        task = Task(
            id=task_data["id"],
            title=task_data["title"],
            status=status,
            assignee=task_data.get("assignee"),
            due_date=task_data.get("due_date"),
            reminder_date=task_data.get("reminder_date"),
            contact_id=task_data.get("contact_id"),
            tags=task_data.get("tags", []),
            notes=task_data.get("notes"),
            outcome=task_data.get("outcome"),
            created_at=task_data.get("created_at", datetime.now().isoformat()),
            updated_at=task_data.get("updated_at", datetime.now().isoformat())
        )
        project.tasks.append(task)
    
    # Import contacts
    for contact_data in proj_data.get("contacts", []):
        contact = Contact(
            id=contact_data["id"],
            name=contact_data["name"],
            phone=contact_data.get("phone"),
            email=contact_data.get("email"),
            role=contact_data.get("role"),
            notes=contact_data.get("notes")
        )
        project.contacts.append(contact)
    
    if dry_run:
        print(f"\nWould import project:")
        print(f"  Slug:     {project.slug}")
        print(f"  Name:     {project.name}")
        print(f"  Tasks:    {len(project.tasks)}")
        print(f"  Contacts: {len(project.contacts)}")
        return
    
    cli.storage.save_project(project)
    
    print(f"✓ Imported project '{project.name}' ({project.slug})")
    print(f"  Tasks:    {len(project.tasks)}")
    print(f"  Contacts: {len(project.contacts)}")

def _import_full_database(cli, data, merge, dry_run):
    """Import entire database."""
    from datetime import datetime
    from scheduler.models import Task, Contact, Project, TaskStatus
    
    if "projects" not in data:
        return print("Error: Invalid database export - missing 'projects' field")
    
    projects_data = data["projects"]
    
    if not merge:
        print(f"Warning: This will REPLACE all existing data with {len(projects_data)} projects.")
        if not dry_run:
            response = input("Continue? Type 'yes' to confirm: ")
            if response != 'yes':
                return print("Import cancelled.")
    
    imported_count = 0
    skipped_count = 0
    
    for proj_data in projects_data:
        slug = proj_data["slug"]
        
        # Check if exists
        existing = cli.storage.load_project(slug)
        if existing and merge:
            print(f"Skipping existing project: {slug}")
            skipped_count += 1
            continue
        
        # Create project
        project = Project(
            slug=slug,
            name=proj_data["name"],
            description=proj_data.get("description", ""),
            created_at=proj_data.get("created_at", datetime.now().isoformat()),
            updated_at=proj_data.get("updated_at", datetime.now().isoformat())
        )
        
        # Import tasks
        for task_data in proj_data.get("tasks", []):
            try:
                status = TaskStatus(task_data.get("status", "todo"))
            except ValueError:
                status = TaskStatus.TODO
            
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                status=status,
                assignee=task_data.get("assignee"),
                due_date=task_data.get("due_date"),
                reminder_date=task_data.get("reminder_date"),
                contact_id=task_data.get("contact_id"),
                tags=task_data.get("tags", []),
                notes=task_data.get("notes"),
                outcome=task_data.get("outcome"),
                created_at=task_data.get("created_at", datetime.now().isoformat()),
                updated_at=task_data.get("updated_at", datetime.now().isoformat())
            )
            project.tasks.append(task)
        
        # Import contacts
        for contact_data in proj_data.get("contacts", []):
            contact = Contact(
                id=contact_data["id"],
                name=contact_data["name"],
                phone=contact_data.get("phone"),
                email=contact_data.get("email"),
                role=contact_data.get("role"),
                notes=contact_data.get("notes")
            )
            project.contacts.append(contact)
        
        if dry_run:
            print(f"  Would import: {project.name} ({len(project.tasks)} tasks)")
        else:
            cli.storage.save_project(project)
            print(f"  Imported: {project.name}")
        
        imported_count += 1
    
    if dry_run:
        print(f"\nDry run complete - would import {imported_count} project(s)")
        if merge and skipped_count > 0:
            print(f"Would skip {skipped_count} existing project(s)")
    else:
        print(f"\n✓ Imported {imported_count} project(s)")
        if merge and skipped_count > 0:
            print(f"  Skipped {skipped_count} existing project(s)")


def cmd_export(cli, args):
    """Export data to various formats."""
    if len(args) < 2:
        return print("Usage: export <task_id or project_slug> <ics|json|csv>")
    
    identifier, fmt = args[0], args[1]
    
    if fmt == "ics":
        if identifier.startswith('t'):
            result = cli.task_service.find_task_by_id(identifier)
            if result:
                project, task = result
                content = cli.cal_service.generate_file_content(task)
                fname = f"{project.slug}_{task.id}.ics"
                Path(fname).write_text(content, encoding="utf-8")
                print(f"✓ Exported to {fname}")
                return
        
        print(f"Task not found: {identifier}")

def cmd_export_json(cli, args):
    """Export tasks, projects, or entire database to JSON.
    
    Usage:
        export-json <task_id>        Export single task to JSON
        export-json <project_slug>   Export project with all tasks/contacts
        export-json --all            Export entire database
        export-json --all --output <file>  Specify output filename
    
    Examples:
        export-json t30b0a           Creates t30b0a.json
        export-json myproject        Creates myproject.json
        export-json --all            Creates scheduler_export_YYYYMMDD_HHMMSS.json
        export-json --all --output full_backup.json
    """
    import json
    from datetime import datetime
    
    pos, opts = cli._opts(args)
    
    # Check for conflicting arguments
    if "all" in opts and pos:
        return print("Error: Cannot use --all with a specific ID.\n"
                    "Usage: export-json --all  (for everything)\n"
                    "   OR: export-json <task_id or project_slug>  (for specific item)")
    
    # Export entire database
    if "all" in opts:
        projects = cli.storage.load_all_projects()
        
        data = {
            "export_date": datetime.now().isoformat(),
            "export_type": "full_database",
            "storage_engine": cli.cfg.preferences.get("storage_engine", "json"),
            "data_directory": str(cli.cfg.data_dir),
            "projects": []
        }
        
        for p in projects:
            project_data = {
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "tasks": [],
                "contacts": []
            }
            
            for t in p.tasks:
                task_data = {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value,
                    "assignee": t.assignee,
                    "due_date": t.due_date,
                    "reminder_date": t.reminder_date,
                    "contact_id": t.contact_id,
                    "tags": t.tags,
                    "notes": t.notes,
                    "outcome": t.outcome,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at
                }
                project_data["tasks"].append(task_data)
            
            for c in p.contacts:
                contact_data = {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "email": c.email,
                    "role": c.role,
                    "notes": c.notes
                }
                project_data["contacts"].append(contact_data)
            
            data["projects"].append(project_data)
        
        # Determine output filename
        if "output" in opts:
            filename = opts["output"]
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scheduler_export_{timestamp}.json"
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        total_tasks = sum(len(p["tasks"]) for p in data["projects"])
        total_contacts = sum(len(p["contacts"]) for p in data["projects"])
        
        print(f"\n✓ Exported full database to: {filename}")
        print(f"  Projects: {len(projects)}")
        print(f"  Tasks:    {total_tasks}")
        print(f"  Contacts: {total_contacts}")
        return
    
    # Export single task or project
    if not pos:
        return print("Usage: export-json <task_id or project_slug> OR export-json --all")
    
    identifier = pos[0]
    
    # Try as task ID
    if identifier.startswith('t'):
        result = cli.task_service.find_task_by_id(identifier)
        if result:
            project, task = result
            
            data = {
                "export_date": datetime.now().isoformat(),
                "export_type": "task",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value,
                    "assignee": task.assignee,
                    "due_date": task.due_date,
                    "reminder_date": task.reminder_date,
                    "contact_id": task.contact_id,
                    "tags": task.tags,
                    "notes": task.notes,
                    "outcome": task.outcome,
                    "created_at": task.created_at,
                    "updated_at": task.updated_at
                },
                "project": {
                    "slug": project.slug,
                    "name": project.name
                }
            }
            
            filename = opts.get("output", f"{task.id}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Exported task '{task.title}' to: {filename}")
            return
    
    # Try as contact ID
    if identifier.startswith('c'):
        result = cli.task_service.find_contact_by_id(identifier)
        if result:
            project, contact = result
            
            data = {
                "export_date": datetime.now().isoformat(),
                "export_type": "contact",
                "contact": {
                    "id": contact.id,
                    "name": contact.name,
                    "phone": contact.phone,
                    "email": contact.email,
                    "role": contact.role,
                    "notes": contact.notes
                },
                "project": {
                    "slug": project.slug,
                    "name": project.name
                }
            }
            
            filename = opts.get("output", f"{contact.id}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Exported contact '{contact.name}' to: {filename}")
            return
    
    # Try as project slug
    p = cli.storage.load_project(identifier)
    if p:
        data = {
            "export_date": datetime.now().isoformat(),
            "export_type": "project",
            "project": {
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "tasks": [],
                "contacts": []
            }
        }
        
        for t in p.tasks:
            task_data = {
                "id": t.id,
                "title": t.title,
                "status": t.status.value,
                "assignee": t.assignee,
                "due_date": t.due_date,
                "reminder_date": t.reminder_date,
                "contact_id": t.contact_id,
                "tags": t.tags,
                "notes": t.notes,
                "outcome": t.outcome,
                "created_at": t.created_at,
                "updated_at": t.updated_at
            }
            data["project"]["tasks"].append(task_data)
        
        for c in p.contacts:
            contact_data = {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "role": c.role,
                "notes": c.notes
            }
            data["project"]["contacts"].append(contact_data)
        
        filename = opts.get("output", f"{p.slug}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Exported project '{p.name}' to: {filename}")
        print(f"  Tasks:    {len(data['project']['tasks'])}")
        print(f"  Contacts: {len(data['project']['contacts'])}")
        return
    
    print(f"Not found: {identifier}")


def cmd_import_manifest(cli, args):
    """Import tasks from a Manifest Manager XML file into the scheduler.

    Usage:
        import-manifest <file> --project <slug> [--xpath <expr>] [--engine json|sqlite]

    Arguments:
        file         Path to the manifest XML file.

    Options:
        --project    Scheduler project slug (required).
                     Created automatically if it does not exist.
        --name       Project display name (only used when creating).
        --xpath      XPath to select nodes (default: from integration.yaml,
                     or "//task[@due]" if not configured).
        --engine     Storage engine: json (default) or sqlite.

    Status conversion is driven by config/integration.yaml.
    Until status_mapping.to_scheduler is configured, all imported
    tasks will have status 'todo'.

    Examples:
        import-manifest projects.xml --project q1-work
        import-manifest projects.xml --project q1-work --xpath "//task[@due][@status='active']"
    """
    pos, opts = cli._opts(args)

    if not pos:
        return print("Usage: import-manifest <file> --project <slug> [--xpath <expr>]")

    filepath = pos[0]
    project_slug = opts.get("project")
    if not project_slug:
        return print("Error: --project <slug> is required.")

    project_name = opts.get("name", project_slug)
    engine = opts.get("engine", "json")
    xpath_override = opts.get("xpath", "")

    try:
        from lxml import etree
        tree = etree.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        return print(f"Error loading manifest '{filepath}': {e}")

    from shared.integration_config import load_integration_config
    cfg = load_integration_config()
    import_cfg = cfg.get("import_manifest", {})

    xpath = xpath_override or import_cfg.get("default_xpath", "") or "//task[@due]"

    try:
        nodes = root.xpath(xpath)
    except Exception as e:
        return print(f"Error evaluating XPath '{xpath}': {e}")

    if not nodes:
        return print(f"No nodes matched '{xpath}' in {filepath}.")

    print(f"Found {len(nodes)} node(s) matching '{xpath}'.")

    from shared.manifest_bridge import build_tasks, push_tasks_to_scheduler

    tasks, skip_reasons = build_tasks(nodes)
    result = push_tasks_to_scheduler(
        tasks=tasks,
        project_slug=project_slug,
        project_name=project_name,
        data_dir=cli.cfg.data_dir,
        storage_engine=engine,
    )
    result.skipped = len(skip_reasons)
    result.skipped_reasons = skip_reasons
    print(result)


