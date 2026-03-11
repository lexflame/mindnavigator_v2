from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from mindnavigator.storage import CloudFileData, Database
from mindnavigator.workspaces import files_workspace


def _upsert_cloud_file(database: Database, rel_path: str, *, description_text: str = "") -> None:
    payload = {
        "text": description_text,
        "folders": [part for part in Path(rel_path).parent.parts if part],
        "stem": Path(rel_path).stem,
        "extension": Path(rel_path).suffix.lower(),
    }
    database.upsert_cloud_file(
        rel_path=rel_path,
        name=Path(rel_path).name,
        description=json.dumps(payload, ensure_ascii=False),
        checksum="a" * 64,
        hash_value="a" * 64,
        size=2048,
        is_image=Path(rel_path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"},
        valid=True,
    )


def test_path_token_index_uses_backslash_path_tokens() -> None:
    file_item = CloudFileData(
        id=17,
        rel_path="assets/ui/mockups/home_screen.png",
        name="home_screen.png",
        description="",
        checksum="a" * 64,
        hash_value="a" * 64,
        size=1,
        is_image=True,
        valid=True,
        updated_at="2026-03-06T12:00:00+00:00",
    )

    index, file_tokens = files_workspace.FileWorkspace._build_path_token_index([file_item])

    assert "assets\\ui\\mockups\\home_screen.png" in file_tokens[file_item.id]
    assert "assets" in index and file_item.id in index["assets"]
    assert "ui" in index and file_item.id in index["ui"]
    assert "mockups" in index and file_item.id in index["mockups"]
    assert "home_screen" in index and file_item.id in index["home_screen"]
    assert "png" in index and file_item.id in index["png"]


def test_files_workspace_smart_search_switches_sketch_mode(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("files_workspace_search", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        _upsert_cloud_file(database, "assets/ui/mockups/home_screen.png", description_text="UI mock home")
        _upsert_cloud_file(database, "docs/architecture/overview.md", description_text="Architecture notes")

        monkeypatch.setattr(files_workspace, "get_database", lambda: database)
        workspace = files_workspace.FileWorkspace()

        workspace.smart_search_edit.setText("ui\\home")
        QApplication.processEvents()

        assert workspace._sketch_mode_active is True
        assert workspace.file_grid.count() == 1
        payload = workspace.file_grid.item(0).data(files_workspace.Qt.ItemDataRole.UserRole)
        assert payload == ("file", "assets/ui/mockups/home_screen.png")
        assert workspace.path_label.text().startswith("Поиск:")

        workspace.smart_search_edit.setText("")
        QApplication.processEvents()

        assert workspace._sketch_mode_active is False
        assert workspace.file_grid.count() >= 1
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_files_workspace_populates_search_hints(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("files_workspace_hints", ".sqlite3")
    database = Database(path=db_path)
    workspace = None
    try:
        _upsert_cloud_file(database, "assets/ui/buttons/primary.png", description_text="buttons")
        _upsert_cloud_file(database, "assets/ui/cards/list.png", description_text="cards")
        _upsert_cloud_file(database, "assets/reports/q1.pdf", description_text="report")

        monkeypatch.setattr(files_workspace, "get_database", lambda: database)
        workspace = files_workspace.FileWorkspace()

        visible_hints = [button.text() for button in workspace._search_hint_buttons if not button.isHidden()]
        assert "assets" in visible_hints
        assert "ui" in visible_hints

        hint_button = next(button for button in workspace._search_hint_buttons if not button.isHidden())
        hint_token = hint_button.text()
        hint_button.click()
        QApplication.processEvents()

        assert hint_token in workspace.smart_search_edit.text()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)


def test_files_workspace_smart_search_tolerates_legacy_cloud_file_with_missing_strings(monkeypatch) -> None:
    _app = QApplication.instance() or QApplication([])

    class _FakeDb:
        def fetch_cloud_files(self):
            return [
                CloudFileData(
                    id=1,
                    rel_path="docs/specs/guide.md",
                    name="guide.md",
                    description="spec guide",
                    checksum="a" * 64,
                    hash_value="a" * 64,
                    size=123,
                    is_image=False,
                    valid=True,
                    updated_at="2026-03-06T12:00:00+00:00",
                ),
                CloudFileData(  # type: ignore[arg-type]
                    id=2,
                    rel_path=None,
                    name=None,
                    description="broken legacy row",
                    checksum="b" * 64,
                    hash_value="b" * 64,
                    size=456,
                    is_image=False,
                    valid=True,
                    updated_at="2026-03-06T12:00:00+00:00",
                ),
            ]

        def get_setting(self, *_args, **_kwargs):
            return ""

        def fetch_projects(self):
            return []

    monkeypatch.setattr(files_workspace, "get_database", lambda: _FakeDb())
    workspace = files_workspace.FileWorkspace()
    try:
        workspace.smart_search_edit.setText("guide")
        QApplication.processEvents()

        assert workspace._sketch_mode_active is True
        assert workspace.file_grid.count() == 1
        payload = workspace.file_grid.item(0).data(files_workspace.Qt.ItemDataRole.UserRole)
        assert payload == ("file", "docs/specs/guide.md")
    finally:
        workspace.deleteLater()
