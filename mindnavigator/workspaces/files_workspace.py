from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from ..repositories.files_repo import FilesRepo
from ..db import connect


class FilesWorkspace(QWidget):
    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self.repo = FilesRepo(db_path)
        self._parent_id: int | None = None

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск…")

        self.btn_up = QPushButton("⬆")
        self.btn_new_folder = QPushButton("Папка")
        self.btn_del = QPushButton("Удалить")

        top = QHBoxLayout()
        top.addWidget(self.btn_up)
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_new_folder)
        top.addWidget(self.btn_del)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setWrapping(True)
        self.list.setMovement(QListWidget.Static)
        self.list.setGridSize(QSize(240, 190))
        self.list.setSpacing(14)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.list, 1)

        self.search.textChanged.connect(self.reload)
        self.btn_new_folder.clicked.connect(self.create_folder)
        self.btn_del.clicked.connect(self.delete_item)
        self.btn_up.clicked.connect(self.go_up)
        self.list.itemDoubleClicked.connect(self.open_item)

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
        rows = self.repo.list_children(self._parent_id, text=text if text else None)
        self.list.clear()
        for f in rows:
            label = f.name
            prefix = "📁 " if f.is_dir else "📄 "
            it = QListWidgetItem(prefix + label)
            it.setData(Qt.UserRole, f.id)
            it.setData(Qt.UserRole + 1, 1 if f.is_dir else 0)
            self.list.addItem(it)

    def create_folder(self):
        name, ok = QInputDialog.getText(self, "Новая папка", "Имя папки:")
        if not ok or not name.strip():
            return
        self.repo.create_folder(self._parent_id, name.strip())
        self.reload()

    def delete_item(self):
        it = self.list.currentItem()
        if not it:
            return
        file_id = int(it.data(Qt.UserRole))
        is_dir = bool(it.data(Qt.UserRole + 1))
        if is_dir and self.repo.count_active_children(file_id) > 0:
            QMessageBox.warning(self, "Нельзя удалить", "Папка не пуста.")
            return
        if QMessageBox.question(self, "Удалить", "Пометить элемент удалённым?") != QMessageBox.Yes:
            return
        self.repo.soft_delete_item(file_id)
        self.reload()

    def open_item(self, it: QListWidgetItem):
        is_dir = bool(it.data(Qt.UserRole + 1))
        if not is_dir:
            return
        self._parent_id = int(it.data(Qt.UserRole))
        self.reload()

    def go_up(self):
        if self._parent_id is None:
            return
        conn = connect(self._db_path)
        try:
            r = conn.execute("SELECT parent_id FROM files WHERE id=?", (self._parent_id,)).fetchone()
            self._parent_id = (int(r["parent_id"]) if r and r["parent_id"] is not None else None)
        finally:
            conn.close()
        self.reload()
