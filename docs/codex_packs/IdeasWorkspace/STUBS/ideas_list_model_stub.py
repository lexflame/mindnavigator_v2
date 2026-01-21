"""Qt list model stub for ideas.

Use QAbstractListModel to render cards in QListView.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt

from .idea_model_stub import Idea


class IdeasListModel(QAbstractListModel):
    ROLE_ID = Qt.UserRole + 1
    ROLE_TITLE = Qt.UserRole + 2
    ROLE_STATUS = Qt.UserRole + 3
    ROLE_TYPE = Qt.UserRole + 4
    ROLE_VALUE = Qt.UserRole + 5
    ROLE_EFFORT = Qt.UserRole + 6
    ROLE_PROJECT_ID = Qt.UserRole + 7

    def __init__(self, ideas: Optional[List[Idea]] = None, parent=None):
        super().__init__(parent)
        self._ideas: List[Idea] = ideas or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._ideas)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        idea = self._ideas[index.row()]
        if role in (Qt.DisplayRole, self.ROLE_TITLE):
            return idea.title or 'Без названия'
        if role == self.ROLE_ID:
            return idea.id
        if role == self.ROLE_STATUS:
            return idea.status
        if role == self.ROLE_TYPE:
            return idea.type
        if role == self.ROLE_VALUE:
            return idea.value_score
        if role == self.ROLE_EFFORT:
            return idea.effort_score
        if role == self.ROLE_PROJECT_ID:
            return idea.project_id
        return None

    def roleNames(self):
        return {
            self.ROLE_ID: b'id',
            self.ROLE_TITLE: b'title',
            self.ROLE_STATUS: b'status',
            self.ROLE_TYPE: b'type',
            self.ROLE_VALUE: b'value_score',
            self.ROLE_EFFORT: b'effort_score',
            self.ROLE_PROJECT_ID: b'project_id',
        }

    def set_ideas(self, ideas: List[Idea]) -> None:
        self.beginResetModel()
        self._ideas = ideas
        self.endResetModel()

    def get_idea(self, row: int) -> Optional[Idea]:
        if row < 0 or row >= len(self._ideas):
            return None
        return self._ideas[row]
