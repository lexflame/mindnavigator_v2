"""Рабочая область настроек приложения.

Входные данные:
    Значения полей настроек, пути для резервного копирования и события UI.

Выходные данные:
    Обновлённые параметры конфигурации и операции бэкапа.
"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
import shutil
import sys
import tempfile
import zipfile
from typing import cast

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QLineEdit,
    QFileDialog,
    QCheckBox,
    QComboBox,
    QDialog,
    QSpinBox,
    QMessageBox,
)

from mindnavigator.constants import APP_VERSION, UPDATE_REPOSITORY_NAME, UPDATE_REPOSITORY_OWNER
from mindnavigator.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, normalize_language_code
from mindnavigator.storage import (
    default_db_path,
    get_configured_db_path,
    get_database,
    is_network_database_path,
    set_configured_db_path,
)
from mindnavigator.update_service import UpdateService, UpdateServiceError
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay


class SettingsWorkspace(QWidget):
    """Рабочая область настроек приложения."""

    setting_changed = Signal(str, str)

    CLOUD_STORAGE_KEY = "cloud_storage_path"
    BACKUP_DIR_KEY = "backup_dir"
    BACKUP_INCLUDE_CLOUD_KEY = "backup_include_cloud"
    BACKUP_AUTO_ENABLED_KEY = "backup_auto_enabled"
    BACKUP_FREQUENCY_KEY = "backup_frequency"
    BACKUP_RETENTION_KEY = "backup_retention"
    BACKUP_LAST_RUN_KEY = "backup_last_run"
    APP_MINIMIZE_ON_FOCUS_LOST_KEY = "app.minimize_on_focus_lost"
    APP_AUTOSTART_WINDOWS_KEY = "app.autostart_windows"
    APP_SINGLE_INSTANCE_KEY = "app.single_instance"
    APP_ENABLED_WORKSPACES_KEY = "app.enabled_workspaces"
    APP_LANGUAGE_KEY = "app.language"
    APP_DATABASE_PATH_SIGNAL_KEY = "app.database_path"
    BACKUP_PREFIX = "mindnavigator_backup_"
    BACKUP_MANIFEST_NAME = "backup_manifest.json"
    WORKSPACE_OPTIONS = [
        ("projects", "Проекты"),
        ("tasks", "Задачи"),
        ("purchases", "Покупки"),
        ("ideas", "Идеи"),
        ("collections", "Коллекции"),
        ("maps", "Карты"),
        ("notes", "Заметки"),
        ("files", "Файлы"),
        ("objects", "Объекты"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._loading_settings = False
        self._backup_entries: list[dict[str, object]] = []
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

        db_card = QFrame()
        db_card.setObjectName("SettingsCard")
        db_layout = QVBoxLayout(db_card)
        db_layout.setContentsMargins(20, 18, 20, 18)
        db_layout.setSpacing(12)

        db_title = QLabel("Database storage")
        db_title.setObjectName("SettingsSectionTitle")
        db_hint = QLabel("Choose where the local SQLite database file is stored.")
        db_hint.setObjectName("SettingsHint")
        db_hint.setWordWrap(True)
        db_layout.addWidget(db_title)
        db_layout.addWidget(db_hint)

        db_row = QHBoxLayout()
        db_row.setSpacing(12)
        db_text = QVBoxLayout()
        db_text.setSpacing(6)

        db_label = QLabel("Database file")
        db_label.setObjectName("SettingsLabel")
        db_desc = QLabel("Path applies on next app start. Current data is copied to the new location.")
        db_desc.setObjectName("SettingsHint")
        db_desc.setWordWrap(True)
        db_text.addWidget(db_label)
        db_text.addWidget(db_desc)
        db_row.addLayout(db_text, 1)

        self.db_path_edit = QLineEdit()
        self.db_path_edit.setObjectName("SettingsPath")
        self.db_path_edit.setReadOnly(True)
        self.db_path_edit.setPlaceholderText("Not set")

        self.btn_db_dir = QToolButton()
        self.btn_db_dir.setText("Choose")
        self.btn_db_dir.setObjectName("SettingsEditButton")
        self.btn_db_dir.clicked.connect(self._edit_database_storage)

        self.btn_db_open = QToolButton()
        self.btn_db_open.setText("Open")
        self.btn_db_open.setObjectName("SettingsEditButton")
        self.btn_db_open.clicked.connect(self._open_database_storage)

        self.btn_check_updates = QToolButton()
        self.btn_check_updates.setText("Check update")
        self.btn_check_updates.setObjectName("SettingsEditButton")
        self.btn_check_updates.clicked.connect(self._check_updates)

        db_row.addWidget(self.db_path_edit, 2)
        db_row.addWidget(self.btn_db_dir, 0)
        db_row.addWidget(self.btn_db_open, 0)
        db_row.addWidget(self.btn_check_updates, 0)
        db_layout.addLayout(db_row)

        self.db_path_status = QLabel("")
        self.db_path_status.setObjectName("SettingsStatus")
        self.db_path_status.setWordWrap(True)
        db_layout.addWidget(self.db_path_status)

        layout.addWidget(db_card)

        workspace_card = QFrame()
        workspace_card.setObjectName("SettingsCard")
        workspace_layout = QVBoxLayout(workspace_card)
        workspace_layout.setContentsMargins(20, 18, 20, 18)
        workspace_layout.setSpacing(12)

        workspace_title = QLabel("Visible workspaces")
        workspace_title.setObjectName("SettingsSectionTitle")
        workspace_hint = QLabel("Select which modes are shown in the left sidebar.")
        workspace_hint.setObjectName("SettingsHint")
        workspace_hint.setWordWrap(True)
        workspace_layout.addWidget(workspace_title)
        workspace_layout.addWidget(workspace_hint)

        self.workspace_checkboxes: dict[str, QCheckBox] = {}
        checkbox_row = QHBoxLayout()
        checkbox_row.setSpacing(12)
        left_col = QVBoxLayout()
        left_col.setSpacing(6)
        right_col = QVBoxLayout()
        right_col.setSpacing(6)
        split_index = (len(self.WORKSPACE_OPTIONS) + 1) // 2
        for idx, (workspace_id, label_text) in enumerate(self.WORKSPACE_OPTIONS):
            checkbox = QCheckBox(label_text)
            checkbox.setObjectName("SettingsToggle")
            checkbox.toggled.connect(self._on_workspace_visibility_changed)
            self.workspace_checkboxes[workspace_id] = checkbox
            if idx < split_index:
                left_col.addWidget(checkbox)
            else:
                right_col.addWidget(checkbox)
        left_col.addStretch(1)
        right_col.addStretch(1)
        checkbox_row.addLayout(left_col, 1)
        checkbox_row.addLayout(right_col, 1)
        workspace_layout.addLayout(checkbox_row)

        self.workspace_status = QLabel("")
        self.workspace_status.setObjectName("SettingsStatus")
        self.workspace_status.setWordWrap(True)
        workspace_layout.addWidget(self.workspace_status)

        layout.addWidget(workspace_card)

        backup_card = QFrame()
        backup_card.setObjectName("SettingsCard")
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(20, 18, 20, 18)
        backup_layout.setSpacing(14)

        backup_title = QLabel("Резервное копирование")
        backup_title.setObjectName("SettingsSectionTitle")
        backup_hint = QLabel(
            "Сохраняйте копии базы данных и облачных файлов, "
            "управляйте расписанием и количеством хранённых архивов."
        )
        backup_hint.setObjectName("SettingsHint")
        backup_hint.setWordWrap(True)
        backup_layout.addWidget(backup_title)
        backup_layout.addWidget(backup_hint)

        backup_row = QHBoxLayout()
        backup_row.setSpacing(12)

        backup_text = QVBoxLayout()
        backup_text.setSpacing(6)

        backup_label = QLabel("Папка резервных копий")
        backup_label.setObjectName("SettingsLabel")
        backup_desc = QLabel("Укажите директорию, в которой будут храниться архивы.")
        backup_desc.setObjectName("SettingsHint")
        backup_desc.setWordWrap(True)
        backup_text.addWidget(backup_label)
        backup_text.addWidget(backup_desc)

        backup_row.addLayout(backup_text, 1)

        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setObjectName("SettingsPath")
        self.backup_path_edit.setReadOnly(True)
        self.backup_path_edit.setPlaceholderText("Не задано")

        self.btn_backup_dir = QToolButton()
        self.btn_backup_dir.setText("Выбрать")
        self.btn_backup_dir.setObjectName("SettingsEditButton")
        self.btn_backup_dir.clicked.connect(self._edit_backup_dir)

        self.btn_backup_open = QToolButton()
        self.btn_backup_open.setText("Открыть")
        self.btn_backup_open.setObjectName("SettingsEditButton")
        self.btn_backup_open.clicked.connect(self._open_backup_dir)

        backup_row.addWidget(self.backup_path_edit, 2)
        backup_row.addWidget(self.btn_backup_dir, 0)
        backup_row.addWidget(self.btn_backup_open, 0)

        backup_layout.addLayout(backup_row)

        options_row = QHBoxLayout()
        options_row.setSpacing(12)

        self.include_cloud_checkbox = QCheckBox("Включать облачное хранилище")
        self.include_cloud_checkbox.setObjectName("SettingsToggle")
        self.include_cloud_checkbox.toggled.connect(self._on_backup_option_changed)

        self.auto_backup_checkbox = QCheckBox("Автокопирование")
        self.auto_backup_checkbox.setObjectName("SettingsToggle")
        self.auto_backup_checkbox.toggled.connect(self._on_backup_option_changed)

        self.frequency_combo = QComboBox()
        self.frequency_combo.setObjectName("SettingsCombo")
        self.frequency_combo.addItem("Ежедневно", "daily")
        self.frequency_combo.addItem("Еженедельно", "weekly")
        self.frequency_combo.addItem("Ежемесячно", "monthly")
        self.frequency_combo.currentIndexChanged.connect(self._on_backup_option_changed)

        self.retention_spin = QSpinBox()
        self.retention_spin.setObjectName("SettingsSpin")
        self.retention_spin.setRange(1, 50)
        self.retention_spin.setSuffix(" копий")
        self.retention_spin.valueChanged.connect(self._on_backup_option_changed)

        options_row.addWidget(self.include_cloud_checkbox)
        options_row.addWidget(self.auto_backup_checkbox)
        options_row.addWidget(self.frequency_combo)
        options_row.addWidget(self.retention_spin)
        options_row.addStretch(1)
        backup_layout.addLayout(options_row)

        list_row = QHBoxLayout()
        list_row.setSpacing(12)

        list_label = QLabel("Последние копии")
        list_label.setObjectName("SettingsLabel")
        list_row.addWidget(list_label, 0)

        self.backup_combo = QComboBox()
        self.backup_combo.setObjectName("SettingsCombo")
        self.backup_combo.currentIndexChanged.connect(self._update_backup_details)
        list_row.addWidget(self.backup_combo, 1)
        backup_layout.addLayout(list_row)

        self.backup_details = QLabel("Архивы не найдены.")
        self.backup_details.setObjectName("SettingsHint")
        self.backup_details.setWordWrap(True)
        backup_layout.addWidget(self.backup_details)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_backup_now = QToolButton()
        self.btn_backup_now.setText("Создать копию")
        self.btn_backup_now.setObjectName("SettingsEditButton")
        self.btn_backup_now.clicked.connect(self._create_backup)

        self.btn_restore_backup = QToolButton()
        self.btn_restore_backup.setText("Восстановить")
        self.btn_restore_backup.setObjectName("SettingsEditButton")
        self.btn_restore_backup.clicked.connect(self._restore_selected_backup)

        self.btn_delete_backup = QToolButton()
        self.btn_delete_backup.setText("Удалить")
        self.btn_delete_backup.setObjectName("SettingsEditButton")
        self.btn_delete_backup.clicked.connect(self._delete_selected_backup)

        action_row.addWidget(self.btn_backup_now)
        action_row.addWidget(self.btn_restore_backup)
        action_row.addWidget(self.btn_delete_backup)
        action_row.addStretch(1)
        backup_layout.addLayout(action_row)

        self.backup_status = QLabel("")
        self.backup_status.setObjectName("SettingsStatus")
        self.backup_status.setWordWrap(True)
        backup_layout.addWidget(self.backup_status)

        layout.addWidget(backup_card)
        behavior_card = QFrame()
        behavior_card.setObjectName("SettingsCard")
        behavior_layout = QVBoxLayout(behavior_card)
        behavior_layout.setContentsMargins(20, 18, 20, 18)
        behavior_layout.setSpacing(10)

        behavior_title = QLabel("Поведение приложения")
        behavior_title.setObjectName("SettingsSectionTitle")
        behavior_layout.addWidget(behavior_title)

        language_row = QHBoxLayout()
        language_row.setSpacing(12)
        language_label = QLabel("Язык приложения")
        language_label.setObjectName("SettingsLabel")
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("SettingsCombo")
        for language_code, language_name in SUPPORTED_LANGUAGES.items():
            self.language_combo.addItem(language_name, language_code)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        language_row.addWidget(language_label, 0)
        language_row.addWidget(self.language_combo, 1)
        behavior_layout.addLayout(language_row)

        self.minimize_on_focus_lost_checkbox = QCheckBox("Убирать в трей при потере фокуса окна приложения")
        self.minimize_on_focus_lost_checkbox.setObjectName("SettingsToggle")
        self.minimize_on_focus_lost_checkbox.toggled.connect(self._on_behavior_option_changed)
        behavior_layout.addWidget(self.minimize_on_focus_lost_checkbox)

        self.autostart_windows_checkbox = QCheckBox("Автостарт приложения при запуске Windows")
        self.autostart_windows_checkbox.setObjectName("SettingsToggle")
        self.autostart_windows_checkbox.toggled.connect(self._on_behavior_option_changed)
        behavior_layout.addWidget(self.autostart_windows_checkbox)

        self.single_instance_checkbox = QCheckBox(
            "Запретить запуск нескольких экземпляров приложения, при повторном запуске вызвать из трея"
        )
        self.single_instance_checkbox.setObjectName("SettingsToggle")
        self.single_instance_checkbox.toggled.connect(self._on_behavior_option_changed)
        behavior_layout.addWidget(self.single_instance_checkbox)
        layout.addWidget(behavior_card)
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
            QLabel#SettingsSectionTitle {
                color: #e6e6e6;
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#SettingsStatus {
                color: #9aa3ad;
                font-size: 11px;
            }
            QCheckBox#SettingsToggle {
                color: #d6d6d6;
                font-size: 11px;
            }
            QComboBox#SettingsCombo, QSpinBox#SettingsSpin {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 6px;
                padding: 4px 8px;
                color: #d6d6d6;
                font-size: 11px;
                min-width: 130px;
            }
            QComboBox#SettingsCombo::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox#SettingsCombo QAbstractItemView {
                background: #1b1d22;
                color: #e0e0e0;
                selection-background-color: #343841;
            }
            """
        )

    def _load_settings(self) -> None:
        self._loading_settings = True
        try:
            path_value = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="")
            self.path_edit.setText(path_value)
            configured_db_path = get_configured_db_path() or default_db_path()
            self.db_path_edit.setText(str(configured_db_path))
            backup_dir = self._db.get_setting(self.BACKUP_DIR_KEY, default="")
            self.backup_path_edit.setText(backup_dir)

            include_cloud = self._db.get_setting(self.BACKUP_INCLUDE_CLOUD_KEY, default="1") == "1"
            auto_enabled = self._db.get_setting(self.BACKUP_AUTO_ENABLED_KEY, default="0") == "1"
            frequency = self._db.get_setting(self.BACKUP_FREQUENCY_KEY, default="weekly")
            retention = self._db.get_setting(self.BACKUP_RETENTION_KEY, default="7")

            self.include_cloud_checkbox.blockSignals(True)
            self.auto_backup_checkbox.blockSignals(True)
            self.frequency_combo.blockSignals(True)
            self.retention_spin.blockSignals(True)
            self.include_cloud_checkbox.setChecked(include_cloud)
            self.auto_backup_checkbox.setChecked(auto_enabled)
            self._set_combo_value(self.frequency_combo, frequency)
            self.retention_spin.setValue(max(1, int(retention) if retention.isdigit() else 7))
            self.include_cloud_checkbox.blockSignals(False)
            self.auto_backup_checkbox.blockSignals(False)
            self.frequency_combo.blockSignals(False)
            self.retention_spin.blockSignals(False)

            selected_language = normalize_language_code(
                self._db.get_setting(self.APP_LANGUAGE_KEY, default=DEFAULT_LANGUAGE)
            )
            self.language_combo.blockSignals(True)
            self._set_combo_value(self.language_combo, selected_language)
            self.language_combo.blockSignals(False)

            minimize_on_focus_lost = self._db.get_setting(self.APP_MINIMIZE_ON_FOCUS_LOST_KEY, default="1") == "1"
            autostart_windows = self._db.get_setting(self.APP_AUTOSTART_WINDOWS_KEY, default="0") == "1"
            single_instance = self._db.get_setting(self.APP_SINGLE_INSTANCE_KEY, default="1") == "1"
            self.minimize_on_focus_lost_checkbox.blockSignals(True)
            self.autostart_windows_checkbox.blockSignals(True)
            self.single_instance_checkbox.blockSignals(True)
            self.minimize_on_focus_lost_checkbox.setChecked(minimize_on_focus_lost)
            self.autostart_windows_checkbox.setChecked(autostart_windows)
            self.single_instance_checkbox.setChecked(single_instance)
            self.minimize_on_focus_lost_checkbox.blockSignals(False)
            self.autostart_windows_checkbox.blockSignals(False)
            self.single_instance_checkbox.blockSignals(False)
            self._apply_windows_autostart(autostart_windows)

            enabled_workspaces_raw = self._db.get_setting(self.APP_ENABLED_WORKSPACES_KEY, default="")
            enabled_workspace_ids = self._normalize_enabled_workspace_ids(enabled_workspaces_raw)
            self._set_workspace_checkboxes(enabled_workspace_ids)
            self._update_workspace_status()
            self._update_database_status()
            self._refresh_backup_list()
        finally:
            self._loading_settings = False

        self._maybe_run_auto_backup()
        self._update_backup_status()

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

    def _edit_database_storage(self) -> None:
        current = self.db_path_edit.text().strip()
        current_path = Path(current) if current else self._db.path
        start_dir = current_path.parent if current_path.parent.exists() else Path.home()
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select database storage directory",
            str(start_dir),
        )
        if not selected_dir:
            return
        target_db_path = Path(selected_dir) / "mindnavigator.db"
        try:
            if target_db_path.resolve() != self._db.path.resolve():
                self._db.backup_to(target_db_path)
            set_configured_db_path(target_db_path)
        except Exception as exc:
            QMessageBox.warning(self, "Database path", str(exc))
            self._update_database_status(message="Failed to update database path.")
            return
        self.db_path_edit.setText(str(target_db_path))
        self.setting_changed.emit(self.APP_DATABASE_PATH_SIGNAL_KEY, str(target_db_path))
        self._update_database_status(message="Database path updated. Restart app to switch active DB.")

    def _open_database_storage(self) -> None:
        selected = self.db_path_edit.text().strip()
        if not selected:
            self._update_database_status(message="Select database storage directory first.")
            return
        db_path = Path(selected)
        target_dir = db_path.parent if db_path.suffix else db_path
        if not target_dir.exists():
            self._update_database_status(message="Database directory not found.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    def _update_database_status(self, message: str | None = None) -> None:
        selected = self.db_path_edit.text().strip()
        status_parts: list[str] = []
        if message:
            status_parts.append(message)
        if selected:
            selected_path = Path(selected)
            try:
                pending_switch = selected_path.resolve() != self._db.path.resolve()
            except OSError:
                pending_switch = str(selected_path) != str(self._db.path)
            if pending_switch:
                status_parts.append("Pending switch: restart required.")
            else:
                status_parts.append("Active database path.")
            if is_network_database_path(selected_path):
                status_parts.append(
                    "Network DB compatibility mode: WAL disabled, writes are serialized between app instances."
                )
        self.db_path_status.setText(" ".join(status_parts).strip())

    def _check_updates(self) -> None:
        try:
            schema_version = self._db.apply_schema_updates()
        except Exception as exc:
            QMessageBox.warning(self, "Check update", f"Failed to update DB schema: {exc}")
            self._update_database_status(message="DB schema update failed.")
            return

        service = UpdateService(
            owner=UPDATE_REPOSITORY_OWNER,
            repository=UPDATE_REPOSITORY_NAME,
        )
        try:
            update_info = service.check_for_update(APP_VERSION)
        except UpdateServiceError as exc:
            message = f"DB schema is up to date (v{schema_version}). Version check failed: {exc}"
            QMessageBox.information(self, "Check update", message)
            self._update_database_status(message=message)
            return

        if update_info.update_available:
            message = (
                f"DB schema is up to date (v{schema_version}). "
                f"New app version available: {update_info.latest_version}. "
                f"Release: {update_info.release_url}"
            )
        else:
            message = (
                f"DB schema is up to date (v{schema_version}). "
                f"Current app version {update_info.current_version} is latest."
            )
        QMessageBox.information(self, "Check update", message)
        self._update_database_status(message=message)

    def _edit_backup_dir(self) -> None:
        current = self.backup_path_edit.text().strip()
        start_dir = Path(current) if current else Path.home()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для резервных копий",
            str(start_dir),
        )
        if not selected:
            return
        self._db.set_setting(self.BACKUP_DIR_KEY, selected)
        self.backup_path_edit.setText(selected)
        self._refresh_backup_list()
        self._update_backup_status(message="Папка резервных копий обновлена.")

    def _open_backup_dir(self) -> None:
        backup_dir = self._get_backup_dir()
        if not backup_dir:
            self._update_backup_status(message="Сначала выберите папку для резервных копий.")
            return
        if not backup_dir.exists():
            self._update_backup_status(message="Папка резервных копий не найдена.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_dir)))

    def _on_backup_option_changed(self) -> None:
        if self._loading_settings:
            return
        try:
            self._db.set_setting(
                self.BACKUP_INCLUDE_CLOUD_KEY,
                "1" if self.include_cloud_checkbox.isChecked() else "0",
            )
            self._db.set_setting(
                self.BACKUP_AUTO_ENABLED_KEY,
                "1" if self.auto_backup_checkbox.isChecked() else "0",
            )
            frequency = self.frequency_combo.currentData()
            if frequency:
                self._db.set_setting(self.BACKUP_FREQUENCY_KEY, frequency)
            self._db.set_setting(self.BACKUP_RETENTION_KEY, str(self.retention_spin.value()))
        except sqlite3.Error as exc:
            self._update_backup_status(message=f"Backup settings were not saved: {exc}")
            return
        self._update_backup_status()

    def _on_behavior_option_changed(self) -> None:
        minimize_on_focus_lost = "1" if self.minimize_on_focus_lost_checkbox.isChecked() else "0"
        autostart_windows = "1" if self.autostart_windows_checkbox.isChecked() else "0"
        single_instance = "1" if self.single_instance_checkbox.isChecked() else "0"
        self._db.set_setting(self.APP_MINIMIZE_ON_FOCUS_LOST_KEY, minimize_on_focus_lost)
        self._db.set_setting(self.APP_AUTOSTART_WINDOWS_KEY, autostart_windows)
        self._db.set_setting(self.APP_SINGLE_INSTANCE_KEY, single_instance)
        self._apply_windows_autostart(self.autostart_windows_checkbox.isChecked())
        self.setting_changed.emit(self.APP_MINIMIZE_ON_FOCUS_LOST_KEY, minimize_on_focus_lost)
        self.setting_changed.emit(self.APP_AUTOSTART_WINDOWS_KEY, autostart_windows)
        self.setting_changed.emit(self.APP_SINGLE_INSTANCE_KEY, single_instance)

    def _on_language_changed(self) -> None:
        selected_language = normalize_language_code(
            str(self.language_combo.currentData() or DEFAULT_LANGUAGE)
        )
        self._db.set_setting(self.APP_LANGUAGE_KEY, selected_language)
        self.setting_changed.emit(self.APP_LANGUAGE_KEY, selected_language)

    def _normalize_enabled_workspace_ids(self, raw_value: str) -> list[str]:
        all_ids = [workspace_id for workspace_id, _ in self.WORKSPACE_OPTIONS]
        if not raw_value:
            return all_ids
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return all_ids
        if not isinstance(parsed, list):
            return all_ids
        enabled = []
        for item in parsed:
            item_value = str(item).strip()
            if item_value in all_ids and item_value not in enabled:
                enabled.append(item_value)
        return enabled if enabled else all_ids

    def _set_workspace_checkboxes(self, enabled_workspace_ids: list[str]) -> None:
        enabled_set = set(enabled_workspace_ids)
        for workspace_id, checkbox in self.workspace_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(workspace_id in enabled_set)
            checkbox.blockSignals(False)

    def _on_workspace_visibility_changed(self) -> None:
        enabled_ids = [
            workspace_id
            for workspace_id, checkbox in self.workspace_checkboxes.items()
            if checkbox.isChecked()
        ]
        if not enabled_ids:
            # Keep at least one workspace enabled to avoid an empty sidebar.
            fallback_id = "tasks" if "tasks" in self.workspace_checkboxes else next(iter(self.workspace_checkboxes))
            self.workspace_checkboxes[fallback_id].blockSignals(True)
            self.workspace_checkboxes[fallback_id].setChecked(True)
            self.workspace_checkboxes[fallback_id].blockSignals(False)
            enabled_ids = [fallback_id]
        serialized = json.dumps(enabled_ids, ensure_ascii=False)
        self._db.set_setting(self.APP_ENABLED_WORKSPACES_KEY, serialized)
        self.setting_changed.emit(self.APP_ENABLED_WORKSPACES_KEY, serialized)
        self._update_workspace_status()

    def _update_workspace_status(self) -> None:
        enabled_count = sum(1 for checkbox in self.workspace_checkboxes.values() if checkbox.isChecked())
        self.workspace_status.setText(f"Enabled workspaces: {enabled_count}")

    @staticmethod
    def _autostart_command() -> str:
        if getattr(sys, "frozen", False):
            return f"\"{Path(sys.executable)}\""
        main_py = Path(__file__).resolve().parents[2] / "main.py"
        return f"\"{Path(sys.executable)}\" \"{main_py}\""

    def _apply_windows_autostart(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        try:
            import winreg
            run_key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            try:
                if enabled:
                    winreg.SetValueEx(run_key, "MindNavigatorV2", 0, winreg.REG_SZ, self._autostart_command())
                else:
                    try:
                        winreg.DeleteValue(run_key, "MindNavigatorV2")
                    except FileNotFoundError:
                        pass
            finally:
                winreg.CloseKey(run_key)
        except OSError:
            pass

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def _get_backup_dir(self) -> Path | None:
        value = self.backup_path_edit.text().strip()
        if not value:
            return None
        return Path(value)

    def _refresh_backup_list(self) -> None:
        backup_dir = self._get_backup_dir()
        self.backup_combo.blockSignals(True)
        self.backup_combo.clear()
        self._backup_entries = []
        if backup_dir and backup_dir.exists():
            entries = sorted(
                backup_dir.glob(f"{self.BACKUP_PREFIX}*.zip"),
                key=lambda backup_file: backup_file.stat().st_mtime,
                reverse=True,
            )
            for backup_path in entries:
                metadata = self._read_backup_manifest(backup_path)
                display = metadata.get("display") if metadata else None
                if not display:
                    display = backup_path.name
                self._backup_entries.append({"path": backup_path, "meta": metadata})
                self.backup_combo.addItem(display)
        self.backup_combo.blockSignals(False)
        self._update_backup_details()

    def _read_backup_manifest(self, path: Path) -> dict[str, object]:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                if self.BACKUP_MANIFEST_NAME not in archive.namelist():
                    return {}
                data = archive.read(self.BACKUP_MANIFEST_NAME)
            manifest = json.loads(data.decode("utf-8"))
        except (OSError, json.JSONDecodeError, zipfile.BadZipFile):
            return {}
        created_at = manifest.get("created_at") or ""
        display_time = created_at.replace("T", " ") if created_at else ""
        include_cloud = "да" if manifest.get("include_cloud") else "нет"
        manifest["display"] = f"{path.name} · {display_time}" if display_time else path.name
        manifest["include_cloud_label"] = include_cloud
        return manifest

    def _update_backup_details(self) -> None:
        if not self._backup_entries:
            self.backup_details.setText("Архивы не найдены.")
            self.btn_restore_backup.setEnabled(False)
            self.btn_delete_backup.setEnabled(False)
            return
        index = self.backup_combo.currentIndex()
        if index < 0 or index >= len(self._backup_entries):
            index = 0
        entry = self._backup_entries[index]
        path = cast(Path, entry.get("path"))
        meta = cast(dict[str, object], entry.get("meta") or {})
        size_text = self._format_bytes(path.stat().st_size)
        created_at = str(meta.get("created_at") or datetime.fromtimestamp(path.stat().st_mtime).isoformat())
        include_cloud = str(meta.get("include_cloud_label") or "нет")
        self.backup_details.setText(
            f"Размер: {size_text} · Дата: {created_at.replace('T', ' ')} · "
            f"Облачное хранилище: {include_cloud}"
        )
        self.btn_restore_backup.setEnabled(True)
        self.btn_delete_backup.setEnabled(True)

    @staticmethod
    def _format_bytes(size: int) -> str:
        units = ["Б", "КБ", "МБ", "ГБ"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} ГБ"

    def _update_backup_status(self, message: str | None = None) -> None:
        last_run = self._db.get_setting(self.BACKUP_LAST_RUN_KEY, default="")
        status = message or ""
        if last_run:
            status = f"{status} Последняя копия: {last_run.replace('T', ' ')}.".strip()
        self.backup_status.setText(status)

    def _create_backup(self, *, silent: bool = False) -> None:
        backup_dir = self._get_backup_dir()
        if not backup_dir:
            if not silent:
                self._edit_backup_dir()
            backup_dir = self._get_backup_dir()
            if not backup_dir:
                self._update_backup_status(message="Укажите папку для резервных копий.")
                return
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{self.BACKUP_PREFIX}{timestamp}.zip"
        app_data_dir = self._db.path.parent
        include_cloud = self.include_cloud_checkbox.isChecked()
        cloud_path = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="")

        try:
            with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                if app_data_dir.exists():
                    for item in app_data_dir.rglob("*"):
                        if item.is_file():
                            archive.write(item, arcname=f"app_data/{item.relative_to(app_data_dir)}")
                if include_cloud and cloud_path:
                    cloud_dir = Path(cloud_path)
                    if cloud_dir.exists():
                        for item in cloud_dir.rglob("*"):
                            if item.is_file():
                                archive.write(item, arcname=f"cloud_storage/{item.relative_to(cloud_dir)}")
                manifest = {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "include_cloud": bool(include_cloud and cloud_path),
                    "cloud_storage_path": cloud_path,
                }
                archive.writestr(self.BACKUP_MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))
        except OSError as exc:
            if not silent:
                QMessageBox.warning(self, "Ошибка резервного копирования", str(exc))
            self._update_backup_status(message="Не удалось создать резервную копию.")
            return

        status_message = "Резервная копия создана."
        try:
            self._db.set_setting(self.BACKUP_LAST_RUN_KEY, datetime.now().isoformat(timespec="seconds"))
        except sqlite3.Error as exc:
            status_message = f"Backup created, but failed to save last run timestamp: {exc}"
        self._refresh_backup_list()
        self._prune_backups()
        self._update_backup_status(message=status_message)

    def _prune_backups(self) -> None:
        backup_dir = self._get_backup_dir()
        if not backup_dir or not backup_dir.exists():
            return
        max_count = self.retention_spin.value()
        backups = sorted(
            backup_dir.glob(f"{self.BACKUP_PREFIX}*.zip"),
            key=lambda backup_file: backup_file.stat().st_mtime,
            reverse=True,
        )
        for backup_path in backups[max_count:]:
            try:
                backup_path.unlink()
            except OSError:
                continue

    def _restore_selected_backup(self) -> None:
        if not self._backup_entries:
            self._update_backup_status(message="Нет доступных архивов для восстановления.")
            return
        index = self.backup_combo.currentIndex()
        if index < 0 or index >= len(self._backup_entries):
            index = 0
        path = cast(Path, self._backup_entries[index].get("path"))
        dialog = ConfirmDialog(
            "Восстановление данных",
            "Восстановление заменит текущие данные. Продолжить?",
            parent=self,
            confirm_text="Восстановить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        self._restore_backup(path)

    def _restore_backup(self, path: Path) -> None:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                with tempfile.TemporaryDirectory() as temp_dir:
                    archive.extractall(temp_dir)
                    temp_path = Path(temp_dir)
                    app_data_src = temp_path / "app_data"
                    cloud_src = temp_path / "cloud_storage"
                    if app_data_src.exists():
                        target_dir = self._db.path.parent
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if target_dir.exists():
                            backup_dir = target_dir.parent / f".mindnavigator_restore_{timestamp}"
                            shutil.move(str(target_dir), str(backup_dir))
                        shutil.copytree(app_data_src, target_dir)
                    if cloud_src.exists():
                        cloud_path = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="")
                        if not cloud_path:
                            cloud_path = QFileDialog.getExistingDirectory(
                                self,
                                "Выберите папку для восстановления облака",
                                str(Path.home()),
                            )
                            if cloud_path:
                                self._db.set_setting(self.CLOUD_STORAGE_KEY, cloud_path)
                                self.path_edit.setText(cloud_path)
                        if cloud_path:
                            cloud_target = Path(cloud_path)
                            cloud_target.mkdir(parents=True, exist_ok=True)
                            for item in cloud_src.rglob("*"):
                                if item.is_file():
                                    rel = item.relative_to(cloud_src)
                                    dest = cloud_target / rel
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(item, dest)
        except (OSError, zipfile.BadZipFile) as exc:
            QMessageBox.warning(self, "Ошибка восстановления", str(exc))
            self._update_backup_status(message="Не удалось восстановить данные.")
            return
        self._update_backup_status(message="Данные восстановлены. Перезапустите приложение.")

    def _delete_selected_backup(self) -> None:
        if not self._backup_entries:
            return
        index = self.backup_combo.currentIndex()
        if index < 0 or index >= len(self._backup_entries):
            index = 0
        path = cast(Path, self._backup_entries[index].get("path"))
        dialog = ConfirmDialog(
            "Удаление копии",
            f"Удалить резервную копию {path.name}?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != QDialog.DialogCode.Accepted:
            return
        try:
            path.unlink()
        except OSError as exc:
            QMessageBox.warning(self, "Ошибка удаления", str(exc))
            return
        self._refresh_backup_list()
        self._update_backup_status(message="Резервная копия удалена.")

    def _maybe_run_auto_backup(self) -> None:
        if not self.auto_backup_checkbox.isChecked():
            return
        frequency = self.frequency_combo.currentData()
        last_run_value = self._db.get_setting(self.BACKUP_LAST_RUN_KEY, default="")
        if last_run_value:
            try:
                last_run = datetime.fromisoformat(last_run_value)
            except ValueError:
                last_run = None
        else:
            last_run = None
        now = datetime.now()
        if frequency == "daily":
            delta = 1
        elif frequency == "weekly":
            delta = 7
        else:
            delta = 30
        if not last_run or (now - last_run).days >= delta:
            self._create_backup(silent=True)


