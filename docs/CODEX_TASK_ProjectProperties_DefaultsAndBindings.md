# CODEX TASK: Project-level defaults and bindings (priority/periodic/map/note/object)

## Goal
Add project-specific properties: default task priority, tasks periodic toggle, and bindings to a map, a note, and an object.

## Definition of Done
- Project stores new properties safely with defaults.
- Task creation respects project defaults.
- UI allows editing these properties.

---

## Step 1: Extend Project model with defaults and bindings
**Modify:** project model (e.g., `mindnavigator/core/models/project.py`)

Add fields:
- `default_task_priority: int | str` (project-level default)
- `tasks_are_periodic: bool` (if true, new tasks created under project default to periodic)
- `map_id: str | None`
- `note_id: str | None`
- `object_id: str | None`

Rules:
- Keep backward compatibility: default None/False values.

**Acceptance check:**
- Project model loads existing data without migration errors (defaults applied).


---

## Step 2: Apply project defaults when creating tasks
**Modify:** task creation flow (TasksWorkspace add action or task service)

Rules:
- If creating task within a project context: prefill priority from project.default_task_priority if task priority not explicitly set.
- If project.tasks_are_periodic: set task periodic flag + schedule default (e.g., weekly) or leave schedule empty but flag true (decide consistent).

**Acceptance check:**
- Creating a task under a project applies default priority.
- Periodic flag is set automatically when project says so.


---

## Step 3: Add Project details editor UI for these properties
**Modify/Create:** `mindnavigator/ui/forms/project_edit_form.py`

Add controls:
- Default priority selector
- Checkbox: all tasks periodic
- Bindings selectors: map/note/object (can be simple id pickers for now)

**Acceptance check:**
- User can set project properties and they persist.
