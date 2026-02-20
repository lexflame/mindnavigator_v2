# Audit Notes: TASK_5B2F6F11-0D53-487E-AF6A-442BFD0C8A61

## Title
UX requirements and baseline audit for scrollbar styling and smooth scroll.

## Baseline Inventory (Scrollable Targets)
1. Navigation and shared UI:
- `mindnavigator/ui/projects_nav.py` (`QListWidget`, local scrollbar QSS exists)
- `mindnavigator/ui/search_nav.py` (`QListWidget`)

2. Workspaces:
- `mindnavigator/workspaces/tasks_workspace.py` (`QScrollArea`, task list, gantt table)
- `mindnavigator/workspaces/notes_workspace.py` (`QTreeWidget`, list area, editor)
- `mindnavigator/workspaces/files_workspace.py` (`QTreeWidget`, `QListWidget`, sync log)
- `mindnavigator/workspaces/objects_workspace.py` (`QTreeWidget`, `QListWidget`, `QPlainTextEdit`)
- `mindnavigator/workspaces/purchases_workspace.py` (`QTreeWidget`, multiple `QTableWidget`, notes editor)
- `mindnavigator/workspaces/collections_workspace.py` (`QTreeWidget`, multiple `QListWidget`)
- `mindnavigator/workspaces/maps_workspace.py` (`QScrollArea`, custom `wheelEvent`, list/table sections)

3. Dialogs:
- `mindnavigator/ui/dialogs/map_label_edit_dialog.py` (`QScrollArea`, completer popup scrollbar QSS)
- `mindnavigator/ui/dialogs/attach_file_select_nav.py` (`QTreeWidget`, `QListWidget`)
- `mindnavigator/ui/dialogs/entity_picker_dialog.py` (`QListWidget`)
- `mindnavigator/ui/dialogs/purchase_compare_dialog.py` (`QTableWidget`)

## Current Issues
- Scrollbar styles are fragmented across modules via local QSS.
- Smooth scrolling is inconsistent; only selected widgets use `ScrollPerPixel`.
- `wheelEvent` behavior is custom in map workspace but not centralized.
- Horizontal scrollbar behavior varies (`AlwaysOff` in some places, default in others).

## UX Requirements (Sprint Baseline)
1. Visual style:
- single scrollbar token set (track/handle colors, width, radius, hover/pressed);
- consistent contrast on dark surfaces;
- no visible jump between focused/non-focused states.

2. Smoothness behavior:
- wheel and trackpad feel consistent across targeted widgets;
- no jitter on boundaries;
- no delayed “stuck” frames when rapidly scrolling.

3. Accessibility and usability:
- handle size remains usable on dense lists;
- focus/hover states stay readable;
- kinetic effect must not reduce precision for short scroll actions.

## Acceptance Criteria For Next Tasks
- Global scrollbar stylesheet applied to target widgets without local conflicts.
- Smooth scroll utility integrated with per-widget overrides.
- Boundary and burst-input regressions covered by tests.
- Performance profile confirms no UI-thread spikes from smoothing logic.
