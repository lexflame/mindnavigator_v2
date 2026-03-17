from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QEventLoop, QObject, QRect, QSize, Qt, QTimer
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

from mindnavigator.ui.modals import ModalOverlay, dialog_presentation_controller
from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog

_PATCHED = False
_ORIGINAL_INIT = None
_ORIGINAL_EXEC = None
_DEFAULT_DIALOG_SIZE = QSize(1450, 812)
_MINIMAL_FLEX_SIZE = QSize(560, 300)
_TASK_EDIT_DIALOG_MAX_SIZE = QSize(1040, 760)
_TASK_DIALOG_OUTSIDE_MARGIN_X = 60
_TASK_DIALOG_OUTSIDE_MARGIN_Y = 48


class _TaskDialogOutsideClickMinimizer(QObject):
    def __init__(self, dialog: QDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._enabled = False
        QApplication.instance().installEventFilter(self)
        dialog.installEventFilter(self)
        dialog.finished.connect(self._cleanup)

    def enable(self) -> None:
        self._enabled = True

    def eventFilter(self, obj, event) -> bool:
        if obj is self._dialog and event.type() in (QEvent.Type.WindowDeactivate, QEvent.Type.FocusOut):
            if self._enabled:
                QTimer.singleShot(0, self._minimize_if_detached)
            return False
        if not self._enabled or not self._dialog.isVisible():
            return False
        if event.type() != QEvent.Type.MouseButtonPress:
            return False
        if QApplication.activePopupWidget() is not None:
            return False
        active_modal = QApplication.activeModalWidget()
        if isinstance(active_modal, QWidget) and self._is_child_of_dialog(active_modal):
            return False

        global_position = getattr(event, "globalPosition", None)
        if not callable(global_position):
            return False
        global_point = global_position().toPoint()
        if self._dialog.frameGeometry().contains(global_point):
            return False

        clicked_widget = QApplication.widgetAt(global_point)
        if isinstance(clicked_widget, QWidget) and self._is_child_of_dialog(clicked_widget):
            return False

        _try_minimize_task_dialog(self._dialog)
        return False

    def _minimize_if_detached(self) -> None:
        if not self._enabled or not self._dialog.isVisible():
            return
        if self._has_transient_child():
            return
        active_window = QApplication.activeWindow()
        if isinstance(active_window, QWidget) and self._is_child_of_dialog(active_window):
            return
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, QWidget) and self._is_child_of_dialog(focus_widget):
            return
        _try_minimize_task_dialog(self._dialog)

    def _is_child_of_dialog(self, widget: QWidget) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is self._dialog:
                return True
            current = current.parentWidget()
        return False

    def _has_transient_child(self) -> bool:
        active_popup = QApplication.activePopupWidget()
        if isinstance(active_popup, QWidget) and self._is_child_of_dialog(active_popup):
            return True
        active_modal = QApplication.activeModalWidget()
        if isinstance(active_modal, QWidget) and self._is_child_of_dialog(active_modal):
            return True
        return False

    def _cleanup(self, *_args) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        try:
            self._dialog.removeEventFilter(self)
        except RuntimeError:
            return


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
        _fit_minimizable_task_dialog_size(self, self.parentWidget())
        _center_dialog(self)

        _attach_dialog_overlay(self)
        if _is_minimizable_task_dialog(self):
            debug_task_dialog(
                f"patched_exec minimizable dialog={type(self).__name__} task_id={self.property('task_dialog_id')} "
                f"geometry={self.geometry().getRect()}"
            )
            return _run_minimizable_task_dialog(self)
        return _ORIGINAL_EXEC(self)

    QDialog.__init__ = _patched_init
    QDialog.exec = _patched_exec
    _PATCHED = True


def are_frameless_qdialogs_enabled() -> bool:
    return _PATCHED


def prepare_minimizable_task_dialog_for_show(
    dialog: QDialog,
    parent: QWidget | None = None,
    *,
    center: bool = True,
) -> None:
    """Ensures size, placement and outside-click support for task dialogs."""
    if not _is_minimizable_task_dialog(dialog):
        return
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    anchor_parent = parent if parent is not None else dialog.parentWidget()
    _fit_minimizable_task_dialog_size(dialog, anchor_parent)
    if center:
        _center_dialog(dialog)
    minimizer = getattr(dialog, "_task_dialog_outside_click_minimizer", None)
    if not isinstance(minimizer, _TaskDialogOutsideClickMinimizer):
        minimizer = _TaskDialogOutsideClickMinimizer(dialog)
        setattr(dialog, "_task_dialog_outside_click_minimizer", minimizer)
    minimizer.enable()


def show_minimizable_task_dialog(dialog: QDialog, parent: QWidget | None = None) -> int:
    """Shows task dialog with the custom minimize-capable lifecycle."""
    if _should_skip_dialog(dialog) or _is_popup_dialog(dialog):
        if callable(_ORIGINAL_EXEC):
            return _ORIGINAL_EXEC(dialog)
        return dialog.exec()

    if not _PATCHED:
        dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

    category = _dialog_category(dialog)
    if category == "minimal_flex":
        dialog.resize(_MINIMAL_FLEX_SIZE)
        _center_dialog(dialog, force_screen_center=True)
    elif category != "keep_size":
        dialog.resize(_DEFAULT_DIALOG_SIZE)

    prepare_minimizable_task_dialog_for_show(dialog, parent, center=True)
    _attach_dialog_overlay(dialog)
    debug_task_dialog(
        f"show_minimizable_task_dialog dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')} "
        f"geometry={dialog.geometry().getRect()}"
    )
    return _run_minimizable_task_dialog(dialog)


def restore_minimizable_task_dialog(dialog: QDialog) -> None:
    debug_task_dialog(
        f"restore_minimizable_task_dialog dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')}"
    )
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    dialog.show()
    ensure_minimizable_task_dialog_overlay(dialog)
    dialog.raise_()
    dialog.activateWindow()


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


def _is_minimizable_task_dialog(dialog: QDialog) -> bool:
    return bool(dialog.property("task_dialog_minimizable"))


def _fit_minimizable_task_dialog_size(dialog: QDialog, parent: QWidget | None) -> None:
    if not _is_minimizable_task_dialog(dialog):
        return
    anchor = parent.window() if parent is not None else QApplication.activeWindow()
    if anchor is None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        bounds = screen.availableGeometry()
    else:
        bounds = anchor.frameGeometry()

    max_width = max(dialog.minimumWidth(), bounds.width() - (_TASK_DIALOG_OUTSIDE_MARGIN_X * 2))
    max_height = max(dialog.minimumHeight(), bounds.height() - (_TASK_DIALOG_OUTSIDE_MARGIN_Y * 2))
    dialog_kind = str(dialog.property("task_dialog_kind") or "").strip().lower()
    if dialog_kind == "edit":
        max_width = min(max_width, _TASK_EDIT_DIALOG_MAX_SIZE.width())
        max_height = min(max_height, _TASK_EDIT_DIALOG_MAX_SIZE.height())
    target_width = min(dialog.width(), max_width)
    target_height = min(dialog.height(), max_height)
    dialog.resize(target_width, target_height)


def _attach_dialog_overlay(dialog: QDialog) -> ModalOverlay | None:
    parent = dialog.parentWidget()
    overlay_parent = _resolve_overlay_parent(parent)
    existing_overlay = getattr(dialog, "_task_dialog_overlay", None)
    if isinstance(existing_overlay, ModalOverlay):
        try:
            if existing_overlay.parent() is overlay_parent:
                existing_overlay.show()
                existing_overlay.raise_()
                debug_task_dialog(
                    f"attach_overlay dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')} "
                    f"overlay_parent={type(overlay_parent).__name__ if overlay_parent is not None else 'None'} "
                    f"overlay=reused"
                )
                return existing_overlay
        except RuntimeError:
            setattr(dialog, "_task_dialog_overlay", None)
    overlay = dialog_presentation_controller().prepare(
        dialog,
        parent=parent,
        center=False,
        overlay_parent=overlay_parent,
    )
    if overlay is not None:
        setattr(dialog, "_task_dialog_overlay", overlay)
        overlay.destroyed.connect(lambda *_args, current_dialog=dialog: setattr(current_dialog, "_task_dialog_overlay", None))
    debug_task_dialog(
        f"attach_overlay dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')} "
        f"overlay_parent={type(overlay_parent).__name__ if overlay_parent is not None else 'None'} "
        f"overlay={'yes' if overlay is not None else 'no'}"
    )
    if overlay is not None:
        _bind_overlay_click_behavior(dialog, overlay)
    return overlay


def ensure_minimizable_task_dialog_overlay(dialog: QDialog) -> ModalOverlay | None:
    if not _is_minimizable_task_dialog(dialog):
        return None
    return _attach_dialog_overlay(dialog)


def _run_minimizable_task_dialog(dialog: QDialog) -> int:
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    prepare_minimizable_task_dialog_for_show(dialog, dialog.parentWidget(), center=False)
    minimizer = getattr(dialog, "_task_dialog_outside_click_minimizer", None)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    debug_task_dialog(
        f"run_minimizable_dialog show dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')} "
        f"active={dialog.isActiveWindow()} visible={dialog.isVisible()}"
    )

    result_holder = {"value": int(dialog.result())}
    loop = QEventLoop(dialog)

    def _finish(result_code: int) -> None:
        result_holder["value"] = int(result_code)
        if loop.isRunning():
            loop.quit()

    dialog.finished.connect(_finish)
    try:
        loop.exec()
    finally:
        try:
            dialog.finished.disconnect(_finish)
        except (RuntimeError, TypeError):
            pass
    return result_holder["value"]


def _bind_overlay_click_behavior(dialog: QDialog, overlay: ModalOverlay) -> None:
    if not bool(dialog.property("task_dialog_minimizable")):
        return
    setattr(overlay, "_overlay_click_handler", lambda d=dialog, o=overlay: _handle_task_dialog_overlay_click(d, o))


def _try_minimize_task_dialog(dialog: QDialog) -> bool:
    if not dialog.isVisible():
        debug_task_dialog(
            f"try_minimize skipped invisible dialog={type(dialog).__name__} task_id={dialog.property('task_dialog_id')}"
        )
        return False
    raw_task_id = dialog.property("task_dialog_id")
    try:
        task_id = int(raw_task_id)
    except (TypeError, ValueError):
        return False
    if task_id <= 0:
        debug_task_dialog(f"try_minimize skipped invalid task_id dialog={type(dialog).__name__}")
        return False
    dialog_kind = str(dialog.property("task_dialog_kind") or "").strip().lower()
    window = dialog.parentWidget().window() if dialog.parentWidget() is not None else QApplication.activeWindow()
    minimize_fn = getattr(window, "minimize_task_dialog", None)
    if not callable(minimize_fn):
        debug_task_dialog(
            f"try_minimize missing minimize_fn dialog={type(dialog).__name__} task_id={task_id} "
            f"window={type(window).__name__ if window is not None else 'None'}"
        )
        return False
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    debug_task_dialog(
        f"try_minimize call dialog={type(dialog).__name__} task_id={task_id} "
        f"window={type(window).__name__ if window is not None else 'None'}"
    )
    minimize_fn(dialog=dialog, task_id=task_id, is_edit_dialog=(dialog_kind == "edit"))
    return True


def _handle_task_dialog_overlay_click(dialog: QDialog, overlay: ModalOverlay) -> None:
    overlay.deleteLater()
    _try_minimize_task_dialog(dialog)
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
