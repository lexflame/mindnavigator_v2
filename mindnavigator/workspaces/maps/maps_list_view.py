"""MapsListView class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .maps_item_delegate import MapsItemDelegate

class MapsListView(QListView):
    editRequested = Signal(QModelIndex)
    openRequested = Signal(QModelIndex)

    def mousePressEvent(self, event):
        # Обрабатываем клики по кнопкам внутри делегата.
        index = self.indexAt(event.pos())
        if index.isValid():
            delegate = self.itemDelegate()
            if isinstance(delegate, MapsItemDelegate):
                rect = self.visualRect(index)
                layout = delegate.row_layout(rect)
                if layout["edit_btn"].contains(event.pos()):
                    self.editRequested.emit(index)
                    return
                if layout["open_btn"].contains(event.pos()):
                    self.openRequested.emit(index)
                    return
        # Передаем событие стандартной реализации.
        super().mousePressEvent(event)

__all__ = ["MapsListView"]
