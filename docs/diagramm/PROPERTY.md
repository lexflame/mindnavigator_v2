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
- `CsvTransferService.import_from_string` is a static parser helper and does not depend on instance state.
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
- Public restore contract: external callers (single-instance bridge, tray shell) use `MainWindow.restore_from_tray()` instead of direct protected access.

## Protected Member Bridge Properties
- Cross-component calls are exposed via stable public wrappers:
  - `MainWindow.snap_to_screen_edges(global_pos)`.
  - `ProjectsNav.handle_project_drop(...)` + `ProjectsNav.last_drop_error`.
  - `_ProjectsListWidget.log_dnd(message)`.
  - `MapCanvas.edit_marker(marker)` and `MapCanvas.open_attachment_view(kind, item_id)`.
  - `TasksItemDelegate.edit_task/open_task_view/row_layout/format_header`.
  - `NotesModel.is_loading()`.

## Hotkey Filter Properties
- `HotkeyEventFilter` uses Qt6 enum namespaces for key-event normalization:
  - `QEvent.Type.KeyPress` for filter gate;
  - `Qt.Key.*` for modifier/system-key skip list;
  - `QKeySequence.SequenceFormat.NativeText` for platform-native sequence text.
- Sequence normalization helper `_to_sequence` is static and side-effect free.
- `HotkeyManager` context-evaluation helpers (`_best_context_priority`, `_command_context_active`) are static and side-effect free.

## Projects DnD Properties
- `ProjectsNav` project list uses Qt6 role/action enums:
  - `Qt.ItemDataRole.UserRole` for row payloads;
  - `Qt.DropAction.MoveAction` for DnD action dispatch.
- Drop reject tooltip resolves point from `QDropEvent.globalPosition()` when available, with `QCursor.pos()` fallback for typed API compatibility.

## Cloud Folder Index Properties
- Navigation tree/grid layers (`AttachFileSelectNav`, `FileWorkspace`) treat folder-index buckets as guarded runtime collections:
  - `folders` is processed only when bucket value is `set[str]`;
  - `files` is processed only when bucket value is `list[CloudFileData]`.
- Guarded extraction avoids `object`-typed `sorted(...)` paths in static analysis while preserving runtime behavior.

## Window Resize/Native Event Properties
- `MainWindow.nativeEvent` compares platform event channel via normalized `event_name` text extracted from Qt payload (`QByteArray`/bytes-like or string).
- Resize edge processing uses explicit `ResizeEdge` flag comparisons (`!= ResizeEdge.NONE`) and diagonal edge sets for cursor mapping.
- Main-window runtime flags and key/mouse handling are bound to Qt6 enum namespaces:
  `Qt.WindowType.*`, `Qt.WidgetAttribute.*`, `Qt.WindowState.*`, `Qt.ApplicationState.*`, `Qt.Key.*`, `Qt.CursorShape.*`, `Qt.MouseButton.*`, `QEvent.Type.*`.
- Stateless helper methods are static (`_hotkey_defaults_path`, `_hotkey_overrides_path`, `_placeholder`, `_cursor_for_edge`).

## Single-Instance Bridge Properties
- In `_SingleInstanceBridge`, incoming local-socket payload is decoded from `QByteArray` using explicit `.data()` bytes extraction before UTF-8 parsing.

## Framed Dialog Patch Properties
- `enable_frameless_qdialogs` patched init path normalizes `(parent, flags)` from incoming args/kwargs and forwards to original `QDialog.__init__` without star-arg passthrough.

## Attach File Selector Properties
- `AttachFileSelectNav` uses Qt6 enum namespaces for selection payloads and icon scaling:
  `Qt.ItemDataRole.*`, `Qt.AlignmentFlag.*`, `Qt.ScrollBarPolicy.*`, `Qt.AspectRatioMode.*`, `Qt.TransformationMode.*`.

## Workspace State Properties
- `BaseWorkspace.restore_state` normalizes `QSettings.value(...)` results to string-safe values before:
  - assigning `search_text`;
  - JSON-decoding stored filter payload.

## Map Label Dialog Properties
- `MapLabelEditDialog` runtime/UI constants are aligned to Qt6 enum namespaces for static-analysis parity:
  `Qt.AlignmentFlag.*`, `Qt.CursorShape.*`, `Qt.TextInteractionFlag.*`, `QEvent.Type.*`, `Qt.ScrollBarPolicy.*`, `Qt.CaseSensitivity.*`, `Qt.MatchFlag.*`, `Qt.MouseButton.*`, `Qt.WindowState.*`, `Qt.AspectRatioMode.*`, `Qt.TransformationMode.*`, `QDialog.DialogCode.*`.

## Maps Workspace Properties
- `MapsWorkspace` and map-preview dialogs use Qt6 enum namespaces for map rendering/input surfaces:
  `Qt.WindowState.*`, `Qt.Key.*`, `Qt.AspectRatioMode.*`, `Qt.TransformationMode.*`, `Qt.BrushStyle.*`, `Qt.PenStyle.*`, `Qt.MouseButton.*`, `Qt.WidgetAttribute.*`, `Qt.ScrollBarPolicy.*`, `Qt.WindowType.*`.
- Map preview open behavior is unchanged: dialog enters fullscreen and renders the initial image immediately.

## Notes Workspace Properties
- `NoteWorkspace` list surface uses Qt6 UI policy enums:
  `Qt.ScrollBarPolicy.ScrollBarAlwaysOff` and `Qt.ContextMenuPolicy.CustomContextMenu`.
- `NotesModel.flags` uses Qt6 item-flag namespace (`Qt.ItemFlag.*`) for loading/category/data-row interaction states.

## Tasks Workspace Properties
- `TasksWorkspace` runtime/UI constants are aligned to Qt6 enum namespaces for list/model/input paths:
  `Qt.ItemFlag.*`, `Qt.Key.*`, `Qt.AspectRatioMode.*`, `Qt.TransformationMode.*`, `Qt.ScrollBarPolicy.*`, `Qt.WidgetAttribute.*`, `QEvent.Type.*`.

## Objects Workspace Properties
- `ObjectsModel.flags` uses Qt6 item-flag namespace (`Qt.ItemFlag.*`) for category/data-row interaction states.

## Ideas Workspace Properties
- `IdeasListModel` and ideas list view use Qt6 enum namespaces for row flags and list policies:
  `Qt.ItemFlag.*`, `Qt.ScrollBarPolicy.*`, `Qt.ContextMenuPolicy.*`.

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

## Shadowing Names Properties
- Lambda/local variables in UI callbacks and tree-build loops are named uniquely per scope (`target_task_id`, `project_row`, `child_node_id`, `item_title`, `category_row`, `cloud_file`) to avoid outer-scope shadowing.
- Renames are behavior-preserving: only symbol names were adjusted in sorting, rendering, and delayed-callback paths.
- Tasks workspace list-build closures and attachment-dialog source fill logic use explicit row-local names (`task_row`, `child_rows`, `root_task`, `selected_kind`, `note_row`, `file_row`) to avoid nested-scope collisions.

## Static Helper Properties
- Dialog/navigation/dragdrop/workspace helper methods that do not use instance state are explicitly static:
  `_resolve_screen`, `_build_folder_index`, `_dnd_log`, `_project_item_label`, `_task_entries`, `_map_entries`, `_marker_entries`, `_validate_project_relocation`, `_hash_file`, `_hash_from_path`, `_description_from_path`, `_is_image`, `_file_matches_project`, `_format_size`, `_copy_path`, `_format_description`, `_format_freshness`, `_normalize_key`.
- Tasks workspace static helpers include attachment/list formatting and mode mapping primitives:
  `_clear_layout`, `_cloud_file_link_text`, `_attachment_kind_label`, `_task_quick_rect`, `_is_overdue`, `_format_header`, `_format_completion_delay`, `_format_parent_schedule_text`, `_tab_from_mode`, `_estimate_task_minutes`.
- Notes/ideas delegates keep category paint helpers static (`_paint_category`), and ideas form selection helper `_set_combo_value` is static.
- Maps workspace static helpers include row/layout and formatting primitives:
  `_row_layout`, `_project_titles`, `_resize_handle_cursor`, `_resize_scale_delta`, `_load_marker_preview`, `_format_value`, `_format_links`, `_format_file_links`.
- Base workspace lifecycle stubs are static no-ops: `on_leave`, `teardown`.

## Type Checker Properties
- Main-window native event channel name is decoded from typed Qt payloads (`bytes` and `QByteArray`) before Win32 hotkey dispatch.
- Resize-edge cursor mapping is driven by normalized integer flag values to keep enum-flag comparisons type-safe.
- Task editor/date controls use explicit `QDate(year, month, day)` conversion from Python `date`.
- Task drag-drop id payload is decoded from `QByteArray.data()` bytes before integer parsing.
