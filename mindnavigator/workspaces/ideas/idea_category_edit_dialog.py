"""Styled dialog for creating and renaming idea categories."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


class IdeaCategoryEditDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        heading: str,
        field_label: str,
        initial_value: str = "",
        submit_text: str = "Сохранить",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("IdeaCategoryEditDialog")
        self.setWindowTitle(title)
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel(heading)
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.title_edit = QLineEdit(initial_value)
        self.title_edit.setPlaceholderText("Введите название категории")
        self.title_edit.selectAll()

        form.addRow(field_label, self.title_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        save_button = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(submit_text)
            save_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QDialog#IdeaCategoryEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#IdeaCategoryEditDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#IdeaCategoryEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#IdeaCategoryEditDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#IdeaCategoryEditDialog QLineEdit:focus {{
                border-color: #4d8dff;
            }}

            QDialog#IdeaCategoryEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#IdeaCategoryEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """
        )

    def title_value(self) -> str:
        return self.title_edit.text().strip()


__all__ = ["IdeaCategoryEditDialog"]
