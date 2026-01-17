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
import shutil
import tempfile
import zipfile

from PySide6.QtCore import Qt, QUrl
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
    QSpinBox,
    QMessageBox,
)

from mindnavigator.storage import get_database
from mindnavigator.ui.modals import ConfirmDialog, exec_with_overlay


class SettingsWorkspace(QWidget):
    """Рабочая область настроек приложения."""

    CLOUD_STORAGE_KEY = "cloud_storage_path"
    BACKUP_DIR_KEY = "backup_dir"
    BACKUP_INCLUDE_CLOUD_KEY = "backup_include_cloud"
    BACKUP_AUTO_ENABLED_KEY = "backup_auto_enabled"
    BACKUP_FREQUENCY_KEY = "backup_frequency"
    BACKUP_RETENTION_KEY = "backup_retention"
    BACKUP_LAST_RUN_KEY = "backup_last_run"
    BACKUP_PREFIX = "mindnavigator_backup_"
    BACKUP_MANIFEST_NAME = "backup_manifest.json"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
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
        path_value = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="")
        self.path_edit.setText(path_value)
        backup_dir = self._db.get_setting(self.BACKUP_DIR_KEY, default="")
        self.backup_path_edit.setText(backup_dir)
        include_cloud = self._db.get_setting(self.BACKUP_INCLUDE_CLOUD_KEY, default="1") == "1"
        self.include_cloud_checkbox.setChecked(include_cloud)
        auto_enabled = self._db.get_setting(self.BACKUP_AUTO_ENABLED_KEY, default="0") == "1"
        self.auto_backup_checkbox.setChecked(auto_enabled)
        frequency = self._db.get_setting(self.BACKUP_FREQUENCY_KEY, default="weekly")
        self._set_combo_value(self.frequency_combo, frequency)
        retention = self._db.get_setting(self.BACKUP_RETENTION_KEY, default="7")
        self.retention_spin.setValue(max(1, int(retention) if retention.isdigit() else 7))
        self._refresh_backup_list()
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
        self._update_backup_status()

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
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
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            for path in entries:
                metadata = self._read_backup_manifest(path)
                display = metadata.get("display") if metadata else None
                if not display:
                    display = path.name
                self._backup_entries.append({"path": path, "meta": metadata})
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
        path = entry["path"]
        meta = entry.get("meta") or {}
        size_text = self._format_bytes(path.stat().st_size)
        created_at = meta.get("created_at") or datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        include_cloud = meta.get("include_cloud_label") or "нет"
        self.backup_details.setText(
            f"Размер: {size_text} · Дата: {created_at.replace('T', ' ')} · "
            f"Облачное хранилище: {include_cloud}"
        )
        self.btn_restore_backup.setEnabled(True)
        self.btn_delete_backup.setEnabled(True)

    def _format_bytes(self, size: int) -> str:
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

        self._db.set_setting(self.BACKUP_LAST_RUN_KEY, datetime.now().isoformat(timespec="seconds"))
        self._refresh_backup_list()
        self._prune_backups()
        self._update_backup_status(message="Резервная копия создана.")

    def _prune_backups(self) -> None:
        backup_dir = self._get_backup_dir()
        if not backup_dir or not backup_dir.exists():
            return
        max_count = self.retention_spin.value()
        backups = sorted(
            backup_dir.glob(f"{self.BACKUP_PREFIX}*.zip"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for path in backups[max_count:]:
            try:
                path.unlink()
            except OSError:
                continue

    def _restore_selected_backup(self) -> None:
        if not self._backup_entries:
            self._update_backup_status(message="Нет доступных архивов для восстановления.")
            return
        index = self.backup_combo.currentIndex()
        if index < 0 or index >= len(self._backup_entries):
            index = 0
        path = self._backup_entries[index]["path"]
        dialog = ConfirmDialog(
            "Восстановление данных",
            "Восстановление заменит текущие данные. Продолжить?",
            parent=self,
            confirm_text="Восстановить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != dialog.Accepted:
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
        path = self._backup_entries[index]["path"]
        dialog = ConfirmDialog(
            "Удаление копии",
            f"Удалить резервную копию {path.name}?",
            parent=self,
            confirm_text="Удалить",
            cancel_text="Отмена",
        )
        if exec_with_overlay(dialog, self) != dialog.Accepted:
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
