from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import mimetypes
import re
from typing import List, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
)

from mindnavigator.storage import Database, default_db_path, get_database


HASH_RE = re.compile(r"[a-fA-F0-9]{32,64}")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"}


@dataclass(frozen=True)
class ScanSummary:
    total: int
    valid: int
    invalid: int
    skipped: int


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
        self.finished.emit(ScanSummary(total, valid, invalid, skipped))

    def _hash_file(self, file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _hash_from_path(self, rel_path: str) -> Optional[str]:
        match = HASH_RE.search(rel_path)
        return match.group(0) if match else None

    def _description_from_path(self, rel_path: str) -> str:
        path = Path(rel_path)
        if path.parent == Path("."):
            return ""
        return " / ".join(part for part in path.parent.parts)

    def _is_image(self, file_path: Path) -> bool:
        if file_path.suffix.lower() in IMAGE_EXTENSIONS:
            return True
        mime = mimetypes.guess_type(file_path.name)[0] or ""
        return mime.startswith("image/")


class FileWorkspace(QWidget):
    """Рабочая область для синхронизации файлов облака."""

    CLOUD_STORAGE_KEY = "cloud_storage_path"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._scan_thread: Optional[QThread] = None
        self._scan_worker: Optional[CloudScanWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.sync_button = QPushButton("Синхронизация")
        self.sync_button.setObjectName("FilesSyncButton")
        self.sync_button.clicked.connect(self._start_sync)

        self.status_label = QLabel("Синхронизация не запускалась.")
        self.status_label.setObjectName("FilesSyncStatus")

        header.addWidget(self.sync_button, 0, Qt.AlignLeft)
        header.addWidget(self.status_label, 1, Qt.AlignLeft)
        header.addStretch(1)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("FilesSyncLog")
        self.log_output.setPlaceholderText("Здесь появятся результаты синхронизации…")

        layout.addLayout(header)
        layout.addWidget(self.log_output, 1)

        self.setStyleSheet(
            """
            QLabel#FilesSyncStatus {
                color: #b7b7b7;
                font-size: 12px;
            }
            QPushButton#FilesSyncButton {
                background: #2a2d33;
                border: 1px solid #3a3d44;
                border-radius: 6px;
                padding: 6px 16px;
                color: #e0e0e0;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#FilesSyncButton:hover {
                background: #343841;
            }
            QPushButton#FilesSyncButton:disabled {
                background: #202225;
                color: #6f7278;
                border-color: #2b2d33;
            }
            QPlainTextEdit#FilesSyncLog {
                background: #1b1d22;
                border: 1px solid #2f3136;
                border-radius: 8px;
                color: #d6d6d6;
                padding: 10px;
                font-size: 11px;
            }
            """
        )

    def _start_sync(self) -> None:
        cloud_path = self._db.get_setting(self.CLOUD_STORAGE_KEY, default="").strip()
        if not cloud_path:
            self._append_log("Путь к облаку не задан. Настройте его в разделе «Настройки».")
            self.status_label.setText("Ожидание пути к облаку.")
            return

        if self._scan_thread and self._scan_thread.isRunning():
            return

        self.log_output.clear()
        self.sync_button.setDisabled(True)
        self.status_label.setText("Подготовка к синхронизации...")

        self._scan_thread = QThread(self)
        self._scan_worker = CloudScanWorker(Path(cloud_path))
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._cleanup_worker)

        self._scan_thread.start()

    def _on_scan_progress(self, message: str, current: int, total: int) -> None:
        self.status_label.setText(f"Сканирование: {current}/{total}")
        self._append_log(message)

    def _on_scan_error(self, message: str) -> None:
        self._append_log(message)
        self.status_label.setText(message)

    def _on_scan_finished(self, summary: ScanSummary) -> None:
        self.sync_button.setDisabled(False)
        self.status_label.setText(
            f"Сканирование завершено: {summary.valid} OK, {summary.invalid} ошибок, {summary.skipped} пропущено."
        )
        self._append_log(
            f"Итого: {summary.total} файлов, {summary.valid} совпадений, {summary.invalid} расхождений."
        )

    def _cleanup_worker(self) -> None:
        if self._scan_worker:
            self._scan_worker.deleteLater()
        self._scan_worker = None
        self._scan_thread = None

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
