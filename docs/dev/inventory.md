# MindNavigator v2 — Inventory & Integration Map

Static integration map for CODEX runs. Paths and hook points are based on repository inspection.

## Tasks workspace

- `mindnavigator/workspaces/tasks_workspace.py`
  - `class TaskEditDialog(QDialog)` — task edit form UI; save wiring via `QDialogButtonBox(...).accepted.connect(self._on_accept)`; description input `self.description_edit = QPlainTextEdit(...)`.
  - `TaskEditDialog._on_accept()` — validation before save; hook for keyboard submit parity.
  - `TaskEditDialog.values()` — payload used by task update flow.
  - `TasksWorkspace.eventFilter(...)` — double-click behavior on task rows (currently opens details when clicking description area, otherwise toggles expanded state).
  - `TaskItemDelegate._edit_task(...)` and `_open_task_view(...)` — edit/details dialog entry points.
  - `TasksModel.move_task_to_parent(...)` and `TasksModel.dropMimeData(...)` — subtask conversion + DnD parent assignment.
  - `TasksModel.toggle_subtasks_expanded_by_row(...)` — expand/collapse state for parent tasks.
  - `TasksModel.add_task(...)` and `TasksWorkspace._on_create_task(...)` — new task creation path.

## Storage / schema / settings

- `mindnavigator/storage.py`
  - `@dataclass TaskData`, `ProjectData`, `MapMarkerData` — main model DTOs to extend for recurrence/project settings.
  - `Database._create_schema()` and migration helpers (`_ensure_*`, `_rebuild_*`) — schema migration insertion points.
  - `Database.create_task(...)` / `update_task(...)` / `fetch_tasks(...)` — task persistence path.
  - `Database.create_project(...)` / `update_project(...)` / `fetch_projects(...)` — project persistence path.
  - `Database.get_setting(...)` / `set_setting(...)` — persistent UI/state settings (`settings` table), suitable for dialog size persistence and feature flags.

## Projects workspace

- `mindnavigator/workspaces/projects_workspace.py`
  - Project create/edit flows; entry points for adding project-level settings UI and persistence calls.

## Maps workspace and marker editing

- `mindnavigator/workspaces/maps_workspace.py`
  - `class MapTool(Enum)` — current map tool enum (`SELECT`, `ADD_MARKER`, `ADD_REGION`, `MEASURE`); extension point for area/path tools.
  - `class MapCanvas(QWidget)` — input and rendering pipeline:
    - zoom hooks: wheel handling + `_scale`/`_min_scale`/`_max_scale` transitions.
    - draw hooks: `paintEvent()`, `_draw_grid()`, `_draw_markers()`, marker hit-testing.
    - marker interactions: selection/drag/resize and detail open (`mouseDoubleClickEvent`, marker signals).
  - workspace-level refresh/wiring around marker CRUD and attachment source synchronization.
- `mindnavigator/ui/dialogs/map_label_edit_dialog.py`
  - Marker (label) form UI and save lifecycle (`_on_save`).
  - Existing shortcuts include `Ctrl+Enter`, `Ctrl+Return`, `Esc`.
  - Best insertion point for “Fill from linked note” action and parsing preview UI.

## Notes workspace

- `mindnavigator/workspaces/notes_workspace.py`
  - note model/controller/view wiring; data source for marker note parsing.

## App startup / timer integration

- `main.py`
  - app bootstrap + `QTimer` use patterns; scheduler start hook location.
- `mindnavigator/workspaces/*` (workspace constructors)
  - potential fallback if scheduler is kept workspace-local.

## Existing tests

- `tests/test_hotkeys.py`
  - test style reference; add new tests adjacent to future recurrence/subtask/link parsing tests if test harness is expanded.
