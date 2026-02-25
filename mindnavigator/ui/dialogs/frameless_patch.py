from __future__ import annotations

from typing import Any

from PySide6.QtCore import QTimer, QRect, QSize, Qt
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

from mindnavigator.ui.animations import DialogAppearAnimator
from mindnavigator.ui.modals import ModalOverlay

_PATCHED = False
_ORIGINAL_INIT = None
_ORIGINAL_EXEC = None
_DEFAULT_DIALOG_SIZE = QSize(1450, 812)
_MINIMAL_FLEX_SIZE = QSize(560, 300)
_DIALOG_APPEAR_ANIMATOR: DialogAppearAnimator | None = None


def enable_frameless_qdialogs() -> None:
    """Enable frameless titlebar for app QDialog windows globally."""
    global _PATCHED, _ORIGINAL_INIT, _ORIGINAL_EXEC
    if _PATCHED:
        return

    _ORIGINAL_INIT = QDialog.__init__
    _ORIGINAL_EXEC = QDialog.exec

    def _patched_init(self, *args: Any, **kwargs: Any):
        parent = kwargs.get("parent")
        if parent is None and args:
            parent = args[0]
        flags = kwargs.get("f")
        if flags is None and len(args) > 1:
            flags = args[1]
        if flags is None:
            _ORIGINAL_INIT(self, parent)
        else:
            _ORIGINAL_INIT(self, parent, flags)
        if _should_skip_dialog(self):
            return
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.resize(_DEFAULT_DIALOG_SIZE)

    def _patched_exec(self):
        if _should_skip_dialog(self) or _is_popup_dialog(self):
            return _ORIGINAL_EXEC(self)

        category = _dialog_category(self)
        if category == "minimal_flex":
            self.resize(_MINIMAL_FLEX_SIZE)
            _center_dialog(self, force_screen_center=True)
        elif category == "keep_size":
            _center_dialog(self)
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
        if _should_animate_dialog(self):
            QTimer.singleShot(0, lambda dialog=self: _dialog_appear_animator().play(dialog))
        return _ORIGINAL_EXEC(self)

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
    return bool(dialog.windowFlags() & Qt.WindowType.Popup)


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


def _should_animate_dialog(dialog: QDialog) -> bool:
    disabled = dialog.property("disable_dialog_appear_animation")
    return not bool(disabled)


def _dialog_appear_animator() -> DialogAppearAnimator:
    global _DIALOG_APPEAR_ANIMATOR
    if _DIALOG_APPEAR_ANIMATOR is None:
        _DIALOG_APPEAR_ANIMATOR = DialogAppearAnimator()
    return _DIALOG_APPEAR_ANIMATOR


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
