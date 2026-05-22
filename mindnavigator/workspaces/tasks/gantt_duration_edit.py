"""Helpers for editing GANTT duration values in HH:MM format."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal

from ._shared import QLineEdit, Qt, QWidget


def clamp_gantt_estimate_minutes(minutes: int) -> int:
    """Clamp duration to the supported GANTT estimate range."""
    return max(GanttEstimateEdit.MINUTES_MIN, min(GanttEstimateEdit.MINUTES_MAX, int(minutes or 0)))


def format_gantt_estimate_minutes(minutes: int, *, empty: str = "—") -> str:
    """Format a stored minute value for HH:MM display."""
    safe_minutes = max(0, int(minutes or 0))
    if safe_minutes <= 0:
        return empty
    hours, remainder = divmod(min(safe_minutes, GanttEstimateEdit.MINUTES_MAX), 60)
    return f"{hours:02d}:{remainder:02d}"


class GanttEstimateEdit(QLineEdit):
    """Editable HH:MM duration field with live commit for keyboard and manual input."""

    minutesCommitted = Signal(int)

    MINUTES_MIN = 5
    MINUTES_MAX = 8 * 60
    _MANUAL_COMMIT_DELAY_MS = 220

    def __init__(self, minutes: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setInputMask("00:00")
        self.setPlaceholderText("HH:MM")
        self.setCursorMoveStyle(Qt.CursorMoveStyle.VisualMoveStyle)

        self._suppress_commit = False
        self._manual_edit_pending = False
        self._last_committed_minutes = self.MINUTES_MIN
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.timeout.connect(self._try_commit_pending_manual)

        self.textChanged.connect(self._on_text_changed)
        self.editingFinished.connect(self.commit_pending)

        self.set_minutes(self.MINUTES_MIN if minutes is None else minutes)

    def lineEdit(self) -> "GanttEstimateEdit":
        return self

    def minutes(self) -> int:
        parsed = self._parse_minutes(self.text())
        if parsed is None:
            return self._last_committed_minutes
        return parsed

    def set_minutes(self, minutes: int) -> None:
        safe_minutes = clamp_gantt_estimate_minutes(minutes)
        self._commit_timer.stop()
        self._manual_edit_pending = False
        self._last_committed_minutes = safe_minutes
        self._suppress_commit = True
        try:
            self.setText(format_gantt_estimate_minutes(safe_minutes, empty="00:05"))
        finally:
            self._suppress_commit = False

    def commit_pending(self) -> None:
        self._try_commit_pending_manual(finalize=True)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            cursor_position = self.cursorPosition()
            delta = 60 if cursor_position <= 2 else 1
            if key == Qt.Key.Key_Down:
                delta = -delta
            self.set_minutes(self.minutes() + delta)
            self.setCursorPosition(cursor_position)
            self.minutesCommitted.emit(self._last_committed_minutes)
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_text_changed(self, _text: str) -> None:
        if self._suppress_commit:
            return
        self._manual_edit_pending = True
        self._commit_timer.start(self._MANUAL_COMMIT_DELAY_MS)

    def _try_commit_pending_manual(self, finalize: bool = False) -> None:
        self._commit_timer.stop()
        if not self._manual_edit_pending:
            return
        parsed = self._parse_minutes(self.text())
        if parsed is not None:
            self._manual_edit_pending = False
            self._emit_minutes_if_changed(parsed)
            return
        if finalize:
            self._manual_edit_pending = False
            self.set_minutes(self._last_committed_minutes)

    def _emit_minutes_if_changed(self, minutes: int) -> None:
        safe_minutes = clamp_gantt_estimate_minutes(minutes)
        if safe_minutes == self._last_committed_minutes:
            return
        self._last_committed_minutes = safe_minutes
        self._suppress_commit = True
        try:
            self.setText(format_gantt_estimate_minutes(safe_minutes, empty="00:05"))
        finally:
            self._suppress_commit = False
        self.minutesCommitted.emit(safe_minutes)

    @classmethod
    def _parse_minutes(cls, value: str) -> int | None:
        normalized = (value or "").strip()
        if len(normalized) != 5 or ":" not in normalized:
            return None
        hour_text, minute_text = normalized.split(":", 1)
        if not (hour_text.isdigit() and minute_text.isdigit()):
            return None
        minutes = int(hour_text) * 60 + int(minute_text)
        if cls.MINUTES_MIN <= minutes <= cls.MINUTES_MAX and int(minute_text) < 60:
            return minutes
        return None


__all__ = [
    "GanttEstimateEdit",
    "clamp_gantt_estimate_minutes",
    "format_gantt_estimate_minutes",
]
