"""_EntryThumbWorker class module for collections workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class _EntryThumbWorker(QRunnable):
    def __init__(
        self,
        entry_id: int,
        source_path: str,
        thumb_path: Path,
        size: QSize,
        signals: _EntryThumbSignals,
        kind: str,
    ):
        super().__init__()
        self.entry_id = entry_id
        self.source_path = source_path
        self.thumb_path = thumb_path
        self.size = size
        self.signals = signals
        self.kind = kind

    def run(self) -> None:
        try:
            if self.thumb_path.exists():
                self.signals.ready.emit(self.entry_id, str(self.thumb_path))
                return
            if self.kind == "video":
                image = self._load_video_frame()
            else:
                image = QImage(self.source_path)
            if image.isNull():
                return
            scaled = image.scaled(self.size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = max(0, (scaled.width() - self.size.width()) // 2)
            y = max(0, (scaled.height() - self.size.height()) // 2)
            cropped = scaled.copy(x, y, self.size.width(), self.size.height())
            self.thumb_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(str(self.thumb_path), b"PNG")
            self.signals.ready.emit(self.entry_id, str(self.thumb_path))
        except (OSError, ValueError):
            return

    def _load_video_frame(self) -> QImage:
        try:
            # noinspection PyPackageRequirements
            import cv2  # type: ignore
        except ImportError:
            return QImage()
        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            return QImage()
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            return QImage()
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except (cv2.error, ValueError, TypeError):
            return QImage()
        h, w, _ = frame.shape
        bytes_per_line = 3 * w
        return QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

__all__ = ["_EntryThumbWorker"]
