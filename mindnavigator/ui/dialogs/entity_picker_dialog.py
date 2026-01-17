from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.ui.styles import MATH_PHYS_BACKGROUND


@dataclass(frozen=True)
class ChipItem:
    id: int
    title: str


class EntityPickerDialog(QDialog):
    def __init__(
        self,
        entity_type: str,
        fetch_fn: Callable[[str], list[ChipItem]],
        selected_ids=None,
        parent=None,
        initial_query: str = "",
        anchor_widget: QWidget | None = None,
        title: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EntityPickerDialog")
        self.setWindowTitle(title or f"Выбор: {entity_type}")
        self.resize(520, 420)
        self._fetch_fn = fetch_fn
        self._selected_ids = set(selected_ids or [])
        self._items: list[ChipItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self._reload)
        if initial_query:
            self.search_input.setText(initial_query)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setSpacing(6)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(buttons)

        if anchor_widget is not None:
            self._apply_anchor_geometry(anchor_widget)

        self.setStyleSheet(
            f"""
            QDialog#EntityPickerDialog {{
                {MATH_PHYS_BACKGROUND}
                color: #e6e6e6;
            }}
            QLineEdit {{
                background: rgba(27, 31, 38, 0.9);
                color: #eef1f5;
                border: 1px solid #2f3440;
                padding: 7px 10px;
                border-radius: 6px;
            }}
            QListWidget {{
                background: rgba(20, 23, 30, 0.95);
                color: #e6e6e6;
                border: 1px solid #2f3440;
                border-radius: 8px;
            }}
            QListWidget::item {{
                background: #1e232c;
                color: #e6e6e6;
                border: 1px solid #2f3440;
                border-radius: 6px;
                padding: 8px 10px;
                margin-bottom: 6px;
            }}
            QListWidget::item:hover {{
                background: #242b36;
            }}
            QListWidget::item:checked {{
                background: #2a3240;
                border-color: #3b4658;
            }}
            QDialogButtonBox QPushButton {{
                background: #2a2f3b;
                color: #e8e8e8;
                border: 1px solid #3a3f4a;
                padding: 6px 14px;
                border-radius: 6px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: #343b4b;
            }}
            """
        )

        self._reload()

    def _apply_anchor_geometry(self, anchor_widget: QWidget) -> None:
        anchor_width = anchor_widget.width()
        if anchor_width > 0:
            self.setFixedWidth(anchor_width)
        global_pos = anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height()))
        self.move(global_pos)

    def selected_items(self) -> list[ChipItem]:
        selected = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            data = item.data(Qt.UserRole)
            if not data:
                continue
            if item.checkState() == Qt.Checked:
                selected.append(data)
        return selected

    def _reload(self) -> None:
        query = self.search_input.text().strip().lower()
        self._items = self._fetch_fn(query)
        self.list_widget.clear()
        if not self._items:
            empty = QListWidgetItem("— нет элементов —")
            empty.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(empty)
            return
        for chip in self._items:
            entry = QListWidgetItem(chip.title)
            entry.setData(Qt.UserRole, chip)
            entry.setFlags(entry.flags() | Qt.ItemIsUserCheckable)
            entry.setCheckState(Qt.Checked if chip.id in self._selected_ids else Qt.Unchecked)
            self.list_widget.addItem(entry)
