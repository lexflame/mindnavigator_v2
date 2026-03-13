from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog

from mindnavigator.transfer.collections import list_files
from mindnavigator.storage import Database
from mindnavigator.workspaces import collections as collections_workspace


def test_list_files_skips_thumbs_db(unique_temp_path) -> None:
    root = unique_temp_path("collection_files", "")
    root.mkdir(parents=True, exist_ok=True)
    (root / "Thumbs.db").write_text("cache", encoding="utf-8")
    (root / "photo.png").write_text("png", encoding="utf-8")
    nested = root / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "THUMBS.DB").write_text("cache", encoding="utf-8")
    (nested / "doc.txt").write_text("doc", encoding="utf-8")

    files_recursive, _errors = list_files(root, include_subfolders=True)
    files_flat, _errors_flat = list_files(root, include_subfolders=False)

    recursive_names = {path.name.lower() for path in files_recursive}
    flat_names = {path.name.lower() for path in files_flat}

    assert "thumbs.db" not in recursive_names
    assert "thumbs.db" not in flat_names
    assert "photo.png" in recursive_names
    assert "doc.txt" in recursive_names


def test_storage_delete_collection_entry_removes_single_row(unique_temp_path) -> None:
    db_path = unique_temp_path("collection_delete_entry", ".sqlite3")
    database = Database(path=db_path)
    try:
        item = database.create_collection_item(
            title="Entry delete",
            entity_type="other",
            category_id=None,
        )
        database.create_collection_entries(
            item.id,
            [
                {
                    "source_path": "D:/tmp/a.txt",
                    "rel_path": "a.txt",
                    "title": "a",
                    "ext": ".txt",
                    "mime": "text/plain",
                    "size_bytes": 1,
                    "meta_json": "",
                },
                {
                    "source_path": "D:/tmp/b.txt",
                    "rel_path": "b.txt",
                    "title": "b",
                    "ext": ".txt",
                    "mime": "text/plain",
                    "size_bytes": 1,
                    "meta_json": "",
                },
            ],
        )
        entries = database.fetch_collection_entries(item.id)
        assert len(entries) == 2

        database.delete_collection_entry(entries[0].id)

        remaining = database.fetch_collection_entries(item.id)
        assert len(remaining) == 1
        assert remaining[0].rel_path == "b.txt"
    finally:
        database.close()
        db_path.unlink(missing_ok=True)


def test_workspace_removes_entry_without_deleting_source_file(monkeypatch, unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    db_path = unique_temp_path("collection_workspace_remove_entry", ".sqlite3")
    source_file = unique_temp_path("collection_source_entry", ".txt")
    source_file.write_text("payload", encoding="utf-8")
    database = Database(path=db_path)
    workspace = None
    try:
        item = database.create_collection_item(
            title="Workspace entry",
            entity_type="other",
            category_id=None,
        )
        database.create_collection_entries(
            item.id,
            [
                {
                    "source_path": str(source_file),
                    "rel_path": "folder/source.txt",
                    "title": "source",
                    "ext": ".txt",
                    "mime": "text/plain",
                    "size_bytes": source_file.stat().st_size,
                    "meta_json": "",
                }
            ],
        )

        monkeypatch.setattr(collections_workspace, "get_database", lambda: database)
        monkeypatch.setattr(
            collections_workspace,
            "show_dialog_standard",
            lambda _dialog, _parent=None: QDialog.DialogCode.Accepted,
        )
        workspace = collections_workspace.CollectionsWorkspace()

        target_row = -1
        for row in range(workspace.items_list.count()):
            if workspace.items_list.item(row).data(collections_workspace.Qt.ItemDataRole.UserRole) == item.id:
                target_row = row
                break
        assert target_row >= 0

        workspace.items_list.setCurrentRow(target_row)
        QApplication.processEvents()

        entry_item = None
        for row in range(workspace.entries_list.count()):
            candidate = workspace.entries_list.item(row)
            payload = candidate.data(collections_workspace.Qt.ItemDataRole.UserRole)
            if payload and payload[0] == "entry":
                entry_item = candidate
                break
        assert entry_item is not None

        workspace.entries_list.setCurrentItem(entry_item)
        QApplication.processEvents()
        assert workspace.remove_entry_button.isEnabled() is True

        workspace._remove_selected_entry()

        assert database.fetch_collection_entries(item.id) == []
        assert source_file.exists() is True
        assert workspace.details_description.objectName() == "CollectionsDescription"
        assert "QLabel#CollectionsDescription" in workspace.styleSheet()
    finally:
        if workspace is not None:
            workspace.deleteLater()
        database.close()
        db_path.unlink(missing_ok=True)
        source_file.unlink(missing_ok=True)
