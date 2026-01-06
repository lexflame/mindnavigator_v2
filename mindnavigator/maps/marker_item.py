
from __future__ import annotations
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen, QBrush
from PySide6.QtWidgets import QGraphicsItem


class MarkerItem(QGraphicsItem):
    def __init__(self, marker_id: int, title: str, x: float, y: float, color: str | None = None):
        super().__init__()
        self.marker_id = marker_id
        self.title = title
        self._r = 8
        self.setPos(x, y)
        self.setZValue(10)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self._color = QColor(color) if color else QColor(80, 200, 120)

    def boundingRect(self) -> QRectF:
        return QRectF(-80, -20, 220, 40)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.Antialiasing, True)
        painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(-self._r, -self._r, self._r * 2, self._r * 2)
        painter.setPen(QColor(230, 230, 230))
        painter.drawText(QRectF(12, -10, 200, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)
