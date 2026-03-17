from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mindnavigator.ui import projects_nav, search_nav
from mindnavigator.workspaces.collections import collections_workspace as collections_module
from mindnavigator.workspaces.minddraw import minddraw_workspace as minddraw_module
from mindnavigator.workspaces.objects import object_workspace as objects_module
from mindnavigator.workspaces.objects import objects_model as objects_model_module


class _DummyDb:
    @staticmethod
    def fetch_tasks():
        return []

    @staticmethod
    def fetch_projects():
        return []

    @staticmethod
    def fetch_maps():
        return []

    @staticmethod
    def fetch_map_markers():
        return []

    @staticmethod
    def fetch_notes():
        return []

    @staticmethod
    def fetch_cloud_files():
        return []

    @staticmethod
    def fetch_objects():
        return []

    @staticmethod
    def fetch_characters(search_text: str = ""):
        return []

    @staticmethod
    def fetch_collection_items(**_kwargs):
        return []

    @staticmethod
    def fetch_collection_categories():
        return []

    @staticmethod
    def fetch_collection_topics():
        return []

    @staticmethod
    def fetch_ideas(archived: bool = False):
        return []

    @staticmethod
    def fetch_shop_items():
        return []


def test_search_nav_switches_to_light_styles(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(search_nav, "get_database", lambda: _DummyDb())

    widget = search_nav.SearchNav()
    widget.set_theme_mode("light")

    assert widget._theme_mode == "light"
    assert "#eef2f8" in widget.styleSheet()
    assert "#1f2430" in widget.styleSheet()


def test_projects_nav_switches_to_light_styles(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(projects_nav, "get_database", lambda: _DummyDb())

    widget = projects_nav.ProjectsNav()
    widget.set_theme_mode("light")

    assert widget._theme_mode == "light"
    assert "#eef2f8" in widget.styleSheet()
    assert "#dfe9ff" in widget.styleSheet()


def test_collections_workspace_switches_to_light_styles(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(collections_module, "get_database", lambda: _DummyDb())

    widget = collections_module.CollectionsWorkspace()
    try:
        widget.set_theme_mode("light")
        palette = collections_module.get_theme_palette("light")

        assert widget._theme_mode == "light"
        assert palette.window_bg in widget.styleSheet()
        assert palette.text in widget.styleSheet()
    finally:
        widget.deleteLater()


def test_minddraw_workspace_switches_to_light_styles(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(minddraw_module, "get_database", lambda: _DummyDb())

    widget = minddraw_module.MindDrawWorkspace()
    try:
        widget.set_theme_mode("light")
        palette = minddraw_module.get_theme_palette("light")

        assert widget._theme_mode == "light"
        assert palette.window_bg in widget.styleSheet()
        assert palette.text in widget.styleSheet()
    finally:
        widget.deleteLater()


def test_objects_workspace_switches_to_light_styles(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(objects_module, "get_database", lambda: _DummyDb())
    monkeypatch.setattr(objects_model_module, "get_database", lambda: _DummyDb())

    widget = objects_module.ObjectWorkspace()
    try:
        widget.set_theme_mode("light")
        palette = objects_module.get_theme_palette("light")

        assert widget._theme_mode == "light"
        assert palette.window_bg in widget.styleSheet()
        assert palette.text in widget.styleSheet()
    finally:
        widget.deleteLater()
