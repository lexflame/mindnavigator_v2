"""Category selection dialog for collections."""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from mindnavigator.storage import CollectionCategoryData, Database
from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


class CollectionCategorySelectDialog(QDialog):
    def __init__(
        self,
        db: Database,
        categories: List[CollectionCategoryData],
        parent=None,
    ):
        super().__init__(parent)
        self._db = db
        self._categories = categories
        self._categories_by_id = {cat.id: cat for cat in categories}
        self.setObjectName("CollectionCategorySelectDialog")
        self.setWindowTitle("Выбор категории")
        self.setMinimumSize(560, 300)
        self.setMaximumSize(560, 300)
        self.resize(560, 300)
        self.setProperty("dialog_category", "minimal_flex")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Выберите категорию")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree, 1)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        self.new_path_edit = QLineEdit()
        self.new_path_edit.setPlaceholderText("Новая категория (например: Техника/Фотоаппараты/Объективы)")
        self.create_under_selected = QCheckBox("Создать как подкатегорию выбранной (если путь не задан)")
        self.create_under_selected.setChecked(True)

        form.addRow("Создать новую", self.new_path_edit)
        form.addRow("", self.create_under_selected)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_btn = buttons.button(QDialogButtonBox.Save)
        if save_btn is not None:
            save_btn.setText("Выбрать")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._build_tree()
        self.setStyleSheet(
            f"""
            QDialog#CollectionCategorySelectDialog {{
                {MATH_PHYS_BACKGROUND}
            }}
            QDialog#CollectionCategorySelectDialog QLabel {{
                color: #cfcfcf;
            }}
            QDialog#CollectionCategorySelectDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 16px;
                font-weight: 600;
            }}
            QDialog#CollectionCategorySelectDialog QLineEdit {{
                background: #202127;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QDialog#CollectionCategorySelectDialog QCheckBox {{
                color: #f2f2f2;
            }}
            QDialog#CollectionCategorySelectDialog QTreeWidget {{
                background: #14171c;
                border: 1px solid #2f333b;
                border-radius: 10px;
                color: #e6e6e6;
            }}
            QDialog#CollectionCategorySelectDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
            }}
            """
        )

    def _build_tree(self) -> None:
        self.tree.clear()
        root = QTreeWidgetItem(["Все коллекции"])
        root.setData(0, Qt.UserRole, None)
        self.tree.addTopLevelItem(root)

        children: Dict[Optional[int], List[CollectionCategoryData]] = {}
        for category in self._categories:
            children.setdefault(category.parent_id, []).append(category)
        for values in children.values():
            values.sort(key=lambda c: (c.sort_index, c.title.lower(), c.id))

        def add_children(parent_item: QTreeWidgetItem, parent_id: Optional[int]) -> None:
            for category_row in children.get(parent_id, []):
                item = QTreeWidgetItem([category_row.title])
                item.setData(0, Qt.UserRole, category_row.id)
                parent_item.addChild(item)
                add_children(item, category_row.id)

        add_children(root, None)
        self.tree.expandToDepth(1)
        self.tree.setCurrentItem(root)

    def _selected_category_id(self) -> Optional[int]:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.UserRole)

    def selected_category_id(self) -> Optional[int]:
        path = (self.new_path_edit.text() or "").strip()
        selected_id = self._selected_category_id()
        if path:
            base_parent = selected_id if self.create_under_selected.isChecked() else None
            return self._db.ensure_collection_category_path(path, base_parent_id=base_parent)
        return selected_id
