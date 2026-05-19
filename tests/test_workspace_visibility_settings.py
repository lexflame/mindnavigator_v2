from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication

import mindnavigator.window.collections.main_window as main_window
import mindnavigator.workspaces.mutaboard.module_impl as mutaboard_module
from mindnavigator.storage import MutaBoardColumnData, MutaBoardData
from mindnavigator.window.collections.main_window import (
    MainWindow,
    normalize_enabled_workspace_ids,
    normalize_nav_collapsed_setting,
)
from mindnavigator.workspaces.settings.settings_workspace import SettingsWorkspace


def test_normalize_enabled_workspace_ids_uses_defaults_on_empty_or_invalid() -> None:
    available = {"projects", "tasks", "notes"}

    assert normalize_enabled_workspace_ids("", available) == available
    assert normalize_enabled_workspace_ids("not-json", available) == available
    assert normalize_enabled_workspace_ids('{"a":1}', available) == available


def test_normalize_enabled_workspace_ids_filters_unknown_values() -> None:
    available = {"projects", "tasks", "notes"}

    result = normalize_enabled_workspace_ids('["tasks", "unknown", "notes", "tasks"]', available)

    assert result == {"tasks", "notes"}


def test_normalize_enabled_workspace_ids_falls_back_when_list_is_empty() -> None:
    available = {"projects", "tasks", "notes"}

    result = normalize_enabled_workspace_ids("[]", available)

    assert result == available


def test_workspace_mode_map_contains_characters_mode() -> None:
    class _DummyWindow:
        MODE_PROJECTS = MainWindow.MODE_PROJECTS
        MODE_TASKS = MainWindow.MODE_TASKS
        MODE_CONCEPTBOARD = MainWindow.MODE_CONCEPTBOARD
        MODE_MUTABOARD = MainWindow.MODE_MUTABOARD
        MODE_PURCHASES = MainWindow.MODE_PURCHASES
        MODE_IDEAS = MainWindow.MODE_IDEAS
        MODE_DOSSIER = MainWindow.MODE_DOSSIER
        MODE_COLLECTIONS = MainWindow.MODE_COLLECTIONS
        MODE_MAPS = MainWindow.MODE_MAPS
        MODE_NOTES = MainWindow.MODE_NOTES
        MODE_FILES = MainWindow.MODE_FILES
        MODE_OBJECTS = MainWindow.MODE_OBJECTS
        MODE_CHARACTERS = MainWindow.MODE_CHARACTERS
        MODE_MINDDRAW = MainWindow.MODE_MINDDRAW

    mapping = MainWindow._workspace_mode_map(_DummyWindow())

    assert mapping["dossier"] == MainWindow.MODE_DOSSIER
    assert mapping["mutaboard"] == MainWindow.MODE_MUTABOARD
    assert mapping["concept_board"] == MainWindow.MODE_CONCEPTBOARD
    assert mapping["characters"] == MainWindow.MODE_CHARACTERS
    assert mapping["minddraw"] == MainWindow.MODE_MINDDRAW


def test_settings_workspace_options_include_concept_board() -> None:
    assert ("concept_board", "Концептборд") in SettingsWorkspace.WORKSPACE_OPTIONS


class _MutaBoardWorkspaceDbStub:
    def __init__(self) -> None:
        self._mutaboards: list[MutaBoardData] = []

    def fetch_tasks(self):
        return []

    def fetch_ideas(self, archived=True):
        return []

    def fetch_objects(self):
        return []

    def fetch_notes(self):
        return []

    def fetch_projects(self):
        return []

    def fetch_maps(self):
        return []

    def fetch_map_markers(self, map_id=None):
        return []

    def fetch_cloud_files(self):
        return []

    def fetch_task_attachments(self, task_id: int):
        return []

    def fetch_idea_relations(self, idea_id: int):
        return []

    def fetch_mutaboards(self):
        return list(self._mutaboards)

    def create_mutaboard(
        self,
        title: str,
        description: str = "",
        capture_text: str = "",
        planning_text: str = "",
        links_text: str = "",
        column_kinds=None,
    ):
        now = datetime.now(timezone.utc)
        board = MutaBoardData(
            id=1,
            title=title,
            description=description,
            capture_text=capture_text,
            planning_text=planning_text,
            links_text=links_text,
            created_at=now,
            updated_at=now,
        )
        self._mutaboards = [board]
        return board

    def fetch_mutaboard_columns(self, mutaboard_id: int):
        now = datetime.now(timezone.utc)
        return [
            MutaBoardColumnData(id=1, mutaboard_id=mutaboard_id, kind="task", title="", position=0, created_at=now, updated_at=now),
            MutaBoardColumnData(id=2, mutaboard_id=mutaboard_id, kind="idea", title="", position=1, created_at=now, updated_at=now),
            MutaBoardColumnData(id=3, mutaboard_id=mutaboard_id, kind="image", title="", position=2, created_at=now, updated_at=now),
        ]

    def replace_mutaboard_columns(self, mutaboard_id: int, columns):
        now = datetime.now(timezone.utc)
        return [
            MutaBoardColumnData(
                id=index + 1,
                mutaboard_id=mutaboard_id,
                kind=kind,
                title=title,
                position=index,
                created_at=now,
                updated_at=now,
            )
            for index, (kind, title) in enumerate(columns)
        ]

    def fetch_mutaboard_items(self, mutaboard_id: int):
        return []


def test_mutaboard_workspace_builds_phase_one_shell(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(mutaboard_module, "get_database", lambda: _MutaBoardWorkspaceDbStub())

    workspace = mutaboard_module.MutaBoardWorkspace()
    try:
        assert workspace.workspace_id == "concept_board"
        assert workspace.search_input.placeholderText() == "Поиск по концептборду..."
        assert workspace.status_row.text() == "Концептборд: элементов 0 · связано 0."
    finally:
        workspace.deleteLater()


def test_normalize_nav_collapsed_setting_parses_known_values() -> None:
    assert normalize_nav_collapsed_setting("1") is True
    assert normalize_nav_collapsed_setting("true") is True
    assert normalize_nav_collapsed_setting("0") is False
    assert normalize_nav_collapsed_setting("off") is False
    assert normalize_nav_collapsed_setting("") is True
    assert normalize_nav_collapsed_setting("unexpected") is True


def test_normalize_theme_mode_defaults_to_dark() -> None:
    assert MainWindow._normalize_theme_mode("light") == "light"
    assert MainWindow._normalize_theme_mode(" LIGHT  ") == "light"
    assert MainWindow._normalize_theme_mode("dark") == "dark"
    assert MainWindow._normalize_theme_mode("unknown") == "dark"


class _FakeDb:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})
        self.set_calls: list[tuple[str, str]] = []

    def get_setting(self, key: str, default: str = "") -> str:
        return self.values.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self.values[key] = value
        self.set_calls.append((key, value))


def test_load_behavior_settings_uses_collapsed_nav_default(monkeypatch) -> None:
    fake_db = _FakeDb(
        {
            MainWindow.APP_LANGUAGE_KEY: "ru",
            MainWindow.APP_ENABLED_WORKSPACES_KEY: '["tasks"]',
        }
    )
    monkeypatch.setattr(main_window, "get_database", lambda: fake_db)

    class _DummyWindow:
        APP_LANGUAGE_KEY = MainWindow.APP_LANGUAGE_KEY
        APP_THEME_KEY = MainWindow.APP_THEME_KEY
        APP_ENABLED_WORKSPACES_KEY = MainWindow.APP_ENABLED_WORKSPACES_KEY
        APP_NAV_COLLAPSED_KEY = MainWindow.APP_NAV_COLLAPSED_KEY

        def __init__(self) -> None:
            self.language_calls: list[str] = []
            self.theme_calls: list[tuple[str, bool]] = []
            self.workspace_calls: list[str] = []
            self.nav_calls: list[tuple[bool, bool]] = []
            self._minimize_on_focus_lost = False

        def _apply_theme_mode(self, theme_mode: str, *, persist: bool) -> None:
            self.theme_calls.append((theme_mode, persist))

        def _apply_enabled_workspaces(self, workspace_ids: set[str], *, persist: bool) -> None:
            self.workspace_calls.append(",".join(sorted(workspace_ids)))

        def _apply_nav_collapsed(self, collapsed: bool, *, persist: bool) -> None:
            self.nav_calls.append((collapsed, persist))

        def _set_nav_collapsed(self, collapsed: bool, *, persist: bool) -> None:
            self.nav_calls.append((collapsed, persist))

        def set_language(self, language_code: str) -> None:
            self.language_calls.append(language_code)

        def _apply_ui_language(self, language_code: str) -> None:
            self.language_calls.append(language_code)

        def _apply_workspace_visibility_from_raw(self, raw_value: str) -> None:
            workspace_ids = normalize_enabled_workspace_ids(raw_value, {"tasks"})
            self.workspace_calls.append(",".join(sorted(workspace_ids)))

    window = _DummyWindow()

    MainWindow._load_behavior_settings(window)

    assert window.language_calls == ["ru"]
    assert window.theme_calls == [("dark", False)]
    assert window.workspace_calls == ["tasks"]
    assert window.nav_calls == [(True, False)]
