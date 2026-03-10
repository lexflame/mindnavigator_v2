"""CloudImagePickerDialog class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class CloudImagePickerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._files = [f for f in self._db.fetch_cloud_files() if f.is_image]
        self._selected_rel_paths: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Изображения из FileWorkspace")
        self.setMinimumSize(620, 460)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListView.ViewMode.IconMode)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        self.list_widget.setIconSize(QSize(72, 72))
        self.list_widget.setGridSize(QSize(140, 120))
        self.list_widget.setSpacing(10)
        self.list_widget.setWordWrap(True)

        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        cloud_path = Path(cloud_root) if cloud_root else None

        for item in self._files:
            label = item.name
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.rel_path)
            if cloud_path:
                file_path = cloud_path / item.rel_path
                pixmap = _load_scaled_pixmap(file_path, QSize(72, 72))
                if not pixmap.isNull():
                    list_item.setIcon(pixmap)
            self.list_widget.addItem(list_item)

        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: #171a20;
                color: #e6e6e6;
            }
            QListWidget {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 8px;
                color: #e6e6e6;
            }
            QListWidget::item:selected {
                background: #2d3440;
            }
            """
        )

    def _accept(self) -> None:
        items = self.list_widget.selectedItems()
        if not items:
            QMessageBox.warning(self, "Изображения", "Выберите изображения для добавления.")
            return
        self._selected_rel_paths = [item.data(Qt.ItemDataRole.UserRole) for item in items]
        self.accept()

    def selected_rel_paths(self) -> List[str]:
        return self._selected_rel_paths

__all__ = ["CloudImagePickerDialog"]
