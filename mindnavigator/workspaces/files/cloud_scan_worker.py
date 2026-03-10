"""CloudScanWorker class module for files workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class CloudScanWorker(QObject):
    progress = Signal(str, int, int)
    error = Signal(str)
    finished = Signal(ScanSummary)

    def __init__(self, root_path: Path) -> None:
        super().__init__()
        self._root = root_path
        self._db = Database(default_db_path())

    def run(self) -> None:
        if not self._root.exists() or not self._root.is_dir():
            self.error.emit("Каталог облака не найден. Проверьте путь в настройках.")
            self.finished.emit(ScanSummary(0, 0, 0, 0))
            return

        files = [p for p in self._root.rglob("*") if p.is_file()]
        total = len(files)
        valid = 0
        invalid = 0
        skipped = 0
        rel_paths: List[str] = []

        for idx, file_path in enumerate(files, start=1):
            try:
                checksum = self._hash_file(file_path)
            except OSError:
                skipped += 1
                self.progress.emit(
                    f"{file_path.name} — ошибка чтения файла",
                    idx,
                    total,
                )
                continue

            rel_path = file_path.relative_to(self._root).as_posix()
            rel_paths.append(rel_path)
            hash_value = self._hash_from_path(rel_path)
            is_valid = bool(hash_value) and checksum == hash_value.lower()
            description = self._description_from_path(rel_path)
            is_image = self._is_image(file_path)

            self._db.upsert_cloud_file(
                rel_path=rel_path,
                name=file_path.name,
                description=description,
                checksum=checksum,
                hash_value=hash_value or "",
                size=file_path.stat().st_size,
                is_image=is_image,
                valid=is_valid,
            )

            if is_valid:
                valid += 1
                status = "OK"
            else:
                invalid += 1
                status = "НЕ СОВПАДАЕТ"

            self.progress.emit(f"{rel_path} — {status}", idx, total)

        self._db.remove_missing_cloud_files(rel_paths)
        self.progress.emit("Переиндексация базы данных...", total, total)
        self._db.reindex()
        self.progress.emit("Переиндексация базы данных завершена.", total, total)
        self.finished.emit(ScanSummary(total, valid, invalid, skipped))

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _hash_from_path(rel_path: str) -> Optional[str]:
        match = HASH_RE.search(rel_path)
        return match.group(0) if match else None

    @staticmethod
    def _description_from_path(rel_path: str) -> str:
        path = Path(rel_path)
        folder_parts = list(path.parent.parts) if path.parent != Path(".") else []
        stem = path.stem
        stem = HASH_RE.sub("", stem).replace("__", " ").strip(" -_")
        description_text = " / ".join(part for part in [*folder_parts, stem] if part)
        payload = {
            "text": description_text,
            "folders": folder_parts,
            "stem": stem,
            "extension": path.suffix.lower(),
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _is_image(file_path: Path) -> bool:
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return True
        mime = mimetypes.guess_type(file_path.name)[0] or ""
        return mime.startswith("image/")

__all__ = ["CloudScanWorker"]
