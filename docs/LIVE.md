# LIVE Property Transform Map

Purpose: map how properties flow through UI, validation, persistence, and rendering.

## Task Pipeline
- Input: `TasksWorkspace._on_create_task`, `TaskEditDialog.values`.
- Validation: `validate_title`, `validate_time_text`, `normalize_priority` (`storage.py`).
- Persistence: `Database.create_task`, `Database.update_task`.
- Projection: `Database.fetch_tasks` -> `TasksModel._reload_from_db` -> `TaskRow`.
- Render: `TasksItemDelegate.paint` + `TaskRoles`.

## Project Pipeline
- Input: `ProjectsWorkspace._on_create_project`, `ProjectEditDialog.values`.
- Validation: `validate_area`, `validate_title`, `normalize_priority`.
- Persistence: `Database.create_project`, `Database.update_project`, `Database.move_project`.
- Projection: `Database.fetch_projects` -> `ProjectsModel._reload_from_db` -> `ProjectRow`.
- Render: `ProjectsItemDelegate.paint` + `ProjectRoles`.

## Subtask and Hierarchy (for 1.2)
- Mutation points: tasks DnD/policy handlers in tasks workspace + dragdrop package.
- Required transform: when task becomes subtask, set `project_id` to top parent project.

## Marker/Highlight Extension (for 1.1)
- Extend storage model (`TaskData`/`ProjectData`) with marker metadata (color/theme key).
- Extend dialogs/edit forms to edit marker metadata.
- Extend list delegates to render highlight backgrounds or themed userbar assets.
- Store only stable keys/paths, not binary image payloads.

## App Behavior Settings (for 1.8-1.10)
- Storage: new `settings` keys via `Database.get_setting/set_setting`.
- Runtime hooks: `MainWindow.changeEvent`, `MainWindow.closeEvent`, startup in `__main__.py`.
- Single instance: startup guard + restore signal to existing tray instance.
- Windows autostart: helper module for Startup registry or shortcut.
