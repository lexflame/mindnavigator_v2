from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from mindnavigator.workspaces.maps.map_canvas import MapCanvas
from mindnavigator.workspaces.maps.map_tool import MapTool
from mindnavigator.workspaces.maps.marker import Marker


def _mouse_event(
    event_type: QMouseEvent.Type,
    pos: QPointF,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        pos,
        pos,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def _build_canvas(marker: Marker) -> MapCanvas:
    _app = QApplication.instance() or QApplication([])
    canvas = MapCanvas()
    canvas.resize(800, 600)
    canvas.set_markers([marker])
    return canvas


def test_move_mode_allows_drag_in_simple_mouse_mode() -> None:
    marker = Marker(1, "Alpha", 120.0, 140.0, QColor("#2f6edb"), "Point", 24.0)
    canvas = _build_canvas(marker)
    try:
        canvas.set_simple_mouse_mode(True)
        canvas._enable_move_mode(marker.id)

        start_pos = canvas._map_from_world(QPointF(marker.x, marker.y))
        target_world = QPointF(210.0, 260.0)
        target_pos = canvas._map_from_world(target_world)

        canvas.mousePressEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonPress,
                start_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
            )
        )
        canvas.mouseMoveEvent(
            _mouse_event(
                QMouseEvent.Type.MouseMove,
                target_pos,
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
            )
        )
        canvas.mouseReleaseEvent(
            _mouse_event(
                QMouseEvent.Type.MouseButtonRelease,
                target_pos,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,
            )
        )

        moved = canvas.markers()[0]
        assert moved.x == pytest.approx(target_world.x())
        assert moved.y == pytest.approx(target_world.y())
        assert canvas._move_marker_id == marker.id
    finally:
        canvas.deleteLater()


def test_escape_finishes_move_mode() -> None:
    marker = Marker(2, "Beta", 80.0, 95.0, QColor("#2f9f63"), "Point", 20.0)
    canvas = _build_canvas(marker)
    try:
        canvas._enable_move_mode(marker.id)

        canvas.keyPressEvent(
            QKeyEvent(
                QEvent.Type.KeyPress,
                int(Qt.Key.Key_Escape),
                Qt.KeyboardModifier.NoModifier,
            )
        )

        assert canvas._move_marker_id is None
        assert canvas._resize_marker_id is None
        assert canvas._selected is not None
        assert canvas._selected.id == marker.id
    finally:
        canvas.deleteLater()


def test_switching_tool_finishes_move_mode() -> None:
    marker = Marker(3, "Gamma", 150.0, 170.0, QColor("#d68a2f"), "Point", 22.0)
    canvas = _build_canvas(marker)
    try:
        canvas._enable_move_mode(marker.id)

        canvas.set_tool(MapTool.ADD_REGION)

        assert canvas._move_marker_id is None
        assert canvas._resize_marker_id is None
        assert canvas.tool() == MapTool.ADD_REGION
    finally:
        canvas.deleteLater()
