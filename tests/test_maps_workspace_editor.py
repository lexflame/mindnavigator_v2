from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from mindnavigator.workspaces.maps import map_editor_workspace, maps_list_workspace, maps_model


class _StubDb:
    def __init__(self) -> None:
        self._settings: dict[str, str] = {}
        self._maps = [
            SimpleNamespace(
                id=1,
                title="Atlas",
                description="World map",
                project="Ops",
                tiles_path="",
                tiles_h=18,
                tiles_w=24,
            )
        ]
        self._markers = [
            SimpleNamespace(
                id=10,
                map_id=1,
                name="Harbor",
                x=120.0,
                y=180.0,
                color="#2f6edb",
                type="Объект",
                size=24.0,
                description="Main harbor",
                properties="",
                task_ids=[201],
                project_ids=[],
                note_ids=[],
                object_ids=[],
                file_ids=[],
                map_ids=[],
                marker_ids=[],
                parent_path="Atlas / Harbor",
                image_path="",
            )
        ]
        self._overlays = [
            SimpleNamespace(
                id=31,
                map_id=1,
                kind="region",
                points=[(10.0, 10.0), (60.0, 10.0), (60.0, 80.0)],
                color="#e2a84e",
                title="Sector 7",
            )
        ]

    def get_setting(self, key: str, default: str = "") -> str:
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self._settings[key] = value

    def fetch_tasks(self):
        return [SimpleNamespace(id=201, title="Inspect harbor")]

    def fetch_projects(self):
        return [SimpleNamespace(id=1, title="Ops", area="West")]

    def fetch_notes(self):
        return []

    def fetch_objects(self):
        return []

    def fetch_cloud_files(self):
        return []

    def fetch_maps(self):
        return list(self._maps)

    def fetch_map_markers(self, map_id=None):
        if map_id is None:
            return list(self._markers)
        return [marker for marker in self._markers if marker.map_id == map_id]

    def fetch_map_overlays(self, map_id=None):
        if map_id is None:
            return list(self._overlays)
        return [overlay for overlay in self._overlays if overlay.map_id == map_id]

    def upsert_map_marker(self, **_kwargs) -> None:
        return None

    def delete_map_marker(self, _marker_id: int) -> None:
        return None

    def create_map_overlay(self, **kwargs):
        return SimpleNamespace(id=kwargs.get("map_id", 1) + 100)

    def update_map_overlay(self, **_kwargs) -> None:
        return None

    def delete_map_overlay(self, _overlay_id: int) -> None:
        return None


def _patch_maps_db(monkeypatch, db: _StubDb) -> None:
    monkeypatch.setattr(map_editor_workspace, "get_database", lambda: db)
    monkeypatch.setattr(maps_list_workspace, "get_database", lambda: db)
    monkeypatch.setattr(maps_model, "get_database", lambda: db)


def test_map_editor_workspace_shows_summary_and_selection_details(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    db = _StubDb()
    _patch_maps_db(monkeypatch, db)

    workspace = map_editor_workspace.MapEditorWorkspace()
    try:
        workspace.resize(1280, 860)
        workspace.set_map_context("Atlas", "Ops")
        workspace.load_map(1, "", 18, 24)

        assert workspace.info_title.text() == "Карта"
        assert "Atlas" in workspace.info_subtitle.text()
        assert workspace.status_markers.text() == "Маркеров: 1"
        assert workspace.status_regions.text() == "Регионов: 1"
        assert workspace.status_routes.text() == "Маршрутов: 0"

        marker = workspace.markers()[0]
        workspace.focus_marker(marker, zoom_boost=0.0)
        assert workspace.info_title.text() == "Harbor"
        assert workspace.detail_labels["coords"].text() == "X: 120  Y: 180"
        assert "Задачи" in workspace.info_links_value.text()

        overlay = workspace.overlays()[0]
        workspace.focus_overlay(overlay, zoom_boost=0.0)
        assert workspace.info_title.text() == "Sector 7"
        assert workspace.detail_labels["type"].text() == "Регион"
        assert workspace.info_links_value.text() == "Нет связанных элементов"
    finally:
        workspace.deleteLater()


def test_map_editor_workspace_search_and_filter_cover_markers_and_overlays(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    db = _StubDb()
    _patch_maps_db(monkeypatch, db)

    workspace = map_editor_workspace.MapEditorWorkspace()
    try:
        workspace.set_map_context("Atlas", "Ops")
        workspace.load_map(1, "", 18, 24)

        marker_hits = workspace.search_objects("harbor", "marker")
        region_hits = workspace.search_objects("sector", "region")
        assert len(marker_hits) == 1
        assert marker_hits[0]["kind"] == "marker"
        assert "Связи: 1" in marker_hits[0]["display"]
        assert len(region_hits) == 1
        assert region_hits[0]["kind"] == "overlay"

        workspace.set_visible_object_filter("region")
        marker = workspace.markers()[0]
        assert workspace.canvas._marker_at(QPointF(marker.x, marker.y)) is None

        workspace.set_visible_object_filter("all")
        assert workspace.canvas._marker_at(QPointF(marker.x, marker.y)) is not None
    finally:
        workspace.deleteLater()


def test_maps_list_workspace_builds_editor_header_with_filter_and_menu(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    db = _StubDb()
    _patch_maps_db(monkeypatch, db)

    workspace = maps_list_workspace.MapsListWorkspace()
    try:
        assert workspace.marker_search.placeholderText() == "Поиск меток, объектов, связей..."
        assert workspace.map_type_filter.currentText() == "Все типы"
        assert workspace.map_menu_btn.menu() is not None
    finally:
        workspace.deleteLater()
