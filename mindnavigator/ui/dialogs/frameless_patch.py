from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QErrorMessage,
    QFileDialog,
    QFontDialog,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

from mindnavigator.ui.modals import ModalOverlay

_PATCHED = False
_ORIGINAL_INIT = None
_ORIGINAL_EXEC = None
_DEFAULT_DIALOG_SIZE = QSize(1450, 812)
_MINIMAL_FLEX_SIZE = QSize(560, 300)


def enable_frameless_qdialogs() -> None:
    """Enable frameless titlebar for app QDialog windows globally."""
    global _PATCHED, _ORIGINAL_INIT, _ORIGINAL_EXEC
    if _PATCHED:
        return

    _ORIGINAL_INIT = QDialog.__init__
    _ORIGINAL_EXEC = QDialog.exec

    def _patched_init(self, *args, **kwargs):
        _ORIGINAL_INIT(self, *args, **kwargs)
        if _should_skip_dialog(self):
            return
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.resize(_DEFAULT_DIALOG_SIZE)

    def _patched_exec(self, *args, **kwargs):
        if _should_skip_dialog(self) or _is_popup_dialog(self):
            return _ORIGINAL_EXEC(self, *args, **kwargs)

        category = _dialog_category(self)
        if category == "minimal_flex":
            self.resize(_MINIMAL_FLEX_SIZE)
            _center_dialog(self, force_screen_center=True)
        else:
            # Enforce default dialog geometry before each modal open.
            self.resize(_DEFAULT_DIALOG_SIZE)
            _center_dialog(self)

        parent = self.parentWidget()
        overlay_parent = _resolve_overlay_parent(parent)
        overlay = ModalOverlay(overlay_parent) if overlay_parent else None
        if overlay is not None:
            self.accepted.connect(overlay.deleteLater)
            self.rejected.connect(overlay.deleteLater)
            self.finished.connect(overlay.deleteLater)
        return _ORIGINAL_EXEC(self, *args, **kwargs)

    QDialog.__init__ = _patched_init
    QDialog.exec = _patched_exec
    _PATCHED = True


def _should_skip_dialog(dialog: QDialog) -> bool:
    # Keep native/system behavior for standard utility dialogs.
    skip_types = (
        QFileDialog,
        QMessageBox,
        QColorDialog,
        QFontDialog,
        QProgressDialog,
        QErrorMessage,
    )
    return isinstance(dialog, skip_types)


def _is_popup_dialog(dialog: QDialog) -> bool:
    return bool(dialog.windowFlags() & Qt.Popup)


def _resolve_overlay_parent(parent: QWidget | None) -> QWidget | None:
    if parent is not None:
        return parent.window()
    active = QApplication.activeWindow()
    return active.window() if active is not None else None


def _dialog_category(dialog: QDialog) -> str:
    value = dialog.property("dialog_category")
    if isinstance(value, str):
        return value
    return ""


def _center_dialog(dialog: QDialog, force_screen_center: bool = False) -> None:
    anchor = dialog.parentWidget().window() if dialog.parentWidget() is not None else QApplication.activeWindow()
    screen = None
    if anchor is not None and anchor.windowHandle() is not None:
        screen = anchor.windowHandle().screen()
    if screen is None and anchor is not None:
        screen = QGuiApplication.screenAt(anchor.frameGeometry().center())
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:
        return

    available = screen.availableGeometry()
    if force_screen_center:
        center_point = available.center()
    else:
        center_point = anchor.frameGeometry().center() if anchor is not None else available.center()

    frame = QRect(dialog.frameGeometry())
    frame.setSize(dialog.size())
    frame.moveCenter(center_point)

    if frame.left() < available.left():
        frame.moveLeft(available.left())
    if frame.top() < available.top():
        frame.moveTop(available.top())
    if frame.right() > available.right():
        frame.moveRight(available.right())
    if frame.bottom() > available.bottom():
        frame.moveBottom(available.bottom())

    dialog.move(frame.topLeft())
