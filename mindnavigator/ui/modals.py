"""Модальные окна и оверлей для блокировки фона.

Входные данные:
    Диалоги Qt и ссылки на родительские виджеты.

Выходные данные:
    Результаты выполнения диалогов и визуальный оверлей.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QLabel, QVBoxLayout, QWidget

from .styles import MATH_PHYS_BACKGROUND


class ModalOverlay(QFrame):
    """Полупрозрачный слой для затемнения интерфейса под модальными окнами."""

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

    def closeEvent(self, event) -> None:
        parent = self.parent()
        if parent is not None:
            parent.removeEventFilter(self)
        super().closeEvent(event)


def exec_with_overlay(dialog: QDialog, parent: QWidget | None) -> int:
    return show_dialog_standard(dialog, parent)


def show_dialog_standard(dialog: QDialog, parent: QWidget | None) -> int:
    """Runs dialog using global dialog standard."""
    center_fn = getattr(dialog, "center_on_active_parent", None)
    if callable(center_fn):
        center_fn(parent)
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

