"""MapImagePreviewDialog class module for maps workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
class MapImagePreviewDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        images: List[CloudFileData],
        start_index: int,
        cloud_root: Path,
    ) -> None:
        # Инициализация окна предпросмотра изображений.
        super().__init__(parent)
        # Данные изображений и кеш для быстрых переключений.
        self._images = images
        self._current_index = max(0, min(start_index, len(images) - 1))
        self._cloud_root = cloud_root
        self._pixmap_cache: Dict[str, QPixmap] = {}

        self.setObjectName("MapImagePreview")
        self.setWindowTitle("Просмотр изображения")

        # Компоновка диалога.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Виджет предпросмотра.
        self.image_label = QLabel()
        self.image_label.setObjectName("MapImagePreviewLabel")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label, 1)

        # Стили диалога.
        self.setStyleSheet(
            """
            QDialog#MapImagePreview {
                background: #0f1115;
            }
            QLabel#MapImagePreviewLabel {
                color: #9aa0a6;
            }
            """
        )

        # Open fullscreen and render the initial image immediately.
        self.setWindowState(self.windowState() | Qt.WindowState.WindowFullScreen)
        self._update_image()

    def keyPressEvent(self, event) -> None:
        # Навигация по изображениям стрелками и выход по Esc.
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
        # При изменении размеров пересчитываем масштаб.
        super().resizeEvent(event)
        if hasattr(self, "image_label"):
            self._update_pixmap()

    def _show_previous(self) -> None:
        # Переход к предыдущему изображению.
        if not self._images:
            return
        self._current_index = max(0, self._current_index - 1)
        self._update_image()

    def _show_next(self) -> None:
        # Переход к следующему изображению.
        if not self._images:
            return
        self._current_index = min(len(self._images) - 1, self._current_index + 1)
        self._update_image()

    def _update_image(self) -> None:
        # Загружает текущий элемент и обновляет UI.
        if not self._images:
            self.setWindowTitle("Просмотр изображения")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображения отсутствуют")
            return

        # Подготовка текущего изображения.
        current = self._images[self._current_index]
        self.setWindowTitle(f"{current.name} ({self._current_index + 1}/{len(self._images)})")
        file_path = self._cloud_root / current.rel_path
        if not file_path.is_file():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setText("Изображение недоступно")
            return

        # Используем кеш, чтобы ускорить переключения.
        cache_key = current.rel_path
        pixmap = self._pixmap_cache.get(cache_key)
        if pixmap is None:
            pixmap = QPixmap(str(file_path))
            self._pixmap_cache[cache_key] = pixmap
        self._update_pixmap(pixmap)

    def _update_pixmap(self, pixmap: Optional[QPixmap] = None) -> None:
        # Пересчитываем и применяем масштаб изображения.
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

__all__ = ["MapImagePreviewDialog"]
