"""MindDrawNodeItem class module for minddraw workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class MindDrawNodeItem(QGraphicsRectItem):
    """Scene item that represents one node and reports position changes."""

    def __init__(self, state: MindDrawNodeState, moved_callback: Callable[[str, QPointF], None]) -> None:
        super().__init__(QRectF(0, 0, 220, 70))
        self.node_id = state.node_id
        self._moved_callback = moved_callback
        self._title_item = QGraphicsSimpleTextItem("", self)
        self._meta_item = QGraphicsSimpleTextItem("", self)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setPen(QPen(QColor("#3b4252"), 1.2))
        self.setBrush(QColor("#1f2430"))
        self._title_item.setBrush(QColor("#ecf2ff"))
        self._meta_item.setBrush(QColor("#9fb3d4"))
        self._meta_item.setScale(0.88)
        self.set_state(state)

    def set_state(self, state: MindDrawNodeState) -> None:
        """Refresh title and metadata from latest node state."""

        self._title_item.setText(state.title)
        meta = ""
        if state.entity_kind and state.entity_id:
            meta = f"{state.entity_kind}:{state.entity_id}"
        elif state.entity_title:
            meta = state.entity_title
        self._meta_item.setText(meta)
        title_width = self._title_item.boundingRect().width()
        meta_width = self._meta_item.boundingRect().width()
        self._title_item.setPos(max(10.0, 110.0 - title_width / 2.0), 14.0)
        self._meta_item.setPos(max(10.0, 110.0 - meta_width / 2.0), 40.0)

    def itemChange(self, change, value):  # noqa: N802 - Qt API
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._moved_callback(self.node_id, QPointF(value))
        return super().itemChange(change, value)

__all__ = ["MindDrawNodeItem"]
