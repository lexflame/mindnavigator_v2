from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from mindnavigator.storage import CloudFileData
from mindnavigator.workspaces.tasks.task_image_preview_dialog import TaskImagePreviewDialog


def _cloud_image(file_id: int, rel_path: str) -> CloudFileData:
    return CloudFileData(file_id, rel_path, rel_path, "", "", "", 0, True, True, "")


def test_task_image_preview_dialog_saves_task_comment(unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    cloud_root = unique_temp_path("task_image_preview", "")
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "preview.png"
    image = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF225588)
    assert image.save(str(image_path))
    saved: list[tuple[int, str]] = []

    dialog = TaskImagePreviewDialog(
        None,
        images=[_cloud_image(7, "preview.png")],
        start_index=0,
        cloud_root=cloud_root,
        comments_by_file_id={7: "Initial"},
        save_comment=lambda file_id, comment: saved.append((file_id, comment)),
    )
    try:
        assert dialog.comment_edit.toPlainText() == "Initial"
        assert dialog.comment_edit.isReadOnly() is False
        dialog.comment_edit.setPlainText(" Updated ")
        dialog._save_current_comment()
        assert saved == [(7, "Updated")]
    finally:
        dialog.close()


def test_task_image_preview_dialog_uses_read_only_comment_in_view_mode(unique_temp_path) -> None:
    _app = QApplication.instance() or QApplication([])
    cloud_root = unique_temp_path("task_image_preview_readonly", "")
    cloud_root.mkdir(parents=True, exist_ok=True)
    image_path = cloud_root / "preview.png"
    image = QImage(32, 32, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0xFF225588)
    assert image.save(str(image_path))

    dialog = TaskImagePreviewDialog(
        None,
        images=[_cloud_image(8, "preview.png")],
        start_index=0,
        cloud_root=cloud_root,
        comments_by_file_id={8: "Read only"},
    )
    try:
        assert dialog.comment_edit.toPlainText() == "Read only"
        assert dialog.comment_edit.isReadOnly() is True
        assert dialog.save_comment_button.isHidden()
    finally:
        dialog.close()
