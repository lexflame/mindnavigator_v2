# DnD Notes: TASK_7E3A9B4D-0C11-4F8E-9D2F-6A1B8C3E5D20

## Title
Drag&Drop interaction for projects.

## Implemented
1. Drag/drop list behavior:
- Added custom list widget `_ProjectsListWidget` for `ProjectsNav`.
- Enabled project drag/drop mode and drop indicators.
- Drop handling is validated via owner callback instead of blind UI reorder.

2. Drop actions:
- Drop to empty area: move project to root tail.
- Drop on project with deep horizontal offset: move as child (`reparent`).
- Drop on project with normal offset: reorder in target sibling group.

3. Data operations:
- DnD routes to storage domain APIs (`move_project`, `fetch_project_children`).
- Selection is restored to moved project after refresh.
- Invalid DnD actions (cycles, missing target, validation errors) are rejected.

## Validation
1. `python -m compileall mindnavigator/ui/projects_nav.py` passed.
