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
- Status: In Progress
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
  - fixed `PyArgumentListInspection` warnings by normalizing `QShortcut` call signatures, replacing tuple-unpack `setRange` call with explicit min/max values, and tightening patched `QDialog.exec` signature forwarding.
  - fixed `PyUnusedLocalInspection` warnings by removing unused temp variables/args in modal + project-nav + dragdrop + purchase dialog paths and simplifying task attachment item-fill loops.
  - fixed `PyAttributeOutsideInitInspection` by predeclaring runtime UI attributes in `TasksWorkspace.__init__` and setting startup `_current_mode` in `MainWindow`.
  - fixed `HttpUrlsUsage` warning in purchase URL parser by validating scheme via `urlparse` (`http`/`https`) instead of hardcoded `http://` literal checks.
