from __future__ import annotations

import sqlite3

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
