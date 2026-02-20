from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .model import DragPayload, DragPhase, DragSessionState, MotionConfig, Point
from .policy import AcceptAllValidator, DefaultHitTestService, DropZoneRect, DropExecutor, DropValidator, HitTestService


@dataclass(slots=True)
class DragStartThreshold:
    distance_px: int = 4
    hold_ms: int = 50


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

        self.state = DragSessionState()
        self.payload: DragPayload | None = None
        self._motion.validate()

        self.on_drag_started: Callable[[DragPayload, DragSessionState], None] | None = None
        self.on_drag_moved: Callable[[DragSessionState], None] | None = None
        self.on_drop_requested: Callable[[DragPayload, str], None] | None = None
        self.on_drop_committed: Callable[[DragPayload, str], None] | None = None
        self.on_drag_canceled: Callable[[str], None] | None = None

    def arm_drag(self, payload: DragPayload, start_pos_global: Point, now_ms: int) -> None:
        self.reset()
        self.payload = payload
        self.state.start_pos_global = start_pos_global
        self.state.current_pos_global = start_pos_global
        self.state.started_at_ms = now_ms
        self.state.last_frame_ms = now_ms
        self.state.transition(DragPhase.ARMING)

    def on_pointer_move(self, pos_global: Point, now_ms: int) -> None:
        if self.payload is None or self.state.phase == DragPhase.IDLE:
            return

        self.state.update_position(pos_global, now_ms)
        if self.state.phase == DragPhase.ARMING and not self._threshold_reached(pos_global, now_ms):
            return

        if self.state.phase == DragPhase.ARMING:
            self.state.transition(DragPhase.DRAGGING)
            self._emit_drag_started()

        if self.state.phase != DragPhase.DRAGGING:
            return

        zone_id = self._resolve_zone(pos_global)
        is_valid = bool(zone_id and self._validator.validate(self.payload, zone_id))
        self.state.set_target(zone_id, is_valid)
        self._render_drag_ghost(
            self.payload,
            pos_global,
            self._motion.ghost_opacity,
            self._motion.ghost_scale,
        )
        self._render_zone_feedback(zone_id, is_valid)
        if self.on_drag_moved:
            self.on_drag_moved(self.state)

    def on_pointer_release(self, pos_global: Point, now_ms: int) -> None:
        if self.payload is None:
            return

        self.state.update_position(pos_global, now_ms)
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
            if success and self.on_drop_committed:
                self.on_drop_committed(self.payload, zone_id)

        self._play_drop_result(success)
        self.reset()

    def on_cancel(self, reason: str) -> None:
        if self.payload is None or self.state.phase == DragPhase.IDLE:
            return
        self._cancel_internal(reason)

    def reset(self) -> None:
        self.payload = None
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
        if self.payload is not None and self.on_drag_started:
            self.on_drag_started(self.payload, self.state)
