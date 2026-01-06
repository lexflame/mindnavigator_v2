from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from ..repositories.notes_repo import NotesRepo


class NotesWorkspace(QWidget):
    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self.repo = NotesRepo(db_path)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск заметок…")

        self.btn_add = QPushButton("Добавить")
        self.btn_del = QPushButton("Удалить")

        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_del)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setWrapping(True)
        self.list.setMovement(QListWidget.Static)
        self.list.setGridSize(QSize(280, 160))
        self.list.setSpacing(12)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.list, 1)

        self.search.textChanged.connect(self.reload)
        self.btn_add.clicked.connect(self.add_note)
        self.btn_del.clicked.connect(self.delete_note)

        self.setStyleSheet("""
            QWidget { background: #16171a; color: #e6e6e6; }
            QLineEdit { background: #1f2126; border: 1px solid #2a2b2f; border-radius: 8px; padding: 8px; }
            QPushButton { background: #2a2b2f; border: 1px solid #2f3136; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #34363c; }
            QListWidget { background: #16171a; border: 1px solid #2a2b2f; border-radius: 10px; padding: 10px; }
        """)

        self.reload()

    def reload(self):
        text = self.search.text().strip()
        rows = self.repo.list_notes(text=text if text else None)
        self.list.clear()
        for n in rows:
            it = QListWidgetItem(n.title)
            it.setData(Qt.UserRole, n.id)
            it.setToolTip((n.content or "")[:200])
            self.list.addItem(it)

    def add_note(self):
        title, ok = QInputDialog.getText(self, "Новая заметка", "Название:")
        if not ok or not title.strip():
            return
        self.repo.create_note(title=title.strip(), content="")
        self.reload()

    def delete_note(self):
        it = self.list.currentItem()
        if not it:
            return
        note_id = int(it.data(Qt.UserRole))
        if QMessageBox.question(self, "Удалить заметку", "Пометить заметку удалённой?") != QMessageBox.Yes:
            return
        self.repo.soft_delete_note(note_id)
        self.reload()
