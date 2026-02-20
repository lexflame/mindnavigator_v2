# Smooth Scroll Integration Guide

## Overview
`mindnavigator/ui/smooth_scroll.py` provides a reusable controller to smooth wheel-based scrolling on Qt scroll areas.

## Quick Start
```python
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll

self._smooth_scroll_controllers = [
    attach_smooth_scroll(self.list_view),
    attach_smooth_scroll(self.tree_widget),
]
```

Keep controller references on the workspace/object (`self`) so event filters remain alive.

## Tuning Knobs
- `frame_interval_ms`: animation tick interval.
- `easing_factor`: interpolation aggressiveness.
- `wheel_step_px`: default wheel step for angle deltas.
- `max_step_px`: per-tick max movement.
- `max_pending_px`: queued delta cap under wheel bursts.
- `min_effective_delta_px`: ignores tiny deltas to reduce overhead.
- `adaptive_step_from_page`: adapts max step to scrollbar page size.
- `horizontal`: enables horizontal scrolling mode.

## Runtime Diagnostics
`SmoothScrollController.snapshot_stats()` returns counters for:
- wheel events,
- applied animation steps,
- target clamps,
- stall-triggered cancels.

Use `reset_stats()` between profiling windows.

## Manual Demo
- Build helper: `mindnavigator.ui.smooth_scroll_demo.build_smooth_scroll_demo_widget()`
- Intended for quick manual validation during UI development.
