"""ObjectEditDialog class module for objects workspace."""

from __future__ import annotations

from ._shared import *  # noqa: F401,F403
from mindnavigator.context_entity_linking import ContextEntityLinkService, PendingContextLink
from mindnavigator.ui.context_entity_linking import attach_context_entity_linking
from .cloud_doc_picker_dialog import CloudDocPickerDialog

class ObjectEditDialog(QDialog):
    def __init__(self, parent=None, initial: Optional[ObjectRow] = None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._initial = initial
        self._pending_context_links: list[PendingContextLink] = []
        self._build_ui()
        if initial:
            self._fill(initial)

    def _build_ui(self) -> None:
        self.setWindowTitle("Карточка объекта")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.title_edit = QLineEdit()
        self.catalog_edit = QLineEdit()
        self.type_edit = QLineEdit()
        self.status_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMinimumHeight(140)
        self._context_link_controllers = [
            attach_context_entity_linking(
                self.title_edit,
                self._db,
                source_type="object",
                source_id_getter=self._context_source_id,
                source_field="title",
                pending_sink=self._add_pending_context_link,
            ),
            attach_context_entity_linking(
                self.description_edit,
                self._db,
                source_type="object",
                source_id_getter=self._context_source_id,
                source_field="description",
                pending_sink=self._add_pending_context_link,
            ),
        ]

        form.addRow("Название", self.title_edit)
        form.addRow("Каталог", self.catalog_edit)
        form.addRow("Тип", self.type_edit)
        form.addRow("Статус", self.status_edit)
        form.addRow("Описание", self.description_edit)

        layout.addLayout(form)

        tools = QHBoxLayout()
        self.import_button = QToolButton()
        self.import_button.setText("Импорт описания")
        self.import_button.clicked.connect(self._import_description)
        tools.addWidget(self.import_button)
        tools.addStretch(1)
        layout.addLayout(tools)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet(
            """
            QDialog {
                background: #171a20;
                color: #e6e6e6;
            }
            QLineEdit, QTextEdit {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px;
                color: #e6e6e6;
            }
            QToolButton {
                background: #232831;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #e6e6e6;
            }
            """
        )

    def _fill(self, initial: ObjectRow) -> None:
        self.title_edit.setText(initial.title)
        self.catalog_edit.setText(initial.catalog)
        self.type_edit.setText(initial.object_type)
        self.status_edit.setText(initial.status)
        self.description_edit.setPlainText(initial.description)

    def values(self) -> dict:
        return {
            "title": self.title_edit.text(),
            "catalog": self.catalog_edit.text(),
            "object_type": self.type_edit.text(),
            "status": self.status_edit.text(),
            "description": self.description_edit.toPlainText(),
        }

    def _context_source_id(self) -> Optional[int]:
        initial = self._initial
        if initial is None:
            return None
        object_id = int(getattr(initial, "id", 0) or 0)
        return object_id if object_id > 0 else None

    def _add_pending_context_link(self, link: PendingContextLink) -> None:
        duplicate = any(
            existing.target_type == link.target_type
            and existing.target_id == link.target_id
            and existing.anchor_text == link.anchor_text
            and existing.source_field == link.source_field
            for existing in self._pending_context_links
        )
        if not duplicate:
            self._pending_context_links.append(link)

    def apply_pending_context_links(self, object_id: int) -> None:
        if not self._pending_context_links:
            return
        service = ContextEntityLinkService(self._db)
        for link in list(self._pending_context_links):
            service.create_context_link(
                "object",
                int(object_id),
                link.target_type,
                link.target_id,
                link.anchor_text,
                link.source_field,
            )
        self._pending_context_links.clear()

    def _import_description(self) -> None:
        dialog = CloudDocPickerDialog(self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        rel_path = dialog.selected_rel_path()
        if not rel_path:
            return
        text = dialog.read_selected_text()
        if not text:
            QMessageBox.warning(self, "Импорт", "Не удалось извлечь текст из файла.")
            return
        self.description_edit.setPlainText(text)

__all__ = ["ObjectEditDialog"]
