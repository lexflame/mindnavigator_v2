"""Reusable editable-list rows with add, edit, delete, and optional actions."""

from __future__ import annotations

from dataclasses import dataclass

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QToolButton, QVBoxLayout, QWidget


@dataclass(frozen=True)
class EditableListItem:
    label: str
    action_icon: str = ""
    action_tooltip: str = ""
    detail: str = ""
    marker_color: str = ""


class EditableListWidget(QFrame):
    addRequested = Signal()
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    actionRequested = Signal(int)

    def __init__(
        self,
        *,
        icon_color: str,
        empty_text: str = "Нет настроенных элементов",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_color = icon_color
        self._empty_text = empty_text
        self.setObjectName("EditableList")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        self.rows_widget = QWidget(self)
        self.rows_widget.setObjectName("EditableListRows")
        self.rows_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(6)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addStretch(1)
        self.add_button = self._icon_button("fa5s.plus", "Добавить")
        self.add_button.clicked.connect(self.addRequested.emit)
        footer.addWidget(self.add_button)

        layout.addWidget(self.rows_widget)
        layout.addLayout(footer)
        self.set_items([])

    def set_items(self, items: list[EditableListItem]) -> None:
        while self.rows_layout.count():
            layout_item = self.rows_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

        if not items:
            empty = QLabel(self._empty_text)
            empty.setObjectName("EditableListEmpty")
            self.rows_layout.addWidget(empty)
            return

        for index, item in enumerate(items):
            self.rows_layout.addWidget(self._create_row(index, item))

    def set_edit_enabled(self, enabled: bool) -> None:
        for button in self.findChildren(QToolButton):
            button.setVisible(enabled)
            button.setEnabled(enabled)
        self.ensurePolished()
        self.rows_widget.ensurePolished()
        self.rows_layout.activate()
        if self.layout() is not None:
            self.layout().activate()
        self.setMinimumHeight(self.sizeHint().height() if enabled else 0)
        self.updateGeometry()

    def _create_row(self, index: int, item: EditableListItem) -> QFrame:
        row = QFrame()
        row.setObjectName("EditableListRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        marker_color = QColor(item.marker_color)
        if marker_color.isValid():
            marker = QFrame()
            marker.setObjectName("EditableListMarker")
            marker.setFixedSize(5, 28)
            marker.setStyleSheet(
                f"background: {marker_color.name()}; border: none; border-radius: 2px;"
            )
            layout.addWidget(marker)

        value = QLineEdit(item.label)
        value.setObjectName("EditableListValue")
        value.setMinimumWidth(110)
        value.setReadOnly(True)
        value.setCursorPosition(0)
        layout.addWidget(value, 1)

        if item.detail:
            detail = QLabel(item.detail)
            detail.setObjectName("EditableListDetail")
            detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(detail)

        edit_button = self._icon_button("fa5s.edit", "Изменить")
        edit_button.clicked.connect(lambda _checked=False, row_index=index: self.editRequested.emit(row_index))
        layout.addWidget(edit_button)

        if item.action_icon:
            action_button = self._icon_button(item.action_icon, item.action_tooltip)
            action_button.clicked.connect(lambda _checked=False, row_index=index: self.actionRequested.emit(row_index))
            layout.addWidget(action_button)

        delete_button = self._icon_button("fa5s.trash", "Удалить")
        delete_button.clicked.connect(lambda _checked=False, row_index=index: self.deleteRequested.emit(row_index))
        layout.addWidget(delete_button)
        return row

    def _icon_button(self, icon_name: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("EditableListIconButton")
        button.setFixedSize(30, 28)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        button.setIcon(qta.icon(icon_name, color=self._icon_color))
        return button
