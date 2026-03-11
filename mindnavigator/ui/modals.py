"""Модальные окна и оверлей для блокировки фона.

Входные данные:
    Диалоги Qt и ссылки на родительские виджеты.

Выходные данные:
    Результаты выполнения диалогов и визуальный оверлей.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QLabel, QVBoxLayout, QWidget

from .animations import DialogAppearAnimator
from .styles import MATH_PHYS_BACKGROUND

_DIALOG_PRESENTATION_CONTROLLER = None


class ModalOverlay(QFrame):
    """Полупрозрачный слой для затемнения интерфейса под модальными окнами."""

    clicked = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("ModalOverlay")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("QFrame#ModalOverlay { background: rgba(10, 10, 12, 160); }")
        self._sync_geometry()
        parent.installEventFilter(self)
        self.show()

    def _sync_geometry(self) -> None:
        self.setGeometry(self.parent().rect())
        self.raise_()

    def eventFilter(self, obj, event) -> bool:
        if obj is self.parent() and event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
            self._sync_geometry()
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton:
            handler = getattr(self, "_overlay_click_handler", None)
            if callable(handler):
                try:
                    from mindnavigator.ui.dialogs.task_dialog_debug import debug_task_dialog

                    debug_task_dialog("modal_overlay mouse_press handler=direct")
                except Exception:
                    pass
                handler()
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def closeEvent(self, event) -> None:
        parent = self.parent()
        if parent is not None:
            parent.removeEventFilter(self)
        super().closeEvent(event)


class DialogPresentationController:
    """Подготавливает модальное окно: центрирование, overlay и анимацию появления."""

    def __init__(self, animator: DialogAppearAnimator | None = None) -> None:
        self._animator = animator or DialogAppearAnimator()

    def prepare(
        self,
        dialog: QDialog,
        parent: QWidget | None = None,
        *,
        center: bool = True,
        overlay_parent: QWidget | None = None,
    ) -> ModalOverlay | None:
        if center:
            center_fn = getattr(dialog, "center_on_active_parent", None)
            if callable(center_fn):
                center_fn(parent)
        resolved_overlay_parent = overlay_parent or self.resolve_overlay_parent(parent)
        overlay = ModalOverlay(resolved_overlay_parent) if resolved_overlay_parent is not None else None
        if overlay is not None:
            self._bind_overlay_cleanup(dialog, overlay)
        if self.should_animate(dialog):
            QTimer.singleShot(0, lambda current_dialog=dialog: self._animator.play(current_dialog))
        return overlay

    @staticmethod
    def should_animate(dialog: QDialog) -> bool:
        return not bool(dialog.property("disable_dialog_appear_animation"))

    @staticmethod
    def resolve_overlay_parent(parent: QWidget | None) -> QWidget | None:
        if parent is not None:
            return parent.window()
        # QApplication imported lazily to keep this module light at import time.
        from PySide6.QtWidgets import QApplication

        active_window = QApplication.activeWindow()
        return active_window.window() if active_window is not None else None

    @staticmethod
    def _bind_overlay_cleanup(dialog: QDialog, overlay: ModalOverlay) -> None:
        dialog.accepted.connect(overlay.deleteLater)
        dialog.rejected.connect(overlay.deleteLater)
        dialog.finished.connect(overlay.deleteLater)


def dialog_presentation_controller() -> DialogPresentationController:
    global _DIALOG_PRESENTATION_CONTROLLER
    if _DIALOG_PRESENTATION_CONTROLLER is None:
        _DIALOG_PRESENTATION_CONTROLLER = DialogPresentationController()
    return _DIALOG_PRESENTATION_CONTROLLER


def _is_global_dialog_patch_enabled() -> bool:
    try:
        from mindnavigator.ui.dialogs.frameless_patch import are_frameless_qdialogs_enabled
    except Exception:
        return False
    return bool(are_frameless_qdialogs_enabled())


def exec_with_overlay(dialog: QDialog, parent: QWidget | None) -> int:
    return show_dialog_standard(dialog, parent)


def show_dialog_standard(dialog: QDialog, parent: QWidget | None) -> int:
    """Runs dialog using global dialog standard."""
    if bool(dialog.property("task_dialog_minimizable")):
        from mindnavigator.ui.dialogs.frameless_patch import show_minimizable_task_dialog

        return show_minimizable_task_dialog(dialog, parent)
    if not _is_global_dialog_patch_enabled():
        dialog_presentation_controller().prepare(dialog, parent=parent)
    return dialog.exec()


class ConfirmDialog(QDialog):
    """Кастомный диалог подтверждения в стиле приложения."""

    def __init__(
        self,
        title: str,
        message: str,
        parent: QWidget | None = None,
        confirm_text: str = "Да",
        cancel_text: str = "Отмена",
    ):
        super().__init__(parent)
        self.setObjectName("ConfirmDialog")
        self.setWindowTitle(title)
        self.setProperty("dialog_category", "minimal_flex")
        self.setFixedSize(560, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("DialogTitle")
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setObjectName("DialogMessage")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        buttons = QDialogButtonBox()
        confirm_btn = buttons.addButton(confirm_text, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(cancel_text, QDialogButtonBox.ButtonRole.RejectRole)
        confirm_btn.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(f"""
            QDialog#ConfirmDialog {{
                {MATH_PHYS_BACKGROUND}
            }}

            QDialog#ConfirmDialog QLabel#DialogTitle {{
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }}

            QDialog#ConfirmDialog QLabel#DialogMessage {{
                color: #cfcfcf;
                font-size: 13px;
            }}

            QDialog#ConfirmDialog QDialogButtonBox QPushButton {{
                background: #2a2b2f;
                color: #e6e6e6;
                border: 1px solid #3a3b40;
                padding: 8px 14px;
                border-radius: 6px;
                min-width: 90px;
            }}

            QDialog#ConfirmDialog QDialogButtonBox QPushButton:hover {{
                background: #34363b;
            }}
        """)

