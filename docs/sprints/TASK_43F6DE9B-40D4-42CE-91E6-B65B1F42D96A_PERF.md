# Implementation Notes: TASK_43F6DE9B-40D4-42CE-91E6-B65B1F42D96A

## Title
Performance and stability for Drag&Drop loop.

## Implemented
1. Added performance config:
- `DragPerformanceConfig(min_render_interval_ms, sample_every_frames)`

2. Added runtime perf snapshots:
- `DragPerformanceSnapshot(frame_count, dropped_frames, avg_move_us, max_move_us)`
- callback hook: `on_performance_sample(snapshot)`

3. Added frame throttling:
- skips rendering on too-frequent updates;
- tracks dropped-frame count.

4. Added lightweight profiling:
- measures move handler duration with `perf_counter_ns`;
- emits periodic perf samples.

5. Tests:
- render throttling behavior;
- perf sample hook emission.

## Validation Result
- `python -m compileall mindnavigator/ui/dragdrop/controller.py tests/test_dragdrop_controller.py` passed.
- `python -m pytest tests/test_dragdrop_controller.py -q` blocked: `No module named pytest`.
