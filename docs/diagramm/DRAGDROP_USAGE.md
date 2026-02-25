# DragDrop Module Usage

## Module
`mindnavigator.ui.dragdrop`

## Quick Start
1. Create `DropZoneRect` list for your view.
2. Create `DragDropController` with:
- zone provider;
- ghost render callback;
- zone feedback callback;
- clear callback;
- drop result callback.
3. Forward view events:
- pointer press => `arm_drag(...)`
- pointer move => `on_pointer_move(...)`
- pointer release => `on_pointer_release(...)`
- Esc key => `on_key_event("Escape")`

## Example
```python
from mindnavigator.ui.dragdrop import DragDropController, DragPayload, DropZoneRect

zones = [DropZoneRect("task-zone", 0, 0, 300, 180)]
controller = DragDropController(
    get_drop_zones=lambda: zones,
    render_drag_ghost=lambda payload, pos, opacity, scale: None,
    render_zone_feedback=lambda zone_id, valid: None,
    clear_drag_visuals=lambda: None,
    play_drop_result=lambda success: None,
)
payload = DragPayload(entity_type="task", entity_id=1, source_workspace="tasks")
controller.arm_drag(payload, (10, 10), 0)
controller.on_pointer_move((30, 30), 60)
controller.on_pointer_release((30, 30), 80)
```

## Tuning
- Motion: `MotionConfig(profile, duration_ms, max_step_px, ...)`
- Safety: `DragSafetyConfig(cancel_on_leave_window, fast_move_threshold_px)`
- Performance: `DragPerformanceConfig(min_render_interval_ms, sample_every_frames)`

## Demo Helper
Use `build_demo_controller()` for a minimal in-memory demo flow with trace events.
