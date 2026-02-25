from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QWidget


class MNBaseDialog(QDialog):
    """Shared base dialog for remastered modal windows."""

    DEFAULT_INITIAL_SIZE = QSize(1450, 812)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.resize(self.DEFAULT_INITIAL_SIZE)
        self._mn_positioned = False

    def showEvent(self, event) -> None:  # noqa: N802 - Qt API
        if not self._mn_positioned:
            self.center_on_active_parent()
            self._mn_positioned = True
        super().showEvent(event)

    def center_on_active_parent(self, parent: QWidget | None = None) -> None:
        anchor = self._resolve_anchor(parent)
        target_screen = self._resolve_screen(anchor)
        if target_screen is None:
            return
        available = target_screen.availableGeometry()

        if anchor is not None:
            anchor_rect = anchor.frameGeometry()
            center_point = anchor_rect.center()
        else:
            center_point = available.center()

        frame = QRect(self.frameGeometry())
        frame.setSize(self.size())
        frame.moveCenter(center_point)

        if frame.left() < available.left():
            frame.moveLeft(available.left())
        if frame.top() < available.top():
            frame.moveTop(available.top())
        if frame.right() > available.right():
            frame.moveRight(available.right())
        if frame.bottom() > available.bottom():
            frame.moveBottom(available.bottom())

        self.move(frame.topLeft())

    def _resolve_anchor(self, parent: QWidget | None) -> QWidget | None:
        anchor = None
        if parent is not None:
            anchor = parent.window()
        elif self.parentWidget() is not None:
            anchor = self.parentWidget().window()
        if anchor is None:
            anchor = QApplication.activeWindow()
        return anchor

    @staticmethod
    def _resolve_screen(anchor: QWidget | None):
        if anchor is not None and anchor.windowHandle() is not None:
            screen = anchor.windowHandle().screen()
            if screen is not None:
                return screen
        if anchor is not None:
            screen = QGuiApplication.screenAt(anchor.frameGeometry().center())
            if screen is not None:
                return screen
        return QGuiApplication.primaryScreen()
