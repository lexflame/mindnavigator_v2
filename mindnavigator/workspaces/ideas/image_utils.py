from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImageReader, QPixmap


def load_scaled_pixmap(file_path: Path, size: QSize) -> QPixmap:
    if not file_path.is_file():
        return QPixmap()
    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return QPixmap()
    pixmap = QPixmap.fromImage(image)
    if not size.isValid():
        return pixmap
    return pixmap.scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


__all__ = ["load_scaled_pixmap"]
