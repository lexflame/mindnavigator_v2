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
  - cloud storage path editor;
  - database storage path editor with copy-to-target and restart requirement;
  - backup policy controls;
  - language selector (`app.language`) with immediate shell relabeling.

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

## Sprint 6 Anchors
- DB storage location: `SettingsWorkspace._edit_database_storage`, `SettingsWorkspace._open_database_storage`.
- Update check action: `SettingsWorkspace._check_updates` (`Check update` button in database settings row).
- Update check integration point: `mindnavigator/update_service.py`.
- Workspace visibility selection: `SettingsWorkspace._on_workspace_visibility_changed` + `MainWindow._apply_workspace_visibility`.
- Language selector: `SettingsWorkspace._on_language_changed` + `MainWindow._apply_ui_language` + `LeftRail.set_mode_labels`.
- CSV transfer service anchor: `mindnavigator/csv_transfer.py` (`CsvTransferService` for workspace import/export wiring).
- Workspace CSV transfer adapter: `mindnavigator/workspaces/csv_workspace_transfer.py` (entity field maps + import reconciliation).
- Workspace export/import UI anchors:
  - `TasksWorkspace.create_actions`, `_export_tasks_csv`, `_import_tasks_csv`.
  - `ProjectsWorkspace._export_projects_csv`, `_import_projects_csv` (`btn_export`, `btn_import` in topbar).
  - `NoteWorkspace._export_notes_csv`, `_import_notes_csv` (`btn_export`, `btn_import` in header).
  - `IdeasWorkspace.create_actions`, `_export_ideas_csv`, `_import_ideas_csv`.
  - `CollectionsWorkspace._export_collections_csv`, `_import_collections_csv` (`export_button`, `import_button` in header).
  - `ObjectWorkspace._export_objects_csv`, `_import_objects_csv` (`export_button`, `import_button` in header).
- Animation class anchors:
  - `mindnavigator/ui/animations.py::WidthExpandAnimator` (fast panel width expansion for hover/focus transitions).
  - `mindnavigator/ui/animations.py::DialogAppearAnimator` (fade + slide-in animation API for dialog opening).
  - global apply hook: `mindnavigator/ui/dialogs/frameless_patch.py::_patched_exec` schedules dialog-appear animation for all non-system dialogs.
- Sidebar hover-expand anchor:
  - `mindnavigator/ui/leftrail.py::LeftRail` uses `set_expand_host` + hover overlay panel with animated width to reveal mode names over content.
- Tray reminder click anchor:
  - `MainWindow._init_tray` binds `QSystemTrayIcon.messageClicked` to `_on_tray_message_clicked`.
  - `MainWindow._open_task_from_tray_notification` switches to tasks mode and delegates reveal to `TasksWorkspace.focus_task`.
  - `TasksWorkspace.focus_task(task_id)` selects, centers, and focuses task row by id (with filter relaxation fallback).
- Protected-call bridge anchor:
  - cross-widget calls are routed via public wrappers to avoid protected-member coupling:
    `MainWindow.restore_from_tray`, `MainWindow.snap_to_screen_edges`, `ProjectsNav.handle_project_drop`, `ProjectsNav.last_drop_error`,
    `MapCanvas.edit_marker`, `MapCanvas.open_attachment_view`, `TasksItemDelegate.edit_task/open_task_view/row_layout/format_header`, `NotesModel.is_loading`.
- Attachment class anchor:
  - `TaskAttachmentData` in `mindnavigator/storage.py` is the domain attachment value object for task links.
  - `Database.add_task_attachment` uses `TaskAttachmentData.normalize_kind` and returns class instances mapped via `TaskAttachmentData.from_row`.
  - `TasksWorkspace` attachment UI consumes these instances for create/open/remove flows.
  - attachment picker in task dialogs includes `idea` entity type and uses `fetch_ideas(archived=True)` for source options.
- Maps simple-mouse anchor:
  - `MapCanvas` applies drag policy through `marker_drag_allowed(tool, simple_mouse_mode)`.
  - in simple mouse mode marker selection is preserved but marker transfer by drag is blocked.
- Notes multiline save anchor:
  - `NoteWorkspace._update_note_body` now passes full editor text through `normalize_note_body` without first-line truncation.
  - note editor to model path preserves multiline content end-to-end.
- Notes-family tasks-like workflow anchor (`TASK_329B82A5...`):
  - notes: category-separated list rows via `NoteRoles.RowType` (`category|note`) and quick top form (`_open_quick_category_menu`, `_create_note_from_quick_form`).
  - ideas: status-category separators via `IdeaRoles.RowType` (`category|idea`) and quick top form (`_open_quick_status_menu`, `_create_idea_from_quick_form`).
  - objects: catalog-category separators via `ObjectRoles.RowType` (`category|object`) and quick top form (`_open_quick_catalog_menu`, `_create_object_from_quick_form`).
  - collections: grouped list by collection category (`group_collection_items_by_category`) and quick top form (`_open_quick_category_menu`, `_create_item_from_quick_form`).
  - collections row surface now includes preview icon + domain-aware row text (`format_collection_item_row`).
- Tasks marker immediate-refresh anchor:
  - `TasksModel.update_task_by_row` applies marker-only updates through `dataChanged` without full list reset.
  - marker list tint remains visible for selected rows through `blend_task_row_background`.
  - `TasksItemDelegate._draw_marker_theme_overlay` paints marker-theme art as a full-row background layer with low opacity, leaving row controls and text visually dominant.
  - storage side uses keyword-based `TaskData` mapping in `Database.create_task`/`Database.update_task` to keep `marker_color` and `marker_theme` aligned.
- Repo ops anchors: `scripts/fix_pytest_permissions.bat`, `scripts/fix_pytest_user_temp_permissions.bat`, and `defenition/*` junction catalog.
