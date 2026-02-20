from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

Point = tuple[int, int]


class DragPhase(str, Enum):
    IDLE = "idle"
    ARMING = "arming"
    DRAGGING = "dragging"
    DROPPING = "dropping"
    CANCELED = "canceled"


@dataclass(slots=True)
class DragPayload:
    entity_type: str
    entity_id: str | int
    source_workspace: str
    meta: dict[str, Any] = field(default_factory=dict)

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "source_workspace": self.source_workspace,
            "meta": dict(self.meta),
        }


@dataclass(slots=True)
class MotionConfig:
    profile: str = "ease_out"
    duration_ms: int = 140
    max_step_px: int = 96
    ghost_opacity: float = 0.86
    ghost_scale: float = 1.0
    ghost_invalid_opacity: float = 0.58
    ghost_invalid_scale: float = 0.95
    hover_scale_boost: float = 1.02
    drop_success_duration_ms: int = 120
    drop_failure_duration_ms: int = 180

    def validate(self) -> None:
        if self.profile not in {"linear", "ease_out", "spring_soft"}:
            raise ValueError("Unsupported motion profile.")
        if self.duration_ms < 1:
            raise ValueError("duration_ms must be >= 1.")
        if self.max_step_px < 1:
            raise ValueError("max_step_px must be >= 1.")
        if not (0.0 <= self.ghost_opacity <= 1.0):
            raise ValueError("ghost_opacity must be in [0.0, 1.0].")
        if not (0.0 <= self.ghost_invalid_opacity <= 1.0):
            raise ValueError("ghost_invalid_opacity must be in [0.0, 1.0].")
        if self.ghost_scale <= 0.0:
            raise ValueError("ghost_scale must be > 0.0.")
        if self.ghost_invalid_scale <= 0.0:
            raise ValueError("ghost_invalid_scale must be > 0.0.")
        if self.hover_scale_boost <= 0.0:
            raise ValueError("hover_scale_boost must be > 0.0.")
        if self.drop_success_duration_ms < 1:
            raise ValueError("drop_success_duration_ms must be >= 1.")
        if self.drop_failure_duration_ms < 1:
            raise ValueError("drop_failure_duration_ms must be >= 1.")


@dataclass(slots=True)
class DragSessionState:
    phase: DragPhase = DragPhase.IDLE
    start_pos_global: Point = (0, 0)
    current_pos_global: Point = (0, 0)
    target_zone_id: str | None = None
    is_target_valid: bool = False
    started_at_ms: int = 0
    last_frame_ms: int = 0

    def transition(self, next_phase: DragPhase) -> None:
        allowed = {
            DragPhase.IDLE: {DragPhase.ARMING},
            DragPhase.ARMING: {DragPhase.DRAGGING, DragPhase.CANCELED},
            DragPhase.DRAGGING: {DragPhase.DROPPING, DragPhase.CANCELED},
            DragPhase.DROPPING: {DragPhase.IDLE},
            DragPhase.CANCELED: {DragPhase.IDLE},
        }
        if next_phase not in allowed[self.phase]:
            raise ValueError(f"Invalid transition: {self.phase.value} -> {next_phase.value}")
        self.phase = next_phase

    def update_position(self, pos_global: Point, now_ms: int) -> None:
        self.current_pos_global = pos_global
        self.last_frame_ms = now_ms

    def set_target(self, zone_id: str | None, is_valid: bool) -> None:
        self.target_zone_id = zone_id
        self.is_target_valid = is_valid

    def reset(self) -> None:
        self.phase = DragPhase.IDLE
        self.start_pos_global = (0, 0)
        self.current_pos_global = (0, 0)
        self.target_zone_id = None
        self.is_target_valid = False
        self.started_at_ms = 0
        self.last_frame_ms = 0

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "start_pos_global": self.start_pos_global,
            "current_pos_global": self.current_pos_global,
            "target_zone_id": self.target_zone_id,
            "is_target_valid": self.is_target_valid,
            "started_at_ms": self.started_at_ms,
            "last_frame_ms": self.last_frame_ms,
        }
