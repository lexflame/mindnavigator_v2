"""Рабочая область для управления объектами и их файлами.

Входные данные:
    Данные объектов, вложенные документы/изображения и события пользователя.

Выходные данные:
    Обновлённые записи объектов и результаты обработки файлов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html
import re
import zipfile
from typing import List, Optional, Any, Union, Dict
from PySide6.QtCore import Qt, QSize, QRect, QModelIndex, QAbstractListModel
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QImageReader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QToolButton,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyle,
    QSplitter,
    QTextEdit,
    QPlainTextEdit,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
)

from mindnavigator.csv_transfer import CsvTransferError, CsvTransferService
from mindnavigator.storage import ObjectData, ObjectImageData, get_database
from mindnavigator.ui.modals import show_dialog_standard
from mindnavigator.ui.smooth_scroll import attach_smooth_scroll
from mindnavigator.workspaces.csv_workspace_transfer import (
    OBJECTS_CSV_FIELDS,
    export_objects_rows,
    import_objects_rows,
)


DOC_EXTENSIONS = {".doc", ".docx", ".txt"}


@dataclass(frozen=True)
class ObjectRow:
    id: int
    title: str
    catalog: str
    object_type: str
    status: str
    description: str


@dataclass(frozen=True)
class ObjectCategoryRow:
    category: str


ObjectListRow = Union[ObjectRow, ObjectCategoryRow]


class ObjectRoles:
    RowType = Qt.ItemDataRole.UserRole + 1
    Id = Qt.ItemDataRole.UserRole + 2
    Title = Qt.ItemDataRole.UserRole + 3
    Catalog = Qt.ItemDataRole.UserRole + 4
    ObjectType = Qt.ItemDataRole.UserRole + 5
    Status = Qt.ItemDataRole.UserRole + 6
    Description = Qt.ItemDataRole.UserRole + 7


def normalize_object_category(catalog: str) -> str:
    value = (catalog or "").strip()
    if not value:
        return "Без каталога"
    return value.split("/", 1)[0].strip() or "Без каталога"


def group_objects_by_category(items: List[ObjectRow]) -> List[ObjectListRow]:
    groups: Dict[str, List[ObjectRow]] = {}
    for item in items:
        groups.setdefault(normalize_object_category(item.catalog), []).append(item)
    rows: List[ObjectListRow] = []
    for category in sorted(groups.keys(), key=lambda value: (value == "Без каталога", value.lower())):
        rows.append(ObjectCategoryRow(category))
        rows.extend(groups[category])
    return rows


class ObjectsModel(QAbstractListModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._all_items: List[ObjectRow] = []
        self._items: List[ObjectRow] = []
        self._rows: List[ObjectListRow] = []
        self._catalog_filter: Optional[str] = None
        self._project_filter_id: Optional[int] = None
        self._task_filter_id: Optional[int] = None
        self._marker_filter_id: Optional[int] = None
        self._search = ""
        self._load_objects()

    def _load_objects(self) -> None:
        objects = self._db.fetch_objects()
        self._all_items = [
            ObjectRow(
                obj.id,
                obj.title,
                obj.catalog,
                obj.object_type,
                obj.status,
                obj.description,
            )
            for obj in objects
        ]
        self._rebuild()

    def reload(self) -> None:
        self._load_objects()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == ObjectRoles.RowType:
            return "category" if isinstance(row, ObjectCategoryRow) else "object"
        if isinstance(row, ObjectCategoryRow):
            if role == ObjectRoles.Title:
                return row.category
            if role == Qt.ItemDataRole.DisplayRole:
                return row.category
            return None
        item = row
        if role == ObjectRoles.Id:
            return item.id
        if role == ObjectRoles.Title:
            return item.title
        if role == ObjectRoles.Catalog:
            return item.catalog
        if role == ObjectRoles.ObjectType:
            return item.object_type
        if role == ObjectRoles.Status:
            return item.status
        if role == ObjectRoles.Description:
            return item.description
        if role == Qt.ItemDataRole.DisplayRole:
            return item.title
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        row = self._rows[index.row()]
        if isinstance(row, ObjectCategoryRow):
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def set_search(self, text: str) -> None:
        self._search = (text or "").strip().lower()
        self._rebuild()

    def set_catalog_filter(self, catalog: Optional[str]) -> None:
        self._catalog_filter = catalog
        self._rebuild()

    def set_project_filter(self, project_id: Optional[int]) -> None:
        self._project_filter_id = project_id
        if project_id is not None:
            self._task_filter_id = None
            self._marker_filter_id = None
        self._rebuild()

    def set_task_filter(self, task_id: Optional[int]) -> None:
        self._task_filter_id = task_id
        if task_id is not None:
            self._project_filter_id = None
            self._marker_filter_id = None
        self._rebuild()

    def set_marker_filter(self, marker_id: Optional[int]) -> None:
        self._marker_filter_id = marker_id
        if marker_id is not None:
            self._project_filter_id = None
            self._task_filter_id = None
        self._rebuild()

    def catalogs(self) -> List[str]:
        catalogs = {item.catalog for item in self._all_items if item.catalog}
        return sorted(catalogs)

    def add_object(self, obj: ObjectData) -> None:
        self._all_items.insert(
            0,
            ObjectRow(
                obj.id,
                obj.title,
                obj.catalog,
                obj.object_type,
                obj.status,
                obj.description,
            ),
        )
        self._rebuild()

    def update_object(self, obj: ObjectData) -> None:
        updated: List[ObjectRow] = []
        for item in self._all_items:
            if item.id == obj.id:
                updated.append(
                    ObjectRow(
                        obj.id,
                        obj.title,
                        obj.catalog,
                        obj.object_type,
                        obj.status,
                        obj.description,
                    )
                )
            else:
                updated.append(item)
        self._all_items = updated
        self._rebuild()

    def delete_object(self, object_id: int) -> None:
        self._all_items = [item for item in self._all_items if item.id != object_id]
        self._rebuild()

    def object_at(self, row: int) -> Optional[ObjectRow]:
        if row < 0 or row >= len(self._rows):
            return None
        row_item = self._rows[row]
        if isinstance(row_item, ObjectRow):
            return row_item
        return None

    def row_for_object_id(self, object_id: int) -> Optional[int]:
        for index, item in enumerate(self._rows):
            if isinstance(item, ObjectRow) and item.id == object_id:
                return index
        return None

    def _rebuild(self) -> None:
        search = self._search
        catalog = self._catalog_filter
        object_ids = None
        if self._marker_filter_id is not None or self._project_filter_id is not None or self._task_filter_id is not None:
            object_ids = set()
            for marker in self._db.fetch_map_markers():
                if not marker.object_ids:
                    continue
                if self._marker_filter_id is not None:
                    if marker.id == self._marker_filter_id:
                        object_ids.update(marker.object_ids)
                elif self._project_filter_id is not None:
                    if self._project_filter_id in marker.project_ids:
                        object_ids.update(marker.object_ids)
                elif self._task_filter_id is not None:
                    if self._task_filter_id in marker.task_ids:
                        object_ids.update(marker.object_ids)
        items: List[ObjectRow] = []
        for item in self._all_items:
            if object_ids is not None and item.id not in object_ids:
                continue
            if catalog:
                if item.catalog != catalog and not item.catalog.startswith(f"{catalog}/"):
                    continue
            if search:
                hay = f"{item.title} {item.catalog} {item.object_type} {item.status} {item.description}".lower()
                if search not in hay:
                    continue
            items.append(item)
        items.sort(
            key=lambda object_row: (
                normalize_object_category(object_row.catalog).lower(),
                object_row.title.lower(),
                object_row.id,
            )
        )

        self.beginResetModel()
        self._items = items
        self._rows = group_objects_by_category(items)
        self.endResetModel()


class ObjectCardDelegate(QStyledItemDelegate):
    ROW_H = 86

    C_BG = QColor("#171a20")
    C_BORDER = QColor("#2f333b")
    C_TEXT = QColor("#e6e6e6")
    C_MUTED = QColor("#9aa0a6")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._font_title = QFont()
        self._font_title.setPointSize(10)
        self._font_title.setBold(True)

        self._font_meta = QFont()
        self._font_meta.setPointSize(9)

        self._font_desc = QFont()
        self._font_desc.setPointSize(9)

    def sizeHint(self, option, index):
        if index.data(ObjectRoles.RowType) == "category":
            return QSize(option.rect.width(), 30)
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        painter.save()
        row_type = index.data(ObjectRoles.RowType)
        if row_type == "category":
            rect = option.rect.adjusted(10, 3, -10, -3)
            title = (index.data(ObjectRoles.Title) or "").strip() or "Без каталога"
            font = QFont(option.font)
            font.setPointSize(max(8, font.pointSize() - 1))
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#8d939b"))
            painter.drawText(rect.adjusted(4, 0, -4, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, title)
            painter.setPen(QColor("#30333a"))
            painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
            painter.restore()
            return

        rect = option.rect.adjusted(8, 4, -8, -4)
        radius = 10

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.C_BG)
        if option.state & QStyle.StateFlag.State_Selected:
            bg = QColor("#232833")
        painter.setBrush(bg)
        painter.setPen(self.C_BORDER)
        painter.drawRoundedRect(rect, radius, radius)

        title = index.data(ObjectRoles.Title) or ""
        catalog = index.data(ObjectRoles.Catalog) or ""
        object_type = index.data(ObjectRoles.ObjectType) or ""
        status = index.data(ObjectRoles.Status) or ""
        description = index.data(ObjectRoles.Description) or ""

        x = rect.x() + 14
        y = rect.y() + 10
        w = rect.width() - 28

        painter.setPen(self.C_TEXT)
        painter.setFont(self._font_title)
        title_metrics = QFontMetrics(self._font_title)
        title_text = title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, w)
        painter.drawText(QRect(x, y, w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title_text)

        meta_y = y + 24
        painter.setFont(self._font_meta)
        painter.setPen(self.C_MUTED)
        meta_parts = [part for part in [catalog, object_type, status] if part]
        meta_text = " · ".join(meta_parts) if meta_parts else "Без каталога"
        meta_metrics = QFontMetrics(self._font_meta)
        meta_text = meta_metrics.elidedText(meta_text, Qt.TextElideMode.ElideRight, w)
        painter.drawText(QRect(x, meta_y, w, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, meta_text)

        desc_y = meta_y + 18
        painter.setFont(self._font_desc)
        painter.setPen(self.C_TEXT)
        desc_rect = QRect(x, desc_y, w, rect.height() - 38)
        desc_text = description.strip() or "Описание пока не добавлено."
        desc_metrics = QFontMetrics(self._font_desc)
        desc_text = desc_metrics.elidedText(desc_text.replace("\n", " "), Qt.TextElideMode.ElideRight, w * 2)
        painter.drawText(desc_rect, Qt.TextFlag.TextWordWrap, desc_text)

        painter.restore()


class ObjectEditDialog(QDialog):
    def __init__(self, parent=None, initial: Optional[ObjectRow] = None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._initial = initial
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
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
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
        self.list_widget.setViewMode(QListView.IconMode)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.setResizeMode(QListView.Adjust)
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


class ObjectWorkspace(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._db = get_database()
        self._csv_service = CsvTransferService()
        self._smooth_scroll_controllers: list[object] = []
        self._images: List[ObjectImageData] = []
        self._current_image_index = 0
        self._current_object_id: Optional[int] = None
        self._build_ui()
        self._refresh_catalogs()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Объекты")
        title.setObjectName("ObjectsTitle")
        header.addWidget(title)

        header.addStretch(1)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по объектам...")
        self.search_edit.textChanged.connect(self._on_search)
        self.search_edit.setObjectName("ObjectsSearch")

        self.add_button = QToolButton()
        self.add_button.setText("Добавить объект")
        self.add_button.setObjectName("ObjectsAddButton")
        self.add_button.clicked.connect(self._add_object)
        self.export_button = QToolButton()
        self.export_button.setText("Экспорт")
        self.export_button.setObjectName("ObjectsExportButton")
        self.export_button.clicked.connect(self._export_objects_csv)
        self.import_button = QToolButton()
        self.import_button.setText("Импорт")
        self.import_button.setObjectName("ObjectsImportButton")
        self.import_button.clicked.connect(self._import_objects_csv)

        header.addWidget(self.search_edit)
        header.addWidget(self.add_button)
        header.addWidget(self.export_button)
        header.addWidget(self.import_button)

        layout.addLayout(header)

        quick_row = QFrame()
        quick_row.setObjectName("ObjectsQuickRow")
        quick_layout = QHBoxLayout(quick_row)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(6)
        self.quick_catalog_btn = QToolButton()
        self.quick_catalog_btn.setText("Категория")
        self.quick_catalog_btn.setObjectName("ObjectsQuickCatalogBtn")
        self.quick_catalog_label = QLabel("Все категории")
        self.quick_catalog_label.setObjectName("ObjectsQuickCatalog")
        self.quick_catalog_label.setStyleSheet("color:#9ea3ac; font-size:11px;")
        self.quick_title_input = QLineEdit()
        self.quick_title_input.setObjectName("ObjectsQuickTitle")
        self.quick_title_input.setPlaceholderText("Быстрое создание объекта...")
        self.quick_create_btn = QToolButton()
        self.quick_create_btn.setText("Создать")
        self.quick_create_btn.setObjectName("ObjectsQuickCreateBtn")
        quick_layout.addWidget(self.quick_catalog_btn)
        quick_layout.addWidget(self.quick_catalog_label)
        quick_layout.addWidget(self.quick_title_input, 1)
        quick_layout.addWidget(self.quick_create_btn)
        layout.addWidget(quick_row)

        self.splitter = QSplitter()
        self.splitter.setObjectName("ObjectsSplitter")

        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setObjectName("ObjectsCatalogs")
        self.catalog_tree.setHeaderHidden(True)
        self.catalog_tree.setFixedWidth(220)
        self.catalog_tree.itemSelectionChanged.connect(self._on_catalog_selected)

        self.model = ObjectsModel(self)
        self.card_list = QListView()
        self.card_list.setObjectName("ObjectsCards")
        self.card_list.setModel(self.model)
        self.card_list.setItemDelegate(ObjectCardDelegate(self.card_list))
        self.card_list.setSelectionMode(QListView.SingleSelection)
        self.card_list.setViewMode(QListView.ListMode)
        self.card_list.setResizeMode(QListView.Adjust)
        self.card_list.setUniformItemSizes(False)
        self.card_list.setSpacing(4)
        self.card_list.selectionModel().currentChanged.connect(self._on_object_selected)

        self.details_panel = QWidget()
        self.details_panel.setObjectName("ObjectsDetails")
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(16, 16, 16, 16)
        details_layout.setSpacing(12)

        self.details_title = QLabel("Выберите объект")
        self.details_title.setObjectName("ObjectsDetailsTitle")

        self.details_meta = QLabel("")
        self.details_meta.setObjectName("ObjectsDetailsMeta")

        self.details_description = QLabel("")
        self.details_description.setWordWrap(True)
        self.details_description.setObjectName("ObjectsDetailsDescription")

        buttons_row = QHBoxLayout()
        self.edit_button = QToolButton()
        self.edit_button.setText("Редактировать")
        self.edit_button.clicked.connect(self._edit_current_object)
        self.edit_button.setObjectName("ObjectsEditButton")

        self.delete_button = QToolButton()
        self.delete_button.setText("Удалить")
        self.delete_button.clicked.connect(self._delete_current_object)
        self.delete_button.setObjectName("ObjectsDeleteButton")

        self.attach_button = QToolButton()
        self.attach_button.setText("Добавить изображения")
        self.attach_button.clicked.connect(self._attach_images)
        self.attach_button.setObjectName("ObjectsAttachButton")

        buttons_row.addWidget(self.edit_button)
        buttons_row.addWidget(self.attach_button)
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.delete_button)

        self.image_frame = QFrame()
        self.image_frame.setObjectName("ObjectsImageFrame")
        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(12, 12, 12, 12)
        image_layout.setSpacing(8)

        nav_row = QHBoxLayout()
        self.prev_button = QToolButton()
        self.prev_button.setText("←")
        self.prev_button.clicked.connect(self._prev_image)
        self.next_button = QToolButton()
        self.next_button.setText("→")
        self.next_button.clicked.connect(self._next_image)
        self.image_counter = QLabel("0/0")
        self.preview_button = QToolButton()
        self.preview_button.setText("Просмотр")
        self.preview_button.clicked.connect(self._preview_image)

        nav_row.addWidget(self.prev_button)
        nav_row.addWidget(self.next_button)
        nav_row.addStretch(1)
        nav_row.addWidget(self.image_counter)
        nav_row.addWidget(self.preview_button)

        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setObjectName("ObjectsImageThumbnails")
        self.thumbnail_list.setViewMode(QListView.IconMode)
        self.thumbnail_list.setFlow(QListView.LeftToRight)
        self.thumbnail_list.setResizeMode(QListView.Adjust)
        self.thumbnail_list.setMovement(QListView.Static)
        self.thumbnail_list.setIconSize(QSize(64, 64))
        self.thumbnail_list.setGridSize(QSize(78, 78))
        self.thumbnail_list.setFixedHeight(92)
        self.thumbnail_list.setSpacing(6)
        self.thumbnail_list.setSelectionMode(QListWidget.SingleSelection)
        self.thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)

        self.image_label = QLabel("Нет изображений")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(220)
        self.image_label.setObjectName("ObjectsImage")

        self.image_comment = QPlainTextEdit()
        self.image_comment.setObjectName("ObjectsImageComment")
        self.image_comment.setPlaceholderText("Комментарий к изображению...")
        self.save_comment_button = QToolButton()
        self.save_comment_button.setText("Сохранить описание")
        self.save_comment_button.setObjectName("ObjectsImageCommentButton")
        self.save_comment_button.clicked.connect(self._save_image_comment)

        image_layout.addLayout(nav_row)
        image_layout.addWidget(self.thumbnail_list)
        image_layout.addWidget(self.image_label)
        image_layout.addWidget(self.image_comment)
        image_layout.addWidget(self.save_comment_button, 0, Qt.AlignmentFlag.AlignRight)

        details_layout.addWidget(self.details_title)
        details_layout.addWidget(self.details_meta)
        details_layout.addWidget(self.details_description)
        details_layout.addLayout(buttons_row)
        details_layout.addWidget(self.image_frame)
        details_layout.addStretch(1)

        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.card_list)
        right_splitter.addWidget(self.details_panel)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 2)

        self.splitter.addWidget(self.catalog_tree)
        self.splitter.addWidget(right_splitter)
        self.splitter.setStretchFactor(1, 1)

        layout.addWidget(self.splitter, 1)
        self._smooth_scroll_controllers = [
            attach_smooth_scroll(self.catalog_tree),
            attach_smooth_scroll(self.card_list),
            attach_smooth_scroll(self.thumbnail_list),
            attach_smooth_scroll(self.image_comment),
        ]
        self.quick_create_btn.clicked.connect(self._create_object_from_quick_form)
        self.quick_catalog_btn.clicked.connect(self._open_quick_catalog_menu)
        self.quick_title_input.returnPressed.connect(self._create_object_from_quick_form)
        self._set_quick_catalog(None)

        self._apply_styles()
        self._update_action_state(False)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QLabel#ObjectsTitle {
                color: #e6e6e6;
                font-size: 20px;
                font-weight: 600;
            }
            QLineEdit#ObjectsSearch,
            QLineEdit#ObjectsQuickTitle {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 10px;
                color: #e6e6e6;
            }
            QLineEdit#ObjectsSearch { min-width: 240px; }
            QToolButton#ObjectsAddButton,
            QToolButton#ObjectsExportButton,
            QToolButton#ObjectsImportButton,
            QToolButton#ObjectsEditButton,
            QToolButton#ObjectsDeleteButton,
            QToolButton#ObjectsAttachButton,
            QToolButton#ObjectsImageCommentButton {
                background: #232831;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px 12px;
                color: #e6e6e6;
            }
            QToolButton#ObjectsDeleteButton {
                background: #3a2323;
                border-color: #4b2b2b;
            }
            QTreeWidget#ObjectsCatalogs {
                background: #171a20;
                border: 1px solid #2f333b;
                border-radius: 10px;
                color: #e6e6e6;
                padding: 6px;
            }
            QTreeWidget#ObjectsCatalogs::item {
                padding: 8px 6px;
                border-radius: 6px;
            }
            QTreeWidget#ObjectsCatalogs::item:selected {
                background: #2d3440;
            }
            QListView#ObjectsCards {
                background: #14171c;
                border: 1px solid #2f333b;
                border-radius: 12px;
            }
            QWidget#ObjectsDetails {
                background: #171a20;
                border: 1px solid #2f333b;
                border-radius: 12px;
            }
            QLabel#ObjectsDetailsTitle {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#ObjectsDetailsMeta {
                color: #9aa0a6;
                font-size: 11px;
            }
            QLabel#ObjectsDetailsDescription {
                color: #d0d4da;
                font-size: 12px;
            }
            QFrame#ObjectsImageFrame {
                background: #1c2027;
                border: 1px solid #2f333b;
                border-radius: 10px;
            }
            QLabel#ObjectsImage {
                background: #111318;
                border: 1px dashed #2f333b;
                border-radius: 8px;
                color: #7d8590;
            }
            QListWidget#ObjectsImageThumbnails {
                background: #111318;
                border: 1px solid #2f333b;
                border-radius: 8px;
            }
            QListWidget#ObjectsImageThumbnails::item {
                padding: 4px;
            }
            QListWidget#ObjectsImageThumbnails::item:selected {
                background: #2d3440;
                border-radius: 6px;
            }
            QPlainTextEdit#ObjectsImageComment {
                background: #1f232a;
                border: 1px solid #2f333b;
                border-radius: 6px;
                padding: 6px;
                color: #e6e6e6;
            }
            """
        )

    def _refresh_catalogs(self) -> None:
        current = self.catalog_tree.currentItem()
        current_name = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.catalog_tree.clear()

        root = QTreeWidgetItem(["Все объекты"])
        root.setData(0, Qt.ItemDataRole.UserRole, None)
        self.catalog_tree.addTopLevelItem(root)

        tree_items: dict[tuple[str, ...], QTreeWidgetItem] = {(): root}
        for catalog in self.model.catalogs():
            parts = [part.strip() for part in catalog.split("/") if part.strip()]
            parent_key: tuple[str, ...] = ()
            for part in parts:
                key = parent_key + (part,)
                item = tree_items.get(key)
                if item is None:
                    parent = tree_items[parent_key]
                    item = QTreeWidgetItem([part])
                    item.setData(0, Qt.ItemDataRole.UserRole, "/".join(key))
                    parent.addChild(item)
                    tree_items[key] = item
                parent_key = key

        root.setExpanded(True)
        if current_name is None:
            self.catalog_tree.setCurrentItem(root)
            return

        for item in tree_items.values():
            if item.data(0, Qt.ItemDataRole.UserRole) == current_name:
                self.catalog_tree.setCurrentItem(item)
                return

        self.catalog_tree.setCurrentItem(root)

    def refresh_objects(self) -> None:
        current_id = self._current_object_id
        self.model.reload()
        self._refresh_catalogs()
        if current_id is None:
            self._update_action_state(False)
            return
        row = self.model.row_for_object_id(current_id)
        if row is None:
            self._update_action_state(False)
            return
        index = self.model.index(row)
        if index.isValid():
            self.card_list.setCurrentIndex(index)

    def set_project_filter(self, project_id: Optional[int]) -> None:
        self.model.set_project_filter(project_id)

    def set_task_filter(self, task_id: Optional[int]) -> None:
        self.model.set_task_filter(task_id)

    def set_marker_filter(self, marker_id: Optional[int]) -> None:
        self.model.set_marker_filter(marker_id)

    def _export_objects_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Objects",
            "objects_export.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        rows = export_objects_rows(self._db.fetch_objects())
        if not rows:
            QMessageBox.information(self, "Объекты", "Нет данных для экспорта.")
            return
        try:
            self._csv_service.export_to_file(path, rows, fieldnames=OBJECTS_CSV_FIELDS)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Объекты", f"Ошибка экспорта: {exc}")
            return
        QMessageBox.information(self, "Объекты", "Экспорт завершен.")

    def _import_objects_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Objects",
            "",
            "CSV (*.csv)",
        )
        if not path:
            return
        try:
            rows = self._csv_service.import_from_file(path)
        except CsvTransferError as exc:
            QMessageBox.warning(self, "Объекты", f"Ошибка импорта: {exc}")
            return
        result = import_objects_rows(self._db, rows)
        self.refresh_objects()
        QMessageBox.information(
            self,
            "Объекты",
            f"Импорт завершен: {result.imported}, пропущено: {result.skipped}.",
        )

    def _on_search(self, text: str) -> None:
        self.model.set_search(text)

    def _on_catalog_selected(self) -> None:
        item = self.catalog_tree.currentItem()
        catalog = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        self.model.set_catalog_filter(catalog)
        self._set_quick_catalog(catalog if isinstance(catalog, str) else None)

    def _on_object_selected(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            self._current_object_id = None
            self._update_action_state(False)
            return
        obj = self.model.object_at(current.row())
        if not obj:
            self._current_object_id = None
            self._update_action_state(False)
            return
        self._current_object_id = obj.id
        self.details_title.setText(obj.title)
        meta_parts = [part for part in [obj.catalog, obj.object_type, obj.status] if part]
        self.details_meta.setText(" · ".join(meta_parts) if meta_parts else "Без каталога")
        self.details_description.setText(obj.description or "Описание не заполнено.")
        self._load_images(obj.id)
        self._update_action_state(True)

    def _update_action_state(self, enabled: bool) -> None:
        self.edit_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)
        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.image_comment.setEnabled(enabled)
        self.save_comment_button.setEnabled(enabled)
        self.thumbnail_list.setEnabled(enabled)
        if not enabled:
            self.details_title.setText("Выберите объект")
            self.details_meta.setText("")
            self.details_description.setText("")
            self.image_label.setText("Нет изображений")
            self.image_counter.setText("0/0")
            self.image_comment.setPlainText("")
            self.thumbnail_list.clear()

    def _set_quick_catalog(self, catalog: Optional[str]) -> None:
        normalized = (catalog or "").strip()
        if not normalized:
            self.quick_catalog_label.setText("Все категории")
            self.quick_catalog_label.setProperty("quick_catalog", None)
            return
        self.quick_catalog_label.setText(normalized)
        self.quick_catalog_label.setProperty("quick_catalog", normalized)

    def _open_quick_catalog_menu(self) -> None:
        menu = QMenu(self)
        action_all = menu.addAction("Все категории")
        menu.addSeparator()
        actions: Dict[Any, str] = {}
        for catalog in self.model.catalogs():
            action = menu.addAction(catalog)
            actions[action] = catalog
        chosen = menu.exec(self.quick_catalog_btn.mapToGlobal(self.quick_catalog_btn.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen == action_all:
            self._select_catalog_tree_item(None)
            return
        catalog = actions.get(chosen)
        if catalog is None:
            return
        self._select_catalog_tree_item(catalog)

    def _select_catalog_tree_item(self, catalog: Optional[str]) -> None:
        stack: List[QTreeWidgetItem] = [self.catalog_tree.topLevelItem(i) for i in range(self.catalog_tree.topLevelItemCount())]
        while stack:
            item = stack.pop(0)
            if item is None:
                continue
            if item.data(0, Qt.ItemDataRole.UserRole) == catalog:
                self.catalog_tree.setCurrentItem(item)
                return
            for idx in range(item.childCount()):
                stack.append(item.child(idx))

    def _create_object_from_quick_form(self) -> None:
        title = (self.quick_title_input.text() or "").strip() or "Новый объект"
        quick_catalog = self.quick_catalog_label.property("quick_catalog")
        catalog = quick_catalog if isinstance(quick_catalog, str) else ""
        try:
            obj = self._db.create_object(
                title=title,
                catalog=catalog,
                object_type="",
                status="",
                description="",
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.add_object(obj)
        self._refresh_catalogs()
        row = self.model.row_for_object_id(obj.id)
        if row is not None:
            index = self.model.index(row)
            if index.isValid():
                self.card_list.setCurrentIndex(index)
        self.quick_title_input.clear()

    def _add_object(self) -> None:
        dialog = ObjectEditDialog(self)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            obj = self._db.create_object(**values)
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.add_object(obj)
        self._refresh_catalogs()

    def _edit_current_object(self) -> None:
        current = self.card_list.currentIndex()
        if not current.isValid():
            return
        obj = self.model.object_at(current.row())
        if not obj:
            return
        dialog = ObjectEditDialog(self, initial=obj)
        if show_dialog_standard(dialog, self) != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            updated = self._db.update_object(obj.id, **values)
        except ValueError as exc:
            QMessageBox.warning(self, "Объекты", str(exc))
            return
        self.model.update_object(updated)
        self._refresh_catalogs()
        self.details_title.setText(updated.title)
        self.details_meta.setText(" · ".join(part for part in [updated.catalog, updated.object_type, updated.status] if part))
        self.details_description.setText(updated.description or "Описание не заполнено.")

    def _delete_current_object(self) -> None:
        current = self.card_list.currentIndex()
        if not current.isValid():
            return
        obj = self.model.object_at(current.row())
        if not obj:
            return
        confirm = QMessageBox.question(
            self,
            "Удаление",
            "Удалить объект и все связанные изображения?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self._db.delete_object(obj.id)
        self.model.delete_object(obj.id)
        self._refresh_catalogs()
        self._update_action_state(False)

    def _attach_images(self) -> None:
        if self._current_object_id is None:
            return
        dialog = CloudImagePickerDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rel_paths = dialog.selected_rel_paths()
        for rel_path in rel_paths:
            try:
                self._db.add_object_image(self._current_object_id, rel_path)
            except ValueError:
                continue
        self._load_images(self._current_object_id)

    def _load_images(self, object_id: int) -> None:
        self._images = self._db.fetch_object_images(object_id)
        self._current_image_index = 0
        self._refresh_thumbnails()
        self._update_image_view()

    def _refresh_thumbnails(self) -> None:
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.clear()
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        for idx, image in enumerate(self._images):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, idx)
            item.setToolTip(image.rel_path)
            if cloud_root:
                file_path = Path(cloud_root) / image.rel_path
                pixmap = _load_scaled_pixmap(file_path, self.thumbnail_list.iconSize())
                if not pixmap.isNull():
                    item.setIcon(pixmap)
            self.thumbnail_list.addItem(item)
        self.thumbnail_list.setEnabled(bool(self._images))
        if self._images:
            self.thumbnail_list.setCurrentRow(self._current_image_index)
        self.thumbnail_list.blockSignals(False)

    def _update_image_view(self) -> None:
        total = len(self._images)
        if total == 0:
            self.image_label.setText("Нет изображений")
            self.image_label.setPixmap(QPixmap())
            self.image_counter.setText("0/0")
            self.image_comment.setPlainText("")
            return

        self._current_image_index = max(0, min(self._current_image_index, total - 1))
        image = self._images[self._current_image_index]
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        pixmap = QPixmap()
        if cloud_root:
            file_path = Path(cloud_root) / image.rel_path
            target_size = self.image_label.size()
            if not target_size.isValid() or target_size.width() < 10:
                target_size = QSize(720, 420)
            pixmap = _load_scaled_pixmap(file_path, target_size)
        if pixmap.isNull():
            self.image_label.setText("Изображение недоступно")
            self.image_label.setPixmap(QPixmap())
        else:
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
        self.image_counter.setText(f"{self._current_image_index + 1}/{total}")
        self.image_comment.setPlainText(image.description)
        self.thumbnail_list.blockSignals(True)
        self.thumbnail_list.setCurrentRow(self._current_image_index)
        self.thumbnail_list.blockSignals(False)

    def _prev_image(self) -> None:
        if not self._images:
            return
        self._current_image_index = max(0, self._current_image_index - 1)
        self._update_image_view()

    def _next_image(self) -> None:
        if not self._images:
            return
        self._current_image_index = min(len(self._images) - 1, self._current_image_index + 1)
        self._update_image_view()

    def _save_image_comment(self) -> None:
        if not self._images:
            return
        image = self._images[self._current_image_index]
        text = self.image_comment.toPlainText()
        updated = self._db.update_object_image(image.id, text)
        self._images[self._current_image_index] = updated

    def _on_thumbnail_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._images):
            return
        self._current_image_index = row
        self._update_image_view()

    def _preview_image(self) -> None:
        if not self._images:
            return
        image = self._images[self._current_image_index]
        cloud_root = self._db.get_setting("cloud_storage_path", default="").strip()
        if not cloud_root:
            return
        file_path = Path(cloud_root) / image.rel_path
        if not file_path.is_file():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(image.rel_path)
        dialog.setMinimumSize(800, 600)
        layout = QVBoxLayout(dialog)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = _load_scaled_pixmap(file_path, QSize(760, 540))
        if not pixmap.isNull():
            label.setPixmap(pixmap)
        layout.addWidget(label)
        dialog.exec()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._images:
            self._update_image_view()


def _load_scaled_pixmap(file_path: Path, size: QSize) -> QPixmap:
    if not file_path.is_file():
        return QPixmap()
    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)
    if size.isValid():
        reader.setScaledSize(size)
    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)


def extract_text_from_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return _read_text_file(file_path)
    if suffix == ".docx":
        return _read_docx(file_path)
    if suffix == ".doc":
        return _read_doc_binary(file_path)
    return ""


def _read_text_file(file_path: Path) -> str:
    for encoding in ("utf-8", "cp1251", "latin-1"):
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, OSError):
            continue
    try:
        return file_path.read_text(errors="ignore")
    except OSError:
        return ""


def _read_docx(file_path: Path) -> str:
    try:
        with zipfile.ZipFile(file_path) as archive:
            data = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, OSError):
        return ""
    xml_text = data.decode("utf-8", errors="ignore")
    xml_text = xml_text.replace("</w:p>", "\n")
    xml_text = re.sub(r"<[^>]+>", " ", xml_text)
    xml_text = html.unescape(xml_text)
    return _clean_extracted_text(xml_text)


def _read_doc_binary(file_path: Path) -> str:
    try:
        data = file_path.read_bytes()
    except OSError:
        return ""
    text_candidates = []
    for encoding in ("utf-8", "cp1251", "latin-1"):
        decoded = data.decode(encoding, errors="ignore")
        text_candidates.append(decoded)
    best = max(text_candidates, key=_score_text)
    return _clean_extracted_text(best)


def _score_text(text: str) -> int:
    return len(re.findall(r"[A-Za-zА-Яа-я0-9]", text))


def _clean_extracted_text(text: str) -> str:
    cleaned = re.sub(r"[^\S\n]+", " ", text)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    cleaned = cleaned.replace("\x00", " ")
    return cleaned.strip()
