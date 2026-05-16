from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import IdeaImageData
from mindnavigator.workspaces.ideas.idea_image_preview_dialog import IdeaImagePreviewDialog
from mindnavigator.workspaces.ideas.image_utils import load_scaled_pixmap


def test_idea_image_preview_dialog_formats_caption(unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    cloud_root = unique_temp_path("idea_preview_cloud", "")
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "ideas" / "preview.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFFAA5500)
    assert image.save(str(image_path))

    dialog = IdeaImagePreviewDialog(
        None,
        idea_id=42,
        images=[
            IdeaImageData(
                id=1,
                idea_id=42,
                rel_path="ideas/preview.png",
                caption="Финальный кадр",
                created_at="2026-05-14T10:00:00+00:00",
                updated_at="2026-05-14T10:00:00+00:00",
            )
        ],
        start_index=0,
        cloud_root=cloud_root,
    )
    try:
        assert dialog.caption_label.text() == "Подпись идеи:42:Финальный кадр"
    finally:
        dialog.close()


def test_idea_image_preview_dialog_show_does_not_crash_before_image_label_ready(unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    cloud_root = unique_temp_path("idea_preview_show_cloud", "")
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "ideas" / "show.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF225588)
    assert image.save(str(image_path))

    dialog = IdeaImagePreviewDialog(
        None,
        idea_id=7,
        images=[
            IdeaImageData(
                id=2,
                idea_id=7,
                rel_path="ideas/show.png",
                caption="Проверка показа",
                created_at="2026-05-17T10:00:00+00:00",
                updated_at="2026-05-17T10:00:00+00:00",
            )
        ],
        start_index=0,
        cloud_root=cloud_root,
    )
    try:
        dialog.show()
        QApplication.processEvents()

        assert dialog.image_label is not None
        assert dialog.windowState() & Qt.WindowState.WindowFullScreen
    finally:
        dialog.close()


def test_load_scaled_pixmap_keeps_aspect_ratio(unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    image_path = unique_temp_path("idea_preview_aspect", ".png")
    image = QImage(400, 200, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF225588)
    assert image.save(str(image_path))

    pixmap = load_scaled_pixmap(image_path, QSize(300, 300))

    assert not pixmap.isNull()
    assert pixmap.width() == 300
    assert pixmap.height() == 150
