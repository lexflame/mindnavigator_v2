# CODEX TASK: Tasks: Double-click parent task opens subtasks list

## Goal
Change UX: double-click on a task that has nested tasks should open/expand the nested list instead of opening details.

## Definition of Done
- Parent tasks expand on double-click.
- Leaf tasks still open details on double-click.
- UI indicates which tasks have children.

---

## Step 1: Differentiate double-click behavior for tasks with children
**Modify:** Tasks list widget/view (e.g., `mindnavigator/ui/workspaces/tasks_workspace.py`)

On double-click of a task row/title:
- If task has `children_count > 0` (or `has_children`): open/expand subtasks list view instead of opening details.
- Else: open details as before.

Implementation options:
- If using `QTreeView`: toggle expand/collapse on double click when has children; open details via separate action (Enter or button).
- If using custom list: route double click event to either `open_subtasks(task_id)` or `open_task_details(task_id)`.

**Acceptance check:**
- Double-click on a parent task expands/opens subtasks list, not details.
- Double-click on a leaf task opens details as before.


---

## Step 2: Add visual affordance for parent tasks
Add an icon/chevron indicator or bold title for tasks with children (minimal).

**Acceptance check:**
- Parent tasks are visually distinct in the list.
