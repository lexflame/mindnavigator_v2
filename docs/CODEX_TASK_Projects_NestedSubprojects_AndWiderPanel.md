# CODEX TASK: Nested Subprojects + Wider Projects Block in Tasks List

## Goal
Implement nested subprojects within projects and improve the projects block UI width to support a sprint-like workflow.

## Definition of Done
- Projects support parent/child nesting.
- UI shows hierarchy clearly.
- Projects panel is widened and comfortable to use.
- Task filtering works with nested projects.

---

## Step 1: Add subproject relationship to Project model
**Modify:** `project` model

Add:
- `parent_project_id: str | None`
- `path: str` or computed hierarchy helper (optional)

Rules:
- Root projects have parent_project_id = None.

**Acceptance check:**
- Project can represent nested hierarchy.


---

## Step 2: Update Projects list UI to show hierarchy (sprint-friendly)
**Modify:** Projects panel inside Tasks list (where projects are shown)

Changes:
- Render projects as a tree (QTreeView) OR indented list.
- Show child projects under parents.
- Provide expand/collapse all actions (optional).

Also widen the projects block in the tasks list UI:
- Increase the left panel minimum width or splitter default sizes to accommodate hierarchy names.

**Acceptance check:**
- Nested subprojects are visible and navigable.
- Projects block is wider and names are not truncated excessively.


---

## Step 3: Ensure task filtering works with nested projects
Selecting a project filters tasks to that project.
Selecting a parent project includes tasks from subprojects too (if desired) OR provides a toggle.

**Acceptance check:**
- Filtering behaves consistently and is documented in code comments.
