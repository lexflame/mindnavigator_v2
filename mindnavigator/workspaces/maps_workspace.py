from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QSize

from ..repositories.maps_repo import MapsRepo
from .editor_map_workspace import EditorMapWorkspace


class MapsWorkspace(QWidget):
    def __init__(self, db_path=None, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self.repo = MapsRepo(db_path)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск карт…")

        self.btn_add = QPushButton("Добавить")
        self.btn_open = QPushButton("Открыть")
        self.btn_del = QPushButton("Удалить")

        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_open)
        top.addWidget(self.btn_del)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setWrapping(True)
        self.list.setMovement(QListWidget.Static)
        self.list.setIconSize(QSize(128, 96))
        self.list.setGridSize(QSize(240, 170))
        self.list.setSpacing(12)

        self.editor = EditorMapWorkspace(db_path)
        self.editor.hide()

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.list, 1)
        lay.addWidget(self.editor, 1)

        self.search.textChanged.connect(self.reload)
        self.btn_add.clicked.connect(self.add_map)
        self.btn_open.clicked.connect(self.open_selected)
        self.btn_del.clicked.connect(self.delete_selected)
        self.list.itemDoubleClicked.connect(lambda _: self.open_selected())

        self.editor.btn_back.clicked.connect(self.back_to_list)

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
        items = self.repo.list_maps(text=text if text else None)
        self.list.clear()
        for m in items:
            it = QListWidgetItem(m.title)
            it.setData(Qt.UserRole, m.id)
            it.setToolTip(m.tiles_path)
            self.list.addItem(it)

    def add_map(self):
        folder = QFileDialog.getExistingDirectory(self, "Папка с тайлами карты")
        if not folder:
            return
        import os, re
        xs, ys = set(), set()
        for fn in os.listdir(folder):
            mm = re.match(r"(\d+)_(\d+)\.(png|jpg|jpeg)$", fn, re.IGNORECASE)
            if not mm:
                continue
            xs.add(int(mm.group(1)))
            ys.add(int(mm.group(2)))
        if not xs or not ys:
            QMessageBox.warning(self, "Тайлы не найдены", "В папке не найдено файлов вида x_y.png")
            return
        tiles_x = max(xs) + 1
        tiles_y = max(ys) + 1
        title = os.path.basename(folder)
        map_id = self.repo.create_map(title=title, tiles_path=folder, tiles_x=tiles_x, tiles_y=tiles_y, tile_size=512)
        self.reload()
        self._open_map_id(map_id)

    def _open_map_id(self, map_id: int):
        m = self.repo.get_map(map_id)
        if not m:
            return
        self.list.hide()
        self.editor.show()
        self.editor.open_map(m.id, m.tiles_path, m.tiles_x, m.tiles_y, m.tile_size)

    def open_selected(self):
        it = self.list.currentItem()
        if not it:
            return
        self._open_map_id(int(it.data(Qt.UserRole)))

    def delete_selected(self):
        it = self.list.currentItem()
        if not it:
            return
        map_id = int(it.data(Qt.UserRole))
        if QMessageBox.question(self, "Удалить карту", "Пометить карту удалённой?") != QMessageBox.Yes:
            return
        self.repo.soft_delete_map(map_id)
        self.reload()

    def back_to_list(self):
        self.editor.hide()
        self.list.show()
        self.reload()
