from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea

import mindnavigator.workspaces.settings.settings_workspace as settings_workspace_impl
from mindnavigator.workspaces import settings as settings_workspace
from mindnavigator.workspaces.settings import SettingsWorkspace


class _DummyCheckBox:
    def __init__(self, checked: bool) -> None:
        self._checked = checked

    def isChecked(self) -> bool:
        return self._checked


class _DummyComboBox:
    def __init__(self, value: str) -> None:
        self._value = value

    def currentData(self) -> str:
        return self._value


class _DummySpinBox:
    def __init__(self, value: int) -> None:
        self._value = value

    def value(self) -> int:
        return self._value


class _DummyDB:
    def __init__(self, error: sqlite3.Error | None = None) -> None:
        self._error = error
        self.calls: list[tuple[str, str]] = []

    def set_setting(self, key: str, value: str) -> None:
        self.calls.append((key, value))
        if self._error is not None:
            raise self._error


class _DummyUiDB:
    def __init__(self) -> None:
        self.path = Path("D:/mindnavigator/mindnavigator.db")

    def get_setting(self, _key: str, default: str = "") -> str:
        return default

    def set_setting(self, _key: str, _value: str) -> None:
        return None


class _DummySettingsWorkspace:
    BACKUP_INCLUDE_CLOUD_KEY = SettingsWorkspace.BACKUP_INCLUDE_CLOUD_KEY
    BACKUP_AUTO_ENABLED_KEY = SettingsWorkspace.BACKUP_AUTO_ENABLED_KEY
    BACKUP_FREQUENCY_KEY = SettingsWorkspace.BACKUP_FREQUENCY_KEY
    BACKUP_RETENTION_KEY = SettingsWorkspace.BACKUP_RETENTION_KEY

    def __init__(self, db: _DummyDB) -> None:
        self._db = db
        self._loading_settings = False
        self.include_cloud_checkbox = _DummyCheckBox(True)
        self.auto_backup_checkbox = _DummyCheckBox(False)
        self.frequency_combo = _DummyComboBox("weekly")
        self.retention_spin = _DummySpinBox(7)
        self.status_messages: list[str | None] = []

    def _update_backup_status(self, message: str | None = None) -> None:
        self.status_messages.append(message)


class _DummyLineEdit:
    def __init__(self, value: str) -> None:
        self._value = value

    def text(self) -> str:
        return self._value


class _DummyLabel:
    def __init__(self) -> None:
        self.value = ""

    def setText(self, value: str) -> None:
        self.value = value


class _DummyDatabaseStatusWorkspace:
    def __init__(self, db_path: Path, selected_path: str) -> None:
        self._db = type("DummyDBPath", (), {"path": db_path})()
        self.db_path_edit = _DummyLineEdit(selected_path)
        self.db_path_status = _DummyLabel()


class _DummyWorkspaceStatusWorkspace:
    def __init__(self, checked_values: list[bool]) -> None:
        self.workspace_checkboxes = {
            f"workspace_{index}": _DummyCheckBox(checked)
            for index, checked in enumerate(checked_values)
        }
        self.workspace_status = _DummyLabel()


def test_backup_options_change_is_ignored_while_loading() -> None:
    workspace = _DummySettingsWorkspace(db=_DummyDB())
    workspace._loading_settings = True

    SettingsWorkspace._on_backup_option_changed(workspace)  # type: ignore[arg-type]

    assert workspace._db.calls == []
    assert workspace.status_messages == []


def test_backup_options_change_handles_readonly_database_error() -> None:
    workspace = _DummySettingsWorkspace(
        db=_DummyDB(sqlite3.OperationalError("attempt to write a readonly database"))
    )

    SettingsWorkspace._on_backup_option_changed(workspace)  # type: ignore[arg-type]

    assert workspace.status_messages
    assert workspace.status_messages[-1] is not None
    assert "readonly" in str(workspace.status_messages[-1]).lower()


def test_database_status_shows_network_compatibility_warning(monkeypatch) -> None:
    db_path = Path("D:/mindnavigator/mindnavigator.db")
    workspace = _DummyDatabaseStatusWorkspace(
        db_path=db_path,
        selected_path=str(db_path),
    )
    monkeypatch.setattr(settings_workspace, "is_network_database_path", lambda _path: True)

    SettingsWorkspace._update_database_status(workspace, "Путь к базе данных обновлён.")  # type: ignore[arg-type]

    assert "Путь к базе данных обновлён." in workspace.db_path_status.value
    assert "Активный путь к базе данных." in workspace.db_path_status.value
    assert "Режим совместимости с сетевой БД" in workspace.db_path_status.value


def test_workspace_status_uses_russian_label() -> None:
    workspace = _DummyWorkspaceStatusWorkspace([True, False, True])

    SettingsWorkspace._update_workspace_status(workspace)  # type: ignore[arg-type]

    assert workspace.workspace_status.value == "Видимые разделы: 2"


def test_backup_section_uses_scroll_and_stacked_rows(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(settings_workspace, "get_database", lambda: _DummyUiDB())
    monkeypatch.setattr(settings_workspace_impl, "get_configured_db_path", lambda: Path("D:/mindnavigator/mindnavigator.db"))
    monkeypatch.setattr(settings_workspace_impl, "default_db_path", lambda: Path("D:/mindnavigator/mindnavigator.db"))
    monkeypatch.setattr(SettingsWorkspace, "_apply_windows_autostart", lambda self, enabled: None)

    workspace = SettingsWorkspace()
    workspace.resize(760, 420)
    workspace.show()
    _app.processEvents()

    scroll = workspace.findChild(QScrollArea, "SettingsScroll")
    assert scroll is not None

    backup_desc = next(
        label for label in workspace.findChildren(QLabel) if label.text() == "Укажите директорию, в которой будут храниться архивы."
    )
    include_cloud = workspace.include_cloud_checkbox

    backup_desc_bottom = backup_desc.mapTo(workspace, QPoint(0, backup_desc.height())).y()
    backup_path_top = workspace.backup_path_edit.mapTo(workspace, QPoint(0, 0)).y()
    include_cloud_top = include_cloud.mapTo(workspace, QPoint(0, 0)).y()
    frequency_top = workspace.frequency_combo.mapTo(workspace, QPoint(0, 0)).y()

    assert backup_path_top >= backup_desc_bottom
    assert frequency_top > include_cloud_top
