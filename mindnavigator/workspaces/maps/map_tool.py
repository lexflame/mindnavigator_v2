"""MapTool class module for maps workspace."""

from __future__ import annotations

from enum import Enum, auto

class MapTool(Enum):
    SELECT = auto()
    ADD_MARKER = auto()
    ADD_REGION = auto()
    MEASURE = auto()


def marker_drag_allowed(tool: MapTool, simple_mouse_mode: bool) -> bool:
    return tool == MapTool.SELECT and not simple_mouse_mode

__all__ = ["MapTool", "marker_drag_allowed"]
