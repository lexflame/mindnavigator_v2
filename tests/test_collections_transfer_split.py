from __future__ import annotations

from pathlib import Path

from mindnavigator.collections_importer import FolderCollectionImporter as LegacyFolderCollectionImporter
from mindnavigator.collections_importer import list_files as legacy_list_files
from mindnavigator.collections_importer import scan_files as legacy_scan_files
from mindnavigator.csv_transfer import CsvTransferError as LegacyCsvTransferError
from mindnavigator.csv_transfer import CsvTransferOptions as LegacyCsvTransferOptions
from mindnavigator.csv_transfer import CsvTransferService as LegacyCsvTransferService
from mindnavigator.transfer.collections import (
    CsvTransferError,
    CsvTransferOptions,
    CsvTransferService,
    FolderCollectionImporter,
    list_files,
    scan_files,
)


def test_collections_transfer_split_keeps_legacy_import_paths() -> None:
    assert LegacyFolderCollectionImporter is FolderCollectionImporter
    assert legacy_list_files is list_files
    assert legacy_scan_files is scan_files
    assert LegacyCsvTransferError is CsvTransferError
    assert LegacyCsvTransferOptions is CsvTransferOptions
    assert LegacyCsvTransferService is CsvTransferService


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
