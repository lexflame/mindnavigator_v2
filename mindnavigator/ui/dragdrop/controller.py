from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

from .model import DragPayload, DragPhase, DragSessionState, MotionConfig, Point
from .policy import AcceptAllValidator, DefaultHitTestService, DropZoneRect, DropExecutor, DropValidator, HitTestService


@dataclass(slots=True)
class DragStartThreshold:
    distance_px: int = 4
    hold_ms: int = 50


@dataclass(slots=True)
class DragSafetyConfig:
    cancel_on_leave_window: bool = True
    fast_move_threshold_px: int = 480


@dataclass(slots=True)
class DragPerformanceConfig:
    min_render_interval_ms: int = 8
    sample_every_frames: int = 20


@dataclass(slots=True)
class DragPerformanceSnapshot:
    frame_count: int
    dropped_frames: int
    avg_move_us: int
    max_move_us: int


class DragDropController:
    def __init__(
        self,
        *,
        get_drop_zones: Callable[[], list[DropZoneRect]],
        render_drag_ghost: Callable[[DragPayload, Point, float, float], None],
        render_zone_feedback: Callable[[str | None, bool], None],
        clear_drag_visuals: Callable[[], None],
        play_drop_result: Callable[[bool], None],
        validator: DropValidator | None = None,
        executor: DropExecutor | None = None,
        hit_test: HitTestService | None = None,
        motion: MotionConfig | None = None,
        threshold: DragStartThreshold | None = None,
        safety: DragSafetyConfig | None = None,
        performance: DragPerformanceConfig | None = None,
        is_within_window: Callable[[Point], bool] | None = None,
        normalize_position: Callable[[Point], Point] | None = None,
    ) -> None:
        self._get_drop_zones = get_drop_zones
        self._render_drag_ghost = render_drag_ghost
        self._render_zone_feedback = render_zone_feedback
        self._clear_drag_visuals = clear_drag_visuals
        self._play_drop_result = play_drop_result
        self._validator = validator or AcceptAllValidator()
        self._executor = executor
        self._hit_test = hit_test or DefaultHitTestService()
        self._motion = motion or MotionConfig()
        self._threshold = threshold or DragStartThreshold()
        self._safety = safety or DragSafetyConfig()
        self._performance = performance or DragPerformanceConfig()
        self._is_within_window = is_within_window
        self._normalize_position = normalize_position or (lambda p: p)

        self.state = DragSessionState()
        self.payload: DragPayload | None = None
        self._visual_pos: Point = (0, 0)
        self._last_render_ms: int = 0
        self._last_render_emit_ms: int = 0
        self._frame_count: int = 0
        self._dropped_frames: int = 0
        self._move_total_us: int = 0
        self._move_max_us: int = 0
        self._motion.validate()

        self.on_drag_started: Callable[[DragPayload, DragSessionState], None] | None = None
        self.on_drag_moved: Callable[[DragSessionState], None] | None = None
        self.on_drop_requested: Callable[[DragPayload, str], None] | None = None
        self.on_drop_committed: Callable[[DragPayload, str], None] | None = None
        self.on_drag_canceled: Callable[[str], None] | None = None
        self.on_drop_transition: Callable[[bool, int], None] | None = None
        self.on_performance_sample: Callable[[DragPerformanceSnapshot], None] | None = None

    def arm_drag(self, payload: DragPayload, start_pos_global: Point, now_ms: int) -> None:
        normalized_start = self._normalize_position(start_pos_global)
        self.reset()
        self.payload = payload
        self.state.start_pos_global = normalized_start
        self.state.current_pos_global = normalized_start
        self.state.started_at_ms = now_ms
        self.state.last_frame_ms = now_ms
        self._visual_pos = normalized_start
        self._last_render_ms = now_ms
        self._last_render_emit_ms = now_ms
        self._frame_count = 0
        self._dropped_frames = 0
        self._move_total_us = 0
        self._move_max_us = 0
        self.state.transition(DragPhase.ARMING)

    def on_pointer_move(self, pos_global: Point, now_ms: int) -> None:
        started_ns = time.perf_counter_ns()
        if self.payload is None or self.state.phase == DragPhase.IDLE:
            return

        normalized_pos = self._normalize_position(pos_global)
        if self._should_cancel_outside_window(normalized_pos):
            self._cancel_internal("out_of_window")
            return

        safe_pos = self._limit_fast_move(self.state.current_pos_global, normalized_pos)
        self.state.update_position(safe_pos, now_ms)
        if self.state.phase == DragPhase.ARMING and not self._threshold_reached(safe_pos, now_ms):
            return

        if self.state.phase == DragPhase.ARMING:
            self.state.transition(DragPhase.DRAGGING)
            self._emit_drag_started()

        if self.state.phase != DragPhase.DRAGGING:
            return

        zone_id = self._resolve_zone(safe_pos)
        is_valid = bool(zone_id and self._validator.validate(self.payload, zone_id))
        self.state.set_target(zone_id, is_valid)
        should_render = self._should_render_frame(now_ms)
        if not should_render:
            self._dropped_frames += 1
            self._record_move_timing(started_ns)
            return
        smooth_pos = self._compute_smooth_position(safe_pos, now_ms)
        self._render_drag_ghost(
            self.payload,
            smooth_pos,
            self._ghost_opacity(is_valid),
            self._ghost_scale(is_valid),
        )
        self._render_zone_feedback(zone_id, is_valid)
        if self.on_drag_moved:
            self.on_drag_moved(self.state)
        self._record_move_timing(started_ns)

    def on_pointer_release(self, pos_global: Point, now_ms: int) -> None:
        if self.payload is None:
            return

        normalized_pos = self._normalize_position(pos_global)
        if self._should_cancel_outside_window(normalized_pos):
            self._cancel_internal("released_outside_window")
            return
        self.state.update_position(normalized_pos, now_ms)
        if self.state.phase == DragPhase.ARMING:
            self._cancel_internal("released_before_drag")
            return
        if self.state.phase != DragPhase.DRAGGING:
            return

        self.state.transition(DragPhase.DROPPING)
        zone_id = self.state.target_zone_id
        success = bool(zone_id and self.state.is_target_valid)

        if success and zone_id:
            if self.on_drop_requested:
                self.on_drop_requested(self.payload, zone_id)
            if self._executor is not None:
                success = self._executor.execute(self.payload, zone_id)
            on_drop_committed = self.on_drop_committed
            if success and on_drop_committed is not None:
                on_drop_committed(self.payload, zone_id)

        transition_ms = self._motion.drop_success_duration_ms if success else self._motion.drop_failure_duration_ms
        if self.on_drop_transition:
            self.on_drop_transition(success, transition_ms)
        self._play_drop_result(success)
        self.reset()

    def on_cancel(self, reason: str) -> None:
        if self.payload is None or self.state.phase == DragPhase.IDLE:
            return
        self._cancel_internal(reason)

    def on_key_event(self, key: str) -> None:
        if key.lower() in {"escape", "esc"}:
            self.on_cancel("escape_key")

    def reset(self) -> None:
        self.payload = None
        self._visual_pos = (0, 0)
        self._last_render_ms = 0
        self._last_render_emit_ms = 0
        self._frame_count = 0
        self._dropped_frames = 0
        self._move_total_us = 0
        self._move_max_us = 0
        if self.state.phase != DragPhase.IDLE:
            self.state.reset()
        self._clear_drag_visuals()

    def _cancel_internal(self, reason: str) -> None:
        if self.state.phase in (DragPhase.ARMING, DragPhase.DRAGGING):
            self.state.transition(DragPhase.CANCELED)
        if self.on_drag_canceled:
            self.on_drag_canceled(reason)
        self.reset()

    def _resolve_zone(self, pos_global: Point) -> str | None:
        return self._hit_test.resolve_zone(pos_global, self._get_drop_zones())

    def _threshold_reached(self, pos_global: Point, now_ms: int) -> bool:
        sx, sy = self.state.start_pos_global
        px, py = pos_global
        dx = abs(px - sx)
        dy = abs(py - sy)
        distance_reached = (dx + dy) >= self._threshold.distance_px
        time_reached = (now_ms - self.state.started_at_ms) >= self._threshold.hold_ms
        return distance_reached or time_reached

    def _emit_drag_started(self) -> None:
        on_drag_started = self.on_drag_started
        if self.payload is not None and on_drag_started is not None:
            on_drag_started(self.payload, self.state)

    def _should_cancel_outside_window(self, pos_global: Point) -> bool:
        if not self._safety.cancel_on_leave_window:
            return False
        if self._is_within_window is None:
            return False
        return not self._is_within_window(pos_global)

    def _limit_fast_move(self, current: Point, target: Point) -> Point:
        max_jump = self._safety.fast_move_threshold_px
        if max_jump < 1:
            return target
        cx, cy = current
        tx, ty = target
        dx = tx - cx
        dy = ty - cy
        if abs(dx) <= max_jump and abs(dy) <= max_jump:
            return target
        clamped_x = cx + (max_jump if dx > 0 else -max_jump if dx < 0 else 0)
        clamped_y = cy + (max_jump if dy > 0 else -max_jump if dy < 0 else 0)
        return clamped_x, clamped_y

    def _ghost_opacity(self, is_valid: bool) -> float:
        return self._motion.ghost_opacity if is_valid else self._motion.ghost_invalid_opacity

    def _ghost_scale(self, is_valid: bool) -> float:
        if is_valid:
            return self._motion.ghost_scale * self._motion.hover_scale_boost
        return self._motion.ghost_invalid_scale

    def _compute_smooth_position(self, target: Point, now_ms: int) -> Point:
        dt_ms = max(0, now_ms - self._last_render_ms)
        self._last_render_ms = now_ms
        alpha = min(1.0, dt_ms / float(self._motion.duration_ms))
        eased = self._apply_profile(alpha)
        cx, cy = self._visual_pos
        tx, ty = target
        next_pos = (
            int(round(cx + (tx - cx) * eased)),
            int(round(cy + (ty - cy) * eased)),
        )
        self._visual_pos = self._clamp_step(self._visual_pos, next_pos, self._motion.max_step_px)
        return self._visual_pos

    def _should_render_frame(self, now_ms: int) -> bool:
        min_interval = self._performance.min_render_interval_ms
        if min_interval <= 0:
            self._last_render_emit_ms = now_ms
            return True
        if (now_ms - self._last_render_emit_ms) < min_interval:
            return False
        self._last_render_emit_ms = now_ms
        return True

    def _record_move_timing(self, started_ns: int) -> None:
        elapsed_us = int((time.perf_counter_ns() - started_ns) / 1000)
        self._frame_count += 1
        self._move_total_us += elapsed_us
        if elapsed_us > self._move_max_us:
            self._move_max_us = elapsed_us
        if self._frame_count % max(1, self._performance.sample_every_frames) == 0:
            avg = int(self._move_total_us / self._frame_count)
            if self.on_performance_sample:
                self.on_performance_sample(
                    DragPerformanceSnapshot(
                        frame_count=self._frame_count,
                        dropped_frames=self._dropped_frames,
                        avg_move_us=avg,
                        max_move_us=self._move_max_us,
                    )
                )

    def _apply_profile(self, alpha: float) -> float:
        if self._motion.profile == "linear":
            return alpha
        if self._motion.profile == "ease_out":
            return 1.0 - (1.0 - alpha) * (1.0 - alpha)
        if self._motion.profile == "spring_soft":
            return min(1.0, (1.0 - (1.0 - alpha) ** 3) * 1.08)
        return alpha

    @staticmethod
    def _clamp_step(current: Point, target: Point, max_step_px: int) -> Point:
        cx, cy = current
        tx, ty = target
        dx = tx - cx
        dy = ty - cy
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx <= max_step_px and abs_dy <= max_step_px:
            return target
        clamped_x = cx + (max_step_px if dx > 0 else -max_step_px if dx < 0 else 0)
        clamped_y = cy + (max_step_px if dy > 0 else -max_step_px if dy < 0 else 0)
        return clamped_x, clamped_y
