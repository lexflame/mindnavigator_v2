from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QLineEdit,
    QFileDialog,
)

from mindnavigator.storage import get_database


class SettingsWorkspace(QWidget):
    """Рабочая область настроек приложения."""

    CLOUD_STORAGE_KEY = "cloud_storage_path"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Настройки")
        title.setObjectName("SettingsTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("SettingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        label = QLabel("Облачное хранилище")
        label.setObjectName("SettingsLabel")
        hint = QLabel("Путь к физической папке на ПК для синхронизации.")
        hint.setObjectName("SettingsHint")
        hint.setWordWrap(True)

        text_col.addWidget(label)
        text_col.addWidget(hint)
        row.addLayout(text_col, 1)

        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("SettingsPath")
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Не задано")

        self.btn_edit = QToolButton()
        self.btn_edit.setText("Изменить")
        self.btn_edit.setObjectName("SettingsEditButton")
        self.btn_edit.clicked.connect(self._edit_cloud_storage)

        row.addWidget(self.path_edit, 2)
        row.addWidget(self.btn_edit, 0)

        card_layout.addLayout(row)
        layout.addWidget(card)
        layout.addStretch(1)

        self.setStyleSheet(
            """
            QWidget#SettingsTitle {
                color: #e6e6e6;
                font-size: 20px;
                font-weight: 600;
            }
            QFrame#SettingsCard {
                background: #222429;
                border: 1px solid #32343a;
                border-radius: 10px;
            }
            QLabel#SettingsLabel {
                color: #e2e2e2;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#SettingsHint {
                color: #8f9299;
                font-size: 11px;
            }
            QLineEdit#SettingsPath {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 6px;
                padding: 6px 10px;
                color: #d6d6d6;
                font-size: 11px;
            }
            QToolButton#SettingsEditButton {
                background: #2a2d33;
                border: 1px solid #3a3d44;
                border-radius: 6px;
                padding: 6px 14px;
                color: #e0e0e0;
                font-size: 11px;
                font-weight: 600;
            }
            QToolButton#SettingsEditButton:hover {
                background: #343841;
            }
            """
        )

    def _load_settings(self) -> None:
        path_value = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="")
        self.path_edit.setText(path_value)

    def _edit_cloud_storage(self) -> None:
        current = self.path_edit.text().strip()
        start_dir = Path(current) if current else Path.home()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для облачного хранилища",
            str(start_dir),
        )
        if not selected:
            return
        self._db.set_setting(self.CLOUD_STORAGE_KEY, selected)
        self.path_edit.setText(selected)
