"""Search-backed command palette dialog."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from mindnavigator.hotkeys import HotkeyBinding, HotkeyCommand
from mindnavigator.ui.styles import get_theme_palette


@dataclass(frozen=True)
class PaletteCommand:
    command: HotkeyCommand
    binding: HotkeyBinding


class CommandPaletteDialog(QDialog):
    itemActivated = Signal(str, object)

    def __init__(self, *, search_service, commands: list[PaletteCommand], theme_mode: str = "dark", parent=None) -> None:
        super().__init__(parent)
        self._search_service = search_service
        self._commands = commands
        self.setObjectName("CommandPaletteDialog")
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.resize(660, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.input = QLineEdit(self)
        self.input.setObjectName("CommandPaletteInput")
        self.input.setPlaceholderText("Команда или сущность...")
        self.input.setClearButtonEnabled(True)
        self.input.installEventFilter(self)
        self.input.textChanged.connect(self._refresh)
        self.input.returnPressed.connect(self._activate_current)

        self.hint = QLabel("Введите текст для поиска сущностей. Команды доступны сразу.", self)
        self.hint.setObjectName("CommandPaletteHint")

        self.results = QListWidget(self)
        self.results.setObjectName("CommandPaletteResults")
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.results.itemDoubleClicked.connect(lambda _item: self._activate_current())

        layout.addWidget(self.input)
        layout.addWidget(self.hint)
        layout.addWidget(self.results, 1)
        self.set_theme_mode(theme_mode)
        self._refresh("")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.reject()
                return True
            if event.key() in {Qt.Key.Key_Down, Qt.Key.Key_Up} and self.results.count():
                step = 1 if event.key() == Qt.Key.Key_Down else -1
                current_row = self.results.currentRow()
                self.results.setCurrentRow((current_row + step) % self.results.count())
                return True
        return super().eventFilter(watched, event)

    def set_theme_mode(self, theme_mode: str) -> None:
        palette = get_theme_palette("light" if str(theme_mode).lower() == "light" else "dark")
        self.setStyleSheet(
            f"""
            QDialog#CommandPaletteDialog {{ background: {palette.panel_bg}; }}
            QLineEdit#CommandPaletteInput {{
                background: {palette.input_bg}; color: {palette.text}; border: 1px solid {palette.border};
                border-radius: 6px; padding: 9px 11px; font-size: 14px;
            }}
            QLabel#CommandPaletteHint {{ color: {palette.dim_text}; }}
            QListWidget#CommandPaletteResults {{
                background: {palette.elevated_bg}; color: {palette.text}; border: 1px solid {palette.border};
                border-radius: 6px; padding: 4px;
            }}
            QListWidget#CommandPaletteResults::item {{ padding: 8px; }}
            QListWidget#CommandPaletteResults::item:selected {{
                background: {palette.selection_bg}; color: {palette.selection_text}; border-radius: 4px;
            }}
            """
        )

    def _refresh(self, text: str) -> None:
        query = str(text or "").strip().casefold()
        self.results.clear()
        for entry in self._commands:
            command = entry.command
            searchable = " ".join((command.title, command.description, entry.binding.sequence)).casefold()
            if query and query not in searchable:
                continue
            item = QListWidgetItem(f"Команда: {command.title}    {entry.binding.sequence}")
            item.setToolTip(command.description)
            item.setData(Qt.ItemDataRole.UserRole, ("command", command.id))
            self.results.addItem(item)

        if query:
            for payload in self._search_service.search(query):
                item = QListWidgetItem(str(payload.get("label") or ""))
                item.setToolTip(str(payload.get("tooltip") or ""))
                item.setData(Qt.ItemDataRole.UserRole, ("entity", payload))
                self.results.addItem(item)

        if self.results.count():
            self.results.setCurrentRow(0)

    def _activate_current(self) -> None:
        item = self.results.currentItem()
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, tuple) or len(payload) != 2:
            return
        kind, value = payload
        self.accept()
        self.itemActivated.emit(str(kind), value)


__all__ = ["CommandPaletteDialog", "PaletteCommand"]
