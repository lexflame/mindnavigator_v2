"""CloudDocPickerDialog class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403

class CloudDocPickerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._files = [f for f in self._db.fetch_cloud_files() if Path(f.rel_path).suffix.lower() in DOC_EXTENSIONS]
        self._selected_rel_path: Optional[str] = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Файлы описаний")
        self.setMinimumSize(520, 420)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for item in self._files:
            label = f"{item.name}"
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.rel_path)
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
        current = self.list_widget.currentItem()
        if current is None:
            QMessageBox.warning(self, "Импорт", "Выберите файл для импорта.")
            return
        self._selected_rel_path = current.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def selected_rel_path(self) -> Optional[str]:
        return self._selected_rel_path

    def read_selected_text(self) -> str:
        rel_path = self._selected_rel_path
        if not rel_path:
            return ""
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            return ""
        file_path = Path(cloud_root) / rel_path
        if not file_path.exists():
            return ""
        return extract_text_from_document(file_path)

__all__ = ["CloudDocPickerDialog"]
