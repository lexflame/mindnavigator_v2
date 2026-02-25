"""Dialog to edit a purchase item."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QFormLayout,
)

from mindnavigator.storage import Database, ShopItemData
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


class PurchaseEditDialog(QDialog):
    def __init__(self, db: Database, item: ShopItemData, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._item = item

        self.setObjectName("PurchaseEditDialog")
        self.setWindowTitle("Редактировать товар")
        self.setProperty("dialog_category", "minimal_flex")
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Редактировать товар")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setText(item.title)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Без категории", None)
        categories = self._db.fetch_shop_categories()
        for cat in categories:
            self.category_combo.addItem(cat.title, cat.id)
        if item.category_id is not None:
            idx = self.category_combo.findData(item.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

        self.notes_input = QPlainTextEdit()
        self.notes_input.setPlainText(item.user_notes or "")

        form.addRow("Название", self.title_input)
        form.addRow("Категория", self.category_combo)
        form.addRow("Заметки", self.notes_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox()
        save_btn = buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        save_btn.setText("Сохранить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#PurchaseEditDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#PurchaseEditDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#PurchaseEditDialog QLabel {{
                color: #e0e0e0;
                font-size: 13px;
            }}
            QDialog#PurchaseEditDialog QLineEdit,
            QDialog#PurchaseEditDialog QPlainTextEdit,
            QDialog#PurchaseEditDialog QComboBox {{
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
                min-height: 28px;
            }}
            QDialog#PurchaseEditDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 110px;
                min-height: 32px;
            }}
            QDialog#PurchaseEditDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def payload(self) -> dict:
        return {
            "title": self.title_input.text(),
            "category_id": self.category_combo.currentData(),
            "user_notes": self.notes_input.toPlainText(),
        }
