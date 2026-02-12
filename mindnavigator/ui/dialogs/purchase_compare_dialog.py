"""Dialog for comparing items within a category."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from mindnavigator.storage import Database, ShopItemPropertyData
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


class PurchaseCompareDialog(QDialog):
    def __init__(self, db: Database, category_id: int | None = None, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._category_id = category_id

        self.setObjectName("PurchaseCompareDialog")
        self.setWindowTitle("Сравнение товаров")
        self.setProperty("dialog_category", "minimal_flex")
        self.setMinimumSize(720, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Сравнение товаров по категории")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        self.category_combo = QComboBox()
        self._load_categories()
        layout.addWidget(self.category_combo)

        self.table = QTableWidget(0, 0)
        self.table.setObjectName("PurchaseCompareTable")
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.category_combo.currentIndexChanged.connect(self._reload_table)
        self._reload_table()

        self.setStyleSheet(f"""
            QDialog#PurchaseCompareDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#PurchaseCompareDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}
            QDialog#PurchaseCompareDialog QLabel {{
                color: #cfcfcf;
                font-size: 13px;
            }}
            QDialog#PurchaseCompareDialog QComboBox {{
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QTableWidget#PurchaseCompareTable {{
                background: #16171a;
                border: 1px solid #2a2b2f;
                border-radius: 8px;
                color: #cfcfcf;
            }}
            QDialog#PurchaseCompareDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}
            QDialog#PurchaseCompareDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

    def _load_categories(self) -> None:
        self.category_combo.clear()
        self.category_combo.addItem("Все категории", None)
        categories = self._db.fetch_shop_categories()
        for cat in categories:
            self.category_combo.addItem(cat.title, cat.id)
        if self._category_id is not None:
            idx = self.category_combo.findData(self._category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

    def _reload_table(self) -> None:
        category_id = self.category_combo.currentData()
        items = self._db.fetch_shop_compare_items(category_id)
        if not items:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        properties_by_item: dict[int, list[ShopItemPropertyData]] = {
            item.id: self._db.fetch_shop_item_properties(item.id) for item in items
        }
        all_keys: list[str] = []
        for props in properties_by_item.values():
            for prop in props:
                key = prop.normalized_key or prop.name
                if key not in all_keys:
                    all_keys.append(key)
        all_keys.sort()

        self.table.setColumnCount(len(items) + 1)
        headers = ["Свойство"] + [item.title for item in items]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(all_keys))
        for row_idx, key in enumerate(all_keys):
            self.table.setItem(row_idx, 0, QTableWidgetItem(key))
            for col_idx, item in enumerate(items, start=1):
                value = ""
                for prop in properties_by_item.get(item.id, []):
                    prop_key = prop.normalized_key or prop.name
                    if prop_key == key:
                        value = prop.value
                        if prop.unit:
                            value = f"{value} {prop.unit}"
                        break
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(value))
