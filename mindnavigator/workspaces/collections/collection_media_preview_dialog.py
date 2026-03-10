"""CollectionMediaPreviewDialog class module for collections workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class CollectionMediaPreviewDialog(QDialog):
    def __init__(
        self,
        entries: List[CollectionEntryData],
        start_index: int,
        parent=None,
    ):
        super().__init__(parent)
        self._entries = entries
        self._index = max(0, min(start_index, len(entries) - 1))
        self.setWindowTitle("Просмотр")
        self.setMinimumSize(720, 520)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel("")
        self.title_label.setObjectName("CollectionPreviewTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.content = QLabel()
        self.content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.content, 1)

        nav = QHBoxLayout()
        self.prev_btn = QToolButton()
        self.prev_btn.setText("◀")
        self.prev_btn.clicked.connect(self._show_prev)
        self.next_btn = QToolButton()
        self.next_btn.setText("▶")
        self.next_btn.clicked.connect(self._show_next)
        nav.addWidget(self.prev_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        layout.addLayout(nav)

        self._player = None
        self._audio = None
        self._video_widget = None

        self._update_content()

        self.setStyleSheet(
            """
            QDialog {
                background: #0f1115;
            }
            QLabel#CollectionPreviewTitle {
                color: #f0f0f0;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel {
                color: #cfcfcf;
            }
            """
        )

    def _show_image(self, path: Path) -> None:
        if not path.is_file():
            self._set_content_text("Изображение недоступно.")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._set_content_text("Изображение недоступно.")
            return
        self._set_pixmap(pixmap)

    def _show_video(self, path: Path) -> None:
        if not path.is_file():
            self._set_content_text("Видео недоступно.")
            return
        if _MULTIMEDIA_AVAILABLE and QVideoWidget is not None and QMediaPlayer is not None:
            self._video_widget = QVideoWidget()
            self._audio = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setVideoOutput(self._video_widget)
            self._player.setAudioOutput(self._audio)
            self._player.setSource(QUrl.fromLocalFile(str(path)))
            self.layout().replaceWidget(self.content, self._video_widget)
            self.content.deleteLater()
            self.content = self._video_widget
            self._player.play()
        else:
            self._set_content_text("Проигрывание видео недоступно.")

    def _show_document(self, path: Path) -> None:
        if not path.is_file():
            self._set_content_text("Документ недоступен.")
            return
        try:
            from mindnavigator.workspaces.objects_workspace import extract_text_from_document
        except ImportError:
            self._set_content_text("Предпросмотр документа недоступен.")
            return
        text = extract_text_from_document(path)
        if not text:
            self._set_content_text("Не удалось извлечь текст из документа.")
            return
        preview = "\n".join(text.splitlines()[:80])
        self._set_content_text(preview)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if isinstance(self.content, QLabel) and self.content.pixmap():
            self._set_pixmap(self.content.pixmap())

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        target = self.content.size()
        scaled = pixmap.scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._set_content_pixmap(scaled)

    def _ensure_label_content(self) -> QLabel:
        if isinstance(self.content, QLabel):
            return self.content
        old_widget = self.content
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().replaceWidget(old_widget, label)
        old_widget.deleteLater()
        self.content = label
        return label

    def _set_content_text(self, text: str) -> None:
        self._ensure_label_content().setText(text)

    def _set_content_pixmap(self, pixmap: QPixmap) -> None:
        self._ensure_label_content().setPixmap(pixmap)

    def closeEvent(self, event) -> None:
        if self._player:
            self._player.stop()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Left:
            self._show_prev()
            return
        if event.key() == Qt.Key.Key_Right:
            self._show_next()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True
        return super().eventFilter(watched, event)

    def _show_prev(self) -> None:
        if not self._entries:
            return
        self._index = max(0, self._index - 1)
        self._update_content()

    def _show_next(self) -> None:
        if not self._entries:
            return
        self._index = min(len(self._entries) - 1, self._index + 1)
        self._update_content()

    def _update_content(self) -> None:
        if not self._entries:
            self.title_label.setText("Нет элементов")
            self._set_content_text("Нет встроенного предпросмотра.")
            return
        entry = self._entries[self._index]
        self.title_label.setText(entry.rel_path)
        path = Path(entry.source_path)
        if self._player:
            self._player.stop()
        if self._video_widget:
            layout_obj = self.layout()
            if isinstance(layout_obj, QVBoxLayout):
                layout_obj.replaceWidget(self._video_widget, self.content)
            self._video_widget.deleteLater()
            self._video_widget = None
            self.content = QLabel()
            self.content.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if isinstance(layout_obj, QVBoxLayout):
                layout_obj.insertWidget(1, self.content, 1)
        kind = FolderCollectionImporter.classify_extension(entry.ext)
        if kind == "document":
            self._show_document(path)
        elif kind == "image":
            self._show_image(path)
        elif kind == "video":
            self._show_video(path)
        else:
            self._set_content_text("Нет встроенного предпросмотра.")

__all__ = ["CollectionMediaPreviewDialog"]
