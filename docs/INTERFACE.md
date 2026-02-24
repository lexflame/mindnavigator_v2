# INTERFACE Map

Purpose: UI composition map and extension points for sprint tasks.

## Main Window Shell
- File: `mindnavigator/main_window.py`.
- Root blocks: `TitleBar`, `LeftRail`, `ProjectsNav`, `SearchNav`, `workspace_stack`.
- Modes: Projects, Tasks, Purchases, Ideas, Collections, Maps, Notes, Files, Objects, Settings.
- Tray hooks: `_init_tray`, `_minimize_to_tray`, `_restore_from_tray`, `changeEvent`, `closeEvent`.

## Workspace Surface
- Tasks list UI: `mindnavigator/workspaces/tasks_workspace.py` (`TasksWorkspace`, `TasksItemDelegate`).
- Projects list UI: `mindnavigator/workspaces/projects_workspace.py` (`ProjectsWorkspace`, `ProjectsItemDelegate`).
- Project tree nav + DnD: `mindnavigator/ui/projects_nav.py`.
- App behavior settings UI: `mindnavigator/workspaces/settings_workspace.py`.

## Fast Action Anchors (current)
- Projects area/project row menu: `_show_area_menu`, `_show_row_menu` in `projects_workspace.py`.
- Tasks row menu: `_show_row_menu` in `tasks_workspace.py`.
- Row interaction events: `ProjectsItemDelegate.editorEvent`, `TasksItemDelegate.editorEvent`.

## Sprint Part 1 Targets
- 1.3: add hover quick action `+ | Project` on area rows in projects list delegate.
- 1.4: add hover quick action `+ | Subproject` on project rows in projects list delegate.
- 1.5: add hover quick action `+ | Subtask` on task rows in tasks list delegate.
- 1.6: add hover quick action `+ | Task` on day separator rows in tasks list delegate.
- 1.7: increase width for project path text region in tasks list row layout.
- 1.8-1.10: extend settings UI and wire behavior in `main_window.py` and startup path.
