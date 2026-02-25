from __future__ import annotations

from mindnavigator.workspaces.maps_workspace import MapTool, marker_drag_allowed


def test_marker_drag_is_blocked_in_simple_mouse_mode() -> None:
    assert marker_drag_allowed(MapTool.SELECT, simple_mouse_mode=True) is False


def test_marker_drag_is_allowed_only_for_select_when_not_simple_mode() -> None:
    assert marker_drag_allowed(MapTool.SELECT, simple_mouse_mode=False) is True
    assert marker_drag_allowed(MapTool.ADD_MARKER, simple_mouse_mode=False) is False
    assert marker_drag_allowed(MapTool.ADD_REGION, simple_mouse_mode=False) is False
    assert marker_drag_allowed(MapTool.MEASURE, simple_mouse_mode=False) is False
