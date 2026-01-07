
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QWheelEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QGraphicsView


class MapGraphicsView(QGraphicsView):
    viewChanged = Signal()
    mouseSceneMoved = Signal(float, float)
    clickedScene = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        # QGraphicsView.setRenderHints expects QPainter.RenderHints.
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

    def mouseMoveEvent(self, e: QMouseEvent):
        p = self.mapToScene(e.position().toPoint())
        self.mouseSceneMoved.emit(float(p.x()), float(p.y()))
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            p = self.mapToScene(e.position().toPoint())
            self.clickedScene.emit(float(p.x()), float(p.y()))
        super().mousePressEvent(e)

    def wheelEvent(self, e: QWheelEvent):
        factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(factor, factor)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.viewChanged.emit()
        super().wheelEvent(e)

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        self.viewChanged.emit()
