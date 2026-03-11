from __future__ import annotations

from PySide6.QtWidgets import QApplication

from mindnavigator.workspaces.minddraw import module_impl as minddraw_module
from mindnavigator.workspaces.minddraw.module_impl import (
    MindDrawLinkState,
    MindDrawNodeState,
    deserialize_minddraw_state,
    serialize_minddraw_state,
)


def test_minddraw_state_roundtrip() -> None:
    nodes = [
        MindDrawNodeState("n1", "Root", 10.0, 20.0, "task", 17, "Task 17"),
        MindDrawNodeState("n2", "Child", 40.5, 55.25, "project", 9, "Project 9"),
    ]
    links = [MindDrawLinkState("n1", "n2")]

    raw = serialize_minddraw_state(nodes, links)
    restored_nodes, restored_links = deserialize_minddraw_state(raw)

    assert restored_nodes == nodes
    assert restored_links == links


def test_minddraw_deserialize_skips_invalid_links() -> None:
    raw = """
    {
      "nodes": [
        {"node_id": "n1", "title": "A", "x": 0, "y": 0},
        {"node_id": "n2", "title": "B", "x": 10, "y": 10}
      ],
      "links": [
        {"source_id": "n1", "target_id": "n2"},
        {"source_id": "n1", "target_id": "unknown"},
        {"source_id": "n2", "target_id": "n2"}
      ]
    }
    """

    nodes, links = deserialize_minddraw_state(raw)

    assert [node.node_id for node in nodes] == ["n1", "n2"]
    assert links == [MindDrawLinkState("n1", "n2")]


class _MindDrawDbStub:
    def fetch_tasks(self):
        return []

    def fetch_projects(self):
        return []

    def fetch_ideas(self, archived=True):
        return []

    def fetch_notes(self):
        return []

    def fetch_maps(self):
        return []

    def fetch_objects(self):
        return []

    def fetch_characters(self):
        return []

    def fetch_cloud_files(self):
        return []

    def fetch_collection_items(self):
        return []

    def fetch_shop_items(self):
        return []


def test_minddraw_workspace_applies_local_theme(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(minddraw_module, "get_database", lambda: _MindDrawDbStub())
    monkeypatch.setattr(minddraw_module.MindDrawWorkspace, "_load_canvas_state", lambda self: None)

    workspace = minddraw_module.MindDrawWorkspace()
    try:
        assert workspace.objectName() == "MindDrawWorkspace"
        assert workspace.hint_label.objectName() == "MindDrawHint"
        assert workspace.view.objectName() == "MindDrawCanvas"
        assert workspace.view.viewport().objectName() == "MindDrawCanvasViewport"
        assert "QWidget#MindDrawWorkspace QWidget#WorkspaceToolbar" in workspace.styleSheet()
        assert "QGraphicsView#MindDrawCanvas" in workspace.styleSheet()
    finally:
        workspace.deleteLater()


def test_minddraw_entity_picker_uses_dialog_theme() -> None:
    _app = QApplication.instance() or QApplication([])
    dialog = minddraw_module.MindDrawEntityPickerDialog(lambda _kind, _query: [])
    try:
        assert dialog.objectName() == "MindDrawEntityPicker"
        assert dialog.kind_combo.objectName() == "MindDrawEntityKind"
        assert dialog.search_edit.objectName() == "MindDrawEntitySearch"
        assert dialog.list_widget.objectName() == "MindDrawEntityList"
        assert dialog.reload_btn.objectName() == "MindDrawEntityReload"
        assert dialog.property("dialog_category") == "minimal_flex"
        assert "QDialog#MindDrawEntityPicker" in dialog.styleSheet()
        assert "QListWidget#MindDrawEntityList" in dialog.styleSheet()
    finally:
        dialog.deleteLater()
