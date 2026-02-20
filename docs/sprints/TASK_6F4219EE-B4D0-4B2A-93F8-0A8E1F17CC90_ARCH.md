# Architecture Design: TASK_6F4219EE-B4D0-4B2A-93F8-0A8E1F17CC90

## Title
MVP architecture for reusable smooth Drag&Drop.

## Objective
Define an implementation-ready MVP design for a `DragDropController` that centralizes drag state, validation, and smooth motion policies while keeping rendering in View.

## Current Context (Codebase)
- Existing drag/drop toggling exists in `mindnavigator/workspaces/tasks_workspace.py:3909`.
- Notes workspace explicitly disables drag/drop and has a TODO for nested movement in `mindnavigator/workspaces/notes_workspace.py:679`.
- Current behavior is widget-local and not reusable as a cross-workspace component.

## Target Architecture (MVP)

### Model Layer
1. `DragPayload`
- `entity_type: str`
- `entity_id: str | int`
- `source_workspace: str`
- `meta: dict[str, object]`

2. `DragSessionState`
- `phase: Literal[idle, arming, dragging, dropping, canceled]`
- `start_pos_global: QPoint`
- `current_pos_global: QPoint`
- `target_zone_id: str | None`
- `is_target_valid: bool`
- `started_at_ms: int`
- `last_frame_ms: int`

3. `MotionConfig`
- `profile: Literal[linear, ease_out, spring_soft]`
- `duration_ms: int`
- `max_step_px: int`
- `ghost_opacity: float`
- `ghost_scale: float`

### Presenter Layer
`DragDropController` is the orchestration unit.

Responsibilities:
- Receive pointer/key events from View.
- Control state transitions.
- Resolve active drop zone via hit testing service.
- Validate drop via policy service.
- Emit render instructions to View (ghost position, target highlight, drop animation hint).
- Emit domain callback events (commit move, cancel).

Public API:
- `arm_drag(payload: DragPayload, start_pos_global: QPoint) -> None`
- `on_pointer_move(pos_global: QPoint, now_ms: int) -> None`
- `on_pointer_release(pos_global: QPoint, now_ms: int) -> None`
- `on_cancel(reason: str) -> None`
- `reset() -> None`

Lifecycle hooks:
- `on_drag_started(payload, state)`
- `on_drag_moved(state)`
- `on_drop_requested(payload, zone_id)`
- `on_drop_committed(payload, zone_id)`
- `on_drag_canceled(reason)`

### View Layer Contract
View remains passive and only handles rendering/input forwarding.

Required View interface:
- `view_get_drop_zones() -> list[DropZoneRect]`
- `view_render_drag_ghost(payload, pos_global, opacity, scale) -> None`
- `view_render_zone_feedback(zone_id: str | None, is_valid: bool) -> None`
- `view_clear_drag_visuals() -> None`
- `view_play_drop_result(success: bool) -> None`
- `view_map_to_local(pos_global: QPoint) -> QPoint`

### Domain Policy Interfaces
1. `DropValidator`
- `validate(payload: DragPayload, zone_id: str) -> bool`

2. `DropExecutor`
- `execute(payload: DragPayload, zone_id: str) -> bool`

3. `HitTestService`
- `resolve_zone(pos_global: QPoint, zones: list[DropZoneRect]) -> str | None`

## State Machine
1. `idle -> arming`: pointer down + payload available.
2. `arming -> dragging`: threshold reached by distance/time.
3. `dragging -> dropping`: pointer release.
4. `dropping -> idle`: successful/failed finalize.
5. `dragging -> canceled`: Esc, out-of-bounds policy, or hard invalidation.
6. `canceled -> idle`: cleanup completed.

## Integration Plan
1. Create reusable module:
- `mindnavigator/ui/dragdrop/controller.py`
- `mindnavigator/ui/dragdrop/model.py`
- `mindnavigator/ui/dragdrop/policy.py`

2. Integrate in `tasks_workspace.py` first:
- Replace direct mode toggles with controller bootstrap + event forwarding.

3. Integrate in `notes_workspace.py` second:
- Implement nested zone tree mapping and validator rules.

## Refactor Boundaries
- Do not change domain storage logic in this task.
- Do not redesign entire widget hierarchy.
- Limit refactor to event wiring and drag/drop behavior surfaces.

## Test Strategy (Design-Level)
- Unit: state machine transitions and threshold logic.
- Unit: validator and hit-test contract behavior.
- Integration: workspace event forwarding and drop commit path.
- Regression: cancel flow and invalid target visual reset.

## Done Criteria For This Task
- MVP contracts are explicit and implementation-ready.
- Reuse path across at least two workspaces is defined.
- Clear refactor boundaries and test strategy are documented.
