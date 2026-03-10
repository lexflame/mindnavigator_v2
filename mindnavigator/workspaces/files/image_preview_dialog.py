"""ImagePreviewDialog class module for files workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class ImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
        description_formatter,
    ) -> None:
        super().__init__(parent)
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._format_description = description_formatter
        self._pixmap_cache: Dict[str, QPixmap] = {}

        self.setWindowTitle("Просмотр изображения")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.path_label = QLabel()
        self.path_label.setObjectName("FilesImagePath")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setObjectName("FilesImagePreview")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.description_label = QLabel()
        self.description_label.setObjectName("FilesImageDescription")
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)

        layout.addWidget(self.path_label)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.description_label)

        self.setStyleSheet(
            """
            QDialog {
                background: #0f1115;
            }
            QLabel#FilesImagePath {
                color: #f0f0f0;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#FilesImagePreview {
                color: #9aa0a6;
            }
            QLabel#FilesImageDescription {
                color: #e0e0e0;
                background: rgba(30, 33, 39, 0.85);
                border: 1px solid #2f333b;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 12px;
            }
            """
        )

        self._update_image()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._show_previous()
            return
        if event.key() == Qt.Key.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_pixmap()

    def _show_previous(self) -> None:
        if not self._images:
            return
        self._current_index = max(0, self._current_index - 1)
        self._update_image()

    def _show_next(self) -> None:
        if not self._images:
            return
        self._current_index = min(len(self._images) - 1, self._current_index + 1)
        self._update_image()

    def _update_image(self) -> None:
        if not self._images:
            self.path_label.setText("Нет изображений")
            self.description_label.setText("")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        current = self._images[self._current_index]
        self.path_label.setText(current.rel_path)
        self.description_label.setText(self._format_description(current.description))

        file_path = self._cloud_root / current.rel_path
        if not file_path.is_file():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return

        cache_key = current.rel_path
        pixmap = self._pixmap_cache.get(cache_key)
        if pixmap is None:
            pixmap = QPixmap(str(file_path))
            self._pixmap_cache[cache_key] = pixmap
        self._update_pixmap(pixmap)

    def _update_pixmap(self, pixmap: Optional[QPixmap] = None) -> None:
        if pixmap is None:
            current = self._images[self._current_index] if self._images else None
            if not current:
                return
            pixmap = self._pixmap_cache.get(current.rel_path)
        if not pixmap or pixmap.isNull():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return
        target_size = self.image_label.size()
        scaled = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")

__all__ = ["ImagePreviewDialog"]
