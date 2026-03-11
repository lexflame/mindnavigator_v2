"""MindDrawNodeItem class module for minddraw workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class MindDrawNodeItem(QGraphicsRectItem):
    """Scene item that represents one node and reports position changes."""

    _ACCENT_COLORS = {
        "": "#61708a",
        "task": "#e3a53f",
        "project": "#5ea4e8",
        "idea": "#d971a7",
        "note": "#71c0b8",
        "map": "#b998f0",
        "object": "#7dbb74",
        "character": "#e8876d",
        "file": "#8aa6d9",
        "collection": "#c9a36a",
        "purchase": "#d6c36f",
    }

    def __init__(self, state: MindDrawNodeState, moved_callback: Callable[[str, QPointF], None]) -> None:
        super().__init__(QRectF(0, 0, 240, 82))
        self.node_id = state.node_id
        self._moved_callback = moved_callback
        self._title_item = QGraphicsSimpleTextItem("", self)
        self._meta_item = QGraphicsSimpleTextItem("", self)
        self._accent_color = QColor(self._ACCENT_COLORS[""])
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor("#353c48"), 1.2))
        self.setBrush(QColor("#1d2129"))
        self._title_item.setBrush(QColor("#ecf2ff"))
        self._meta_item.setBrush(QColor("#9fb3d4"))
        title_font = QFont(self._title_item.font())
        title_font.setBold(True)
        self._title_item.setFont(title_font)
        meta_font = QFont(self._meta_item.font())
        meta_font.setPointSizeF(max(8.0, meta_font.pointSizeF() - 0.5))
        self._meta_item.setFont(meta_font)
        self.set_state(state)

    def set_state(self, state: MindDrawNodeState) -> None:
        """Refresh title and metadata from latest node state."""

        self._accent_color = QColor(self._ACCENT_COLORS.get((state.entity_kind or "").strip().lower(), self._ACCENT_COLORS[""]))
        self._title_item.setText(self._shorten(state.title, limit=26))
        meta = ""
        if state.entity_kind and state.entity_id:
            meta = f"{state.entity_kind.upper()} #{state.entity_id}"
        elif state.entity_title:
            meta = state.entity_title
        self._meta_item.setText(self._shorten(meta, limit=32))
        self.setToolTip("\n".join(part for part in (state.title, meta) if part))
        self._title_item.setPos(18.0, 16.0)
        self._meta_item.setPos(18.0, 47.0)

    @staticmethod
    def _shorten(text: str, *, limit: int) -> str:
        normalized = (text or "").strip()
        if len(normalized) <= limit:
            return normalized
        return f"{normalized[: max(0, limit - 1)].rstrip()}…"

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()
        frame_rect = rect.adjusted(0.6, 0.6, -0.6, -0.6)

        border_color = QColor("#353c48")
        fill_color = QColor("#1d2129")
        glow_color = QColor("#202733")
        if self.isSelected():
            border_color = QColor("#f0b14a")
            fill_color = QColor("#252b35")
            glow_color = QColor("#2b3341")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow_color)
        painter.drawRoundedRect(frame_rect.adjusted(0.0, 2.0, 0.0, 2.0), 16.0, 16.0)

        painter.setBrush(fill_color)
        painter.setPen(QPen(border_color, 1.4))
        painter.drawRoundedRect(frame_rect, 16.0, 16.0)

        accent_rect = QRectF(frame_rect.left() + 10.0, frame_rect.top() + 10.0, 6.0, frame_rect.height() - 20.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent_color)
        painter.drawRoundedRect(accent_rect, 3.0, 3.0)

        meta_rect = QRectF(frame_rect.left() + 18.0, frame_rect.bottom() - 24.0, frame_rect.width() - 36.0, 14.0)
        painter.setBrush(QColor(255, 255, 255, 14) if self.isSelected() else QColor(255, 255, 255, 10))
        painter.drawRoundedRect(meta_rect, 7.0, 7.0)

    def itemChange(self, change, value):  # noqa: N802 - Qt API
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._moved_callback(self.node_id, QPointF(value))
        return super().itemChange(change, value)

__all__ = ["MindDrawNodeItem"]
