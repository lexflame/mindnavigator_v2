from __future__ import annotations

import mindnavigator.window.collections.main_window as main_window
from mindnavigator.window.collections.main_window import (
    MainWindow,
    normalize_enabled_workspace_ids,
    normalize_nav_collapsed_setting,
)


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

    result = normalize_enabled_workspace_ids('[]', available)

    assert result == available


def test_workspace_mode_map_contains_characters_mode() -> None:
    class _DummyWindow:
        MODE_PROJECTS = MainWindow.MODE_PROJECTS
        MODE_TASKS = MainWindow.MODE_TASKS
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
    assert mapping["characters"] == MainWindow.MODE_CHARACTERS
    assert mapping["minddraw"] == MainWindow.MODE_MINDDRAW


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

        def _apply_ui_language(self, code: str) -> None:
            self.language_calls.append(code)

        def _apply_workspace_visibility_from_raw(self, raw_value: str) -> None:
            self.workspace_calls.append(raw_value)

        def _set_nav_collapsed(self, collapsed: bool, *, persist: bool = True) -> None:
            self.nav_calls.append((collapsed, persist))

    window = _DummyWindow()

    MainWindow._load_behavior_settings(window)

    assert window._minimize_on_focus_lost is True
    assert window.nav_calls == [(True, False)]
    assert window.theme_calls == [("dark", False)]
    assert window.language_calls == ["ru"]
    assert window.workspace_calls == ['["tasks"]']


def test_set_nav_collapsed_persists_state(monkeypatch) -> None:
    fake_db = _FakeDb()
    monkeypatch.setattr(main_window, "get_database", lambda: fake_db)

    class _DummyVisible:
        def __init__(self) -> None:
            self._visible = True

        def setVisible(self, visible: bool) -> None:
            self._visible = visible

        def isVisible(self) -> bool:
            return self._visible

    class _DummyToggle:
        def __init__(self) -> None:
            self.text = ""
            self.tooltip = ""

        def setText(self, text: str) -> None:
            self.text = text

        def setToolTip(self, text: str) -> None:
            self.tooltip = text

    class _DummyStack:
        def __init__(self, widget: object) -> None:
            self._widget = widget

        def currentWidget(self) -> object:
            return self._widget

    workspace = object()

    class _DummyWindow:
        APP_NAV_COLLAPSED_KEY = MainWindow.APP_NAV_COLLAPSED_KEY

        def __init__(self) -> None:
            self.nav_column = _DummyVisible()
            self.nav_toggle = _DummyToggle()
            self.workspace_stack = _DummyStack(workspace)
            self.workspace_state_calls: list[object] = []

        def _apply_nav_state_to_workspace(self, current_workspace: object) -> None:
            self.workspace_state_calls.append(current_workspace)

    window = _DummyWindow()

    MainWindow._set_nav_collapsed(window, True)

    assert window.nav_column.isVisible() is False
    assert fake_db.set_calls == [(MainWindow.APP_NAV_COLLAPSED_KEY, "1")]
    assert window.workspace_state_calls == [workspace]

    MainWindow._set_nav_collapsed(window, False, persist=False)

    assert window.nav_column.isVisible() is True
    assert fake_db.set_calls == [(MainWindow.APP_NAV_COLLAPSED_KEY, "1")]
    assert window.workspace_state_calls == [workspace, workspace]


def test_apply_theme_mode_persists_and_updates_shell(monkeypatch) -> None:
    fake_db = _FakeDb()
    monkeypatch.setattr(main_window, "get_database", lambda: fake_db)

    class _DummyLeftRail:
        def __init__(self) -> None:
            self.values: list[str] = []

        def set_theme_mode(self, theme_mode: str) -> None:
            self.values.append(theme_mode)

    class _DummyWindow:
        APP_THEME_KEY = MainWindow.APP_THEME_KEY

        def __init__(self) -> None:
            self.left_rail = _DummyLeftRail()
            self._theme_mode = "dark"
            self.titlebar_calls = 0
            self.root_calls = 0

        def _apply_titlebar_style(self) -> None:
            self.titlebar_calls += 1

        def _apply_root_style(self) -> None:
            self.root_calls += 1

        _normalize_theme_mode = staticmethod(MainWindow._normalize_theme_mode)

    window = _DummyWindow()

    MainWindow._apply_theme_mode(window, "light", persist=True)

    assert window._theme_mode == "light"
    assert window.left_rail.values == ["light"]
    assert window.titlebar_calls == 1
    assert window.root_calls == 1
    assert fake_db.set_calls == [(MainWindow.APP_THEME_KEY, "light")]
