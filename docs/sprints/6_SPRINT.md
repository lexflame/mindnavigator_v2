# Sprint 6: Notes, Export, Import

## Sprint Status
- Completed: 2026-02-25

## Sprint Goal
Deliver end-to-end update/import/export infrastructure, workspace-level UX upgrades for notes-family modes, and targeted stability fixes while preserving existing desktop behavior.

## Scope
- Core: updater, DB migrations, DB path settings, language/runtime settings.
- Workspaces: tasks, notes, collections, ideas, objects, maps, projects.
- UI platform: sidebar behavior, dialog/width animations, tray notification deep-link.
- Quality: static-analysis remediation from `docs/inspect` with commit split by error type.

## Backlog (Sorted By Type And Workspace)

### `chore` / `planning` / `infra-docs`
1. `TASK_GUID: TASK_53A85F68-1AC3-415C-82B2-4E1B5FBD424D` - Sprint composition and backlog classification by type/workspace.
2. `TASK_GUID: TASK_6BFC8077-FB99-46CE-876D-AEA9492371C6` - Process PyCharm reports from `docs/inspect`; commit each error class separately.

### `feat` / `core-platform`
3. `TASK_GUID: TASK_F42B8258-3D69-4555-BEFA-8F2B311F63EA` - Implement DB migration module for schema upgrades.
4. `TASK_GUID: TASK_75026A8B-7FB9-4AE1-9F6C-BD1092D24B1A` - Implement update module.
5. `TASK_GUID: TASK_E0A0B865-013E-445B-9656-84CE4A697CB5` - Add setting: DB storage location.
6. `TASK_GUID: TASK_18C5FA49-0E96-4009-B903-A12AA581F7AA` - Add "Check update" action: run DB update path and check newer repository version.
7. `TASK_GUID: TASK_E32E5C80-2EC6-4663-A336-5DD0BE013784` - Add application language selector: EN/RU/DE/FR/ZH.
8. `TASK_GUID: TASK_14D8E869-90D7-48F1-A1F0-0509FDFD039A` - Add setting with checkboxes for enabled workspaces.

### `feat` / `data-transfer`
9. `TASK_GUID: TASK_2639BE33-BC91-42E1-A3AC-A5402D06CCBD` - Implement CSV import/export service class.
10. `TASK_GUID: TASK_4266DF47-F05A-419E-931B-CC7675EF65D8` - Add Import/Export buttons (top-right) for tasks, collections, projects, notes, ideas, objects workspaces.

### `feat` / `ui-animation`
11. `TASK_GUID: TASK_585678D4-1572-45F1-9570-2B5E5F6817CB` - Implement smooth fast width-expansion animation class.
12. `TASK_GUID: TASK_420CB243-F7B0-479C-9652-B501AE4AC7DF` - Implement smooth fast dialog-appearance animation class.
13. `TASK_GUID: TASK_5CCD9BE4-C5DC-4D14-98E9-231EB8D8E2A1` - Apply dialog appearance animation across all dialogs.

### `feat` / `ui-shell`
14. `TASK_GUID: TASK_905129B0-3848-4C30-9490-CFC00F5A838A` - Sidebar mode icons: hover-expand overlay and show mode names.
15. `TASK_GUID: TASK_E8446B40-0DA1-43CC-9206-FCC7EC37C0F0` - On system notification click: restore app from tray and navigate to target task.

### `feat` / `domain-attachments`
16. `TASK_GUID: TASK_12A60D96-05E6-4868-91D5-0D2AA70B64CF` - Implement attachment class.
17. `TASK_GUID: TASK_93B6AFF6-967A-403F-94C2-6CA6C9A2B0FD` - Tasks attachments: add ability to attach Ideas.

### `feat` / `workspace-maps`
18. `TASK_GUID: TASK_E76B6B30-7CA6-4C6D-9B6F-B19AA473450B` - Maps simple mouse mode: forbid marker dragging.

### `feat` / `workspace-notes-family`
19. `TASK_GUID: TASK_329B82A5-0968-4121-9E24-2983E0C430E2` - Rework notes/collections/ideas/objects to tasks-like workflow:
- categories as separators;
- top quick form for navigation and entity creation;
- collection preview image in entity row;
- entity-row layout adjusted to each domain.

### `fix` / `workspace-notes`
20. `TASK_GUID: TASK_3ED7E7F2-C87E-4611-85D7-AF271D6E4D31` - Notes save bug: multiline text after line breaks is not persisted correctly.

### `fix` / `workspace-tasks`
21. `TASK_GUID: TASK_04E6A669-898B-498F-827D-FD51B4C678D2` - Tasks list: refresh marker property immediately after marker update.

## Workspace Index
- `settings`: TASK_E0A0B865..., TASK_18C5FA49..., TASK_E32E5C80..., TASK_14D8E869...
- `tasks`: TASK_4266DF47..., TASK_93B6AFF6..., TASK_04E6A669...
- `notes`: TASK_4266DF47..., TASK_329B82A5..., TASK_3ED7E7F2...
- `collections`: TASK_4266DF47..., TASK_329B82A5...
- `ideas`: TASK_4266DF47..., TASK_329B82A5..., TASK_93B6AFF6...
- `objects`: TASK_4266DF47..., TASK_329B82A5...
- `projects`: TASK_4266DF47...
- `maps`: TASK_E76B6B30...
- `ui/dialogs/animations`: TASK_585678D4..., TASK_420CB243..., TASK_5CCD9BE4...
- `ui shell/tray/sidebar`: TASK_905129B0..., TASK_E8446B40...
- `core/storage/update`: TASK_F42B8258..., TASK_75026A8B..., TASK_12A60D96..., TASK_2639BE33...
- `infra/docs/quality`: TASK_53A85F68..., TASK_6BFC8077...

## Execution Waves (Dependency-Oriented)
1. Wave A (foundation): TASK_F42B8258..., TASK_75026A8B..., TASK_E0A0B865..., TASK_18C5FA49...
2. Wave B (cross-cutting settings): TASK_E32E5C80..., TASK_14D8E869...
3. Wave C (data transfer): TASK_2639BE33..., TASK_4266DF47...
4. Wave D (attachments): TASK_12A60D96..., TASK_93B6AFF6...
5. Wave E (UI shell + animation): TASK_585678D4..., TASK_420CB243..., TASK_5CCD9BE4..., TASK_905129B0..., TASK_E8446B40...
6. Wave F (workspace behavior/fixes): TASK_E76B6B30..., TASK_329B82A5..., TASK_3ED7E7F2..., TASK_04E6A669...
7. Wave G (quality closure): TASK_6BFC8077...

## Validation Matrix (Auto-tests, Tests, Compile)

### Planning / Docs
- `TASK_53A85F68-1AC3-415C-82B2-4E1B5FBD424D`: no compile/tests required (documentation and backlog classification only).

### Core Platform
- `TASK_F42B8258-3D69-4555-BEFA-8F2B311F63EA`:
  - compile: `python -m compileall mindnavigator/storage.py main.py`
  - auto-tests: migration unit/integration tests on legacy and current DB fixtures
  - tests: startup migration smoke (open app on migrated DB)
- `TASK_75026A8B-7FB9-4AE1-9F6C-BD1092D24B1A`:
  - compile: `python -m compileall mindnavigator main.py`
  - auto-tests: updater service tests with mocked network/version source
  - tests: manual update-check flow from settings/UI entry points
- `TASK_E0A0B865-013E-445B-9656-84CE4A697CB5`:
  - compile: `python -m compileall mindnavigator/workspaces/settings_workspace.py mindnavigator/storage.py`
  - auto-tests: settings persistence and DB reopen on selected path
  - tests: path change/restart behavior on Windows path edge-cases
- `TASK_18C5FA49-0E96-4009-B903-A12AA581F7AA`:
  - compile: `python -m compileall mindnavigator/workspaces/settings_workspace.py mindnavigator/storage.py`
  - auto-tests: action triggers DB update path + remote version check (mocked)
  - tests: manual click on "Check update" with online/offline scenarios
- `TASK_E32E5C80-2EC6-4663-A336-5DD0BE013784`:
  - compile: `python -m compileall mindnavigator/workspaces/settings_workspace.py mindnavigator/main_window.py`
  - auto-tests: language setting persistence and runtime apply
  - tests: manual switch EN/RU/DE/FR/ZH and verify key UI texts
- `TASK_14D8E869-90D7-48F1-A1F0-0509FDFD039A`:
  - compile: `python -m compileall mindnavigator/workspaces/settings_workspace.py mindnavigator/main_window.py`
  - auto-tests: selected workspaces persisted and restored
  - tests: manual toggle checkboxes and workspace visibility

### Data Transfer
- `TASK_2639BE33-BC91-42E1-A3AC-A5402D06CCBD`:
  - compile: `python -m compileall mindnavigator`
  - auto-tests: CSV import/export round-trip tests with special chars, multiline text, delimiters
  - tests: manual import/export smoke on sample datasets
- `TASK_4266DF47-F05A-419E-931B-CC7675EF65D8`:
  - compile: `python -m compileall mindnavigator/workspaces`
  - auto-tests: UI action wiring tests for all target workspaces
  - tests: manual click-flow per workspace (tasks, collections, projects, notes, ideas, objects)

### UI Animation / Shell
- `TASK_585678D4-1572-45F1-9570-2B5E5F6817CB`:
  - compile: `python -m compileall mindnavigator/ui`
  - auto-tests: animation timing/target width boundary tests
  - tests: visual smoothness and interruption behavior (rapid hover/click)
- `TASK_420CB243-F7B0-479C-9652-B501AE4AC7DF`:
  - compile: `python -m compileall mindnavigator/ui/dialogs`
  - auto-tests: dialog animation state/lifecycle tests (show/close/reopen)
  - tests: manual open/close burst test for representative dialogs
- `TASK_5CCD9BE4-C5DC-4D14-98E9-231EB8D8E2A1`:
  - compile: `python -m compileall mindnavigator/ui/dialogs mindnavigator/workspaces`
  - auto-tests: reuse coverage via shared dialog animation hooks
  - tests: manual sweep of all dialogs for regressions and focus behavior
- `TASK_905129B0-3848-4C30-9490-CFC00F5A838A`:
  - compile: `python -m compileall mindnavigator/main_window.py mindnavigator/ui`
  - auto-tests: sidebar expand/collapse state tests where possible
  - tests: manual hover interaction on desktop resolutions and overlap cases
- `TASK_E8446B40-0DA1-43CC-9206-FCC7EC37C0F0`:
  - compile: `python -m compileall mindnavigator/main_window.py mindnavigator/__main__.py`
  - auto-tests: notification payload routing to restore/open handlers
  - tests: manual tray restore from system notification click

### Domain Attachments
- `TASK_12A60D96-05E6-4868-91D5-0D2AA70B64CF`:
  - compile: `python -m compileall mindnavigator/storage.py mindnavigator/workspaces/tasks_workspace.py`
  - auto-tests: attachment class CRUD/serialization tests
  - tests: manual attachment create/open/remove flow
- `TASK_93B6AFF6-967A-403F-94C2-6CA6C9A2B0FD`:
  - compile: `python -m compileall mindnavigator/workspaces/tasks_workspace.py`
  - auto-tests: regression test for attaching idea entities to tasks
  - tests: manual attach-idea flow from task details

### Workspace Behavior / Fixes
- `TASK_E76B6B30-7CA6-4C6D-9B6F-B19AA473450B`:
  - compile: `python -m compileall mindnavigator/workspaces/maps_workspace.py`
  - auto-tests: maps simple-mouse mode prevents marker move
  - tests: manual drag attempts in simple vs normal modes
- `TASK_329B82A5-0968-4121-9E24-2983E0C430E2`:
  - compile: `python -m compileall mindnavigator/workspaces`
  - auto-tests: per-workspace list/model behavior tests for separators and quick form actions
  - tests: manual UX pass for notes/collections/ideas/objects including collection preview image
- `TASK_3ED7E7F2-C87E-4611-85D7-AF271D6E4D31`:
  - compile: `python -m compileall mindnavigator/workspaces/notes_workspace.py`
  - auto-tests: mandatory regression test for multiline save/load with line breaks
  - tests: manual multiline edit/save/reopen verification
- `TASK_04E6A669-898B-498F-827D-FD51B4C678D2`:
  - compile: `python -m compileall mindnavigator/workspaces/tasks_workspace.py`
  - auto-tests: mandatory regression test for immediate marker refresh in list model/delegate
  - tests: manual marker change and instant row refresh verification

### Static Analysis Closure
- `TASK_6BFC8077-FB99-46CE-876D-AEA9492371C6`:
  - compile: `python -m compileall mindnavigator main.py` after each error-type batch
  - auto-tests: run targeted pytest for touched modules after each error-type commit
  - tests: verify no behavior regressions for edited workspaces/dialogs

## Definition Of Done
- Each task is delivered in a dedicated commit with required prefix and task GUID.
- Validation matrix above is followed per task (compile + auto-tests + manual checks where defined).
- DB-related tasks validate migration + read/write paths together.
- For TASK_6BFC8077..., each static-analysis error type is fixed in a separate commit.
