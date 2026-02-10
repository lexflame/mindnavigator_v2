# MindNavigator v2 — CODEX Run Plan (Executable)

Date: 2026-02-11  
Owner: Саня  
Mode: **One step = one CODEX run**

This file converts the raw task pack into CODEX-ready runs with explicit scope and acceptance.

---

## Operating rules for every run

1. Keep change-set minimal and local to listed files.
2. Preserve backward compatibility unless migration is explicitly part of the step.
3. Safe default policy: **apply only when target field is empty**.
4. For schema changes, include migration + read fallback for older rows.
5. Update `docs/qa/manual_steps.md` with quick validation for each completed step (if no automated test added).

---

## Run 0 — Inventory & integration map (mandatory bootstrap)

- **What to change**: Produce inventory document with real hook points.
- **Where**: `docs/dev/inventory.md`.
- **Acceptance**: Inventory exists and includes task edit form, save flow, description editor, timers/scheduler hook, project model, subtask tree, marker form + note linkage, map tools + zoom hooks.

**Status in repo**: prepared in `docs/dev/inventory.md`.

---

## Run 1 — Persist Task Edit form size

- **What to change**: Save/restore TaskEditDialog width/height.
- **Where**:
  - `mindnavigator/workspaces/tasks_workspace.py` (`TaskEditDialog`)
  - `mindnavigator/storage.py` (`get_setting`/`set_setting` usage only; no schema change required)
- **Implementation notes**:
  - Key: `ui.task_edit_form.size`.
  - Save on `resizeEvent` with debounce (`QTimer.singleShot` or reusable timer).
  - Restore at dialog init; clamp to min/max constraints.
- **Acceptance**:
  - Resize → close → reopen dialog: size restored.

---

## Run 2 — Ctrl+Enter saves Task Edit form

- **What to change**: Add save hotkey parity with Save button.
- **Where**: `mindnavigator/workspaces/tasks_workspace.py` (`TaskEditDialog`).
- **Implementation notes**:
  - Add `QShortcut("Ctrl+Enter")` and `QShortcut("Ctrl+Return")` bound to `_on_accept`.
  - Scope shortcut to dialog so it works from focused inputs.
  - Keep plain Enter behavior in `QPlainTextEdit` unchanged (newline).
- **Acceptance**:
  - Ctrl+Enter saves.
  - Enter in description adds newline only.

---

## Run 3 — Task description auto-links

- **What to change**: URL detection + Word-like space conversion behavior.
- **Where**:
  - `mindnavigator/workspaces/tasks_workspace.py`
    - `TaskEditDialog.description_edit` input handling
    - `TaskDetailsDialog` rendering for clickable links
- **Implementation notes**:
  - Use robust URL regex (`https?://...`).
  - On space after URL token: convert token into clickable representation (if rich text path) or store plain text and render links in details/preview.
  - Also treat lines starting with URL as links on render.
  - Ensure editing doesn’t duplicate markup.
- **Acceptance**:
  - Typing URL + space yields clickable link in view context.
  - URL-first line renders clickable.
  - Multiple links remain stable after edits.

---

## Run 4 — Recurrence model + scheduler tick

- **What to change**: Introduce recurrence fields and processing tick.
- **Where**:
  - `mindnavigator/storage.py` (schema + DTO + CRUD)
  - `main.py` (scheduler bootstrap timer) and/or dedicated scheduler module under `mindnavigator/`
  - `mindnavigator/workspaces/tasks_workspace.py` (task create/edit propagation)
- **Implementation notes**:
  - Add fields: `enabled`, `rule`, `interval`, `next_run_at`, `mode`.
  - Timer cadence 1–5 min; run once on startup.
  - Catch-up loop bounded to avoid long blocking/spam.
  - Default mode: `SHIFT_DEADLINE` unless an instance system is introduced in same run.
- **Acceptance**:
  - Task reschedules at due recurrence point.
  - Restart catch-up works without duplicate spam.

---

## Run 5 — Project rules (default priority, force periodic, links)

- **What to change**: Project-level settings and new-task inheritance.
- **Where**:
  - `mindnavigator/storage.py` (project schema/model)
  - `mindnavigator/workspaces/projects_workspace.py` (settings UI)
  - `mindnavigator/workspaces/tasks_workspace.py` (new task creation inheritance)
- **Implementation notes**:
  - Add settings: `default_priority`, `force_periodic`, recurrence template, linked map/note/object ids.
  - Apply only when task field is empty / unset.
- **Acceptance**:
  - New project task inherits default priority only if unset.
  - force_periodic applies recurrence template to new tasks.
  - Linked entities can be opened from project UI.

---

## Run 6 — Parent dblclick toggles subtasks, leaf dblclick opens details

- **What to change**: Dblclick policy split by child presence.
- **Where**: `mindnavigator/workspaces/tasks_workspace.py` (`eventFilter`, possibly delegate helpers).
- **Implementation notes**:
  - If row has children (`TaskRoles.HasSubtasks`): dblclick toggles expand/collapse.
  - If leaf: dblclick opens details.
  - Keep alternate detail path for parents (context menu action “Открыть”, Enter key binding).
- **Acceptance**:
  - Parent: dblclick toggles only.
  - Leaf: dblclick opens details.
  - Parent details still accessible by alternate action.

---

## Run 7 — Nested projects + wider project context in task list

- **What to change**: project hierarchy and display improvements.
- **Where**:
  - `mindnavigator/storage.py` (`projects.parent_id` migration)
  - `mindnavigator/workspaces/projects_workspace.py` (hierarchical list/tree)
  - `mindnavigator/workspaces/tasks_workspace.py` (project context rendering/column width behavior)
- **Implementation notes**:
  - Add optional include-subprojects filter default ON.
  - Ensure names are not excessively truncated in task list project section.
- **Acceptance**:
  - Subprojects create/display correctly.
  - Task list shows hierarchy context.
  - Visual truncation improved for typical nested names.

---

## Run 8 — Frameless forms (task edit + marker view)

- **What to change**: Hide standard OS title bar and provide custom controls.
- **Where**:
  - `mindnavigator/workspaces/tasks_workspace.py` (`TaskEditDialog`)
  - `mindnavigator/ui/dialogs/map_label_edit_dialog.py`
  - optional shared helper in `mindnavigator/ui/` for drag/resize chrome reuse
- **Implementation notes**:
  - Frameless flag + drag region + close/min/max + resize grips.
  - Preserve Esc close behavior.
- **Acceptance**:
  - Forms are frameless and still movable/resizable/closable.

---

## Run 9 — Convert task to subtask: inherit parent deadline safely

- **What to change**: On parent assignment, copy deadline if child deadline empty.
- **Where**:
  - `mindnavigator/workspaces/tasks_workspace.py`
    - `TasksModel.move_task_to_parent(...)`
    - DnD path `dropMimeData(...)`
- **Implementation notes**:
  - Empty-only overwrite rule:
    - child `day/time_text` empty → copy parent
    - child already has deadline → keep existing
  - Persist via existing task update API.
- **Acceptance**:
  - Move under parent copies missing deadline fields only.
  - Existing child deadline remains unchanged.

---

## Run 10 — Marker form redesign + parse fields from linked notes

- **What to change**: Marker form UX refresh + note parser.
- **Where**:
  - `mindnavigator/ui/dialogs/map_label_edit_dialog.py`
  - parser helper module (new): `mindnavigator/parsing/note_to_marker.py` (or equivalent)
  - `mindnavigator/storage.py` if marker schema extension is required
- **Implementation notes**:
  - Adopt `Key: Value` parser first (tolerant mode).
  - Keys: Address, Source, Tags, Year, Description, Links.
  - Add “Fill from linked note” button, optional preview.
- **Acceptance**:
  - Linked note can populate marker fields.
  - Extra free text is tolerated.

---

## Run 11 — Map AREA_DRAW polygon (grid-snapped)

- **What to change**: polygon drawing/edit tool.
- **Where**:
  - `mindnavigator/workspaces/maps_workspace.py` (`MapTool`, `MapCanvas` input/render)
  - `mindnavigator/storage.py` for geometry persistence (GeoJSON-like)
- **Implementation notes**:
  - Add tool mode `AREA_DRAW`.
  - Snap vertices to grid intersections.
  - Support add vertex / undo / close polygon / move vertex.
- **Acceptance**:
  - Polygon can be drawn/edited and survives reload.
  - Vertices align to grid.

---

## Run 12 — Map PATH_DRAW polyline

- **What to change**: route/path drawing tool.
- **Where**:
  - `mindnavigator/workspaces/maps_workspace.py`
  - `mindnavigator/storage.py` (polyline persistence)
- **Implementation notes**:
  - Add tool mode `PATH_DRAW`.
  - Editing similar to polygon without closure requirement.
  - Optional style properties (type/width).
- **Acceptance**:
  - Polyline draw/edit/persist/reopen works.

---

## Run 13 — Marker LOD visibility by zoom (with hysteresis)

- **What to change**: zoom-threshold marker visibility rules.
- **Where**: `mindnavigator/workspaces/maps_workspace.py` (`MapCanvas` draw + zoom handlers).
- **Implementation notes**:
  - Introduce marker visibility thresholds (`Z_show`, `Z_hide`, with `Z_hide < Z_show`).
  - Evaluate only affected markers where possible.
- **Acceptance**:
  - Small markers hide on zoom-out and reappear on zoom-in.
  - No flicker near thresholds.

---

## Run 14 — New “Collections” workspace MVP

- **What to change**: add workspace, storage models, cross-linking, JSON import/export.
- **Where**:
  - `mindnavigator/workspaces/collections_workspace.py` (new)
  - `mindnavigator/workspaces/__init__.py` and navigation wiring (`mindnavigator/ui/leftrail.py` etc.)
  - `mindnavigator/storage.py` (schema + CRUD + migrations)
- **Implementation notes**:
  - Models: `Collection`, `CollectionItem`, `CrossLink`.
  - Minimal usable UI: list + detail + cross-link panel.
  - Add portable JSON import/export.
- **Acceptance**:
  - Create collections/items/links; data persists; basic filter/search works.

---

## Suggested execution order constraints

- Must complete before recurrence/project features: **Run 0**.
- Must complete before nested-project UX: **Run 5** before **Run 7**.
- Must complete before map LOD tuning: **Run 11/12** before **Run 13**.

---

## QA checklist mapping

- Task save/edit regressions: Runs 1–3, 6, 9.
- Settings persistence: Run 1 (+ any new UI settings in 5/7/13).
- Scheduler duplicates: Run 4.
- Drag/drop + dblclick behavior: Runs 6, 9.
- Geometry persistence: Runs 11, 12.
- Marker parsing quality: Run 10.
- Collections MVP usability: Run 14.

