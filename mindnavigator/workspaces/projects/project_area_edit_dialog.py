"""ProjectAreaEditDialog class module for projects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class ProjectAreaEditDialog(QDialog):
    def __init__(self, area: str, parent=None):
        """Создает диалог редактирования области проектов."""
        super().__init__(parent)
        self.setWindowTitle("Редактирование области")
        self.setObjectName("ProjectAreaEditDialog")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Редактирование области")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.area_edit = QLineEdit(area)
        self.area_edit.setPlaceholderText("Область проекта")
        form.addRow("Область", self.area_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ProjectAreaEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ProjectAreaEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#ProjectAreaEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ProjectAreaEditDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ProjectAreaEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _on_accept(self):
        """Проверяет ввод перед сохранением изменений."""
        try:
            validate_area(self.area_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Проверка", str(exc))
            return
        self.accept()

    def values(self) -> dict:
        """Возвращает значения формы области."""
        return {
            "area": self.area_edit.text().strip(),
        }

__all__ = ["ProjectAreaEditDialog"]
