"""CollectionItemEditDialog class module for collections workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class CollectionItemEditDialog(QDialog):
    def __init__(
        self,
        item: Optional[CollectionItemData] = None,
        category_options: Optional[List[tuple[str, Optional[int]]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("CollectionItemEditDialog")
        self.setWindowTitle("Создание элемента коллекции" if item is None else "Редактирование элемента коллекции")
        self.setMinimumSize(620, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Новый элемент коллекции" if item is None else "Редактирование элемента коллекции")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit(item.title if item else "")
        self.title_edit.setPlaceholderText("Название")

        self.type_edit = QComboBox()
        for label, value in ENTITY_CHOICES:
            self.type_edit.addItem(label, value)
        if item is not None:
            idx = self.type_edit.findData(item.entity_type)
            if idx >= 0:
                self.type_edit.setCurrentIndex(idx)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Без категории", None)
        for label, value in category_options or []:
            self.category_combo.addItem(label, value)
        if item is not None:
            idx = self.category_combo.findData(item.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        self.topic_edit = QLineEdit(item.topic if item else "")
        self.topic_edit.setPlaceholderText("Тема (например: sci-fi, архитектура, индустриальный урбанизм)")

        self.image_url_edit = QLineEdit(item.image_url if item else "")
        self.image_url_edit.setPlaceholderText("Ссылка на изображение")

        self.source_url_edit = QLineEdit(item.source_url if item else "")
        self.source_url_edit.setPlaceholderText("Ссылка на источник")

        self.description_edit = QPlainTextEdit(item.description if item else "")
        self.description_edit.setPlaceholderText("Описание / заметка")
        self.description_edit.setMinimumHeight(130)

        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.type_edit)
        form.addRow("Тема", self.topic_edit)
        form.addRow("Изображение URL", self.image_url_edit)
        form.addRow("Источник URL", self.source_url_edit)
        form.addRow("Описание", self.description_edit)
        form.addRow("Категория", self.category_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        if save_btn is not None:
            save_btn.setText("Создать" if item is None else "Сохранить")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionItemEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionItemEditDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionItemEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#CollectionItemEditDialog QLineEdit,
            QDialog#CollectionItemEditDialog QPlainTextEdit,
            QDialog#CollectionItemEditDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionItemEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def _accept(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Введите название элемента.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "title": self.title_edit.text().strip(),
            "entity_type": self.type_edit.currentData(),
            "category_id": self.category_combo.currentData(),
            "topic": self.topic_edit.text().strip(),
            "image_url": self.image_url_edit.text().strip(),
            "source_url": self.source_url_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
        }

__all__ = ["CollectionItemEditDialog"]
