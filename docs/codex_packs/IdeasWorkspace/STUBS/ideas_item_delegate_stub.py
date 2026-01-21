"""Item delegate stub for idea cards.

If you already have a card-style delegate pattern in the project, copy it and adapt.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QStyledItemDelegate

from .ideas_list_model_stub import IdeasListModel


class IdeasItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        # TODO: return card height
        return QSize(option.rect.width(), 68)

    def paint(self, painter: QPainter, option, index):
        # TODO: draw rounded card, title, status, scores, tags
        painter.save()
        rect = option.rect
        title = index.data(IdeasListModel.ROLE_TITLE)
        status = index.data(IdeasListModel.ROLE_STATUS)
        value_score = index.data(IdeasListModel.ROLE_VALUE)
        effort_score = index.data(IdeasListModel.ROLE_EFFORT)

        # Placeholder minimal rendering
        painter.drawText(QRect(rect.left() + 10, rect.top() + 6, rect.width() - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, str(title))
        painter.drawText(QRect(rect.left() + 10, rect.top() + 28, rect.width() - 20, 18), Qt.AlignLeft | Qt.AlignVCenter, f"{status}  ⭐{value_score}  ⚙{effort_score}")
        painter.restore()
