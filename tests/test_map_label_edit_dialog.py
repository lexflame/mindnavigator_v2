from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from mindnavigator.ui.dialogs import map_label_edit_dialog
from mindnavigator.ui.dialogs.map_label_edit_dialog import MapLabelEditDialog, MapLabelEntitySource
from mindnavigator.workspaces.maps.marker import Marker


class _EntityItem:
    def __init__(self, item_id: int, title: str) -> None:
        self.id = item_id
        self.title = title


class _StubDb:
    pass


def test_map_label_edit_dialog_builds_links_section_with_completer(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(map_label_edit_dialog, "get_database", lambda: _StubDb())

    marker = Marker(
        id=1,
        name="Marker",
        x=10.0,
        y=20.0,
        color=QColor("#44aa88"),
        type="poi",
        size=18.0,
    )
    note_item = _EntityItem(7, "Beta reference note")
    sources = {
        "note": MapLabelEntitySource(
            label="Заметки",
            items=[note_item],
            label_fn=lambda item: item.title,
            placeholder="Найти заметку…",
            icon_name="fa6s.note-sticky",
            item_prefix="note",
        )
    }

    dialog = MapLabelEditDialog(marker, sources, type_suggestions=["poi"])
    try:
        link_input = dialog._link_inputs["note"]
        completer = link_input.search_input.completer()

        assert completer is not None
        completer.activated[str].emit("Beta reference note")

        items = link_input.items()
        assert len(items) == 1
        assert items[0].id == note_item.id
        assert items[0].title == "Beta reference note"
        assert items[0].link == "note:7"
    finally:
        dialog.deleteLater()


def test_map_label_edit_dialog_popup_sync_ignores_deleted_popup(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(map_label_edit_dialog, "get_database", lambda: _StubDb())

    marker = Marker(
        id=1,
        name="Marker",
        x=10.0,
        y=20.0,
        color=QColor("#44aa88"),
        type="poi",
        size=18.0,
    )
    dialog = MapLabelEditDialog(marker, {}, type_suggestions=["poi"])
    try:
        popup_sync = dialog._popup_syncs[0]
        popup = popup_sync._popup

        assert popup is not None
        popup_sync._on_popup_destroyed()

        try:
            popup_sync.eventFilter(popup_sync._line_edit, QEvent(QEvent.Type.Resize))
            popup_sync._sync_popup()
        except RuntimeError as exc:  # pragma: no cover - regression guard
            pytest.fail(f"Popup sync touched deleted popup: {exc}")
    finally:
        dialog.deleteLater()
