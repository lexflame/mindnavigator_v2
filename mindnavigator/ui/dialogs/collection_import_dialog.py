"""Dialog for importing a collection from a folder."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


class CollectionImportDialog(QDialog):
    def __init__(self, default_title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("CollectionImportDialog")
        self.setWindowTitle("Создать коллекцию")
        self.setMinimumSize(560, 300)
        self.setMaximumSize(560, 300)
        self.resize(560, 300)
        self.setProperty("dialog_category", "minimal_flex")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Импорт коллекции из папки")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.title_edit = QLineEdit(default_title or "")
        self.title_edit.setPlaceholderText("Название коллекции")

        self.include_subfolders = QCheckBox("Сканировать подпапки")
        self.include_subfolders.setChecked(True)

        form.addRow("Название", self.title_edit)
        form.addRow("", self.include_subfolders)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        if save_btn is not None:
            save_btn.setText("Создать")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#CollectionImportDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionImportDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionImportDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }}
            QDialog#CollectionImportDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionImportDialog QCheckBox {{
                color: #f2f2f2;
            }}
            QDialog#CollectionImportDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def values(self) -> dict:
        return {
            "title": self.title_edit.text().strip(),
            "include_subfolders": self.include_subfolders.isChecked(),
        }
