"""Styled dialogs for creating and renaming idea categories."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout

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


class IdeaCategoryRenameDialog(QDialog):
    def __init__(
        self,
        *,
        categories: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("IdeaCategoryRenameDialog")
        self.setWindowTitle("Переименовать категорию")
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title_label = QLabel("Переименовать категорию")
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        self.category_combo = QComboBox()
        for category_code, category_title in categories:
            self.category_combo.addItem(category_title, category_code)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите новое название")

        form.addRow("Категория", self.category_combo)
        form.addRow("Новое название", self.title_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(self)
        save_button = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText("Сохранить")
            save_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.category_combo.currentIndexChanged.connect(self._sync_title_from_selection)
        self._sync_title_from_selection()

        self.setStyleSheet(
            f"""
            QDialog#IdeaCategoryRenameDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#IdeaCategoryRenameDialog QLabel {{
                color: #cfcfcf;
            }}

            QDialog#IdeaCategoryRenameDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#IdeaCategoryRenameDialog QLineEdit,
            QDialog#IdeaCategoryRenameDialog QComboBox {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}

            QDialog#IdeaCategoryRenameDialog QLineEdit:focus,
            QDialog#IdeaCategoryRenameDialog QComboBox:focus {{
                border-color: #4d8dff;
            }}

            QDialog#IdeaCategoryRenameDialog QComboBox::drop-down {{
                border: none;
                width: 18px;
            }}

            QDialog#IdeaCategoryRenameDialog QComboBox QAbstractItemView {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                selection-background-color: #34363b;
                selection-color: #f2f2f2;
            }}

            QDialog#IdeaCategoryRenameDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#IdeaCategoryRenameDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """
        )

    def _sync_title_from_selection(self, *_args: object) -> None:
        current_title = self.category_combo.currentText().strip()
        self.title_edit.setText(current_title)
        self.title_edit.selectAll()

    def category_code(self) -> str:
        return str(self.category_combo.currentData() or "").strip()

    def title_value(self) -> str:
        return self.title_edit.text().strip()


__all__ = ["IdeaCategoryEditDialog", "IdeaCategoryRenameDialog"]
