from __future__ import annotations

from dataclasses import dataclass, field

from .controller import DragDropController
from .model import DragPayload
from .policy import DropZoneRect


@dataclass(slots=True)
class DemoTrace:
    events: list[str] = field(default_factory=list)


def build_demo_controller(trace: DemoTrace | None = None) -> DragDropController:
    """Builds a minimal in-memory drag/drop demo controller for manual verification."""
    trace = trace or DemoTrace()
    zones = [DropZoneRect("demo-zone", 0, 0, 320, 220)]

    def render_drag_ghost(payload: DragPayload, pos, opacity: float, scale: float) -> None:
        trace.events.append(f"ghost:{payload.entity_id}:{pos}:{opacity:.2f}:{scale:.2f}")

    def render_zone_feedback(zone_id: str | None, is_valid: bool) -> None:
        trace.events.append(f"zone:{zone_id}:{is_valid}")

    def clear_drag_visuals() -> None:
        trace.events.append("clear")

    def play_drop_result(success: bool) -> None:
        trace.events.append(f"drop:{success}")

    controller = DragDropController(
        get_drop_zones=lambda: zones,
        render_drag_ghost=render_drag_ghost,
        render_zone_feedback=render_zone_feedback,
        clear_drag_visuals=clear_drag_visuals,
        play_drop_result=play_drop_result,
    )
    return controller
