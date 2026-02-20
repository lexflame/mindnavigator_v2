# Implementation Notes: TASK_C4D406F4-3D37-43D8-A3BE-4D6B655B4A8A

## Title
Smooth motion engine for Drag&Drop ghost movement.

## Implemented
1. Motion interpolation in `DragDropController`:
- Frame-synced delta by `now_ms - last_render_ms`
- Profile-based easing:
  - `linear`
  - `ease_out`
  - `spring_soft`

2. Visual position state:
- Internal `self._visual_pos`
- Internal `self._last_render_ms`
- Reset behavior for visual state on `reset()`

3. Safety constraints:
- Step clamping with `max_step_px` per axis
- Motion config validation reused from `MotionConfig`

4. Tests:
- Added interpolation and clamp tests in `tests/test_dragdrop_controller.py`

## Validation Result
- `python -m compileall mindnavigator/ui/dragdrop tests/test_dragdrop_controller.py` passed.
- `python -m pytest tests/test_dragdrop_controller.py -q` blocked: `No module named pytest`.
