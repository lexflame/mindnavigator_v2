"""Collections workspace: thematic links/images with cross-links."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mindnavigator.core.models.collection_item import CollectionItem
from mindnavigator.core.serializers.collections_share_v1 import (
    export_collections_share_v1,
    import_collections_share_v1,
)
from mindnavigator.ui.workspaces.base_workspace import BaseWorkspace


class CollectionItemDialog(QDialog):
    """Dialog for creating/editing one collection item with link rows."""

    def __init__(self, item: CollectionItem | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Элемент коллекции")
        self.resize(640, 420)
        self._item = item

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit(item.title if item else "")
        self.kind_combo = QComboBox()
        self.kind_combo.addItems(["image", "link", "note", "object"])
        if item:
            idx = self.kind_combo.findText(item.kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)
        self.url_edit = QLineEdit(item.url or "" if item else "")
        self.tags_edit = QLineEdit(", ".join(item.tags) if item and item.tags else "")

        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.kind_combo)
        form.addRow("URL", self.url_edit)
        form.addRow("Теги", self.tags_edit)
        layout.addLayout(form)

        links_header = QHBoxLayout()
        links_label = QLabel("Links")
        self.add_link_btn = QPushButton("Добавить ссылку")
        self.add_link_btn.clicked.connect(self._add_link_row)
        links_header.addWidget(links_label)
        links_header.addStretch(1)
        links_header.addWidget(self.add_link_btn)
        layout.addLayout(links_header)

        self.links_table = QTableWidget(0, 3)
        self.links_table.setHorizontalHeaderLabels(["Type", "Target ID", ""])
        self.links_table.horizontalHeader().setStretchLastSection(False)
        self.links_table.horizontalHeader().setSectionResizeMode(0, self.links_table.horizontalHeader().Stretch)
        self.links_table.horizontalHeader().setSectionResizeMode(1, self.links_table.horizontalHeader().Stretch)
        self.links_table.horizontalHeader().setSectionResizeMode(2, self.links_table.horizontalHeader().ResizeToContents)
        layout.addWidget(self.links_table, 1)

        if item:
            for link in item.links:
                self._add_link_row(str(link.get("type") or ""), str(link.get("target_id") or ""))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_link_row(self, link_type: str = "", target_id: str = "") -> None:
        row = self.links_table.rowCount()
        self.links_table.insertRow(row)
        self.links_table.setItem(row, 0, QTableWidgetItem(link_type))
        self.links_table.setItem(row, 1, QTableWidgetItem(target_id))
        remove_btn = QPushButton("✕")
        remove_btn.clicked.connect(self._remove_link_row)
        self.links_table.setCellWidget(row, 2, remove_btn)

    def _remove_link_row(self) -> None:
        button = self.sender()
        if button is None:
            return
        for row in range(self.links_table.rowCount()):
            if self.links_table.cellWidget(row, 2) is button:
                self.links_table.removeRow(row)
                return

    def build_item(self) -> CollectionItem:
        title = self.title_edit.text().strip()
        if not title:
            raise ValueError("Название не должно быть пустым.")

        tags = [tag.strip() for tag in self.tags_edit.text().split(",") if tag.strip()]
        links: list[dict[str, str]] = []
        for row in range(self.links_table.rowCount()):
            type_item = self.links_table.item(row, 0)
            target_item = self.links_table.item(row, 1)
            link_type = (type_item.text() if type_item else "").strip()
            target_id = (target_item.text() if target_item else "").strip()
            if not link_type and not target_id:
                continue
            links.append({"type": link_type, "target_id": target_id})

        base = self._item.to_dict() if self._item else {}
        item = CollectionItem.from_dict(
            {
                **base,
                "title": title,
                "kind": self.kind_combo.currentText(),
                "url": self.url_edit.text().strip() or None,
                "tags": tags,
                "links": links,
                "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }
        )
        return item


class CollectionsWorkspace(BaseWorkspace):
    """Workspace to browse and edit thematic collection items."""

    workspace_id = "collections"
    workspace_title = "Коллекции"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._items: list[CollectionItem] = []
        self._filtered_items: list[CollectionItem] = []
        self._last_export_payload = ""
        super().__init__(parent)
        self.set_content(self.build_content())
        self._refresh_view()

    def build_content(self) -> QWidget:
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)

        self.kind_filter_combo = QComboBox()
        self.kind_filter_combo.addItem("Все типы", "")
        self.kind_filter_combo.addItems(["image", "link", "note", "object"])
        self.kind_filter_combo.currentTextChanged.connect(
            lambda _text: self.set_filter("kind", self.kind_filter_combo.currentText() or None)
        )
        layout.addWidget(self.kind_filter_combo)

        self.table = QTableWidget(0, 4)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["Title", "Kind", "Tags", "Updated"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, self.table.horizontalHeader().ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, self.table.horizontalHeader().Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, self.table.horizontalHeader().ResizeToContents)
        self.table.itemSelectionChanged.connect(self.update_action_states)
        layout.addWidget(self.table, 1)
        return host

    def create_actions(self) -> dict[str, QAction]:
        actions = {
            "add": QAction("Добавить", self),
            "edit": QAction("Изменить", self),
            "delete": QAction("Удалить", self),
            "refresh": QAction("Обновить", self),
            "share": QAction("Поделиться", self),
            "import": QAction("Импорт", self),
            "export": QAction("Экспорт", self),
        }
        actions["add"].triggered.connect(self._add_item)
        actions["edit"].triggered.connect(self._edit_selected)
        actions["delete"].triggered.connect(self._delete_selected)
        actions["refresh"].triggered.connect(self._refresh_view)
        actions["share"].setEnabled(False)
        actions["import"].triggered.connect(self._import_stub)
        actions["export"].triggered.connect(self._export_stub)
        return actions

    def get_selection(self) -> CollectionItem | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._filtered_items):
            return None
        return self._filtered_items[row]

    def apply_query(self, query: str) -> None:
        self._query = (query or "").strip().lower()
        self._refresh_view()

    def apply_filters(self, filters: dict[str, object]) -> None:
        self._filters = dict(filters)
        self._refresh_view()

    def _refresh_view(self) -> None:
        query = (self._query or "").strip().lower()
        filter_kind = (self._filters.get("kind") or "").strip().lower() if self._filters else ""
        filter_tag = (self._filters.get("tag") or "").strip().lower() if self._filters else ""

        filtered = []
        for item in self._items:
            if query and query not in f"{item.title} {item.kind} {' '.join(item.tags)}".lower():
                continue
            if filter_kind and item.kind != filter_kind:
                continue
            if filter_tag and filter_tag not in [tag.lower() for tag in item.tags]:
                continue
            filtered.append(item)

        self._filtered_items = filtered
        self.table.setRowCount(len(filtered))
        for row, item in enumerate(filtered):
            self.table.setItem(row, 0, QTableWidgetItem(item.title))
            self.table.setItem(row, 1, QTableWidgetItem(item.kind))
            self.table.setItem(row, 2, QTableWidgetItem(", ".join(item.tags)))
            self.table.setItem(row, 3, QTableWidgetItem(item.updated_at))

        self.set_status(f"Элементов: {len(filtered)}")
        self.update_action_states()

    def _add_item(self) -> None:
        dialog = CollectionItemDialog(parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            item = dialog.build_item()
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self._items.append(item)
        self._refresh_view()

    def _edit_selected(self) -> None:
        selected = self.get_selection()
        if selected is None:
            return
        dialog = CollectionItemDialog(selected, self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            updated = dialog.build_item()
        except ValueError as exc:
            QMessageBox.warning(self, "Коллекции", str(exc))
            return
        self._items = [updated if item.id == updated.id else item for item in self._items]
        self._refresh_view()

    def _delete_selected(self) -> None:
        selected = self.get_selection()
        if selected is None:
            return
        self._items = [item for item in self._items if item.id != selected.id]
        self._refresh_view()

    def _export_stub(self) -> None:
        self._last_export_payload = export_collections_share_v1(self._filtered_items or self._items)
        self.set_status("Экспорт v1 подготовлен в памяти (без сохранения в файл).")

    def _import_stub(self) -> None:
        if not self._last_export_payload:
            self.set_status("Импорт пропущен: нет экспортированного payload.")
            return
        restored_items = import_collections_share_v1(self._last_export_payload)
        if not restored_items:
            self.set_status("Импорт не выполнился: payload пустой или неподдерживаемый.")
            return
        existing_ids = {item.id for item in self._items}
        for item in restored_items:
            if item.id in existing_ids:
                continue
            self._items.append(item)
        self._refresh_view()
        self.set_status(f"Импортировано: {len(restored_items)}")
