"""MapEditDialog class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MapEditDialog(QDialog):
    def __init__(self, map_row: MapRow, parent=None):
        # Инициализируем диалог редактирования карты.
        super().__init__(parent)
        # Базовые настройки диалога.
        self.setWindowTitle("Редактирование карты")
        self.setObjectName("MapEditDialog")
        self.setMinimumWidth(460)
        self.setMinimumHeight(400)

        self._db = get_database()

        # Основная вертикальная компоновка.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Заголовок диалога.
        title_label = QLabel("Редактирование карты")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        # Форма с полями карты.
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(map_row.title)
        self.title_edit.setPlaceholderText("Название карты")

        self.description_edit = QLineEdit(map_row.description)
        self.description_edit.setPlaceholderText("Описание карты")

        self.project_edit = QComboBox()
        self.project_edit.addItems(self._project_titles())
        idx = self.project_edit.findText(map_row.project)
        if idx >= 0:
            self.project_edit.setCurrentIndex(idx)

        self.tiles_path = QLineEdit(map_row.tiles_path)
        self.tiles_path.setPlaceholderText("Каталог хранения тайлов")

        self.tiles_path_btn = QToolButton()
        self.tiles_path_btn.setText("…")
        self.tiles_path_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tiles_path_btn.clicked.connect(self._on_pick_tiles_path)

        tiles_path_row = QFrame()
        tiles_path_row.setObjectName("MapTilesPathRow")
        tiles_path_layout = QHBoxLayout(tiles_path_row)
        tiles_path_layout.setContentsMargins(0, 0, 0, 0)
        tiles_path_layout.setSpacing(6)
        tiles_path_layout.addWidget(self.tiles_path, 1)
        tiles_path_layout.addWidget(self.tiles_path_btn)

        self.tiles_w = QSpinBox()
        self.tiles_w.setRange(1, 512)
        self.tiles_w.setValue(map_row.tiles_w)

        self.tiles_h = QSpinBox()
        self.tiles_h.setRange(1, 512)
        self.tiles_h.setValue(map_row.tiles_h)

        # Блок выбора размера тайлов.
        tiles_block = QFrame()
        tiles_block.setObjectName("MapTilesBlock")
        tiles_layout = QHBoxLayout(tiles_block)
        tiles_layout.setContentsMargins(8, 4, 8, 4)
        tiles_layout.setSpacing(8)
        tiles_layout.addWidget(QLabel("W"))
        tiles_layout.addWidget(self.tiles_w)
        tiles_layout.addWidget(QLabel("H"))
        tiles_layout.addWidget(self.tiles_h)

        form.addRow("Название", self.title_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Проект", self.project_edit)
        form.addRow("Каталог хранения тайлов", tiles_path_row)
        form.addRow("Тайлы", tiles_block)

        layout.addLayout(form)

        # Кнопки сохранения/отмены.
        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Стили диалога.
        self.setStyleSheet(f"""
            QDialog#MapEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#MapEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#MapEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#MapEditDialog QLineEdit,
            QDialog#MapEditDialog QComboBox,
            QDialog#MapEditDialog QSpinBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#MapEditDialog QFrame#MapTilesPathRow QToolButton {{
                background: #2a2b2f;
                border: 1px solid #3a3b40;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
            }}

            QDialog#MapEditDialog QFrame#MapTilesPathRow QToolButton:hover {{
                background: #34363b;
            }}

            QDialog#MapEditDialog QFrame#MapTilesBlock {{
                background: #202127;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }}

            QDialog#MapEditDialog QFrame#MapTilesBlock QSpinBox {{
                background: transparent;
                border: none;
                padding: 6px 6px;
            }}

            QDialog#MapEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#MapEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    @staticmethod
    def _project_titles() -> List[str]:
        # Список проектов для комбобокса.
        projects = get_database().fetch_projects()
        titles = sorted({p.title for p in projects})
        return titles or ["Без проекта"]

    def _cloud_storage_root(self) -> str:
        # Корневая папка облачного хранилища.
        return self._db.get_setting("cloud_storage_path", default="")

    def _on_pick_tiles_path(self) -> None:
        # Диалог выбора каталога с тайлами.
        current = self.tiles_path.text().strip()
        start_dir = current or self._cloud_storage_root() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите каталог хранения тайлов",
            start_dir,
        )
        if not selected:
            return
        self.tiles_path.setText(selected)

    def _on_accept(self):
        # Проверка обязательных полей перед сохранением.
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название карты.")
            return
        self.accept()

    def values(self) -> dict:
        # Возвращаем значения формы в виде словаря.
        return {
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.text().strip(),
            "project": self.project_edit.currentText(),
            "tiles_path": self.tiles_path.text().strip(),
            "tiles_w": self.tiles_w.value(),
            "tiles_h": self.tiles_h.value(),
        }

__all__ = ["MapEditDialog"]
