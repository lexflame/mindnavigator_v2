"""Folder importer for Collections workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import mimetypes
import os
from typing import Iterable, List, Tuple


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}


@dataclass(frozen=True)
class CollectionImportItem:
    source_path: str
    rel_path: str
    title: str
    ext: str
    mime: str
    size_bytes: int
    meta_json: str = ""


def list_files(folder_path: Path, *, include_subfolders: bool = True) -> Tuple[List[Path], List[str]]:
    root = Path(folder_path)
    files: List[Path] = []
    errors: List[str] = []
    if include_subfolders:
        for dirpath, _subdirs, filenames in os.walk(root, onerror=lambda walk_err: errors.append(str(walk_err))):
            for name in filenames:
                files.append(Path(dirpath) / name)
    else:
        try:
            for entry in root.iterdir():
                try:
                    if entry.is_file():
                        files.append(entry)
                except Exception as entry_err:  # noqa: BLE001
                    errors.append(f"{entry}: {entry_err}")
        except Exception as root_err:  # noqa: BLE001
            errors.append(f"{root}: {root_err}")
    return files, errors


def scan_files(
        folder_path: Path,
    files: Iterable[Path],
    *,
    progress_cb=None,
    cancel_cb=None,
) -> Tuple[List[CollectionImportItem], List[str], bool]:
    root = Path(folder_path)
    items: List[CollectionImportItem] = []
    errors: List[str] = []
    total = len(files) if isinstance(files, list) else None
    cancelled = False
    index = 0
    seen_rel: set[str] = set()
    for entry in files:
        try:
            index += 1
            if cancel_cb and cancel_cb():
                cancelled = True
                break
            try:
                rel_path = entry.relative_to(root).as_posix()
            except Exception as rel_err:  # noqa: BLE001
                errors.append(f"{entry}: {rel_err}")
                continue
            if rel_path in seen_rel:
                errors.append(f"{entry}: duplicate rel_path {rel_path}")
                continue
            seen_rel.add(rel_path)
            ext = entry.suffix.lower()
            mime = mimetypes.guess_type(entry.name)[0] or ""
            size_bytes = int(entry.stat().st_size)
            title = entry.stem or entry.name
            items.append(
                CollectionImportItem(
                    source_path=str(entry.resolve()),
                    rel_path=rel_path,
                    title=title,
                    ext=ext,
                    mime=mime,
                    size_bytes=size_bytes,
                )
            )
            if progress_cb:
                progress_cb(index, total, entry)
        except Exception as scan_err:  # noqa: BLE001
            errors.append(f"{entry}: {scan_err}")
    return items, errors, cancelled


class FolderCollectionImporter:

    @staticmethod
    def classify_extension(ext: str) -> str:
        ext = (ext or "").lower()
        if ext in IMAGE_EXTENSIONS:
            return "image"
        if ext in VIDEO_EXTENSIONS:
            return "video"
        if ext in DOC_EXTENSIONS:
            return "document"
        return "other"
