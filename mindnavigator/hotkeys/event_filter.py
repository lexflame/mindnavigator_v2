from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QPlainTextEdit, QTextEdit, QWidget

from .manager import HotkeyManager, normalize_sequence


class HotkeyEventFilter(QObject):
    def __init__(self, manager: HotkeyManager, callback_resolver: Callable[[str], Callable[[], None] | None], parent: QObject | None = None):
        super().__init__(parent)
        self._manager = manager
        self._callback_resolver = callback_resolver

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.Type.KeyPress:
            return False
        key_event = event
        if not isinstance(key_event, QKeyEvent):
            return False
        if key_event.isAutoRepeat():
            return False

        sequence = self._to_sequence(key_event)
        if not sequence:
            return False

        focus_widget = QApplication.focusWidget()
        focus_is_text = is_editable_widget(focus_widget)

        command_id = self._manager.resolve(
            sequence=sequence,
            focus_is_text_input=focus_is_text,
        )
        if not command_id:
            return False

        callback = self._callback_resolver(command_id)
        if callback is None:
            return False
        callback()
        event.accept()
        return True

    @staticmethod
    def _to_sequence(event: QKeyEvent) -> str:
        key = event.key()
        if key in {
            Qt.Key.Key_unknown,
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        }:
            return ""
        seq = QKeySequence(event.keyCombination()).toString(QKeySequence.SequenceFormat.NativeText)
        return normalize_sequence(seq)


def is_editable_widget(widget: QWidget | None) -> bool:
    if widget is None:
        return False
    if isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
        return True
    if isinstance(widget, QComboBox):
        return widget.isEditable()
    return bool(widget.property("hotkeys_editable") is True)
