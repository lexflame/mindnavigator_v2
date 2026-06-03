"""TaskImagePreviewDialog class module for tasks workspace."""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QPushButton

from ._shared import *  # noqa: F401,F403
class TaskImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
        comments_by_file_id: Optional[Dict[int, str]] = None,
        save_comment: Optional[Callable[[int, str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._comments_by_file_id = dict(comments_by_file_id or {})
        self._save_comment = save_comment

        self.setObjectName("TaskImagePreview")
        self.setWindowTitle("Просмотр изображения")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setObjectName("TaskImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label, 1)

        comment_panel = QFrame(self)
        comment_panel.setObjectName("TaskImageCommentPanel")
        comment_layout = QHBoxLayout(comment_panel)
        comment_layout.setContentsMargins(16, 12, 16, 12)
        comment_layout.setSpacing(10)
        self.comment_edit = QPlainTextEdit(comment_panel)
        self.comment_edit.setObjectName("TaskImageCommentEdit")
        self.comment_edit.setPlaceholderText("Комментарий к изображению в рамках задачи")
        self.comment_edit.setFixedHeight(64)
        self.comment_edit.setReadOnly(save_comment is None)
        comment_layout.addWidget(self.comment_edit, 1)
        self.save_comment_button = QPushButton("Сохранить комментарий", comment_panel)
        self.save_comment_button.setObjectName("TaskImageCommentSave")
        self.save_comment_button.setVisible(save_comment is not None)
        self.save_comment_button.clicked.connect(self._save_current_comment)
        comment_layout.addWidget(self.save_comment_button)
        layout.addWidget(comment_panel)

        self.setStyleSheet(
            """
            QDialog#TaskImagePreview {
                background: #0f1115;
            }
            QLabel#TaskImagePreviewLabel {
                color: #9aa0a6;
            }
            QFrame#TaskImageCommentPanel {
                background: #151922;
                border-top: 1px solid #30394d;
            }
            QPlainTextEdit#TaskImageCommentEdit {
                color: #e6eaf2;
                background: #0f131b;
                border: 1px solid #30394d;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton#TaskImageCommentSave {
                color: #ffffff;
                background: #315fb8;
                border: 1px solid #4f7ecf;
                border-radius: 6px;
                padding: 8px 12px;
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
            self.setWindowTitle("Просмотр изображения")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        current = self._images[self._current_index]
        self.setWindowTitle(f"{current.name} ({self._current_index + 1}/{len(self._images)})")
        self.comment_edit.setPlainText(self._comments_by_file_id.get(int(current.id), ""))
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
        scaled = pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")

    def _save_current_comment(self) -> None:
        if not self._images or self._save_comment is None:
            return
        current = self._images[self._current_index]
        comment = self.comment_edit.toPlainText().strip()
        self._save_comment(int(current.id), comment)
        self._comments_by_file_id[int(current.id)] = comment

__all__ = ["TaskImagePreviewDialog"]
