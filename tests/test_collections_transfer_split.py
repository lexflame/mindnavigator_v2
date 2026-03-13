from __future__ import annotations

from pathlib import Path

from mindnavigator.transfer.collections import (
    CsvTransferError,
    CsvTransferOptions,
    CsvTransferService,
    FolderCollectionImporter,
    list_files,
    scan_files,
)


def test_collections_transfer_package_exports_expected_symbols() -> None:
    assert FolderCollectionImporter is not None
    assert list_files is not None
    assert scan_files is not None
    assert CsvTransferError is not None
    assert CsvTransferOptions is not None
    assert CsvTransferService is not None


def test_collection_import_helpers_keep_file_scan_behavior(unique_temp_path) -> None:
    root = unique_temp_path("transfer_collections_root", "")
    root.mkdir(parents=True, exist_ok=True)
    nested = root / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (root / "Thumbs.db").write_text("ignore", encoding="utf-8")
    (root / "cover.jpg").write_text("image", encoding="utf-8")
    (nested / "note.txt").write_text("note", encoding="utf-8")

    files, errors = list_files(root, include_subfolders=True)
    items, scan_errors, cancelled = scan_files(root, files)

    assert errors == []
    assert scan_errors == []
    assert cancelled is False
    assert [item.rel_path for item in items] == ["cover.jpg", "nested/note.txt"]
    assert FolderCollectionImporter.classify_extension(".jpg") == "image"
    assert FolderCollectionImporter.classify_extension(".txt") == "document"
