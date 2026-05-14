"""Full-screen preview for idea images."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from .image_utils import load_scaled_pixmap


class IdeaImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        idea_id: int,
        images: List[IdeaImageData],
        start_index: int,
        cloud_root: Path,
    ) -> None:
        super().__init__(parent)
        self._idea_id = idea_id
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root

        self.setObjectName("IdeaImagePreview")
        self.setWindowTitle("Просмотр изображения")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.path_label = QLabel()
        self.path_label.setObjectName("IdeaImagePreviewPath")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setObjectName("IdeaImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.caption_label = QLabel()
        self.caption_label.setObjectName("IdeaImagePreviewCaption")
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setWordWrap(True)

        layout.addWidget(self.path_label)
        layout.addWidget(self.image_label, 1)
        layout.addWidget(self.caption_label)

        self.setStyleSheet(
            """
            QDialog#IdeaImagePreview {
                background: #0f1115;
            }
            QLabel#IdeaImagePreviewPath {
                color: #f0f0f0;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#IdeaImagePreviewLabel {
                color: #9aa0a6;
            }
            QLabel#IdeaImagePreviewCaption {
                color: #e0e0e0;
                background: rgba(30, 33, 39, 0.88);
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
            self.caption_label.setText("")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        current = self._images[self._current_index]
        self.path_label.setText(current.rel_path)
        self.caption_label.setText(f"Подпись идеи:{self._idea_id}:{current.caption}")
        self.setWindowTitle(f"{Path(current.rel_path).name} ({self._current_index + 1}/{len(self._images)})")
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        current = self._images[self._current_index] if self._images else None
        if current is None:
            return
        target_size = self.image_label.size()
        if not target_size.isValid() or target_size.width() < 10:
            target_size = QSize(1280, 860)
        pixmap = load_scaled_pixmap(self._cloud_root / current.rel_path, target_size)
        if pixmap.isNull():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return
        self.image_label.setPixmap(pixmap)
        self.image_label.setText("")


__all__ = ["IdeaImagePreviewDialog"]
