from __future__ import annotations

"""Reusable entity picker dialog."""

"""Диалог выбора сущностей с чипами.

Входные данные:
    Список доступных сущностей и выбранные элементы.

Выходные данные:
    Итоговый набор выбранных сущностей.
"""



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
    ) -> None:
        super().__init__(parent)
        self.setObjectName("EntityPickerDialog")
        self.setWindowTitle(f"Выбор: {entity_type}")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.resize(320, 280)
        self._fetch_fn = fetch_fn
        self._selected_ids = set(selected_ids or [])
        self._items: list[ChipItem] = []
        self._anchor_widget = anchor_widget

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._reload)
        if initial_query:
            self.search_input.setText(initial_query)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setSpacing(6)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list_widget.setFixedHeight(180)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Добавить")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog#EntityPickerDialog {
                background: #1b1c1f;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
            }
            QLineEdit {
                background: #202127;
                color: #cfcfcf;
                border: 1px solid #2a2b2f;
                padding: 6px 8px;
                border-radius: 6px;
            }
            QListWidget {
                background: #1b1c1f;
                color: #e6e6e6;
                border: 1px solid #2a2b2f;
                border-radius: 6px;
                padding: 0px;
            }
            QListWidget::item {
                padding: 6px 8px;
            }
            QListWidget::item:hover {
                background: #2a2b2f;
            }
            QListWidget::item:checked {
                background: #3b4a7a;
            }
            QListWidget::item:disabled {
                background: transparent;
                color: #8e919a;
            }
            QDialogButtonBox QPushButton {
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 6px 12px;
                border-radius: 6px;
            }
            QDialogButtonBox QPushButton:hover {
                background: #34363b;
            }
            """
        )

        self._reload()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().showEvent(event)
        if not self._anchor_widget:
            return
        width = self._anchor_widget.width()
        self.setFixedWidth(width)
        anchor_pos = self._anchor_widget.mapToGlobal(QPoint(0, self._anchor_widget.height()))
        self.move(anchor_pos)

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
