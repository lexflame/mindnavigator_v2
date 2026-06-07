"""Reusable read-only list for linked entities grouped into sections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


@dataclass(frozen=True)
class LinkedEntityListItem:
    text: str
    entity_kind: str
    entity_id: int
    origin_id: int | None = None
    tooltip: str = ""


@dataclass(frozen=True)
class LinkedEntityListSection:
    title: str
    items: tuple[LinkedEntityListItem, ...]


class LinkedEntitiesListWidget(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drop_mime_type = ""
        self._drop_decoder: Callable[[object], tuple[str, int] | None] | None = None
        self._drop_validator: Callable[[str, int], bool] | None = None
        self._drop_handler: Callable[[str, int], bool] | None = None

    def set_sections(self, sections: list[LinkedEntityListSection], *, empty_text: str) -> None:
        self.clear()
        if not sections:
            item = QListWidgetItem(empty_text)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.addItem(item)
            return
        for section in sections:
            header = QListWidgetItem(f"{section.title} · {len(section.items)}")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            self.addItem(header)
            for entry in section.items:
                item = QListWidgetItem(entry.text)
                if entry.origin_id is not None:
                    item.setData(Qt.ItemDataRole.UserRole, entry.origin_id)
                item.setData(int(Qt.ItemDataRole.UserRole) + 1, entry.entity_kind)
                item.setData(int(Qt.ItemDataRole.UserRole) + 2, entry.entity_id)
                item.setToolTip(entry.tooltip)
                self.addItem(item)

    def configure_drop(
        self,
        *,
        mime_type: str,
        decoder: Callable[[object], tuple[str, int] | None],
        validator: Callable[[str, int], bool],
        handler: Callable[[str, int], bool],
    ) -> None:
        self._drop_mime_type = str(mime_type or "")
        self._drop_decoder = decoder
        self._drop_validator = validator
        self._drop_handler = handler
        self.setAcceptDrops(bool(self._drop_mime_type))

    def _drop_payload(self, mime_data) -> tuple[str, int] | None:
        if not self._drop_mime_type or not mime_data.hasFormat(self._drop_mime_type):
            return None
        if self._drop_decoder is None:
            return None
        return self._drop_decoder(mime_data)

    def _can_accept_drop(self, mime_data) -> bool:
        payload = self._drop_payload(mime_data)
        return payload is not None and self._drop_validator is not None and self._drop_validator(*payload)

    def dragEnterEvent(self, event) -> None:
        if self._can_accept_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._can_accept_drop(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        payload = self._drop_payload(event.mimeData())
        if payload is not None and self._drop_handler is not None and self._drop_handler(*payload):
            event.acceptProposedAction()
            return
        event.ignore()


__all__ = ["LinkedEntitiesListWidget", "LinkedEntityListItem", "LinkedEntityListSection"]
