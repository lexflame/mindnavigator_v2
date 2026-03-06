# PARITY Backlog

## Purpose
This file stores parity tasks that must be executed at the end of the sprint.
It also stores:
- tasks not completed within the sprint scope;
- tasks not solved during implementation;
- application improvement tasks.

## Rules
1. Every entry must have a `TASK_GUID`.
2. Commit prefix for parity tasks: `parity::// TASK_GUID`.
3. Status values: `Planned`, `In Progress`, `Done`, `Skipped`.
4. Each task must include clear acceptance criteria.

## Tasks

### TASK_5D95A5AE-2E6D-4A7B-9C4E-8F4C4E7A3B12
- Type: parity
- Title: Register Sprint 5 debug summary and environment constraint
- Sprint: 5
- Status: Done
- Why:
  Sprint 5 summary was created in `docs/sprints/5_SPRINT.md` and must be explicitly linked from parity tracking for end-of-sprint visibility.
- Scope:
  - add parity record with link to sprint summary;
  - capture test environment limitation (`pytest tmpdir` ACL cleanup issue on current machine).
- Acceptance criteria:
  - parity entry exists and references `docs/sprints/5_SPRINT.md`;
  - environment constraint is documented with current fallback test command.
- Result:
  - sprint summary file added: `docs/sprints/5_SPRINT.md`;
  - validated fallback test command in this environment:
    `PYTHONPATH=. pytest tests -q -p no:cacheprovider -p no:tmpdir -k "not test_persistence_round_trip"`
    with result `37 passed, 1 deselected`.

### TASK_3EE8F658-4E55-4A52-A2A7-6A7ACCB1D0F0
- Type: parity
- Title: Review unexpected file `.codex/manual/ERROR_GIT/git_runner.txt`
- Sprint: 1
- Status: Done
- Why:
  Unexpected file appeared during sprint execution and was not created intentionally in task flow.
- Scope:
  - determine origin of the file;
  - classify as needed artifact or accidental debug output;
  - decide keep/remove/ignore policy;
  - align git ignore rules if needed.
- Acceptance criteria:
  - file origin is documented;
  - clear decision is made (`keep`/`remove`/`ignore`);
  - repository state is consistent with decision.
- Result:
  - origin identified: file added by commit `4636c8d` (`CODEX ADDON FILE`);
  - classification: accidental debug output (CI lint error log), not product artifact;
  - decision: `remove` from repository and `ignore` path `.codex/manual/ERROR_GIT/`.

### TASK_CE3BF9F0-A286-4ED6-BD37-B250D90ECEDB
- Type: parity
- Title: Restore local automated test runner (`pytest`) in active Python environment
- Sprint: 1
- Status: Done
- Why:
  Multiple sprint tasks include tests, but runtime execution is blocked by missing dependency (`No module named pytest`).
- Scope:
  - install/enable `pytest` in active interpreter;
  - run dragdrop test suite end-to-end;
  - capture failures (if any) and create follow-up fix tasks.
- Acceptance criteria:
  - `python -m pytest tests/test_dragdrop_*.py -q` runs;
  - test execution report is recorded in `.codex/HISTORY_ACTION.md`;
  - any failing tests are tracked with new TASK_GUID entries.
- Result:
  - `pytest` installed (`pytest 9.0.2`);
  - dragdrop suite executed with `-p no:cacheprovider`;
  - discovered and fixed one regression in `tests/test_dragdrop_controller.py` related to frame throttling.

### TASK_5743A7F2-2D90-41A8-9D25-663435E0B526
- Type: parity
- Title: Fix throttling-related regression in clamp motion test
- Sprint: 1
- Status: Done
- Why:
  `test_controller_motion_clamps_max_step` failed after performance throttling was added.
- Scope:
  - make test deterministic under throttling;
  - rerun dragdrop suite.
- Acceptance criteria:
  - regression test passes;
  - full dragdrop suite passes.
- Result:
  - updated test to use `DragPerformanceConfig(min_render_interval_ms=0)`;
  - dragdrop suite: `23 passed`.

### TASK_1FA90F88-2294-4074-88E2-75C3769E6768
- Type: parity
- Title: Keep `PARITY` and diagram maps in sync during Sprint 6 delivery
- Sprint: 6
- Status: Done
- Why:
  Sprint execution requires continuous doc sync for parity scope and architecture maps.
- Scope:
  - append parity notes for each completed sprint task where cross-cutting changes are made;
  - update `docs/diagramm/*.md` when data flow, class map, or interface wiring changes.
- Acceptance criteria:
  - each completed Sprint 6 task has traceable parity/diagram updates where applicable;
  - diagram docs include new migration/update/db-path modules and flows.
- Result (current iteration):
  - updated `docs/diagramm/CLASS.md` with `db_migrations` and `update_service`;
  - updated `docs/diagramm/INTERFACE.md`, `LIVE.md`, `PROPERTY.md` for DB path flow and settings surface.
  - synced diagram maps for `Check update` action flow and constants-based repository/version properties.
  - synced diagram maps for workspace visibility flow (`app.enabled_workspaces`, sidebar runtime apply).
  - synced diagram maps for language setting flow (`app.language`, runtime relabeling in `MainWindow` and `LeftRail`).
  - synced diagram maps for CSV transfer service module and data pipeline (`mindnavigator/csv_transfer.py`).
  - synced repository operational layout: `codex_conf` unified with `.codex`, pytest local temp moved to `.pytest_dir`, `defenition/` receives catalog links for `artifacts/build/defaults/dist/tests`.
  - restored runtime/build/test backward compatibility after physical `defenition/*` move by creating root junctions: `artifacts`, `build`, `defaults`, `dist`, `tests` -> `defenition/*` (no data copy/rollback).
  - added root `pytest.ini` (`pythonpath = .`, `testpaths = tests`) so legacy `pytest tests ...` commands continue working with the new junction-based tests layout.
  - completed workspace-level CSV import/export wiring for `tasks`, `projects`, `notes`, `ideas`, `collections`, `objects` with top-right buttons and file dialogs.
  - added shared transfer layer `mindnavigator/workspaces/csv_workspace_transfer.py` and new tests `tests/test_workspace_csv_transfer.py`.
  - fixed SQL ambiguity in `Database.create_task` (`p.linked_map_id`, `p.linked_note_id`, `p.linked_object_id`) discovered during CSV task import validation.
  - added animation module `mindnavigator/ui/animations.py` with `WidthExpandAnimator` and `DialogAppearAnimator` classes (+ config normalizers).
  - added tests `tests/test_animations.py` for animation config normalization and guardrails.
  - applied dialog appearance animation globally through `mindnavigator/ui/dialogs/frameless_patch.py` (`QDialog.exec` patch path), covering modal dialogs opened by both helper wrappers and direct `dialog.exec()` calls.
  - implemented sidebar hover-expansion overlay in `LeftRail`: animated width panel with mode names shown over neighboring content columns (without layout reflow of main workspace stack).
  - implemented tray-notification click navigation for task reminders: `MainWindow` now restores from tray on message click and routes to `TasksWorkspace.focus_task(task_id)` for direct task reveal.
  - added tests `tests/test_tray_task_navigation.py` for reminder-notification click flow (`restore` + task routing) and timer-scheduled task focus dispatch.
  - implemented attachment domain class behavior in `TaskAttachmentData`: kind normalization, row/dict deserialization, and dict serialization.
  - updated `Database` task-attachment CRUD to use class-based normalization/mapping (`from_row`, `normalize_kind`) and strict id validation.
  - added `tests/test_task_attachment_class.py` covering attachment class serialization + storage CRUD and validation paths.
  - extended task attachments with `idea` support across task dialogs: type label, source loading (`fetch_ideas`), add-attachment picker, display text, and open-details view.
  - added regression coverage for idea attachments in tasks: `test_task_attachment_supports_idea_entities`.
  - implemented maps simple-mouse guardrail: marker dragging is blocked in simple mouse mode (`MapTool.SELECT` with simple mode enabled).
  - added regression tests for drag-allowance policy in maps mode: `tests/test_maps_simple_mouse_mode.py`.
  - fixed notes multiline save path: removed first-line truncation in note body sync and preserved full multiline text.
  - added regression tests `tests/test_notes_multiline_save.py` for body normalization and DB persistence after line breaks.
  - implemented immediate task-list marker refresh path: `TasksModel.update_task_by_row` now emits targeted `dataChanged` for marker-only edits without full model reset.
  - fixed storage mapping defect for task marker fields by switching `TaskData` returns in `create_task`/`update_task` to keyword arguments (prevents marker field shift after `gantt_forecasted`).
  - added regression tests `tests/test_tasks_marker_refresh.py` for marker-only update detection, selected-row marker tint blending, and marker role update emission.
  - completed notes-family workflow rework (`TASK_329B82A5...`): notes/ideas/objects/collections lists now use category separators and top quick forms for navigation + entity creation.
  - collections list rows now keep preview icons and use domain-aware row text formatter (`format_collection_item_row`); grouped rendering is driven by category helpers.
  - added regression tests `tests/test_workspace_category_layout.py` for notes/ideas/objects/collections category grouping and row formatting helpers.
  - started `TASK_6BFC8077...` static-analysis pass with per-type commit strategy; fixed `PyUnboundLocalVariableInspection` warning in `purchases_workspace` (`json` import scope).
  - fixed `PyRedundantParenthesesInspection` warnings in `projects_nav` and `tasks_workspace` (tuple returns in sort keys), validated via compile + targeted task/project tests.
  - fixed `PyUnusedImportsInspection` warnings in smooth-scroll/maps/notes/settings modules by cleaning unused Qt/dataclass imports; validated via compile + focused workspace tests.
  - fixed `PyPep8NamingInspection` warnings by renaming non-lowercase method arguments (`supportedActions`/`eventType`) to PEP8-compliant names.
  - fixed `PyPackageRequirementsInspection` by declaring `shiboken6` in `requirements.txt` for explicit dependency parity with maps workspace imports.
  - fixed `PyBroadExceptionInspection` by narrowing broad catches in tray/hotkey paths, DnD logging, and Wildberries parser fallback flow.
  - fixed remaining `PyBroadExceptionInspection` in `storage.reset_database`: now closes cached singleton only when present and ignores only `sqlite3.Error` on close.
  - fixed `PyTypeHintsInspection` warnings by importing `QIcon` for dialog annotations and replacing `callable` with `Callable[[], bool]` in purchases parser worker signatures.
  - fixed `PyCallingNonCallableInspection` in dragdrop controller by switching callback dispatch to explicit `callable(...)` guards and stable local payload binding.
  - started `PyUnresolvedReferencesInspection` cleanup from hotkeys layer: migrated `hotkeys/event_filter.py` to Qt6 enum namespaces (`QEvent.Type`, `Qt.Key`, `QKeySequence.SequenceFormat`).
  - fixed `PyTypeCheckerInspection` for CSV workspace flows by widening `CsvTransferService.import/export_to_file` path signatures to `Path | str` (Qt file dialogs return `str`).
  - fixed `PyTypeCheckerInspection`/Qt6 enum warnings in `ui/projects_nav.py`: migrated drag/drop/item roles to Qt6 namespaces and hardened drop-tooltip position resolution for typed drop events.
  - fixed `PyTypeCheckerInspection` in cloud-file navigation (`attach_file_select_nav`, `files_workspace`) by adding explicit runtime type guards for `folders/files` buckets before `sorted(...)`.
  - fixed `PyTypeCheckerInspection` in `main_window.py`: normalized `nativeEvent` type matching through decoded `event_name` and replaced ambiguous `ResizeEdge` checks with explicit flag comparisons/diagonal sets.
  - continued `PyUnresolvedReferencesInspection` cleanup in `main_window.py`: switched legacy Qt constants to Qt6 enums (`WindowType`, `WidgetAttribute`, `WindowState`, `ApplicationState`, `Key`, `CursorShape`, `MouseButton`, `QEvent.Type`).
  - fixed `PyTypeCheckerInspection` in single-instance bridge (`__main__.py`) by decoding `QLocalSocket.readAll()` via explicit QByteArray `.data()` bytes conversion.
  - fixed `PyTypeCheckerInspection` in `ui/workspaces/base_workspace.py`: normalized `QSettings.value(...)` reads to guaranteed `str` before JSON decode and query restore.
  - continued `PyUnresolvedReferencesInspection` cleanup in `ui/dialogs/map_label_edit_dialog.py`: migrated legacy Qt constants to Qt6 enum namespaces (`AlignmentFlag`, `CursorShape`, `TextInteractionFlag`, `QEvent.Type`, `ScrollBarPolicy`, `CaseSensitivity`, `MatchFlag`, `MouseButton`, `WindowState`, `AspectRatioMode`, `TransformationMode`, `QDialog.DialogCode`).
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/maps_workspace.py`: migrated remaining legacy Qt constants (`WindowState`, `Key`, `AspectRatioMode`, `TransformationMode`, `BrushStyle`, `PenStyle`, `MouseButton`, `WidgetAttribute`, `ScrollBarPolicy`, `WindowType`) to Qt6 enums.
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/notes_workspace.py`: migrated list view policy/constants to Qt6 enums (`Qt.ScrollBarPolicy`, `Qt.ContextMenuPolicy`).
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/tasks_workspace.py`: migrated remaining legacy Qt constants to Qt6 enums (`Qt.ItemFlag`, `Qt.Key`, `Qt.AspectRatioMode`, `Qt.TransformationMode`, `Qt.ScrollBarPolicy`, `Qt.WidgetAttribute`, `QEvent.Type`).
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/objects_workspace.py`: migrated list-model row flags to Qt6 enum namespace (`Qt.ItemFlag.*`).
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/ideas_workspace.py`: migrated list/model/context-menu constants to Qt6 enums (`Qt.ItemFlag`, `Qt.ScrollBarPolicy`, `Qt.ContextMenuPolicy`).
  - fixed `PyArgumentListInspection` in `ui/dialogs/frameless_patch.py`: replaced star-arg forwarding into original `QDialog.__init__` with explicit parent/flags normalization and direct call signatures.
  - continued `PyUnresolvedReferencesInspection` cleanup in `ui/dialogs/attach_file_select_nav.py`: migrated dialog/tree/list constants to Qt6 enums (`Qt.AlignmentFlag`, `Qt.ScrollBarPolicy`, `Qt.ItemDataRole`, `Qt.AspectRatioMode`, `Qt.TransformationMode`).
  - continued `PyUnresolvedReferencesInspection` cleanup in `workspaces/notes_workspace.py`: migrated model row flags to Qt6 `Qt.ItemFlag.*`.
  - fixed `PyArgumentListInspection` warnings by normalizing `QShortcut` call signatures, replacing tuple-unpack `setRange` call with explicit min/max values, and tightening patched `QDialog.exec` signature forwarding.
  - fixed `PyUnusedLocalInspection` warnings by removing unused temp variables/args in modal + project-nav + dragdrop + purchase dialog paths and simplifying task attachment item-fill loops.
  - fixed `PyAttributeOutsideInitInspection` by predeclaring runtime UI attributes in `TasksWorkspace.__init__` and setting startup `_current_mode` in `MainWindow`.
  - fixed `HttpUrlsUsage` warning in purchase URL parser by validating scheme via `urlparse` (`http`/`https`) instead of hardcoded `http://` literal checks.
  - fixed `PyProtectedMemberInspection` by introducing public bridge methods and wrappers for cross-component calls (`MainWindow.restore_from_tray`, `MainWindow.snap_to_screen_edges`, `ProjectsNav.handle_project_drop`, `ProjectsNav.last_drop_error`, `MapCanvas.edit_marker`, `MapCanvas.open_attachment_view`, delegate/model safe accessors).
  - validated protected-member cleanup with focused compile + regression suite (`tests/test_tray_task_navigation.py`, `tests/test_maps_simple_mouse_mode.py`, `tests/test_notes_multiline_save.py`, `tests/test_tasks_marker_refresh.py`, `tests/test_workspace_category_layout.py`, `tests/test_project_tree_storage.py`): `19 passed`.
  - fixed `GrazieInspection` in `workspaces/maps_workspace.py` by normalizing fullscreen-preview comment wording (no runtime behavior changes).
  - validated grammar-fix safety with targeted compile and map regression tests (`tests/test_maps_simple_mouse_mode.py`): `2 passed`.
  - started `PyMethodMayBeStaticInspection` cleanup by converting self-free helper methods to `@staticmethod` in `csv_transfer`, `hotkeys/event_filter`, `main_window`, and `storage` (`_normalize_collection_entity_type`).
  - validated staticmethod batch with compile + focused regression suite (`tests/test_csv_transfer.py`, `tests/test_workspace_csv_transfer.py`, `tests/test_workspace_visibility_settings.py`, `tests/test_tray_task_navigation.py`, `tests/test_project_tree_storage.py`): `19 passed`.
  - continued `PyShadowingNamesInspection` cleanup (batch-1): renamed shadowing locals/lambda args in tray routing, project tree validation, category dialogs, file/cloud sorting, maps links/tabs, and purchase/object workspace helpers.
  - validated shadowing batch with targeted compile and regression suite (`tests/test_maps_simple_mouse_mode.py`, `tests/test_tray_task_navigation.py`, `tests/test_project_tree_storage.py`, `tests/test_workspace_visibility_settings.py`, `tests/test_workspace_csv_transfer.py`): `17 passed`.
  - continued `PyMethodMayBeStaticInspection` cleanup (batch-2): converted self-free helpers to `@staticmethod` in hotkeys manager, attach-file/base dialogs, dragdrop policies, project nav, and file/purchase workspaces.
  - validated staticmethod batch-2 with compile + focused regression suite (`tests/test_dragdrop_policy.py`, `tests/test_dragdrop_model.py`, `tests/test_dragdrop_integration.py`, `tests/test_dragdrop_controller.py`, `tests/test_project_tree_storage.py`, `tests/test_workspace_csv_transfer.py`, `tests/test_workspace_visibility_settings.py`): `34 passed`.
  - continued `PyShadowingNamesInspection` cleanup (batch-2): removed shadowing in task list tree-build/sort closures and in attachment dialog source fill logic (`tasks_workspace`).
  - validated shadowing batch-2 with targeted compile + task regressions (`tests/test_tasks_marker_refresh.py`, `tests/test_task_attachment_class.py`, `tests/test_tray_task_navigation.py`, `tests/test_workspace_csv_transfer.py`): `16 passed`.
  - continued `PyMethodMayBeStaticInspection` cleanup (batch-3): converted self-free task helpers in `tasks_workspace` (`_clear_layout`, `_cloud_file_link_text`, `_attachment_kind_label`, `_task_quick_rect`, `_is_overdue`, `_format_*`, `_tab_from_mode`, `_estimate_task_minutes`) to `@staticmethod`.
  - validated staticmethod batch-3 with targeted compile + task regressions (`tests/test_tasks_marker_refresh.py`, `tests/test_task_attachment_class.py`, `tests/test_tray_task_navigation.py`, `tests/test_workspace_csv_transfer.py`): `16 passed`.
  - continued `PyMethodMayBeStaticInspection` cleanup (batch-4): converted self-free notes/ideas helpers (`_paint_category` delegates and ideas `_set_combo_value`) to `@staticmethod`.
  - validated staticmethod batch-4 with focused workspace regressions (`tests/test_workspace_category_layout.py`, `tests/test_notes_multiline_save.py`, `tests/test_workspace_csv_transfer.py`): `10 passed`.
  - continued `PyMethodMayBeStaticInspection` cleanup (batch-5): converted self-free maps helpers (row/layout math, project-title providers, resize helpers, marker preview loader, info-format helpers) to `@staticmethod`.
  - validated staticmethod batch-5 with focused map/workspace regressions (`tests/test_maps_simple_mouse_mode.py`, `tests/test_workspace_category_layout.py`): `6 passed`.
  - continued `PyMethodMayBeStaticInspection` cleanup (batch-6): converted `BaseWorkspace` no-op lifecycle hooks (`on_leave`, `teardown`) to static.
  - validated staticmethod batch-6 with focused workspace regressions (`tests/test_workspace_visibility_settings.py`, `tests/test_workspace_csv_transfer.py`, `tests/test_workspace_category_layout.py`): `11 passed`.
  - continued `PyTypeCheckerInspection` cleanup (batch-1): normalized Qt payload/date typing in `main_window` and `tasks_workspace` (`nativeEvent` event-type decoding, resize-edge cursor mapping via int flags, `QByteArray` task-id decode, explicit `QDate` conversion for task editors).
  - validated typechecker batch-1 with focused task/tray regressions (`tests/test_tray_task_navigation.py`, `tests/test_tasks_marker_refresh.py`, `tests/test_task_attachment_class.py`, `tests/test_workspace_csv_transfer.py`): `16 passed`.
  - continued `PyTypeCheckerInspection` cleanup (batch-2): simplified projects DnD reject-tooltip anchor to cursor-position path (`projects_nav._show_drop_reject`) to avoid typed `QDropEvent.globalPosition` ambiguity.
  - validated typechecker batch-2 with focused project/tray regressions (`tests/test_project_tree_storage.py`, `tests/test_tray_task_navigation.py`): `8 passed`.
  - continued `PyTypeCheckerInspection` cleanup (batch-3): hardened folder-index extraction in file selectors (`attach_file_select_nav`, `files_workspace`) with typed bucket normalizers for folder paths and `CloudFileData` rows.
  - validated typechecker batch-3 with focused workspace/task regressions (`tests/test_workspace_csv_transfer.py`, `tests/test_task_attachment_class.py`, `tests/test_workspace_visibility_settings.py`): `12 passed`.
  - continued `PyTypeCheckerInspection` cleanup (batch-4): fixed maps typing edges (`QPointF` world-transform math, integer label font sizing, object-safe entity label formatters for map marker binding dialog).
  - validated typechecker batch-4 with focused maps/workspace regressions (`tests/test_maps_simple_mouse_mode.py`, `tests/test_workspace_category_layout.py`): `6 passed`.
  - continued `PyTypeCheckerInspection` cleanup (batch-5): normalized task-focus selection flags in `tasks_workspace` to typed-safe `QItemSelectionModel.SelectionFlag` usage without mixed flag combos.
  - validated typechecker batch-5 with focused task/tray regressions (`tests/test_tray_task_navigation.py`, `tests/test_tasks_marker_refresh.py`, `tests/test_task_attachment_class.py`, `tests/test_workspace_csv_transfer.py`): `16 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-1): migrated remaining legacy Qt enum references in lightweight UI modules (`search_nav`, `smooth_scroll`, `smooth_scroll_demo`) to Qt6 namespaces.
  - validated unresolved batch-1 with compile + focused smooth-scroll tests (`tests/test_smooth_scroll.py`): `5 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-2): migrated legacy Qt enums in shell UI modules (`splash`, `titlebar`) and removed typed-unsafe `QMainWindow.title_bar` cross-reference by using local `TitleBar.sync_max_button()`.
  - validated unresolved batch-2 with compile + focused tray/workspace regressions (`tests/test_tray_task_navigation.py`, `tests/test_workspace_visibility_settings.py`): `7 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-3): migrated modal/dialog Qt enums in `base_dialog`, `frameless_patch`, and `modals` (`WindowType`, `FocusPolicy`, `WidgetAttribute`, `QEvent.Type`, `QDialogButtonBox.ButtonRole`).
  - validated unresolved batch-3 with compile + focused animation/tray regressions (`tests/test_animations.py`, `tests/test_tray_task_navigation.py`): `8 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-4): migrated marker pixmap scaling enums in `marker_types` to Qt6 namespaces (`Qt.AspectRatioMode`, `Qt.TransformationMode`).
  - validated unresolved batch-4 with compile + focused maps regression (`tests/test_maps_simple_mouse_mode.py`): `2 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-5): migrated legacy Qt constants in `collection_category_dialog`, `collection_import_dialog`, and `purchase_edit_dialog` to Qt6 enum namespaces (`Qt.AlignmentFlag`, `Qt.ItemDataRole`, `QDialogButtonBox.StandardButton`).
  - validated unresolved batch-5 with compile + focused workspace/task regressions (`tests/test_workspace_category_layout.py`, `tests/test_workspace_csv_transfer.py`, `tests/test_task_attachment_class.py`): `13 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-6): migrated legacy Qt constants in `entity_picker_dialog`, `purchase_add_dialog`, and `purchase_compare_dialog` to Qt6 namespaces (`Qt.WindowType`, `Qt.WidgetAttribute`, `Qt.FocusReason`, `Qt.ItemDataRole`, `Qt.CheckState`, `QDialogButtonBox.StandardButton`, `QAbstractItemView.EditTrigger`, `QHeaderView.ResizeMode`).
  - validated unresolved batch-6 with compile + focused workspace/task regressions (`tests/test_workspace_csv_transfer.py`, `tests/test_task_attachment_class.py`): `9 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-7): migrated legacy Qt constants in `purchases_workspace` to Qt6 enum namespaces (`Qt.Orientation`, `Qt.ContextMenuPolicy`, `QAbstractItemView.SelectionBehavior`, `QAbstractItemView.SelectionMode`, `QAbstractItemView.EditTrigger`, `QMessageBox.StandardButton`).
  - validated unresolved batch-7 with compile + focused workspace regressions (`tests/test_workspace_visibility_settings.py`, `tests/test_workspace_csv_transfer.py`): `7 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-8): migrated legacy list/item constants in `projects_nav` to Qt6 enums (`Qt.ItemFlag`, `Qt.GlobalColor`, `QAbstractItemView.SelectionMode`, `QAbstractItemView.ScrollMode`, `QAbstractItemView.DragDropMode`).
  - validated unresolved batch-8 with compile + focused project/tray regressions (`tests/test_project_tree_storage.py`, `tests/test_tray_task_navigation.py`): `8 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-9): migrated remaining legacy Qt constants in `main_window` and `tasks_workspace` (tray message icons, cursor/alignment enums, text interaction flags, dialog button lookup, gantt table selection/edit/resize enums).
  - validated unresolved batch-9 with compile + focused task/tray regressions (`tests/test_tray_task_navigation.py`, `tests/test_tasks_marker_refresh.py`, `tests/test_task_attachment_class.py`, `tests/test_workspace_csv_transfer.py`): `16 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-10): migrated remaining map/idea UI enums in `maps_workspace`, `map_label_edit_dialog`, and `ideas_workspace` (text-interaction flags, size-policy enums, list/scroll modes, `QStyleOptionViewItem` delegate typing).

### TASK_A5309C79-AAB3-4D9F-A2D3-3CC498AF6A22
- Type: parity
- Title: Register Sprint 8 partition PR and pipeline parity closure
- Sprint: 8
- Status: Done
- Why:
  Sprint 8 partition delivery requires explicit parity closure with per-partition PR links and pipeline outcomes.
- Scope:
  - register partition PR links for `pA`, `pB`, `pC`, `pD`;
  - confirm all partition pipelines passed before parity closure;
  - confirm no deferred parity tasks remained after partition execution.
- Acceptance criteria:
  - parity entry contains all four partition PR links;
  - each partition has a recorded successful pipeline status;
  - parity status is explicitly marked as `Done`.
- Result:
  - `pA` PR: https://github.com/lexflame/mindnavigator_v2/pull/187 (pipeline passed);
  - `pB` PR: https://github.com/lexflame/mindnavigator_v2/pull/188 (pipeline passed);
  - `pC` PR: https://github.com/lexflame/mindnavigator_v2/pull/189 (pipeline passed);
  - `pD` PR: https://github.com/lexflame/mindnavigator_v2/pull/190 (pipeline passed).
  - validated unresolved batch-10 with compile + focused maps/workspace regressions (`tests/test_maps_simple_mouse_mode.py`, `tests/test_workspace_category_layout.py`, `tests/test_workspace_csv_transfer.py`): `10 passed`.
  - continued `PyUnresolvedReferencesInspection` cleanup (batch-11): migrated residual legacy Qt constants across navigation/list/dialog modules (`search_nav`, `base_workspace`, `tasks_workspace`, `objects_workspace`, `notes_workspace`, `maps_workspace`, `ideas_workspace`, `files_workspace`, `attach_file_select_nav`) to Qt6 enum namespaces.
  - validated unresolved batch-11 with compile + focused workspace/task/map regressions (`tests/test_workspace_category_layout.py`, `tests/test_workspace_csv_transfer.py`, `tests/test_maps_simple_mouse_mode.py`, `tests/test_tasks_marker_refresh.py`, `tests/test_tray_task_navigation.py`): `17 passed`.
  - started `PyTypeHintsInspection` cleanup (batch-1): normalized `QIcon | None` type hints to `Optional[QIcon]` in `map_label_edit_dialog` for PyCharm-compatible Qt typing.
  - validated typehints batch-1 with compile + focused maps/workspace regressions (`tests/test_maps_simple_mouse_mode.py`, `tests/test_workspace_category_layout.py`): `6 passed`.
  - continued `PyCallingNonCallableInspection` cleanup (batch-2): hardened drag-drop transition callback execution in `ui/dragdrop/controller.py` with explicit `callable(...)` guard.
  - validated calling-non-callable batch-2 with compile + focused dragdrop regressions (`tests/test_dragdrop_policy.py`, `tests/test_dragdrop_model.py`, `tests/test_dragdrop_integration.py`, `tests/test_dragdrop_controller.py`): `23 passed`.
  - continued `TASK_6BFC8077...` cleanup for `tasks_workspace` report pack (`PyUnresolvedReferencesInspection`, `PyTypeCheckerInspection`, `PyUnusedLocalInspection`, `PyShadowingNamesInspection`, `SpellCheckingInspection`): migrated residual Qt6 enums (`ItemDataRole`, `DropAction`, `WindowState`, `ColorRole`, `PenStyle`, `DragDropMode`), fixed undefined `plan_mode`, hardened delegate event/model typing (`QMouseEvent`, `QStyleOptionViewItem`, typed `TasksModel` narrowing), removed unused locals/shadowing, and normalized flagged typo tokens.
  - validated `tasks_workspace` batch with compile + focused regressions: `python -m compileall mindnavigator/workspaces/tasks_workspace.py` and `pytest tests/test_tasks_marker_refresh.py tests/test_workspace_category_layout.py tests/test_workspace_csv_transfer.py tests/test_maps_simple_mouse_mode.py tests/test_tray_task_navigation.py -p no:cacheprovider --basetemp .pytest_dir/tmp_tasks_workspace` -> `17 passed`.
  - fixed startup migration crash `sqlite3.IntegrityError: CHECK constraint failed: priority ...` by normalizing legacy priority payloads during table rebuild (`'Отложенная'`, mojibake alias, and numeric legacy codes `1..4`) before applying `CHECK`.
  - aligned runtime priority constants between storage and UI reminder flow (`DEFERRED_PRIORITY` in `storage` + `main_window`) and added regression test `test_database_migration_normalizes_legacy_priority_values` (`tests/test_db_migrations.py`).
  - fixed restart crash `sqlite3.OperationalError: there is already another table or index with this name: projects_old` by making table-rebuild flow recover from stale `<table>_old` artifacts before `ALTER TABLE ... RENAME`.
  - added migration regression `test_database_migration_recovers_from_stale_projects_old_table` to verify recovery path and cleanup of stale `projects_old`.
  - fixed startup UI crash `AttributeError: NoneType object has no attribute currentIndex` in `TasksWorkspace.get_selection()` by guarding pre-build state where `self.list`/`self.model` are not initialized yet.
  - added regression `test_tasks_workspace_get_selection_is_safe_before_list_init` (`tests/test_tasks_marker_refresh.py`).
  - fixed UI mojibake in `main_window.py`: restored corrupted UTF-8 literals (mode names, tray captions, notifications, tooltips, and command/help captions), so Russian text renders correctly in the main shell.
  - hardened startup splash lifecycle in `__main__.py`: added idempotent `finish_startup()`, explicit `hide/close/deleteLater` path, exception-safe splash close during `MainWindow()` init, and fallback timer (`2500ms`) to prevent stuck splash when status-chain timing is interrupted.
  - validated splash/encoding fix with compile + focused regressions: `python -m compileall mindnavigator/main_window.py mindnavigator/__main__.py`, `pytest tests/test_tray_task_navigation.py tests/test_workspace_visibility_settings.py -q` -> `7 passed`.
  - startup bootstrap hardening (follow-up): `finish_startup()` now performs maximize/sync in deferred callback with guaranteed splash teardown in `finally`; splash close is centralized in `close_splash()` and reused for exception paths during startup.
  - validated follow-up startup fix with `python -m compileall mindnavigator/__main__.py` and `pytest tests/test_tray_task_navigation.py -q` -> `4 passed`.
  - fixed startup crash in `settings_workspace`: backup controls (`include_cloud`, `auto_backup`, `frequency`, `retention`) are now loaded under `blockSignals`, so `_on_backup_option_changed` is not triggered during initial UI state hydration.
  - hardened backup-option persistence for read-only DB mode: `_on_backup_option_changed` now catches `sqlite3.Error` and reports status instead of propagating exception and crashing app startup.
  - hardened backup run bookkeeping: `_create_backup` now handles failure to persist `backup_last_run` timestamp in read-only DB without aborting the app.
  - added regression tests `tests/test_settings_workspace_backup_safety.py` covering loading-guard behavior and read-only DB error handling in backup option callback.
  - validated with `python -m compileall mindnavigator/workspaces/settings_workspace.py tests/test_settings_workspace_backup_safety.py`, `pytest tests/test_settings_workspace_backup_safety.py -q`, `pytest tests/test_tray_task_navigation.py -q`.
  - fixed silent startup/runtime crash path on Windows event loop: `MainWindow.nativeEvent` now normalizes `message` pointer via `int(...)` + `ctypes.c_void_p`, and catches `ctypes.ArgumentError` for `shiboken6.Shiboken.VoidPtr` payloads to avoid recursive native-event exceptions.
  - removed unsafe splash teardown re-entrancy in `__main__.py`: `close_splash()` no longer calls `app.processEvents()`/`deleteLater()` during startup callback chain.
  - hardened shutdown path: `MainWindow.closeEvent` now ignores `OSError` when saving hotkey overrides, so read-only profile paths do not abort app close/startup flow.
  - validated with `python -m compileall mindnavigator/main_window.py mindnavigator/__main__.py`, `pytest tests/test_tray_task_navigation.py -q`, `python -X faulthandler main.py` (no traceback).
  - final parity review completed: `docs/PARITY.md`, `.codex/HISTORY_TASK.md`, and `.codex/HISTORY_ACTION.md` are now aligned for this tracking task, with no remaining open Sprint 6 parity backlog item under `TASK_1FA90F88-2294-4074-88E2-75C3769E6768`.

### TASK_53A85F68-1AC3-415C-82B2-4E1B5FBD424D
- Type: parity
- Title: Sprint composition and backlog classification by type/workspace
- Sprint: 6
- Status: Done
- Why:
  Sprint 6 delivery needed an explicit parity pass to classify work items by type and workspace before implementation started.
- Scope:
  - normalize the Sprint 6 backlog structure;
  - mark parity work separately from feature and fix work;
  - keep the task ledger consistent with the sprint plan.
- Acceptance criteria:
  - Sprint 6 backlog is classified by task type and workspace;
  - parity work is visible as parity in the task ledger.
- Result:
  - Sprint 6 backlog was normalized and registered with explicit type/workspace classification;
  - `TASK_53A85F68-1AC3-415C-82B2-4E1B5FBD424D` is tracked as a completed parity item in `.codex/HISTORY_TASK.md`.

### TASK_6BFC8077-FB99-46CE-876D-AEA9492371C6
- Type: parity
- Title: Static-analysis remediation by error type with separate commits
- Sprint: 6
- Status: Done
- Why:
  Sprint 6 accumulated a broad static-analysis backlog that required parity cleanup outside the direct feature stream.
- Scope:
  - remediate static-analysis findings by inspection type;
  - keep fixes grouped in focused batches;
  - validate each remediation pass with targeted compile and regression checks.
- Acceptance criteria:
  - targeted static-analysis groups are remediated in completed batches;
  - resulting changes are tracked as parity work and validated incrementally.
- Result:
  - static-analysis cleanup was completed across multiple inspection groups (`PyUnboundLocalVariable`, `PyShadowingNames`, `PyUnresolvedReferences`, `PyTypeChecker`, and related follow-up batches);
  - the remediation stream is tracked as completed parity work in `.codex/HISTORY_TASK.md` and detailed in `.codex/HISTORY_ACTION.md`.

## Sprint 9 - Delivery Sync
- `TASK_EC9B9B77-2D33-4A4A-A5F8-3A0E4258B651` (`MN-202`) delivery synced.
- Tasks workspace updates: `Gantt/Board/Dash` strip, top project quick links, attachment-aware row menu, row priority switch, marker-theme overlay visuals, and title-based project suggestion.
- Validation synced: `python -m compileall mindnavigator main.py`; `PYTHONPATH=. pytest tests/test_tasks_workspace_mn202.py tests/test_tasks_marker_refresh.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`16 passed`).
- `TASK_3B934AFD-53C5-4F72-B386-5F2AFEFDF97F` (`MN-206`) delivery synced.
- Files workspace updates: smart-search block with hint chips, dedicated path-token index (`\\` split), and search-triggered large sketch mode with return to normal navigation on clear.
- Validation synced: `python -m compileall mindnavigator main.py`; `$env:PYTHONPATH='.'; pytest tests/test_files_workspace_mn206.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`3 passed`).
- `TASK_B201341A-69C2-410A-8B13-FFA8E6A956AD` (`MN-207`) delivery synced.
- Collections workspace updates: entry-level remove action (DB-only, source file preserved), `Thumbs.db` exclusion in folder import listing, and white description text in details panel.
- Validation synced: `python -m compileall mindnavigator main.py`; `$env:PYTHONPATH='.'; pytest tests/test_collections_workspace_mn207.py tests/test_workspace_category_layout.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`10 passed`).
- `TASK_A3D78EC8-32AE-4C1E-B9EA-44D459345397` (`MN-204`) delivery synced.
- Characters mode updates: new workspace UI (`Персонажи`), storage CRUD/link model (`characters`, `character_links`), left-rail/settings/i18n/search integration, and cross-entity attachment support for application domains.
- Validation synced: `python -m compileall mindnavigator main.py`; `$env:PYTHONPATH='.'; pytest tests/test_characters_workspace_mn204.py tests/test_workspace_visibility_settings.py tests/test_i18n.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`12 passed`).
- `TASK_9BFC4D13-C8AA-453A-AB26-264751A2EDFE` (`MN-290`) delivery synced.
- Workspace modular split updates: moved workspace implementations into per-workspace directories (`mindnavigator/workspaces/<workspace>/workspace.py`), kept package exports, and added legacy module aliases for backward-compatible import paths.
- Validation synced: `python -m compileall mindnavigator main.py`; `$env:PYTHONPATH='.'; pytest tests/test_workspace_module_split_mn290.py tests/test_tasks_marker_refresh.py tests/test_projects_workspace_mn201.py tests/test_projects_workspace_mn203.py tests/test_files_workspace_mn206.py tests/test_collections_workspace_mn207.py -p no:cacheprovider --basetemp .pytest_dir/run_tmp` (`25 passed`).
