# PROPERTY Map

Purpose: entity property map and UI role map.

## Storage Dataclasses
- Source file: `mindnavigator/storage.py`.
- Main entities: `TaskData`, `ProjectData`, `MapData`, `MapMarkerData`, `NoteData`, `ObjectData`, `CollectionItemData`, `Shop*Data`, `Wishlist*Data`.
- Task properties include hierarchy and planning fields (`parent_id`, recurrence, gantt).
- Project properties include hierarchy and linkage fields (`parent_project_id`, linked map/note/object, `sort_order`).

## Settings Keys (current)
- `cloud_storage_path`
- `backup_dir`
- `backup_include_cloud`
- `backup_auto_enabled`
- `backup_frequency`
- `backup_retention`
- `backup_last_run`
- `app.enabled_workspaces` (JSON list of visible sidebar modes)
- `app.language` (selected UI language code: `ru|en|de|fr|zh`)
- external app config key: `db_path` in `~/.mindnavigator/app_config.json`

## UI Role Sets
- `TaskRoles`: task/day/header rendering roles in tasks list.
- `ProjectRoles`: project/header/tree rendering roles in projects list.
- `MapRoles`, `ObjectRoles`, `NoteRoles`: workspace-specific role sets.

## Storage Path Properties
- Active DB path: `Database.path` (resolved during startup by `default_db_path`).
- Configured DB path override: `get_configured_db_path` / `set_configured_db_path`.
- DB singleton lifecycle: `get_database` / `reset_database`.
- `reset_database` closes only an existing cached singleton instance and suppresses only `sqlite3.Error` from `close()` before cache reset.

## Update Properties
- `APP_VERSION` in `mindnavigator/constants.py` is used as current application version for update checks.
- `UPDATE_REPOSITORY_OWNER` and `UPDATE_REPOSITORY_NAME` define GitHub repository source for release lookup.

## i18n Properties
- Source: `mindnavigator/i18n.py`.
- Language catalog: `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`.
- Mode label transform: `get_mode_labels(language_code)` maps shell mode keys to translated captions.

## CSV Transfer Properties
- Source: `mindnavigator/csv_transfer.py`.
- Runtime options: `CsvTransferOptions(delimiter, quotechar, encoding)`.
- File path input contract: `CsvTransferService.import_from_file` / `export_to_file` accept both `Path` and `str` paths from UI file dialogs.
- Import contract: CSV must contain header row; importer returns string-valued column map per row.
- Workspace adapter source: `mindnavigator/workspaces/csv_workspace_transfer.py`.
- CSV field contracts:
  - `TASKS_CSV_FIELDS` includes hierarchy columns (`id`, `parent_id`) and task properties.
  - `PROJECTS_CSV_FIELDS` includes hierarchy columns (`id`, `parent_project_id`) and project linkage fields.
  - `NOTES_CSV_FIELDS`, `IDEAS_CSV_FIELDS`, `OBJECTS_CSV_FIELDS`, `COLLECTIONS_CSV_FIELDS` define stable workspace import/export schemas.
- Import result contract: `CsvImportResult(imported, skipped)` is used by workspace UI status dialogs.

## Repository Ops Layout
- Unified codex config root: `codex_conf` is linked to `.codex` (legacy snapshot preserved in `codex_conf_legacy`).
- Local pytest paths are centralized in `.pytest_dir` (`tmp`, `run_tmp`, `user_tmp`), with compatibility links from `.pytest_tmp` and `.pytest_run_tmp`.
- Catalog folder `defenition` stores canonical `artifacts`, `build`, `defaults`, `dist`, `tests` directories.
- Root compatibility layer maps legacy paths `artifacts`, `build`, `defaults`, `dist`, `tests` to `defenition/*` via Windows junctions (no data duplication).
- Pytest runtime compatibility is fixed in root `pytest.ini` (`pythonpath = .`, `testpaths = tests`) to keep `pytest tests ...` commands stable.

## Animation Properties
- Source: `mindnavigator/ui/animations.py`.
- Width animation config: `collapsed_width`, `expanded_width`, `duration_ms`, `easing`.
- Dialog animation config: `duration_ms`, `offset_px`, `start_opacity`, `end_opacity`, `easing`.
- Normalization guards: invalid widths/durations/opacities are clamped by `normalize_width_bounds`, `normalize_duration_ms`, and config `.normalized()`.
- Dialog runtime opt-out property: `disable_dialog_appear_animation` (checked in `frameless_patch` before scheduling animation).
- Sidebar hover panel properties (`LeftRail`):
  - `HOVER_PANEL_WIDTH`, `HOVER_ANIMATION_MS`, collapsed width guard (`1px`).
  - host binding via `set_expand_host(body)` in `MainWindow` for overlay rendering above nav/workspace columns.

## DragDrop Callback Safety
- `DragDropController` dispatches optional callbacks (`on_drag_started`, `on_drop_requested`, `on_drop_committed`) via `callable(...)` guards.
- Release-path payload is stabilized in a local variable before callback/executor calls to avoid nullable-flow ambiguities in static analysis.

## Tray Reminder Properties
- `MainWindow._tray_message_task_id`: transient binding of currently displayed tray toast to task id for click-to-open routing.
- Reset points:
  - set to `None` for non-task tray notifications (for example minimize-to-tray notice);
  - consumed and cleared in `_on_tray_message_clicked`.
- Task reveal contract: `TasksWorkspace.focus_task(task_id) -> bool` returns whether target task row was found and focused.

## Hotkey Filter Properties
- `HotkeyEventFilter` uses Qt6 enum namespaces for key-event normalization:
  - `QEvent.Type.KeyPress` for filter gate;
  - `Qt.Key.*` for modifier/system-key skip list;
  - `QKeySequence.SequenceFormat.NativeText` for platform-native sequence text.

## Projects DnD Properties
- `ProjectsNav` project list uses Qt6 role/action enums:
  - `Qt.ItemDataRole.UserRole` for row payloads;
  - `Qt.DropAction.MoveAction` for DnD action dispatch.
- Drop reject tooltip resolves point from `QDropEvent.globalPosition()` when available, with `QCursor.pos()` fallback for typed API compatibility.

## Task Attachment Properties
- Value object: `TaskAttachmentData(id, task_id, kind, ref_id, created_at)`.
- Supported kinds (`TaskAttachmentData.SUPPORTED_KINDS`): `note`, `object`, `map`, `marker`, `file`, `image`, `idea`.
- Normalization/validation: `TaskAttachmentData.normalize_kind(kind)` enforces allowed attachment kinds.
- Serialization contract:
  - `TaskAttachmentData.from_dict(payload)` for payload hydration;
  - `TaskAttachmentData.to_dict()` for stable dict export.
- UI label mapping: `ATTACHMENT_KIND_LABELS` in `tasks_workspace` includes `idea -> "Идея"` for summary chips and rows.

## Maps Mouse Properties
- `MapCanvas._simple_mouse_mode`: simple mouse interaction state for maps canvas.
- Drag policy function: `marker_drag_allowed(tool, simple_mouse_mode)`; marker transfer by drag is disabled when simple mode is active.

## Notes Body Properties
- Normalizer: `normalize_note_body(text)` in `notes_workspace` converts CRLF/CR to LF and preserves multiline content.
- Save behavior: note body is no longer truncated to first line during editor-driven autosave/update path.

## Notes-Family List Properties
- Row type roles:
  - `NoteRoles.RowType`: `category|note|skeleton`.
  - `IdeaRoles.RowType`: `category|idea`.
  - `ObjectRoles.RowType`: `category|object`.
- Category grouping helpers:
  - notes: `normalize_note_category`, `group_notes_by_category`.
  - ideas: `normalize_idea_category`, `group_ideas_by_category`.
  - objects: `normalize_object_category`, `group_objects_by_category`.
  - collections: `normalize_collection_category_title`, `group_collection_items_by_category`.
- Quick-form selection properties:
  - notes: `quick_category` on `quick_category_label`.
  - ideas: `quick_status` on `quick_status_label`.
  - objects: `quick_catalog` on `quick_catalog_label`.
  - collections: `quick_category_id` on `quick_category_label`.
- Collections row formatter: `format_collection_item_row` composes row text from title + entity type + category + topic + source marker.

## Tasks Marker Refresh Properties
- Role payloads: `TaskRoles.MarkerColor`, `TaskRoles.MarkerTheme` are emitted in targeted `dataChanged` for marker-only edits.
- Marker-only predicate: `is_marker_only_task_update(previous, updated)` gates fast UI refresh path in `TasksModel`.
- Selected row paint: `blend_task_row_background(base, marker_color, selected)` keeps marker tint visible for selected task rows.
- Storage projection safety: `TaskData` return mapping in `Database.create_task`/`Database.update_task` is keyword-based to preserve `gantt_forecasted`, `marker_color`, and `marker_theme` positions.
