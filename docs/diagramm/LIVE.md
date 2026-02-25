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

## Database Path Pipeline (Sprint 6)
- Input: `SettingsWorkspace._edit_database_storage`.
- Copy: `Database.backup_to(target_path)` performs consistent SQLite copy with WAL checkpoint.
- Persistence: `set_configured_db_path` stores selected DB path in external config (`~/.mindnavigator/app_config.json`).
- Startup resolution: `default_db_path` reads configured path and opens the selected database file.
- Runtime note: switching active DB requires app restart; UI shows pending switch status.

## Update Check Pipeline (Sprint 6)
- Input: `SettingsWorkspace._check_updates` (`Check update` button).
- DB update phase: `Database.apply_schema_updates` runs pending migrations and returns schema `user_version`.
- Version check phase: `UpdateService.check_for_update(APP_VERSION)` calls GitHub Releases API via `HttpClient`.
- Output: workspace status label + info dialog with either `latest` state or release link for available update.

## Workspace Visibility Pipeline (Sprint 6)
- Input: workspace checkboxes in `SettingsWorkspace`.
- Persistence: selected ids are serialized into `app.enabled_workspaces` via `Database.set_setting`.
- Runtime apply: `MainWindow._on_setting_changed` updates sidebar button visibility and navigation cycle.
- Guardrails: at least one workspace remains enabled; hidden modes are blocked by `MainWindow.set_mode` fallback.

## Language Pipeline (Sprint 6)
- Input: language combo in `SettingsWorkspace`.
- Persistence: selected code is stored as `app.language` via `Database.set_setting`.
- Runtime apply: `MainWindow._on_setting_changed` routes to `_apply_ui_language` and rebuilds mode label map from `mindnavigator/i18n.py`.
- Render impact: `LeftRail.set_mode_labels` updates tooltips; title/nav use translated mode caption in `MainWindow.set_mode`.

## CSV Transfer Pipeline (Sprint 6)
- Export input: list of row mappings from workspace/domain layer.
- Export transform: `CsvTransferService.export_to_string/export_to_file` normalizes values and writes header-based CSV.
- Import input: CSV text/file selected by user.
- Import transform: `CsvTransferService.import_from_string/import_from_file` returns normalized `list[dict[str, str]]` with header validation.
- Workspace entity adapter: `mindnavigator/workspaces/csv_workspace_transfer.py` maps storage dataclasses to CSV fieldsets and applies import reconciliation:
  - tasks/projects parent-child restoration by source id mapping;
  - project/category reference restoration by title/path mapping;
  - bool/int/date normalization with safe defaults and row-level skip accounting.
- UI trigger points: workspace header/topbar actions in `tasks/projects/notes/ideas/collections/objects` call adapter + service and refresh list models after import.

## Local Pytest Path Pipeline (Repo Ops)
- Local temp root: `.pytest_dir`.
- Compatibility aliases: `.pytest_tmp` -> `.pytest_dir/tmp`, `.pytest_run_tmp` -> `.pytest_dir/run_tmp`.
- Script entry points: `scripts/fix_pytest_permissions.bat`, `scripts/fix_pytest_user_temp_permissions.bat` (repo-root aware).

## Motion Pipeline (Sprint 6)
- Width expansion class: `WidthExpandAnimator` animates `minimumWidth` + `maximumWidth` with fast easing for deterministic panel growth/shrink.
- Dialog appearance class: `DialogAppearAnimator` applies `QGraphicsOpacityEffect` plus `geometry` translation animation (fade + slide-in).
- Config normalization: `WidthExpandAnimationConfig.normalized` and `DialogAppearAnimationConfig.normalized` clamp invalid durations/ranges before runtime usage.
- Global dialog application path: `enable_frameless_qdialogs` patches `QDialog.exec`; `_patched_exec` schedules `DialogAppearAnimator.play(...)` via `QTimer.singleShot(0, ...)` before entering modal loop.
- Sidebar hover flow: entering `LeftRail` expands overlay panel (`LeftRailHoverPanel`) via `WidthExpandAnimator`; leaving rail/panel schedules collapse with cursor-outside guard and hides panel after animation.

## Tray Reminder Click Pipeline (Sprint 6)
- Reminder emit: `MainWindow._check_task_reminders` binds currently shown reminder toast to `_tray_message_task_id` before `QSystemTrayIcon.showMessage(...)`.
- Click event: `QSystemTrayIcon.messageClicked` triggers `MainWindow._on_tray_message_clicked`.
- Restore phase: `_on_tray_message_clicked` always calls `_restore_from_tray`, then clears message binding.
- Navigation phase: when a bound task exists, `_open_task_from_tray_notification(task_id)` switches workspace mode to tasks and schedules `page_tasks.focus_task(task_id)` on next event-loop tick.
- Reveal phase: `TasksWorkspace.focus_task` attempts direct row lookup by `TaskRoles.TaskId`; if hidden by active filters, it relaxes to plan view, clears restrictive filters/search, then selects and centers the task row.

## Task Attachment Class Pipeline (Sprint 6)
- Input: attachment action in `TasksWorkspace` calls `Database.add_task_attachment(task_id, kind, ref_id)`.
- Normalization: `TaskAttachmentData.normalize_kind` validates/normalizes attachment kind (`note/object/map/marker/file/image/idea`).
- Persistence: `task_attachments` stores unique `(task_id, kind, ref_id)` with creation timestamp.
- Projection: `Database.fetch_task_attachments` maps rows through `TaskAttachmentData.from_row`.
- Serialization: class-level `from_dict` and instance `to_dict` provide stable payload representation for tests/import layers.
- Idea-link flow: task attachment dialogs load `ideas` via `fetch_ideas(archived=True)`, allow selecting an idea in add-dialog combo, and open idea metadata dialog on click.

## Maps Simple Mouse Pipeline (Sprint 6)
- Input: map canvas receives marker click/drag events in `MapCanvas.mousePressEvent` and `mouseMoveEvent`.
- Policy: `marker_drag_allowed(tool, simple_mouse_mode)` allows marker transfer only for non-simple select mode.
- Guardrail: when simple mouse mode is enabled, marker selection still works but `_dragging_marker_id` is not armed and resize-frame move drag is blocked.
- Result: accidental marker transfer is prevented while keeping marker view/edit actions available via existing context and dialogs.

## Notes Multiline Save Pipeline (Sprint 6)
- Input: editor text change in `NoteWorkspace._update_note_body`.
- Transform: `normalize_note_body` keeps multiline payload and normalizes line breaks to `\n`.
- Persistence: full note body is passed to `NotesModel.update_note` and stored via `Database.update_note`.
- Result: text after line breaks is preserved and reloaded correctly in note editor/list source data.

## Notes-Family Tasks-Like Pipeline (Sprint 6)
- Notes list:
  - Input: `NotesModel._rebuild` -> `group_notes_by_category`.
  - Projection: `NoteRoles.RowType` emits `category|note`; category rows are non-selectable.
  - Quick form: `_open_quick_category_menu` drives project navigation; `_create_note_from_quick_form` creates note in selected category.
- Ideas list:
  - Input: `IdeasWorkspace.refresh` -> `IdeasListModel.set_items` -> `group_ideas_by_category`.
  - Projection: `IdeaRoles.RowType` emits `category|idea`; delegate renders compact section headers.
  - Quick form: `_open_quick_status_menu` syncs with status filters; `_create_idea_from_quick_form` creates idea in selected status category.
- Objects list:
  - Input: `ObjectsModel._rebuild` -> `group_objects_by_category` (catalog root as category).
  - Projection: `ObjectRoles.RowType` emits `category|object`; list renders row-mode headers and rows.
  - Quick form: `_open_quick_catalog_menu` navigates catalog tree; `_create_object_from_quick_form` creates object in selected catalog.
- Collections list:
  - Input: `CollectionsWorkspace.refresh_collections` -> `group_collection_items_by_category`.
  - Projection: category header rows + entity rows with preview icons and domain-aware text via `format_collection_item_row`.
  - Quick form: `_open_quick_category_menu` navigates category tree; `_create_item_from_quick_form` creates category-bound collection items.

## Tasks Marker Immediate Refresh Pipeline (Sprint 6)
- Input: marker edit in `TaskEditDialog` (`marker_color`, `marker_theme`).
- Model update: `TasksModel.update_task_by_row` detects marker-only mutation via `is_marker_only_task_update`.
- UI refresh: marker-only path updates cached row and emits targeted `dataChanged` roles (`MarkerColor`, `MarkerTheme`) instead of full `beginResetModel/endResetModel`.
- Render: `TasksItemDelegate.paint` uses `blend_task_row_background` so marker tint remains visible even when the row stays selected after edit.
- Persistence contract: `Database.create_task` / `Database.update_task` now construct `TaskData` with keyword fields, preventing marker field shifts when gantt flags are present.
