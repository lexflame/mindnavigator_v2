# Sprint 10 Extension: MutaBoard Mode

## Sprint Status
- Planned: 2026-05-14
- Status: Proposed
- Branch: `docs/mutaboard-sprint-plan`
- Workstream: new mixed-entity workspace mode

## Sprint Goal
Deliver a new `Мутаборд` mode as a unified operational board for `tasks`, `ideas`, and `objects`, focused on transformation flow rather than task-only planning.

## Product Directives
- Build `Мутаборд` as a standalone workspace, not as another sub-mode inside `TasksWorkspace`.
- Keep V1 storage-light: derive board stages from existing task, idea, and object fields instead of introducing new persistence schema immediately.
- Use one unified board card model so filtering, rendering, selection, and drag policy stay cheap and coherent.
- Preserve stable behavior of existing `tasks`, `ideas`, and `objects` workspaces; `Мутаборд` should integrate with them, not replace them.
- Prioritize mutation actions over visual complexity: the mode must support turning ideas and objects into actionable work.

## V1 Scope
### 1. Core mode
- Add a new workspace `Мутаборд` with a board-only presentation.
- Show mixed cards for `task`, `idea`, and `object` entities in one board.
- Add a right-side inspector for card details and actions.

### 2. Lifecycle columns
- Use lifecycle-oriented columns shared by all entity kinds:
- `inbox`
- `thinking`
- `prep`
- `active`
- `review`
- `done`
- `frozen`

### 3. Entity coverage
- `task`: full participation in board flow, including drag between stages.
- `idea`: visible in the same board, with controlled drag only where stage-to-status mapping is unambiguous.
- `object`: visible in the same board, but V1 should default to read-mostly behavior unless object status semantics are explicitly mapped.

### 4. Mutation actions
- `idea -> create task`
- `idea -> link to existing task`
- `object -> create task`
- `object -> create idea`
- `task -> link to idea`
- `task -> link to object`

### 5. Filters
- Filter by entity kind: `all / tasks / ideas / objects`
- Filter by project
- Filter by actionable-only
- Filter by linked/unlinked
- Search by title/subtitle

## Explicit V1 Non-Goals
- No new `mutaboard_stage` columns in `tasks`, `ideas`, or `objects`.
- No dedicated `mutaboard_cards` table.
- No graph canvas or flow-map visualization.
- No batch multi-entity mutation actions.
- No custom swimlanes or user-defined board schemas.
- No AI-generated classification or auto-routing.

## Workspace Architecture
### New package
- `mindnavigator/workspaces/mutaboard/__init__.py`
- `mindnavigator/workspaces/mutaboard/module_impl.py`
- `mindnavigator/workspaces/mutaboard/_shared.py`
- `mindnavigator/workspaces/mutaboard/mutaboard_workspace.py`
- `mindnavigator/workspaces/mutaboard/mutaboard_model.py`
- `mindnavigator/workspaces/mutaboard/mutaboard_card.py`
- `mindnavigator/workspaces/mutaboard/mutaboard_delegate.py`

### Core view-model
Introduce one board card dataclass for all entity kinds.

Recommended shape:
- `entity_kind`
- `entity_id`
- `title`
- `subtitle`
- `stage`
- `project_id`
- `project_title`
- `accent_color`
- `meta_text`
- `linked_task_count`
- `linked_idea_count`
- `linked_object_count`
- `can_drag`
- `can_mutate`
- `source_payload`

### Mapping rules
Board stage must be derived in V1.

For `task`:
- deferred priority -> `frozen`
- queue board column -> `prep`
- in-progress board column -> `active`
- completed board column or done flag -> `done`

For `idea`:
- `inbox` -> `inbox`
- `ripe` -> `thinking`
- `work` -> `prep`
- `done` -> `done`
- `archived` -> `frozen`

For `object`:
- archive-like status -> `frozen`
- active/work-like status -> `active`
- default unresolved state -> `thinking` or `prep`

## Integration Points
### Main window
Update:
- `mindnavigator/window/collections/main_window.py`

Required changes:
- add `MODE_MUTABOARD`
- import `MutaBoardWorkspace`
- create `self.page_mutaboard`
- register page in `_page_index`
- include in `_workspace_mode_map()`
- include in ordered mode cycling
- include in `_workspace_context_name()`
- add refresh branch in `set_mode()`

### Left rail
Update:
- `mindnavigator/ui/leftrail.py`

Required changes:
- add `btn_mutaboard`
- add icon and tooltip
- include in `_mode_buttons`
- include in top mode order

### Settings visibility
Update:
- `mindnavigator/workspaces/settings/settings_workspace.py`

Required changes:
- add `("mutaboard", "Мутаборд")` to `WORKSPACE_OPTIONS`

## Existing Modules To Reuse
- `mindnavigator/workspaces/tasks/cast_board/panel.py` for board-column layout patterns
- `mindnavigator/workspaces/minddraw/minddraw_workspace.py` for mixed-entity fetch patterns
- existing task, idea, and object dialogs/details surfaces
- `mindnavigator/ui/dragdrop/` infrastructure for controlled drag policy

## Existing Modules Not To Reuse As Base Models
- `mindnavigator/workspaces/tasks/tasks_model.py`
- `mindnavigator/workspaces/ideas/ideas_list_model.py`
- `mindnavigator/workspaces/objects/objects_model.py`

These are entity-specific and should stay isolated.

## Storage And Service Layer
### V1 rule
Prefer workspace/service composition over schema changes.

### Existing database methods to use
- `fetch_tasks()`
- `fetch_ideas(archived=True)`
- `fetch_objects()`
- existing task board/status update methods
- existing task and idea creation methods

### Optional new facade methods
Only add these if mutation glue becomes noisy at workspace level:
- `create_task_from_idea(idea_id, *, project_id=None)`
- `create_task_from_object(object_id, *, project_id=None)`
- `create_idea_from_object(object_id, *, project_id=None)`
- `set_idea_status(idea_id, status)`

## UI Structure
### Top area
- search
- entity-kind filter
- project filter
- actionable-only toggle
- linked/unlinked toggle

### Center area
- horizontal board with lifecycle columns
- compact mixed-type cards

### Right area
- inspector with details
- mutation actions
- relation actions

## Drag And Drop Policy
### Allowed in V1
- `task`: full stage drag
- `idea`: controlled stage drag where stage maps cleanly to idea status

### Limited or blocked in V1
- `object`: either read-only or restricted drag until object-stage semantics are explicit

## Phased Rollout
### Phase 1 - Workspace Registration
- Create `mutaboard` package skeleton.
- Register mode in main window, left rail, and settings visibility.
- Add empty workspace page with title and placeholder.

### Phase 2 - Unified Card Model
- Add `MutaBoardCard`.
- Build `MutaBoardModel` that fetches tasks, ideas, and objects.
- Implement stage derivation and core filters.

### Phase 3 - Board UI
- Render lifecycle columns.
- Render mixed cards with type accents and metadata.
- Support selection and inspector synchronization.

### Phase 4 - Task And Idea Flow
- Add task drag between stages.
- Add idea stage updates where mapping is safe.
- Keep object behavior conservative.

### Phase 5 - Mutation Actions
- Add inspector-driven create/link actions:
- idea to task
- object to task
- object to idea
- task to idea/object links

### Phase 6 - Validation And Hardening
- Add focused tests.
- Validate visibility wiring, mode switching, mixed filtering, and mutation commands.
- Reassess whether V2 needs persistent `mutaboard_stage`.

## Task Decomposition Matrix
| Phase | Type | Scope | Dependencies | Validation | Rollback |
| --- | --- | --- | --- | --- | --- |
| Phase 1 | feat | Add new workspace package and register `Мутаборд` in window, rail, and settings. | None | compileall; focused tests for workspace visibility and mode map | Revert workspace registration and new package skeleton |
| Phase 2 | feat | Implement unified mixed-card model and derived stage mapping for tasks, ideas, and objects. | Phase 1 | compileall; focused model tests for stage mapping and filters | Revert model package while keeping empty workspace shell |
| Phase 3 | feat | Build board UI, mixed-card delegate, and inspector shell. | Phases 1-2 | compileall; focused workspace tests for rendering and selection | Revert delegate/workspace UI while keeping model |
| Phase 4 | feat | Enable controlled drag for tasks and mapped idea transitions. | Phases 2-3; existing drag/drop infra | compileall; focused drag tests | Disable drag paths and keep board read-only |
| Phase 5 | feat | Add mutation actions between idea, object, and task entities. | Phases 2-4; existing create/update APIs | compileall; focused action tests | Revert mutation commands and keep board read-only |
| Phase 6 | test/docs | Regression coverage, UX tightening, and V2 persistence decision. | Phases 1-5 | focused pytest plus broader regression if stable | Revert only docs/tests if feature must be split |

## First Test Package
### New tests
- `tests/test_mutaboard_model.py`
- `tests/test_mutaboard_workspace.py`
- `tests/test_mutaboard_actions.py`
- `tests/test_mutaboard_visibility.py`

### Coverage targets
- mixed entity fetch and mapping
- filtering by kind and project
- stage derivation rules
- inspector updates on selection
- task drag behavior
- idea status drag behavior
- mutation actions
- visibility settings integration

### Existing tests likely affected
- `tests/test_workspace_visibility_settings.py`
- main-window mode map and mode-switch tests

## Validation Order
1. `python -m compileall mindnavigator main.py`
2. Focused tests for workspace registration and visibility
3. Focused tests for mutaboard model mapping
4. Focused tests for workspace behavior and mutation actions
5. Broader `pytest` run only after drag and mutation flows stabilize

## Risks
- Embedding `Мутаборд` into `TasksWorkspace` would create a mixed-responsibility monolith.
- Introducing persistence too early risks freezing a bad stage model for ideas and objects.
- Free drag for objects without explicit lifecycle semantics will make UI behavior incoherent.
- Without a right-side inspector, mixed-card density will reduce clarity too much.

## V2 Decision Gate
Only consider persistent `mutaboard_stage` after V1 proves that:
- derived mapping is insufficient,
- object lifecycle semantics are stable,
- users need cross-entity custom staging independent of native task/idea/object fields.
