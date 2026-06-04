"""
services/task_service.py - ENHANCED with Global ID Lookup

New features:
1. find_task_by_id() - Find any task by ID across all projects
2. find_contact_by_id() - Find any contact by ID across all projects
3. delete_task_by_id() - Delete task by ID without needing project

parse_date() has moved to shared.dates and is re-exported from here
for backward compatibility.
"""
from typing import List, Optional, Tuple
import re
from ..models import Task, Project, Contact, TaskStatus
from ..storage.base import StorageStrategy
from shared.dates import parse_date  # canonical home is now shared.dates

# Fields to scan during full-text search. Each value is a callable that
# returns a list of strings to test against the search term for a given task.
# Add new fields here if Task gains additional text-bearing attributes.
_SEARCHABLE_FIELDS = {
    "title":    lambda t: [t.title]    if t.title    else [],
    "notes":    lambda t: [t.notes]    if t.notes    else [],
    "outcome":  lambda t: [t.outcome]  if t.outcome  else [],
    "assignee": lambda t: [t.assignee] if t.assignee else [],
    "tags":     lambda t: t.tags or [],
}


class TaskService:
    def __init__(self, storage: StorageStrategy):
        self.storage = storage

    # ========================================================================
    # GLOBAL ID LOOKUP - NEW METHODS
    # ========================================================================
    
    def find_task_by_id(self, task_id: str) -> Optional[Tuple[Project, Task]]:
        """Find a task by ID across ALL projects.
        
        Returns:
            Tuple of (Project, Task) if found, None otherwise
        """
        # Search all projects for this task ID
        for project in self.storage.load_all_projects():
            for task in project.tasks:
                if task.id == task_id or task.id.startswith(task_id):
                    return (project, task)
        return None
    
    def find_contact_by_id(self, contact_id: str) -> Optional[Tuple[Project, Contact]]:
        """Find a contact by ID across ALL projects.
        
        Returns:
            Tuple of (Project, Contact) if found, None otherwise
        """
        for project in self.storage.load_all_projects():
            for contact in project.contacts:
                if contact.id == contact_id or contact.id.startswith(contact_id):
                    return (project, contact)
        return None
    
    def delete_task_by_id(self, task_id: str) -> bool:
        """Delete a task by ID without needing to know its project.
        
        Returns:
            True if deleted, False if not found
        """
        result = self.find_task_by_id(task_id)
        if not result:
            return False
        
        project, task = result
        project.tasks = [t for t in project.tasks if t.id != task.id]
        self.storage.save_project(project)
        return True
    
    def delete_contact_by_id(self, contact_id: str) -> bool:
        """Delete a contact by ID without needing to know its project.
        
        Returns:
            True if deleted, False if not found
        """
        result = self.find_contact_by_id(contact_id)
        if not result:
            return False
        
        project, contact = result
        project.contacts = [c for c in project.contacts if c.id != contact.id]
        self.storage.save_project(project)
        return True

    def search(
        self,
        term: str,
        include_inactive: bool = False,
        field: str = None,
        project_slug: str = None,
        use_regexp: bool = False,
    ) -> list[dict]:
        """Full-text search across tasks.

        Default behaviour is case-insensitive substring match (scheduler tasks
        are prose).  Pass use_regexp=True to compile term as a regexp; the
        pattern is always matched case-insensitively so behaviour stays
        consistent with the plain-string default.

        Args:
            term: Substring (case-insensitive) or regexp pattern to find.
            include_inactive: If True, include done/cancelled tasks.
                              Default is active tasks only.
            field: Restrict to one field name (title, notes, outcome,
                   assignee, tags). Default is all fields.
            project_slug: Restrict to one project. Default is all projects.
            use_regexp: If True, compile term with re.IGNORECASE.
                        re.error propagates to the caller.

        Returns:
            List of result dicts, one per matching task:
                project_slug  str  — slug of the containing project
                task          Task — the matching Task object
                matched_fields list[str] — which fields contained the term
        """
        if use_regexp:
            pattern = re.compile(term, re.IGNORECASE)
            match = pattern.search
        else:
            lo = term.lower()
            match = lambda val: lo in val.lower()

        if project_slug:
            project = self.storage.load_project(project_slug)
            projects = [project] if project else []
        else:
            projects = self.storage.load_all_projects()

        results = []

        for project in projects:
            tasks = project.tasks if include_inactive else project.active_tasks
            for task in tasks:
                matched_fields = []
                for field_name, extractor in _SEARCHABLE_FIELDS.items():
                    if field and field_name != field:
                        continue
                    for v in extractor(task):
                        if match(v):
                            matched_fields.append(field_name)
                            break   # don't double-count the same field
                if matched_fields:
                    results.append({
                        "project_slug": project.slug,
                        "task": task,
                        "matched_fields": matched_fields,
                    })

        return results

    # ========================================================================
    # EXISTING METHODS (unchanged)
    # ========================================================================

    def get_summary(self) -> dict:
        projects = self.storage.load_all_projects()
        return { "total_projects": len(projects), "total_active": sum(len(p.active_tasks) for p in projects) }

    def create_project(self, slug: str, name: str) -> Project:
        if self.storage.load_project(slug): raise ValueError("Slug taken")
        p = Project(slug, name)
        self.storage.save_project(p)
        return p

    def update_project(self, slug: str, name: str = None, desc: str = None) -> Project:
        p = self.storage.load_project(slug)
        if not p: raise ValueError("Project not found")
        if name: p.name = name
        if desc: p.description = desc
        self.storage.save_project(p)
        return p

    def rename_project(self, old: str, new: str) -> str:
        self.storage.rename_project(old, new)
        return new

    def delete_project(self, slug: str) -> bool:
        """Deletes a project and all its tasks/contacts."""
        return self.storage.delete_project(slug)

    def add_task(self, slug: str, title: str, assignee: str=None, due: str=None, tags: list=None, contact: str=None, notes: str=None) -> Task:
        p = self.storage.load_project(slug)
        if not p: raise ValueError("Project not found")
        
        parsed_due = parse_date(due) if due else None
        
        t = Task.create(title, assignee, parsed_due, tags)
        if notes: t.notes = notes
        if contact: t.contact_id = contact 
        p.tasks.append(t)
        self.storage.save_project(p)
        return t

    def update_task(self, slug: str, task_id: str, **kwargs) -> Task:
        p = self.storage.load_project(slug)
        if not p: raise ValueError("Project not found")
        t = next((x for x in p.tasks if x.id.startswith(task_id)), None)
        if not t: raise ValueError("Task not found")
        
        if "title" in kwargs: t.title = kwargs["title"]
        if "due_date" in kwargs: t.due_date = parse_date(kwargs["due_date"])
        if "assignee" in kwargs: t.assignee = kwargs["assignee"]
        if "notes" in kwargs: t.notes = kwargs["notes"]
        if "status" in kwargs:
            val = kwargs["status"]
            if isinstance(val, str):
                try: t.status = TaskStatus(val)
                except: pass 
        if "tags" in kwargs: t.tags = kwargs["tags"]
        
        self.storage.save_project(p)
        return t

    def add_contact(self, slug: str, name: str, role: str=None, note: str=None) -> Contact:
        p = self.storage.load_project(slug)
        if not p: raise ValueError("Project not found")
        c = Contact.create(name, role=role, notes=note)
        p.contacts.append(c)
        self.storage.save_project(p)
        return c
